"""Unit tests for src/ingestion/loader.py — ProgressEvent / progress_callback semantics.

These tests assert the loader emits ProgressEvents in the documented order at
batch flushes, file boundaries, and on done. They use a fake Engine whose
``begin()`` yields a no-op connection that records (but does not execute)
batches; real-DB exercise lives in tests/integration/test_corpus_ingest.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from src.ingestion import loader as loader_module
from src.ingestion.corpus_parser import CorpusToken
from src.ingestion.loader import ProgressEvent, load_tokens


def _make_token(
    book: str,
    *,
    chapter: int = 1,
    verse: int = 1,
    position: int = 1,
    global_position: int = 1,
) -> CorpusToken:
    """Build a minimal valid CorpusToken; surface/lemma/morph fields are placeholders."""
    return CorpusToken(
        book=book,
        chapter=chapter,
        verse=verse,
        position=position,
        global_position=global_position,
        surface_form="x",
        normalized_form="x",
        lemma="x",
        morph_code="----",
        pos="N-",
    )


class _FakeConnection:
    """Records batches passed to ``execute`` without running any SQL."""

    def __init__(self) -> None:
        self.batches: list[list[dict]] = []

    def execute(self, _stmt: object, batch: list[dict]) -> None:
        self.batches.append(list(batch))


class _FakeEngine:
    """Minimal Engine stand-in: ``begin()`` yields a recording no-op connection."""

    def __init__(self) -> None:
        self.connection = _FakeConnection()

    @contextmanager
    def begin(self) -> Iterator[_FakeConnection]:
        yield self.connection


@pytest.fixture
def fake_engine() -> _FakeEngine:
    return _FakeEngine()


class TestProgressCallback:
    def test_no_callback_is_default_and_changes_no_behavior(
        self, fake_engine: _FakeEngine
    ) -> None:
        tokens = [
            _make_token("01", position=i + 1, global_position=i + 1) for i in range(3)
        ]

        result = load_tokens(fake_engine, tokens)  # type: ignore[arg-type]

        assert result == 3
        assert sum(len(b) for b in fake_engine.connection.batches) == 3

    def test_callback_fires_per_batch(
        self,
        fake_engine: _FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(loader_module, "BATCH_SIZE", 2)
        events: list[ProgressEvent] = []
        tokens = [
            _make_token("01", position=i + 1, global_position=i + 1) for i in range(5)
        ]

        result = load_tokens(
            fake_engine,  # type: ignore[arg-type]
            tokens,
            progress_callback=events.append,
        )

        assert result == 5
        batch_events = [e for e in events if e.kind == "batch"]
        assert [e.tokens_loaded for e in batch_events] == [2, 4, 5]
        assert all(e.book is None for e in batch_events)

    def test_callback_fires_at_file_boundary(
        self,
        fake_engine: _FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # BATCH_SIZE > total tokens → no batch fires before either file boundary,
        # so each boundary event reports tokens_loaded=0 (nothing committed yet).
        monkeypatch.setattr(loader_module, "BATCH_SIZE", 1000)
        events: list[ProgressEvent] = []
        tokens = [
            _make_token("01", position=i + 1, global_position=i + 1) for i in range(3)
        ] + [
            _make_token("02", position=i + 1, global_position=i + 4) for i in range(3)
        ]

        load_tokens(
            fake_engine,  # type: ignore[arg-type]
            tokens,
            progress_callback=events.append,
        )

        boundaries = [e for e in events if e.kind == "file_boundary"]
        assert [e.book for e in boundaries] == ["01", "02"]
        assert [e.tokens_loaded for e in boundaries] == [0, 0]

    def test_callback_emits_done_with_final_count(
        self,
        fake_engine: _FakeEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(loader_module, "BATCH_SIZE", 2)
        events: list[ProgressEvent] = []
        tokens = [
            _make_token("01", position=i + 1, global_position=i + 1) for i in range(5)
        ]

        load_tokens(
            fake_engine,  # type: ignore[arg-type]
            tokens,
            progress_callback=events.append,
        )

        assert events[-1] == ProgressEvent(kind="done", book=None, tokens_loaded=5)
