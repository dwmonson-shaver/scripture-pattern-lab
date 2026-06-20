"""Span-annotation (mark) writes + reads (Slice 1, DEC-129/143/145).

A mark is a span (char offsets into a named English version, plus a verse range
that may cross verses — DEC-143) tied to 0..n concepts. Concepts are referenced
by NAME at the API boundary (human-facing) and resolved to concept_id (FK) here.
A mark with no concepts is a plain highlight.

Lives in src/ontology alongside the concept tables it joins; takes an Engine and
opens its own transaction, mirroring concept_editor / concept_grouping.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Connection

from src.ontology.registry import concepts_table

# Mark + mark_concepts table mirrors. A dedicated MetaData keeps these from
# colliding with the registry's reflection (same discipline as the other
# bindings); the FK targets are expressed as plain integer columns since DDL is
# never issued from here.
metadata: MetaData = MetaData()

marks_table: Table = Table(
    "marks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("corpus_id", String(10), nullable=False, server_default="nt"),
    Column("book", String(10), nullable=False),
    Column("chapter", Integer, nullable=False),
    Column("verse_start", Integer, nullable=False),
    Column("verse_end", Integer, nullable=False),
    Column("char_start", Integer, nullable=False),
    Column("char_end", Integer, nullable=False),
    Column("version_code", String(16), nullable=False),
    Column("actor", Text, nullable=False, server_default="local"),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
)

mark_concepts_table: Table = Table(
    "mark_concepts",
    metadata,
    Column("mark_id", Integer, primary_key=True),
    Column("concept_id", Integer, primary_key=True),
)

DEFAULT_ACTOR = "local"


class UnknownConcept(Exception):  # noqa: N818 — name parallels ConceptNotMapped
    """Raised when a mark references a concept name that does not exist."""


class MarkNotFound(Exception):  # noqa: N818 — name parallels ConceptNotMapped
    """Raised when updating/deleting a mark id that does not exist."""


class Mark(BaseModel):
    """A span annotation with its associated concept names."""

    model_config = ConfigDict(frozen=True)

    id: int
    corpus_id: str
    book: str
    chapter: int
    verse_start: int
    verse_end: int
    char_start: int
    char_end: int
    version_code: str
    actor: str
    concept_names: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _resolve_concept_ids(
    connection: Connection, names: list[str]
) -> dict[str, int]:
    """Map concept names → ids; raise UnknownConcept if any name is missing."""
    if not names:
        return {}
    rows = connection.execute(
        select(concepts_table.c.id, concepts_table.c.name).where(
            concepts_table.c.name.in_(names)
        )
    ).all()
    found = {r.name: r.id for r in rows}
    missing = [n for n in names if n not in found]
    if missing:
        raise UnknownConcept(f"unknown concept name(s): {missing}")
    return found


def _names_for_mark(connection: Connection, mark_id: int) -> list[str]:
    rows = connection.execute(
        select(concepts_table.c.name)
        .select_from(
            mark_concepts_table.join(
                concepts_table,
                concepts_table.c.id == mark_concepts_table.c.concept_id,
            )
        )
        .where(mark_concepts_table.c.mark_id == mark_id)
        .order_by(concepts_table.c.name)
    ).all()
    return [r.name for r in rows]


def _load_mark(connection: Connection, mark_id: int) -> Mark:
    row = connection.execute(
        select(marks_table).where(marks_table.c.id == mark_id)
    ).first()
    if row is None:
        raise MarkNotFound(f"mark {mark_id} does not exist")
    return Mark(
        id=row.id,
        corpus_id=row.corpus_id,
        book=row.book,
        chapter=row.chapter,
        verse_start=row.verse_start,
        verse_end=row.verse_end,
        char_start=row.char_start,
        char_end=row.char_end,
        version_code=row.version_code,
        actor=row.actor,
        concept_names=_names_for_mark(connection, mark_id),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_mark(
    engine: Engine,
    *,
    corpus_id: str = "nt",
    book: str,
    chapter: int,
    verse_start: int,
    verse_end: int,
    char_start: int,
    char_end: int,
    version_code: str,
    concept_names: list[str] | None = None,
    actor: str = DEFAULT_ACTOR,
) -> Mark:
    """Create a span annotation and attach 0..n concepts (by name).

    Raises ``UnknownConcept`` if any concept name does not exist (all-or-nothing
    in one transaction). ``book`` is the 2-digit BB code; the caller normalizes.
    """
    names = concept_names or []
    with engine.begin() as connection:
        ids = _resolve_concept_ids(connection, names)
        mark_id = connection.execute(
            insert(marks_table)
            .values(
                corpus_id=corpus_id,
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                char_start=char_start,
                char_end=char_end,
                version_code=version_code,
                actor=actor,
            )
            .returning(marks_table.c.id)
        ).scalar_one()
        for cid in ids.values():
            connection.execute(
                insert(mark_concepts_table).values(
                    mark_id=mark_id, concept_id=cid
                )
            )
        return _load_mark(connection, mark_id)


def list_marks_for_chapter(
    engine: Engine,
    *,
    corpus_id: str,
    book: str,
    chapter: int,
    version_code: str,
) -> list[Mark]:
    """Return all marks for a chapter in one version, ordered by span start."""
    with engine.connect() as connection:
        rows = connection.execute(
            select(marks_table.c.id)
            .where(
                marks_table.c.corpus_id == corpus_id,
                marks_table.c.book == book,
                marks_table.c.chapter == chapter,
                marks_table.c.version_code == version_code,
            )
            .order_by(marks_table.c.verse_start, marks_table.c.char_start)
        ).all()
        return [_load_mark(connection, r.id) for r in rows]


# Sentinel so an update can leave the span / concept set untouched.
_UNSET = object()


def update_mark(
    engine: Engine,
    mark_id: int,
    *,
    verse_start: object = _UNSET,
    verse_end: object = _UNSET,
    char_start: object = _UNSET,
    char_end: object = _UNSET,
    concept_names: object = _UNSET,
) -> Mark:
    """Adjust a mark's span and/or replace its concept set.

    Span fields default to unchanged. When ``concept_names`` is provided it
    REPLACES the mark's concept set wholesale (the prototype's change/add flow
    sends the full set). Raises ``MarkNotFound`` if the mark is absent and
    ``UnknownConcept`` if a replacement name is unknown.
    """
    span_values: dict[str, object] = {}
    if verse_start is not _UNSET:
        span_values["verse_start"] = verse_start
    if verse_end is not _UNSET:
        span_values["verse_end"] = verse_end
    if char_start is not _UNSET:
        span_values["char_start"] = char_start
    if char_end is not _UNSET:
        span_values["char_end"] = char_end

    with engine.begin() as connection:
        exists = connection.execute(
            select(marks_table.c.id).where(marks_table.c.id == mark_id)
        ).first()
        if exists is None:
            raise MarkNotFound(f"mark {mark_id} does not exist")

        if span_values:
            span_values["updated_at"] = datetime.now().astimezone()
            connection.execute(
                update(marks_table)
                .where(marks_table.c.id == mark_id)
                .values(**span_values)
            )

        if concept_names is not _UNSET:
            names: list[str] = concept_names or []  # type: ignore[assignment]
            ids = _resolve_concept_ids(connection, names)
            connection.execute(
                delete(mark_concepts_table).where(
                    mark_concepts_table.c.mark_id == mark_id
                )
            )
            for cid in ids.values():
                connection.execute(
                    insert(mark_concepts_table).values(
                        mark_id=mark_id, concept_id=cid
                    )
                )

        return _load_mark(connection, mark_id)


def delete_mark(engine: Engine, mark_id: int) -> None:
    """Delete a mark (and its concept links via ON DELETE CASCADE).

    Raises ``MarkNotFound`` if no such mark exists.
    """
    with engine.begin() as connection:
        result = connection.execute(
            delete(marks_table).where(marks_table.c.id == mark_id)
        )
        if result.rowcount == 0:
            raise MarkNotFound(f"mark {mark_id} does not exist")
