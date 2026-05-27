"""Unit tests for src/ontology/concept_writer.py (Slice N, Phase N4).

Covers the unresolved-guard and the outcome model invariants without a DB. The
actual write path + the corpus-is-ground-truth invariant are exercised against
a live DB in tests/integration/test_concept_writer.py.
"""

from __future__ import annotations

import pytest

from src.ontology.concept_writer import (
    LEXICON_ORIGIN,
    LEXICON_VSTATE,
    ConceptCreationOutcome,
    auto_create_cited_concept,
)
from src.ontology.lexicon_resolver import LexiconResolution, ResolvedLemma


class _NeverConnectedEngine:
    def connect(self) -> object:  # pragma: no cover
        raise AssertionError("unresolved guard must precede any DB access")

    def begin(self) -> object:  # pragma: no cover
        raise AssertionError("unresolved guard must precede any DB access")


class TestUnresolvedGuard:
    def test_unresolved_resolution_raises_before_db(self) -> None:
        res = LexiconResolution(english_term="zzz", resolved_lemmas=[])
        with pytest.raises(ValueError, match="unresolved"):
            auto_create_cited_concept(res, _NeverConnectedEngine())  # type: ignore[arg-type]


class TestEpistemicConstants:
    def test_origin_is_lexicon_imported(self) -> None:
        assert LEXICON_ORIGIN == "lexicon_imported"

    def test_vstate_is_unverified_not_confirmed(self) -> None:
        assert LEXICON_VSTATE == "unverified"
        assert LEXICON_VSTATE != "human_confirmed"
        assert LEXICON_VSTATE != "corpus_observed"


class TestOutcomeModel:
    def test_outcome_is_frozen(self) -> None:
        from pydantic import ValidationError

        outcome = ConceptCreationOutcome(
            concept_name="humility",
            created=True,
            reused_existing=False,
            lemmas_written=["ταπεινοφροσύνη"],
            origin="lexicon_imported",
            verification_state="unverified",
        )
        with pytest.raises(ValidationError):
            outcome.created = False  # type: ignore[misc]

    def test_resolution_with_lemmas_is_resolvable(self) -> None:
        res = LexiconResolution(
            english_term="humility",
            resolved_lemmas=[
                ResolvedLemma(
                    lemma="ταπεινοφροσύνη",
                    strongs=["G5012"],
                    glosses=["humility"],
                    corpus_token_count=7,
                )
            ],
        )
        assert not res.unresolved
