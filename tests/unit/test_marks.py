"""Unit tests for src/ontology/marks.py (Slice 1, DEC-129/143/145).

A scripted fake connection returns canned results per execute() call so we can
exercise create/list/update/delete + the cross-verse span and unknown-concept
paths without a DB. The marks module issues a known sequence of statements per
operation; tests script the returns to match.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from src.ontology.marks import (
    MarkNotFound,
    UnknownConcept,
    create_mark,
    delete_mark,
    update_mark,
)


class _Row:
    def __init__(self, **kw: object) -> None:
        for k, v in kw.items():
            setattr(self, k, v)


class _Result:
    def __init__(self, *, rows=None, scalar=None, first=None, rowcount=0) -> None:  # noqa: ANN001
        self._rows = rows or []
        self._scalar = scalar
        self._first = first
        self.rowcount = rowcount

    def all(self) -> list:
        return self._rows

    def scalar_one(self) -> object:
        return self._scalar

    def first(self) -> object:
        return self._first


class _ScriptedConnection:
    """Returns queued results in order; records each statement's SQL text."""

    def __init__(self, results: list[_Result]) -> None:
        self._results = results
        self._i = 0
        self.statements: list[str] = []

    def execute(self, stmt: object) -> _Result:
        self.statements.append(str(stmt).lower())
        r = self._results[self._i] if self._i < len(self._results) else _Result()
        self._i += 1
        return r


class _FakeEngine:
    def __init__(self, results: list[_Result]) -> None:
        self.connection = _ScriptedConnection(results)

    @contextmanager
    def begin(self) -> Iterator[_ScriptedConnection]:
        yield self.connection

    @contextmanager
    def connect(self) -> Iterator[_ScriptedConnection]:
        yield self.connection


def _mark_row(**kw: object) -> _Row:
    base = dict(
        id=1, corpus_id="nt", book="06", chapter=8, verse_start=24, verse_end=25,
        char_start=0, char_end=10, version_code="kjv", actor="local",
        created_at=None, updated_at=None,
    )
    base.update(kw)
    return _Row(**base)


class TestCreateMark:
    def test_cross_verse_span_with_concept(self) -> None:
        # Sequence: resolve names (all()), insert mark (scalar_one id),
        # insert link (no return), then _load_mark: select mark (first),
        # _names_for_mark (all()).
        engine = _FakeEngine([
            _Result(rows=[_Row(id=7, name="Hope")]),       # _resolve_concept_ids
            _Result(scalar=1),                              # insert mark RETURNING id
            _Result(),                                      # insert link
            _Result(first=_mark_row()),                     # _load_mark select
            _Result(rows=[_Row(name="Hope")]),              # _names_for_mark
        ])
        mark = create_mark(
            engine,  # type: ignore[arg-type]
            book="06", chapter=8, verse_start=24, verse_end=25,
            char_start=0, char_end=10, version_code="kjv",
            concept_names=["Hope"],
        )
        assert mark.verse_start == 24 and mark.verse_end == 25  # cross-verse
        assert mark.concept_names == ["Hope"]

    def test_plain_highlight_no_concepts(self) -> None:
        engine = _FakeEngine([
            _Result(scalar=2),                              # insert mark RETURNING id
            _Result(first=_mark_row(id=2)),                 # _load_mark select
            _Result(rows=[]),                               # _names_for_mark
        ])
        mark = create_mark(
            engine,  # type: ignore[arg-type]
            book="06", chapter=8, verse_start=1, verse_end=1,
            char_start=0, char_end=5, version_code="kjv",
        )
        assert mark.concept_names == []

    def test_unknown_concept_raises(self) -> None:
        engine = _FakeEngine([
            _Result(rows=[]),  # resolve finds nothing → missing
        ])
        with pytest.raises(UnknownConcept):
            create_mark(
                engine,  # type: ignore[arg-type]
                book="06", chapter=8, verse_start=1, verse_end=1,
                char_start=0, char_end=5, version_code="kjv",
                concept_names=["Nope"],
            )


class TestUpdateMark:
    def test_replace_concept_set(self) -> None:
        engine = _FakeEngine([
            _Result(first=_Row(id=1)),                      # exists check
            _Result(rows=[_Row(id=9, name="Love")]),        # resolve replacement
            _Result(),                                      # delete old links
            _Result(),                                      # insert new link
            _Result(first=_mark_row()),                     # _load_mark select
            _Result(rows=[_Row(name="Love")]),              # _names_for_mark
        ])
        mark = update_mark(engine, 1, concept_names=["Love"])  # type: ignore[arg-type]
        assert mark.concept_names == ["Love"]
        assert any("delete" in s for s in engine.connection.statements)

    def test_missing_mark_raises(self) -> None:
        engine = _FakeEngine([_Result(first=None)])  # exists check fails
        with pytest.raises(MarkNotFound):
            update_mark(engine, 99, char_end=20)  # type: ignore[arg-type]


class TestDeleteMark:
    def test_delete_ok(self) -> None:
        engine = _FakeEngine([_Result(rowcount=1)])
        delete_mark(engine, 1)  # type: ignore[arg-type]  # no raise

    def test_delete_missing_raises(self) -> None:
        engine = _FakeEngine([_Result(rowcount=0)])
        with pytest.raises(MarkNotFound):
            delete_mark(engine, 99)  # type: ignore[arg-type]
