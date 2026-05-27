"""Unit tests for src/ontology/concept_document.py (Slice N, Phase N6).

Covers the pure deterministic builders (short summary) and the frozen model
shapes. build_comparative_section + persist/get touch the DB and are covered in
tests/integration/test_concept_document.py.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.ontology.concept_document import (
    ComparativeLexiconSection,
    ConceptDocument,
    EducationalArticleSection,
    LexiconComparisonRow,
    build_short_summary,
)
from src.ontology.lexicon_resolver import LexiconResolution, ResolvedLemma


def _resolution(n: int = 2) -> LexiconResolution:
    lemmas = ["πίστις", "ἐλπίς", "ἀγάπη", "χάρις", "εἰρήνη", "σοφία"][:n]
    return LexiconResolution(
        english_term="faith",
        resolved_lemmas=[
            ResolvedLemma(
                lemma=lem,
                strongs=[f"G{i:04d}"],
                glosses=["faith"],
                corpus_token_count=3,
            )
            for i, lem in enumerate(lemmas, start=1)
        ],
    )


class TestShortSummary:
    def test_names_term_and_lemmas(self) -> None:
        summary = build_short_summary(_resolution(2))
        assert "faith" in summary
        assert "πίστις" in summary
        assert "ἐλπίς" in summary

    def test_states_unverified_status_honestly(self) -> None:
        summary = build_short_summary(_resolution(1))
        assert "unverified" in summary.lower()
        assert "lexicon" in summary.lower()

    def test_caps_lemmas_with_more_suffix(self) -> None:
        summary = build_short_summary(_resolution(6))
        assert "+1 more" in summary  # 6 lemmas, cap 5


class TestModels:
    def test_comparative_section_frozen(self) -> None:
        section = ComparativeLexiconSection(
            english_term="faith",
            rows=[
                LexiconComparisonRow(
                    lemma="πίστις",
                    strongs=["G4102"],
                    usual_renderings=["faith"],
                    corpus_verse_refs=["1Cor 13:13"],
                )
            ],
            generated_from=["TBESG"],
        )
        with pytest.raises(ValidationError):
            section.english_term = "x"  # type: ignore[misc]

    def test_educational_section_defaults_generated_true(self) -> None:
        section = EducationalArticleSection(
            prose="...", cited_sources=["TBESG"], model_label="claude"
        )
        assert section.generated is True

    def test_document_part2_defaults_none(self) -> None:
        doc = ConceptDocument(
            concept_name="faith",
            short_summary="...",
            part1_comparative=ComparativeLexiconSection(
                english_term="faith", rows=[], generated_from=[]
            ),
        )
        assert doc.part1_educational is None
        assert doc.part2_grouping_placeholder is None
