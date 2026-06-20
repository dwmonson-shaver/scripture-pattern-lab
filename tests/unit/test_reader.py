"""Unit tests for src/retrieval/reader.py (Slice 1, DEC-148).

MagicMock SQL paths: verse assembly, grouping Greek tokens under their verse,
empty-chapter raising, and the versions list. No DB.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.retrieval.reader import (
    ChapterNotFound,
    list_versions,
    read_chapter,
)


def _engine_two_selects(first_rows: list, second_rows: list) -> object:  # noqa: ANN401
    """Engine whose connect().execute().all() returns first_rows then second_rows."""
    engine = MagicMock()
    connection = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = connection
    cm.__exit__.return_value = False
    engine.connect.return_value = cm

    r1, r2 = MagicMock(), MagicMock()
    r1.all.return_value = first_rows
    r2.all.return_value = second_rows
    connection.execute.side_effect = [r1, r2]
    return engine


def _verse_row(verse: int, text: str) -> object:  # noqa: ANN401
    r = MagicMock()
    r.verse = verse
    r.text = text
    return r


def _greek_row(verse: int, position: int, lemma: str) -> object:  # noqa: ANN401
    r = MagicMock()
    r.verse = verse
    r.position = position
    r.surface_form = lemma
    r.normalized_form = lemma
    r.lemma = lemma
    r.morph_code = "N-----"
    r.pos = "N-"
    return r


class TestReadChapter:
    def test_assembles_verses_with_grouped_greek(self) -> None:
        english = [
            _verse_row(24, "For we are saved by hope:"),
            _verse_row(25, "But if we hope for that we see not"),
        ]
        greek = [
            _greek_row(24, 1, "σῴζω"),
            _greek_row(24, 2, "ἐλπίς"),
            _greek_row(25, 1, "ὑπομονή"),
        ]
        engine = _engine_two_selects(english, greek)
        read = read_chapter(
            engine,  # type: ignore[arg-type]
            corpus_id="nt",
            book_bb="06",
            chapter=8,
            version_code="kjv",
        )
        assert read.book_display == "Rom"
        assert read.chapter == 8
        assert [v.verse for v in read.verses] == [24, 25]
        assert read.verses[0].reference == "Rom 8:24"
        assert [t.lemma for t in read.verses[0].greek_tokens] == ["σῴζω", "ἐλπίς"]
        assert [t.lemma for t in read.verses[1].greek_tokens] == ["ὑπομονή"]

    def test_verse_with_no_greek_gets_empty_list(self) -> None:
        engine = _engine_two_selects([_verse_row(1, "a")], [])
        read = read_chapter(
            engine,  # type: ignore[arg-type]
            corpus_id="nt",
            book_bb="06",
            chapter=1,
            version_code="kjv",
        )
        assert read.verses[0].greek_tokens == []

    def test_empty_chapter_raises(self) -> None:
        engine = _engine_two_selects([], [])
        with pytest.raises(ChapterNotFound):
            read_chapter(
                engine,  # type: ignore[arg-type]
                corpus_id="nt",
                book_bb="06",
                chapter=99,
                version_code="kjv",
            )


class TestListVersions:
    def test_none_engine_returns_empty(self) -> None:
        assert list_versions(None) == []

    def test_maps_rows(self) -> None:
        v1, v2 = MagicMock(), MagicMock()
        v1.code, v1.name, v1.is_public_domain = "kjv", "King James Version", True
        v2.code, v2.name, v2.is_public_domain = "web", "World English Bible", True
        engine = MagicMock()
        connection = MagicMock()
        cm = MagicMock()
        cm.__enter__.return_value = connection
        cm.__exit__.return_value = False
        engine.connect.return_value = cm
        result = MagicMock()
        result.all.return_value = [v1, v2]
        connection.execute.return_value = result

        versions = list_versions(engine)
        assert [v.code for v in versions] == ["kjv", "web"]
        assert versions[0].is_public_domain is True
