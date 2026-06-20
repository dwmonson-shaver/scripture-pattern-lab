"""Unit tests for src/ingestion/translations/parser.py.

Covers book-name → BB mapping (incl. roman-numeral and spacing variants), verse
row assembly, and loud-failure on malformed input. No DB.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ingestion.translations.parser import (
    TranslationParseError,
    TranslationVerse,
    book_name_to_bb,
    parse_translation_directory,
    parse_translation_file,
)


class TestBookNameToBb:
    def test_full_names(self) -> None:
        assert book_name_to_bb("Romans") == "06"
        assert book_name_to_bb("Matthew") == "01"
        assert book_name_to_bb("Revelation") == "27"

    def test_case_insensitive(self) -> None:
        assert book_name_to_bb("ROMANS") == "06"
        assert book_name_to_bb("romans") == "06"

    def test_numbered_book_spacing_variants(self) -> None:
        assert book_name_to_bb("1Corinthians") == "07"
        assert book_name_to_bb("1 Corinthians") == "07"
        assert book_name_to_bb("I Corinthians") == "07"
        assert book_name_to_bb("III John") == "25"
        assert book_name_to_bb("3 John") == "25"

    def test_revelation_of_john_variant(self) -> None:
        assert book_name_to_bb("Revelation of John") == "27"

    def test_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            book_name_to_bb("Genesis")  # OT not in NT-only corpus


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


class TestParseTranslationFile:
    def test_yields_verses_with_bb_and_ints(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "Romans.json",
            {
                "book": "Romans",
                "chapters": [
                    {
                        "chapter": "8",
                        "verses": [
                            {"verse": "24", "text": "For we are saved by hope:"},
                            {"verse": "25", "text": "But if we hope for that"},
                        ],
                    }
                ],
            },
        )
        rows = list(parse_translation_file(path))
        assert len(rows) == 2
        assert rows[0] == TranslationVerse(
            corpus_id="nt",
            book="06",
            chapter=8,
            verse=24,
            text="For we are saved by hope:",
        )
        assert rows[1].verse == 25

    def test_bad_json_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        with pytest.raises(TranslationParseError):
            list(parse_translation_file(p))

    def test_missing_book_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "x.json", {"chapters": []})
        with pytest.raises(TranslationParseError):
            list(parse_translation_file(path))

    def test_unknown_book_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path, "gen.json", {"book": "Genesis", "chapters": []}
        )
        with pytest.raises(TranslationParseError):
            list(parse_translation_file(path))

    def test_bad_verse_number_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "Romans.json",
            {
                "book": "Romans",
                "chapters": [
                    {"chapter": "1", "verses": [{"verse": "x", "text": "t"}]}
                ],
            },
        )
        with pytest.raises(TranslationParseError):
            list(parse_translation_file(path))


class TestParseTranslationDirectory:
    def test_reads_all_json_sorted(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "Romans.json",
            {"book": "Romans", "chapters": [
                {"chapter": "1", "verses": [{"verse": "1", "text": "a"}]}
            ]},
        )
        _write(
            tmp_path,
            "John.json",
            {"book": "John", "chapters": [
                {"chapter": "1", "verses": [{"verse": "1", "text": "b"}]}
            ]},
        )
        rows = list(parse_translation_directory(tmp_path))
        assert {r.book for r in rows} == {"04", "06"}
        assert len(rows) == 2
