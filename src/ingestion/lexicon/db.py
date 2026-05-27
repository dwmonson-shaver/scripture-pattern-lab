"""SQLAlchemy 2.0 Core mirrors for the lexicon tables (Slice N).

`lemma_strongs_table` and `strongs_glosses_table` mirror
`data/schemas/03_lexicon.sql` column-for-column for typing and Core-style
inserts; this module never issues DDL and `metadata.create_all` is never called
(same discipline as `src/ingestion/db.py` and `src/ontology/registry.py`).

The `Engine` factory is reused from `src/ingestion/db.py` — there is exactly one
engine factory in the project (DEC-029 normalization lives there).
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)

metadata: MetaData = MetaData()

_SOURCE_CHECK = "source IN ('tbesg', 'dodson')"

lemma_strongs_table: Table = Table(
    "lemma_strongs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("morphgnt_lemma", Text, nullable=False),
    Column("strongs", String(12), nullable=False),
    UniqueConstraint("morphgnt_lemma", "strongs"),
)

strongs_glosses_table: Table = Table(
    "strongs_glosses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("strongs", String(12), nullable=False),
    Column("lemma", Text, nullable=True),
    Column("gloss", Text, nullable=False),
    Column("source", String(8), nullable=False),
    UniqueConstraint("strongs", "source", "gloss"),
    CheckConstraint(_SOURCE_CHECK),
)


def truncate_lexicon(engine: Engine) -> None:
    """Wipe both lexicon tables and reset their identity counters.

    Single FK-free ``TRUNCATE ... RESTART IDENTITY`` in a short-lived
    transaction. Destructive and irreversible; the caller is responsible for
    confirming intent (CLI flag + env var). Not self-gating (mirrors
    ``truncate_tokens`` per DEC-038).
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE lemma_strongs, strongs_glosses RESTART IDENTITY"
            )
        )
