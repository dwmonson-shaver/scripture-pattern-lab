"""Unit tests for the lexicon dataset parsers (Slice N, Phase N1).

Parsers run against small real-format fixtures under tests/fixtures/lexicon/
(carved from the vendored datasets in data/raw/lexicon/). They assert the
typed-row shape, Strong's normalization, and that non-data lines are skipped.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.lexicon.datasets import (
    LemmaStrongs,
    StrongsGloss,
    normalize_strongs,
    parse_dodson,
    parse_jtauber_mappings,
    parse_tbesg,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "lexicon"


class TestNormalizeStrongs:
    def test_bare_int(self) -> None:
        assert normalize_strongs("26") == "G0026"

    def test_zero_padded(self) -> None:
        assert normalize_strongs("0026") == "G0026"

    def test_already_prefixed(self) -> None:
        assert normalize_strongs("G0001") == "G0001"

    def test_disambiguation_suffix_preserved_uppercased(self) -> None:
        assert normalize_strongs("G2264g") == "G2264G"

    def test_empty_returns_none(self) -> None:
        assert normalize_strongs("") is None
        assert normalize_strongs("   ") is None

    def test_non_numeric_returns_none(self) -> None:
        assert normalize_strongs("Herod@Mat.2.1") is None


class TestParseJtauber:
    def test_yields_lemma_strongs_rows(self) -> None:
        rows = list(parse_jtauber_mappings(FIXTURES / "jtauber-sample.yaml"))
        assert all(isinstance(r, LemmaStrongs) for r in rows)
        by_lemma = {r.morphgnt_lemma: r.strongs for r in rows}
        # Key IS the MorphGNT lemma (aligns to corpus by construction).
        assert by_lemma["ἀγάπη"] == "G0026"
        assert by_lemma["ἐλπίς"] == "G1680"
        assert by_lemma["πίστις"] == "G4102"
        assert by_lemma["ταπεινοφροσύνη"] == "G5012"
        assert by_lemma["ταπεινός"] == "G5011"

    def test_lemma_key_is_the_morphgnt_form(self) -> None:
        rows = list(parse_jtauber_mappings(FIXTURES / "jtauber-sample.yaml"))
        assert "ἀγάπη" in {r.morphgnt_lemma for r in rows}


class TestParseTbesg:
    def test_yields_strongs_gloss_rows(self) -> None:
        rows = list(parse_tbesg(FIXTURES / "tbesg-sample.txt"))
        assert all(isinstance(r, StrongsGloss) for r in rows)
        assert all(r.source == "tbesg" for r in rows)

    def test_reverse_lookup_glosses_present(self) -> None:
        rows = list(parse_tbesg(FIXTURES / "tbesg-sample.txt"))
        glosses = {(r.strongs, r.gloss) for r in rows}
        assert ("G5012", "humility") in glosses
        assert ("G0026", "love") in glosses
        assert ("G4102", "faith") in glosses
        assert ("G1680", "hope") in glosses

    def test_header_and_comment_lines_skipped(self) -> None:
        # The fixture's leading "# ..." comment has < 7 tab fields → skipped.
        rows = list(parse_tbesg(FIXTURES / "tbesg-sample.txt"))
        assert all(r.strongs.startswith("G") for r in rows)

    def test_unicode_greek_captured_as_lemma(self) -> None:
        # The TBESG `lemma` is provenance-only (its Greek may differ in Unicode
        # normalization from the corpus — which is exactly why the bridge runs
        # through Strong's/jtauber, NOT a Greek byte-match). Assert it is
        # populated and not blank rather than byte-equal to the corpus form.
        rows = list(parse_tbesg(FIXTURES / "tbesg-sample.txt"))
        humility = next(r for r in rows if r.strongs == "G5012")
        assert humility.lemma is not None and humility.lemma.strip()


class TestParseDodson:
    def test_yields_strongs_gloss_rows(self) -> None:
        rows = list(parse_dodson(FIXTURES / "dodson-sample.tsv"))
        assert all(isinstance(r, StrongsGloss) for r in rows)
        assert all(r.source == "dodson" for r in rows)

    def test_header_row_skipped_and_strongs_normalized(self) -> None:
        rows = list(parse_dodson(FIXTURES / "dodson-sample.tsv"))
        by_strongs = {r.strongs: r.gloss for r in rows}
        assert by_strongs["G0026"] == "love"
        assert "humility" in by_strongs["G5012"]
        assert "hope" in by_strongs["G1680"]

    def test_no_row_has_bare_strongs(self) -> None:
        rows = list(parse_dodson(FIXTURES / "dodson-sample.tsv"))
        assert all(r.strongs.startswith("G") for r in rows)


@pytest.mark.parametrize(
    "parser, fixture",
    [
        (parse_jtauber_mappings, "jtauber-sample.yaml"),
        (parse_tbesg, "tbesg-sample.txt"),
        (parse_dodson, "dodson-sample.tsv"),
    ],
)
def test_parsers_are_nonempty(parser, fixture) -> None:  # type: ignore[no-untyped-def]
    assert list(parser(FIXTURES / fixture))
