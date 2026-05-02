"""Tests for MorphGNT corpus parser (src/ingestion/corpus_parser.py)."""

from pathlib import Path

import pytest

from src.ingestion.corpus_parser import (
    CorpusParseError,
    CorpusToken,
    parse_corpus_file,
    parse_corpus_line,
)

FIXTURE_PATH = Path("tests/fixtures/morphgnt/3jn-sample.txt")
REAL_3JN_PATH = Path("data/raw/morphgnt-sblgnt/85-3Jn-morphgnt.txt")


# ---------------------------------------------------------------------------
# parse_corpus_line — happy path and BBCCVV decoding
# ---------------------------------------------------------------------------


class TestParseCorpusLine:
    def test_happy_path_field_by_field(self) -> None:
        line = "250101 N- ----DSM- Γαΐῳ Γαΐῳ Γαΐῳ Γάϊος"
        token = parse_corpus_line(
            line,
            line_no=3,
            source="<test>",
            position=3,
            global_position=3,
        )
        assert token == CorpusToken(
            book="25",
            chapter=1,
            verse=1,
            position=3,
            global_position=3,
            surface_form="Γαΐῳ",
            normalized_form="Γαΐῳ",
            lemma="Γάϊος",
            morph_code="----DSM-",
            pos="N-",
            language="grc",
            corpus_id="nt",
        )

    def test_bbccvv_decoding(self) -> None:
        line = "250101 RA ----NSM- Ὁ Ὁ ὁ ὁ"
        token = parse_corpus_line(
            line, line_no=1, source="<test>", position=1, global_position=1
        )
        assert token.book == "25"
        assert token.chapter == 1
        assert token.verse == 1

    def test_bbccvv_decoding_double_digit(self) -> None:
        # Synthetic row: book 11, chapter 23, verse 47
        line = "112347 N- -------- λόγος λόγος λόγος λόγος"
        token = parse_corpus_line(
            line, line_no=1, source="<test>", position=1, global_position=1
        )
        assert token.book == "11"
        assert token.chapter == 23
        assert token.verse == 47


# ---------------------------------------------------------------------------
# parse_corpus_line — error paths
# ---------------------------------------------------------------------------


class TestParseCorpusLineErrors:
    def test_six_column_row_raises(self) -> None:
        line = "250101 N- ----DSM- Γαΐῳ Γαΐῳ Γαΐῳ"  # 6 columns, missing lemma
        with pytest.raises(CorpusParseError) as exc_info:
            parse_corpus_line(
                line, line_no=42, source="3jn.txt", position=1, global_position=1
            )
        assert exc_info.value.line_no == 42
        assert exc_info.value.source == "3jn.txt"
        # The malformed line itself is included in the message for context.
        assert "Γαΐῳ" in str(exc_info.value)

    def test_non_numeric_bbccvv_raises(self) -> None:
        line = "abcdef N- ----DSM- Γαΐῳ Γαΐῳ Γαΐῳ Γάϊος"
        with pytest.raises(CorpusParseError) as exc_info:
            parse_corpus_line(
                line, line_no=7, source="<test>", position=1, global_position=1
            )
        assert exc_info.value.line_no == 7
        assert exc_info.value.source == "<test>"

    def test_short_bbccvv_raises(self) -> None:
        line = "25010 N- ----DSM- Γαΐῳ Γαΐῳ Γαΐῳ Γάϊος"  # only 5 digits
        with pytest.raises(CorpusParseError):
            parse_corpus_line(
                line, line_no=1, source="<test>", position=1, global_position=1
            )


# ---------------------------------------------------------------------------
# parse_corpus_file — verse boundaries, global_position monotonicity, fixtures
# ---------------------------------------------------------------------------


class TestParseCorpusFile:
    def test_position_resets_at_verse_boundary(self) -> None:
        # Fixture: 5 rows in v4 (positions 1..5), then 6 rows in v5 (positions 1..6).
        tokens = list(parse_corpus_file(FIXTURE_PATH))
        assert len(tokens) == 11

        # v4 segment
        assert [t.verse for t in tokens[:5]] == [4, 4, 4, 4, 4]
        assert [t.position for t in tokens[:5]] == [1, 2, 3, 4, 5]

        # v5 segment — position resets to 1
        assert [t.verse for t in tokens[5:]] == [5, 5, 5, 5, 5, 5]
        assert [t.position for t in tokens[5:]] == [1, 2, 3, 4, 5, 6]

    def test_global_position_monotonic(self) -> None:
        tokens = list(parse_corpus_file(FIXTURE_PATH))
        assert [t.global_position for t in tokens] == list(range(1, 12))

    def test_start_global_position_kwarg(self) -> None:
        tokens = list(parse_corpus_file(FIXTURE_PATH, start_global_position=1000))
        assert tokens[0].global_position == 1000
        assert tokens[-1].global_position == 1010

    def test_apparatus_mark_preserved_in_surface_form(self) -> None:
        # Fixture row 3 (index 2): "250104 RA ----DSF- ⸀τῇ τῇ τῇ ὁ"
        tokens = list(parse_corpus_file(FIXTURE_PATH))
        apparatus_token = tokens[2]
        assert "⸀" in apparatus_token.surface_form
        assert "⸀" not in apparatus_token.normalized_form
        assert apparatus_token.surface_form == "⸀τῇ"
        assert apparatus_token.normalized_form == "τῇ"


# ---------------------------------------------------------------------------
# Smoke test against real 3 John data (no DB)
# ---------------------------------------------------------------------------


class TestRealCorpusSmoke:
    def test_3jn_yields_219_records(self) -> None:
        assert sum(1 for _ in parse_corpus_file(REAL_3JN_PATH)) == 219

    def test_3jn_first_three_lemmas(self) -> None:
        # Sanity: the opening of 3 John is "Ὁ πρεσβύτερος Γαΐῳ"; row 3 lemma = Γάϊος.
        tokens = list(parse_corpus_file(REAL_3JN_PATH))
        assert tokens[0].lemma == "ὁ"
        assert tokens[1].lemma == "πρεσβύτερος"
        assert tokens[2].lemma == "Γάϊος"
        assert tokens[2].book == "25"
        assert tokens[2].chapter == 1
        assert tokens[2].verse == 1
        assert tokens[2].position == 3
