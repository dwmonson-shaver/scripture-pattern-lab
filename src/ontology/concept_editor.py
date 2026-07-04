"""Human-authored concept create/edit writes (Slice 1, DEC-130/146/147).

This is the write path behind the reader's concept library: a human creating or
editing a concept while reading. It is SEPARATE from the read-only
``ConceptRegistry`` (which must stay read-only) and from the Tier-1 lexicon
auto-create path (``concept_writer.py``).

Human-created concepts are ``origin='curated'``, ``verification_state='unverified'``
(never auto-promoted — DEC-081/102). Authored display metadata (color, polarity,
opposite name) is written ONLY to the ``concepts`` authored columns; this module
NEVER writes ``polarity_claims`` or ``inverse_claims`` — those are the
evidence-grounded layer and must not be fed by authored UI input (DEC-146).
"""

from __future__ import annotations

from sqlalchemy import Engine, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.ontology.registry import Concept, Polarity, concepts_table

# Human-authored concepts are always curated + unverified. They are never
# auto-promoted; a curator promotion is a separate, evidence-gated path.
CURATED_ORIGIN = "curated"
CURATED_VSTATE = "unverified"


class ConceptExists(Exception):  # noqa: N818 — name parallels ConceptNotMapped
    """Raised when creating a concept whose name already exists."""


class ConceptNotFound(Exception):  # noqa: N818 — name parallels ConceptNotMapped
    """Raised when editing a concept that does not exist."""


def _row_to_concept(row: object) -> Concept:
    return Concept(
        id=row.id,  # type: ignore[attr-defined]
        name=row.name,  # type: ignore[attr-defined]
        description=row.description,  # type: ignore[attr-defined]
        origin=row.origin,  # type: ignore[attr-defined]
        verification_state=row.verification_state,  # type: ignore[attr-defined]
        authored_color=row.authored_color,  # type: ignore[attr-defined]
        authored_polarity=row.authored_polarity,  # type: ignore[attr-defined]
        authored_opposite_name=row.authored_opposite_name,  # type: ignore[attr-defined]
    )


_RETURNING = (
    concepts_table.c.id,
    concepts_table.c.name,
    concepts_table.c.description,
    concepts_table.c.origin,
    concepts_table.c.verification_state,
    concepts_table.c.authored_color,
    concepts_table.c.authored_polarity,
    concepts_table.c.authored_opposite_name,
)


def create_concept(
    engine: Engine,
    *,
    name: str,
    description: str | None = None,
    authored_color: str | None = None,
    authored_polarity: Polarity | None = None,
    authored_opposite_name: str | None = None,
) -> Concept:
    """Create a human-authored concept (curated, unverified).

    Raises ``ConceptExists`` if a concept with ``name`` already exists. Writes
    only the ``concepts`` row (incl. authored display columns) — never
    polarity_claims / inverse_claims (DEC-146).
    """
    with engine.begin() as connection:
        result = (
            connection.execute(
                pg_insert(concepts_table)
                .values(
                    name=name,
                    description=description,
                    origin=CURATED_ORIGIN,
                    verification_state=CURATED_VSTATE,
                    authored_color=authored_color,
                    authored_polarity=authored_polarity,
                    authored_opposite_name=authored_opposite_name,
                )
                .on_conflict_do_nothing(index_elements=["name"])
                .returning(*_RETURNING)
            )
        ).first()
        if result is None:
            raise ConceptExists(f"concept {name!r} already exists")
        return _row_to_concept(result)


# Sentinel so callers can distinguish "set to NULL" from "leave unchanged".
_UNSET = object()


def update_concept(
    engine: Engine,
    name: str,
    *,
    description: object = _UNSET,
    authored_color: object = _UNSET,
    authored_polarity: object = _UNSET,
    authored_opposite_name: object = _UNSET,
) -> Concept:
    """Update authored fields of an existing concept.

    Only the fields explicitly passed are changed (the ``_UNSET`` sentinel
    distinguishes "set to NULL" from "leave unchanged"). Never touches
    origin/verification_state (a human edit is not a promotion) and never writes
    polarity_claims / inverse_claims (DEC-146). Raises ``ConceptNotFound`` if no
    concept named ``name`` exists.
    """
    values: dict[str, object] = {}
    if description is not _UNSET:
        values["description"] = description
    if authored_color is not _UNSET:
        values["authored_color"] = authored_color
    if authored_polarity is not _UNSET:
        values["authored_polarity"] = authored_polarity
    if authored_opposite_name is not _UNSET:
        values["authored_opposite_name"] = authored_opposite_name

    with engine.begin() as connection:
        if not values:
            # No-op update: just read the row back (still 404 if absent).
            row = connection.execute(
                select(*_RETURNING).where(concepts_table.c.name == name)
            ).first()
        else:
            row = connection.execute(
                update(concepts_table)
                .where(concepts_table.c.name == name)
                .values(**values)
                .returning(*_RETURNING)
            ).first()
        if row is None:
            raise ConceptNotFound(f"concept {name!r} does not exist")
        return _row_to_concept(row)


def delete_concept(engine: Engine, name: str) -> None:
    """Delete a concept by name.

    Removal of a registry entry is removal of a PRIOR — the corpus is
    untouched, and a lexicon-sourced concept can be auto-recreated on demand
    (Slice N). Dependent rows are cleaned by the schema's ``ON DELETE CASCADE``
    FKs: concept_lemmas, polarity/inverse claims, the concept document,
    grouping promotions, and mark_concepts links. Marks themselves survive as
    plain highlights (the mark row is user work; only its concept association
    goes). Raises ``ConceptNotFound`` if no concept named ``name`` exists.
    """
    with engine.begin() as connection:
        row = connection.execute(
            delete(concepts_table)
            .where(concepts_table.c.name == name)
            .returning(concepts_table.c.id)
        ).first()
        if row is None:
            raise ConceptNotFound(f"concept {name!r} does not exist")
