"""Unit tests for src/ingestion/lexicon/loader.py — load_lexicon callback semantics.

A fake Engine yields a no-op connection that records but does not execute the
ON CONFLICT inserts. Real-DB exercise lives in
tests/integration/test_lexicon_ingest.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from src.ingestion.lexicon.datasets import LemmaStrongs, StrongsGloss
from src.ingestion.lexicon.loader import (
    LexiconProgressEvent,
    load_lexicon,
)


class _FakeConnection:
    """Records single-arg ``execute(stmt)`` calls without running SQL."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, _stmt: object) -> None:
        self.calls += 1


class _FakeEngine:
    def __init__(self) -> None:
        self.connection = _FakeConnection()

    @contextmanager
    def begin(self) -> Iterator[_FakeConnection]:
        yield self.connection


def _lemma_rows(n: int) -> list[LemmaStrongs]:
    return [LemmaStrongs(morphgnt_lemma=f"λ{i}", strongs=f"G{i:04d}") for i in range(n)]


def _gloss_rows(n: int, source: str) -> list[StrongsGloss]:
    return [
        StrongsGloss(strongs=f"G{i:04d}", lemma=f"λ{i}", gloss=f"g{i}", source=source)
        for i in range(n)
    ]


class TestLoadLexiconCounts:
    def test_returns_per_table_counts(self) -> None:
        engine = _FakeEngine()
        counts = load_lexicon(
            engine,  # type: ignore[arg-type]
            lemma_strongs=_lemma_rows(3),
            tbesg_glosses=_gloss_rows(2, "tbesg"),
            dodson_glosses=_gloss_rows(4, "dodson"),
        )
        assert counts == {"lemma_strongs": 3, "strongs_glosses": 6}

    def test_empty_inputs_are_clean(self) -> None:
        engine = _FakeEngine()
        counts = load_lexicon(
            engine,  # type: ignore[arg-type]
            lemma_strongs=[],
            tbesg_glosses=[],
            dodson_glosses=[],
        )
        assert counts == {"lemma_strongs": 0, "strongs_glosses": 0}


class TestLoadLexiconCallback:
    def test_emits_dataset_boundaries_and_done(self) -> None:
        engine = _FakeEngine()
        events: list[LexiconProgressEvent] = []
        load_lexicon(
            engine,  # type: ignore[arg-type]
            lemma_strongs=_lemma_rows(1),
            tbesg_glosses=_gloss_rows(1, "tbesg"),
            dodson_glosses=_gloss_rows(1, "dodson"),
            progress_callback=events.append,
        )
        kinds = [e.kind for e in events]
        # Three dataset boundaries (jtauber/tbesg/dodson) + 3 batch + 1 done.
        assert kinds.count("dataset_boundary") == 3
        assert kinds[-1] == "done"
        datasets = [e.dataset for e in events if e.kind == "dataset_boundary"]
        assert datasets == ["jtauber", "tbesg", "dodson"]

    def test_done_carries_total_rows(self) -> None:
        engine = _FakeEngine()
        events: list[LexiconProgressEvent] = []
        load_lexicon(
            engine,  # type: ignore[arg-type]
            lemma_strongs=_lemma_rows(2),
            tbesg_glosses=_gloss_rows(3, "tbesg"),
            dodson_glosses=_gloss_rows(1, "dodson"),
            progress_callback=events.append,
        )
        done = events[-1]
        assert done.kind == "done"
        assert done.rows_loaded == 6
