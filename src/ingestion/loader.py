"""Bulk loader for CorpusToken records via SQLAlchemy 2.0 Core.

A single transaction wraps the entire load. Rows are inserted in 1000-row
batches via ``connection.execute(insert(tokens_table), batch)``. SQLAlchemy
errors are NOT wrapped — bare exceptions surface to the caller per design
decision #10.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Engine, insert

from src.ingestion.corpus_parser import CorpusToken
from src.ingestion.db import tokens_table

BATCH_SIZE: int = 1000


def load_tokens(engine: Engine, tokens: Iterable[CorpusToken]) -> int:
    """Insert CorpusToken records into the ``tokens`` table.

    Returns the count of rows inserted. The whole load runs in one transaction:
    ``engine.begin()`` commits on success and rolls back on exception.
    """
    inserted = 0
    batch: list[dict] = []
    with engine.begin() as connection:
        for token in tokens:
            batch.append(token.model_dump())
            if len(batch) >= BATCH_SIZE:
                connection.execute(insert(tokens_table), batch)
                inserted += len(batch)
                batch = []
        if batch:
            connection.execute(insert(tokens_table), batch)
            inserted += len(batch)
    return inserted
