"""SQLAlchemy 2.0 Core binding for the translation tables.

Mirrors ``data/schemas/06_translations.sql`` for typing and Core-style inserts;
issues no DDL (the SQL file is canonical). A distinct ``MetaData`` instance from
the corpus binding, per the project's separate-reflection discipline.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Engine,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)

metadata: MetaData = MetaData()

translations_table: Table = Table(
    "translations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("code", String(16), nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("license", Text, nullable=True),
    Column("is_public_domain", Boolean, nullable=False, server_default="false"),
)

translation_verses_table: Table = Table(
    "translation_verses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "translation_id",
        Integer,
        ForeignKey("translations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("corpus_id", String(10), nullable=False, server_default="nt"),
    Column("book", String(10), nullable=False),
    Column("chapter", Integer, nullable=False),
    Column("verse", Integer, nullable=False),
    Column("text", Text, nullable=False),
    UniqueConstraint("translation_id", "corpus_id", "book", "chapter", "verse"),
)


def truncate_translations(engine: Engine) -> None:
    """Wipe both translation tables and reset identity counters.

    Destructive and irreversible; the caller (CLI) gates intent before calling.
    ``CASCADE`` handles the FK from translation_verses → translations.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE translation_verses, translations "
                "RESTART IDENTITY CASCADE"
            )
        )
