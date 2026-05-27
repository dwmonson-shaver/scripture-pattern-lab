"""Bulk loader for the lexicon datasets via SQLAlchemy 2.0 Core (Slice N).

A single transaction wraps the entire load (mirrors ``src/ingestion/loader.py``
for the corpus). Rows are inserted in 1000-row batches with
``INSERT ... ON CONFLICT DO NOTHING`` so a partial load is a clean restart and
duplicate dataset rows (TBESG ships some) do not raise. An optional
``progress_callback`` reports per-dataset and per-batch progress without the
loader owning a logger.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.ingestion.lexicon.datasets import LemmaStrongs, StrongsGloss
from src.ingestion.lexicon.db import lemma_strongs_table, strongs_glosses_table

BATCH_SIZE: int = 1000


class LexiconProgressEvent(BaseModel):
    """Observability event emitted by ``load_lexicon`` via an optional callback."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["dataset_boundary", "batch", "done"]
    dataset: str | None
    rows_loaded: int


LexiconProgressCallback = Callable[[LexiconProgressEvent], None]


def _load_one(
    connection,  # type: ignore[no-untyped-def]
    table,  # type: ignore[no-untyped-def]
    rows: Iterable[BaseModel],
    index_elements: list[str],
    dataset: str,
    progress_callback: LexiconProgressCallback | None,
) -> int:
    """Insert one dataset's rows in batches; return rows inserted-or-skipped count.

    The returned count is the number of rows STREAMED (post-conflict count is
    not cheap to obtain per-batch); callers treat it as "rows processed".
    """
    if progress_callback is not None:
        progress_callback(
            LexiconProgressEvent(
                kind="dataset_boundary", dataset=dataset, rows_loaded=0
            )
        )
    processed = 0
    batch: list[dict] = []
    for row in rows:
        batch.append(row.model_dump())
        if len(batch) >= BATCH_SIZE:
            connection.execute(
                pg_insert(table)
                .values(batch)
                .on_conflict_do_nothing(index_elements=index_elements)
            )
            processed += len(batch)
            batch = []
            if progress_callback is not None:
                progress_callback(
                    LexiconProgressEvent(
                        kind="batch", dataset=dataset, rows_loaded=processed
                    )
                )
    if batch:
        connection.execute(
            pg_insert(table)
            .values(batch)
            .on_conflict_do_nothing(index_elements=index_elements)
        )
        processed += len(batch)
        if progress_callback is not None:
            progress_callback(
                LexiconProgressEvent(
                    kind="batch", dataset=dataset, rows_loaded=processed
                )
            )
    return processed


def load_lexicon(
    engine: Engine,
    *,
    lemma_strongs: Iterable[LemmaStrongs],
    tbesg_glosses: Iterable[StrongsGloss],
    dodson_glosses: Iterable[StrongsGloss],
    progress_callback: LexiconProgressCallback | None = None,
) -> dict[str, int]:
    """Load all three datasets into the lexicon tables in one transaction.

    Returns a per-table processed-row count map
    (``{"lemma_strongs": N, "strongs_glosses": M}``). The whole load runs in one
    ``engine.begin()`` so a mid-load failure rolls everything back. TBESG and
    Dodson both write ``strongs_glosses`` (deduped by the UNIQUE
    ``(strongs, source, gloss)`` constraint via ON CONFLICT DO NOTHING).
    """
    counts = {"lemma_strongs": 0, "strongs_glosses": 0}
    with engine.begin() as connection:
        counts["lemma_strongs"] += _load_one(
            connection,
            lemma_strongs_table,
            lemma_strongs,
            ["morphgnt_lemma", "strongs"],
            "jtauber",
            progress_callback,
        )
        counts["strongs_glosses"] += _load_one(
            connection,
            strongs_glosses_table,
            tbesg_glosses,
            ["strongs", "source", "gloss"],
            "tbesg",
            progress_callback,
        )
        counts["strongs_glosses"] += _load_one(
            connection,
            strongs_glosses_table,
            dodson_glosses,
            ["strongs", "source", "gloss"],
            "dodson",
            progress_callback,
        )
    if progress_callback is not None:
        progress_callback(
            LexiconProgressEvent(
                kind="done",
                dataset=None,
                rows_loaded=counts["lemma_strongs"] + counts["strongs_glosses"],
            )
        )
    return counts
