"""Typed connections between concepts (Slice 2, 2026-07-05).

A connection is a HUMAN-AUTHORED hypothesis that two (later: n) concepts are
related. It is a prior, not a corpus-tested fact — it carries no
verification_state and is never auto-promoted. One edge can hold several typed
claims at once (multi-type: e.g. faith→hope may be both `sequence` and
`prerequisite`); each claim is its own row so it can grow evidence/notes later.
Directional claim types read member order from `position`; symmetric ones
(opposite/association/interchange/unknown) ignore it.

Concepts are referenced by NAME at the API boundary and resolved to concept_id
(FK) here. Lives in src/ontology alongside the concept tables it joins; takes an
Engine and opens its own transaction, mirroring concept_editor / marks.
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
)
from sqlalchemy.engine import Connection as SAConnection

from src.ontology.registry import concepts_table

# Dedicated MetaData so these mirrors don't collide with the registry's; FK
# targets are plain integer columns since DDL is never issued from here (the
# canonical schema is data/schemas/08_connections.sql).
metadata: MetaData = MetaData()

connections_table: Table = Table(
    "connections",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("note", Text),
    Column("actor", Text, nullable=False, server_default="local"),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
)

connection_members_table: Table = Table(
    "connection_members",
    metadata,
    Column("connection_id", Integer, primary_key=True),
    Column("concept_id", Integer, primary_key=True),
    Column("position", Integer, nullable=False),
)

connection_claims_table: Table = Table(
    "connection_claims",
    metadata,
    Column("connection_id", Integer, primary_key=True),
    Column("claim_type", String(20), primary_key=True),
    Column("note", Text),
    Column("created_at", DateTime(timezone=True)),
)

# The typed-claim vocabulary. Mirrors the CHECK in 08_connections.sql. Symmetric
# vs directional is a display/interpretation concern, not stored here — the whole
# set is valid on any connection; member order carries direction where it means
# something.
ALLOWED_CLAIM_TYPES: frozenset[str] = frozenset(
    {
        "opposite",
        "prerequisite",
        "produces",
        "sequence",
        "compound",
        "association",
        "interchange",
        "unknown",
    }
)

DEFAULT_ACTOR = "local"


class UnknownConcept(Exception):  # noqa: N818 — parallels marks.UnknownConcept
    """Raised when a connection references a concept name that does not exist."""


class ConnectionNotFound(Exception):  # noqa: N818 — parallels MarkNotFound
    """Raised when deleting a connection id that does not exist."""


class InvalidConnection(ValueError):  # noqa: N818 — a ValueError, not an *Error
    """Raised when a connection's members/types are structurally invalid."""


class Connection(BaseModel):
    """A typed connection between concepts, with its ordered members."""

    model_config = ConfigDict(frozen=True)

    id: int
    note: str | None
    actor: str
    members: list[str]  # concept names, in position order
    types: list[str]  # claim types, sorted
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _resolve_ordered_ids(
    connection: SAConnection, names: list[str]
) -> list[int]:
    """Resolve member names → ids, preserving the caller's order.

    Raises UnknownConcept if any name is missing.
    """
    rows = connection.execute(
        select(concepts_table.c.id, concepts_table.c.name).where(
            concepts_table.c.name.in_(names)
        )
    ).all()
    by_name = {r.name: r.id for r in rows}
    missing = [n for n in names if n not in by_name]
    if missing:
        raise UnknownConcept(f"unknown concept name(s): {missing}")
    return [by_name[n] for n in names]


def _load_connection(connection: SAConnection, conn_id: int) -> Connection:
    head = connection.execute(
        select(connections_table).where(connections_table.c.id == conn_id)
    ).first()
    if head is None:
        raise ConnectionNotFound(f"connection {conn_id} does not exist")
    member_rows = connection.execute(
        select(concepts_table.c.name)
        .select_from(
            connection_members_table.join(
                concepts_table,
                concepts_table.c.id == connection_members_table.c.concept_id,
            )
        )
        .where(connection_members_table.c.connection_id == conn_id)
        .order_by(connection_members_table.c.position)
    ).all()
    type_rows = connection.execute(
        select(connection_claims_table.c.claim_type)
        .where(connection_claims_table.c.connection_id == conn_id)
        .order_by(connection_claims_table.c.claim_type)
    ).all()
    return Connection(
        id=head.id,
        note=head.note,
        actor=head.actor,
        members=[r.name for r in member_rows],
        types=[r.claim_type for r in type_rows],
        created_at=head.created_at,
        updated_at=head.updated_at,
    )


def _validate(member_names: list[str], claim_types: list[str]) -> None:
    if len(member_names) < 2:
        raise InvalidConnection("a connection needs at least two concepts")
    if len(set(member_names)) != len(member_names):
        raise InvalidConnection("a connection's concepts must be distinct")
    if not claim_types:
        raise InvalidConnection("a connection needs at least one type")
    bad = [t for t in claim_types if t not in ALLOWED_CLAIM_TYPES]
    if bad:
        raise InvalidConnection(f"unknown connection type(s): {bad}")


def create_connection(
    engine: Engine,
    *,
    member_names: list[str],
    claim_types: list[str],
    note: str | None = None,
    actor: str = DEFAULT_ACTOR,
) -> Connection:
    """Create a human-authored connection between concepts.

    ``member_names`` is ordered (position 0, 1, ...); order carries direction for
    directional claim types. ``claim_types`` is the set of typed claims on the
    edge (at least one). Raises ``InvalidConnection`` on structural problems and
    ``UnknownConcept`` if a name is not in the registry.
    """
    _validate(member_names, claim_types)
    deduped_types = sorted(set(claim_types))
    with engine.begin() as connection:
        ids = _resolve_ordered_ids(connection, member_names)
        conn_id = connection.execute(
            insert(connections_table)
            .values(note=note, actor=actor)
            .returning(connections_table.c.id)
        ).scalar_one()
        connection.execute(
            insert(connection_members_table),
            [
                {"connection_id": conn_id, "concept_id": cid, "position": pos}
                for pos, cid in enumerate(ids)
            ],
        )
        connection.execute(
            insert(connection_claims_table),
            [
                {"connection_id": conn_id, "claim_type": t, "note": None}
                for t in deduped_types
            ],
        )
        return _load_connection(connection, conn_id)


def list_connections(engine: Engine) -> list[Connection]:
    """Return all connections (newest first), each with members + types."""
    with engine.begin() as connection:
        ids = connection.execute(
            select(connections_table.c.id).order_by(
                connections_table.c.id.desc()
            )
        ).scalars().all()
        return [_load_connection(connection, cid) for cid in ids]


def delete_connection(engine: Engine, connection_id: int) -> None:
    """Delete a connection (members + claims cascade). 404 if absent."""
    with engine.begin() as connection:
        row = connection.execute(
            delete(connections_table)
            .where(connections_table.c.id == connection_id)
            .returning(connections_table.c.id)
        ).first()
        if row is None:
            raise ConnectionNotFound(
                f"connection {connection_id} does not exist"
            )
