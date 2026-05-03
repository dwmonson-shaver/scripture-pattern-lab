"""Bulk loader for CorpusToken records via SQLAlchemy 2.0 Core.

A single transaction wraps the entire load. Rows are inserted in 1000-row
batches via ``connection.execute(insert(tokens_table), batch)``. SQLAlchemy
errors are NOT wrapped — bare exceptions surface to the caller per design
decision #10.

An optional ``progress_callback`` lets callers observe per-batch, per-file-
boundary, and end-of-load events without the loader owning a logger.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, insert

from src.ingestion.corpus_parser import CorpusToken
from src.ingestion.db import tokens_table

BATCH_SIZE: int = 1000


class ProgressEvent(BaseModel):
    """Observability event emitted by ``load_tokens`` via an optional callback."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["batch", "file_boundary", "done"]
    book: str | None
    tokens_loaded: int


ProgressCallback = Callable[[ProgressEvent], None]


def load_tokens(
    engine: Engine,
    tokens: Iterable[CorpusToken],
    *,
    progress_callback: ProgressCallback | None = None,
) -> int:
    """Insert CorpusToken records into the ``tokens`` table.

    Returns the count of rows inserted. The whole load runs in one transaction:
    ``engine.begin()`` commits on success and rolls back on exception.

    If ``progress_callback`` is supplied, it is invoked with a ProgressEvent at
    every file boundary (when ``token.book`` changes between consecutive tokens,
    including the very first token), at every batch flush, and once at the end
    after the transaction commits. ``tokens_loaded`` is the count already
    committed at the moment of emission — file-boundary events therefore report
    the count *before* the new book's tokens are inserted.
    """
    inserted = 0
    batch: list[dict] = []
    last_book: str | None = None
    with engine.begin() as connection:
        for token in tokens:
            if token.book != last_book:
                if progress_callback is not None:
                    progress_callback(
                        ProgressEvent(
                            kind="file_boundary",
                            book=token.book,
                            tokens_loaded=inserted,
                        )
                    )
                last_book = token.book
            batch.append(token.model_dump())
            if len(batch) >= BATCH_SIZE:
                connection.execute(insert(tokens_table), batch)
                inserted += len(batch)
                batch = []
                if progress_callback is not None:
                    progress_callback(
                        ProgressEvent(
                            kind="batch",
                            book=None,
                            tokens_loaded=inserted,
                        )
                    )
        if batch:
            connection.execute(insert(tokens_table), batch)
            inserted += len(batch)
            if progress_callback is not None:
                progress_callback(
                    ProgressEvent(
                        kind="batch",
                        book=None,
                        tokens_loaded=inserted,
                    )
                )
    if progress_callback is not None:
        progress_callback(
            ProgressEvent(kind="done", book=None, tokens_loaded=inserted)
        )
    return inserted
