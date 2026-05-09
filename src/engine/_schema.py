"""Private read-only SQLAlchemy mirror of the ``tokens`` table for the engine.

Per DEC-025 and ``docs/canonical/09_backend-service-boundaries.md`` §6, query-side
packages (including ``src/engine/``) MUST NOT import from ``src/ingestion/``. The
executor needs a typed handle on the ``tokens`` table to assemble SQL via
SQLAlchemy Core, so we mirror the column shape here in a private module that
only the engine imports.

This file is the engine's own mirror of ``data/schemas/01_tokens.sql`` — the SQL
file is canonical and authoritative; this Python definition and the parallel
mirror in ``src/ingestion/db.py`` are independent reflections of the same
canonical schema (the same pattern as ``src/ontology/registry.py`` mirroring
``02_concept_registry.sql`` separately from any ingestion mirror).

This module never issues DDL: no ``metadata.create_all`` is ever invoked, and
``_metadata`` is a separate ``MetaData`` instance from
``src/ingestion/db.py::metadata`` so the two mirrors cannot accidentally collide.
The leading underscore on the module name marks it as private — only
``src/engine/executor.py`` (and tests) should import from it.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, String, Table, Text

# Distinct MetaData instance — intentionally separate from the ingestion mirror
# so the two cannot accidentally cross-pollinate (e.g. via create_all on a
# shared MetaData). DDL is never issued from this module.
_metadata: MetaData = MetaData()

tokens_table: Table = Table(
    "tokens",
    _metadata,
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
