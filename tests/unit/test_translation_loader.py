"""Unit tests for src/ingestion/translations/loader.py — progress + batching.

A fake Engine whose ``begin()`` yields a connection that records statements and
returns a fixed translation_id for the registry-id SELECT. Real-DB exercise lives
in tests/integration/test_translation_ingest.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from src.ingestion.translations.loader import (
    BATCH_SIZE,
    TranslationProgressEvent,
    load_translation,
)
from src.ingestion.translations.parser import TranslationVerse


def _verse(n: int) -> TranslationVerse:
    return TranslationVerse(book="06", chapter=1, verse=n, text=f"v{n}")


class _Result:
    def __init__(self, scalar: object) -> None:
        self._scalar = scalar

    def scalar_one(self) -> object:
        return self._scalar


class _FakeConnection:
    """Records executed statements; the first SELECT returns translation_id=42."""

    def __init__(self) -> None:
        self.insert_calls: int = 0

    def execute(self, stmt: object) -> _Result:
        # The loader issues: pg_insert(translations) [no return used],
        # select(id).scalar_one(), then pg_insert(verses) batches.
        text_repr = str(stmt).lower()
        if text_repr.startswith("select"):
            return _Result(42)
        if "translation_verses" in text_repr:
            self.insert_calls += 1
        return _Result(None)


class _FakeEngine:
    def __init__(self) -> None:
        self.connection = _FakeConnection()

    @contextmanager
    def begin(self) -> Iterator[_FakeConnection]:
        yield self.connection


def test_returns_submitted_count_and_emits_events() -> None:
    engine = _FakeEngine()
    events: list[TranslationProgressEvent] = []
    n = BATCH_SIZE + 5  # forces two flushes
    count = load_translation(
        engine,  # type: ignore[arg-type]
        code="kjv",
        name="King James Version",
        license="Public Domain",
        is_public_domain=True,
        verses=(_verse(i) for i in range(1, n + 1)),
        progress_callback=events.append,
    )
    assert count == n
    kinds = [e.kind for e in events]
    assert kinds[0] == "registry"
    assert kinds[-1] == "done"
    assert kinds.count("batch") == 2  # full batch + trailing partial
    assert events[-1].verses_loaded == n
    assert engine.connection.insert_calls == 2


def test_empty_verses_still_upserts_registry() -> None:
    engine = _FakeEngine()
    events: list[TranslationProgressEvent] = []
    count = load_translation(
        engine,  # type: ignore[arg-type]
        code="web",
        name="World English Bible",
        license="Public Domain",
        is_public_domain=True,
        verses=iter(()),
        progress_callback=events.append,
    )
    assert count == 0
    assert [e.kind for e in events] == ["registry", "done"]
    assert engine.connection.insert_calls == 0
