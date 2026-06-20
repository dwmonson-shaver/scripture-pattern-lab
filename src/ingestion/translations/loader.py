"""Bulk loader for a single translation's verses via SQLAlchemy 2.0 Core.

One transaction wraps the whole load: the ``translations`` registry row is
upserted first (ON CONFLICT DO NOTHING on ``code``), then its verses are inserted
in 1000-row batches with ON CONFLICT DO NOTHING on the natural key — so a
re-run is idempotent. Mirrors ``src/ingestion/loader.py`` (corpus) and
``src/ingestion/lexicon/loader.py`` (ON CONFLICT) in shape.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.ingestion.translations.db import (
    translation_verses_table,
    translations_table,
)
from src.ingestion.translations.parser import TranslationVerse

BATCH_SIZE: int = 1000


class TranslationProgressEvent(BaseModel):
    """Observability event emitted by ``load_translation`` via a callback."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["registry", "batch", "done"]
    verses_loaded: int


TranslationProgressCallback = Callable[[TranslationProgressEvent], None]


def load_translation(
    engine: Engine,
    *,
    code: str,
    name: str,
    license: str | None,
    is_public_domain: bool,
    verses: Iterable[TranslationVerse],
    progress_callback: TranslationProgressCallback | None = None,
) -> int:
    """Upsert the translation registry row and insert its verses.

    Returns the count of verse rows submitted for insert (ON CONFLICT means the
    committed count may be lower on a re-run). Runs in one ``engine.begin()``
    transaction. Raises if the registry row cannot be resolved after upsert.
    """
    submitted = 0
    batch: list[dict] = []
    with engine.begin() as connection:
        connection.execute(
            pg_insert(translations_table)
            .values(
                code=code,
                name=name,
                license=license,
                is_public_domain=is_public_domain,
            )
            .on_conflict_do_nothing(index_elements=["code"])
        )
        translation_id = connection.execute(
            select(translations_table.c.id).where(
                translations_table.c.code == code
            )
        ).scalar_one()
        if progress_callback is not None:
            progress_callback(
                TranslationProgressEvent(kind="registry", verses_loaded=0)
            )

        def _flush() -> None:
            nonlocal submitted, batch
            if not batch:
                return
            connection.execute(
                pg_insert(translation_verses_table)
                .values(batch)
                .on_conflict_do_nothing(
                    index_elements=[
                        "translation_id",
                        "corpus_id",
                        "book",
                        "chapter",
                        "verse",
                    ]
                )
            )
            submitted += len(batch)
            batch = []
            if progress_callback is not None:
                progress_callback(
                    TranslationProgressEvent(
                        kind="batch", verses_loaded=submitted
                    )
                )

        for v in verses:
            row = v.model_dump()
            row["translation_id"] = translation_id
            batch.append(row)
            if len(batch) >= BATCH_SIZE:
                _flush()
        _flush()

    if progress_callback is not None:
        progress_callback(
            TranslationProgressEvent(kind="done", verses_loaded=submitted)
        )
    return submitted
