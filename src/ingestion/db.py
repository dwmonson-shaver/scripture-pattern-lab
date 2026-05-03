"""SQLAlchemy 2.0 Core binding for the corpus tokens table.

The `tokens_table` defined here mirrors `data/schemas/01_tokens.sql` for typing
and Core-style inserts; it does NOT issue DDL. The SQL file is canonical.
`metadata.create_all` is intentionally never called.
"""

from __future__ import annotations

import os

from sqlalchemy import Column, Engine, Integer, MetaData, String, Table, Text, create_engine, text

metadata: MetaData = MetaData()

tokens_table: Table = Table(
    "tokens",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("book", String(10), nullable=False),
    Column("chapter", Integer, nullable=False),
    Column("verse", Integer, nullable=False),
    Column("position", Integer, nullable=False),
    Column("global_position", Integer, nullable=False),
    Column("surface_form", Text, nullable=False),
    Column("normalized_form", Text, nullable=False),
    Column("lemma", Text, nullable=False),
    Column("morph_code", String(20), nullable=False),
    Column("pos", String(10), nullable=False),
    Column("language", String(5), default="grc"),
    Column("corpus_id", String(10), default="nt"),
)


def get_engine() -> Engine:
    """Return a SQLAlchemy 2.0 Engine bound to DATABASE_URL.

    Raises RuntimeError if DATABASE_URL is unset or empty — no fallback to a
    fake or local DB. Normalizes a bare ``postgresql://`` URL to
    ``postgresql+psycopg://`` so the project's psycopg3 driver is used instead
    of SQLAlchemy's default psycopg2 (which is not a project dependency).
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required (export it or set it in .env); "
            "ingestion has no fallback to a local DB."
        )
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return create_engine(url)


def truncate_tokens(engine: Engine) -> None:
    """Wipe the ``tokens`` table and reset its identity counter.

    Issues ``TRUNCATE TABLE tokens RESTART IDENTITY`` inside a short-lived
    transaction. This is destructive and irreversible; the caller is
    responsible for confirming intent (e.g. CLI flag + env var) before
    invoking. The function does not gate on its own.
    """
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE tokens RESTART IDENTITY"))
