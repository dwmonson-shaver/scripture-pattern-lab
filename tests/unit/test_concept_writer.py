"""Unit tests for src/ontology/concept_writer.py (Slice N, Phase N4).

Covers the unresolved-guard and the outcome model invariants without a DB. The
actual write path + the corpus-is-ground-truth invariant are exercised against
a live DB in tests/integration/test_concept_writer.py.

DEC-081 runtime-guard tests (backported from DEC-115 / Tier-2 in Slice O):
    * Layer A (structural): ``auto_create_cited_concept`` signature has no
      ``verification_state`` or ``origin`` parameter.
    * Layer B-i (Pydantic Literal): ``ConceptCreationOutcome`` rejects any
      non-``'unverified'`` verification_state and any non-``'lexicon_imported'``
      origin at construction.
    * Layer B-ii (model_validator): the validator names DEC-081 explicitly so
      any bypass (model_construct, signature regression, __setattr__ hole)
      produces a debuggable trail.
"""

from __future__ import annotations

import inspect

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


class TestLayerAStructuralGuard:
    """DEC-081 Layer A: writer signature has no verification_state/origin parameter."""

    def test_auto_create_has_no_verification_state_parameter(self) -> None:
        sig = inspect.signature(auto_create_cited_concept)
        assert "verification_state" not in sig.parameters, (
            "auto_create_cited_concept must NOT accept a verification_state "
            "parameter — DEC-081 Layer A structural guard"
        )

    def test_auto_create_has_no_origin_parameter(self) -> None:
        sig = inspect.signature(auto_create_cited_concept)
        assert "origin" not in sig.parameters, (
            "auto_create_cited_concept must NOT accept an origin parameter — "
            "DEC-081 Layer A structural guard (only 'lexicon_imported' is valid)"
        )


class TestLayerBPydanticLiteralGuard:
    """DEC-081 Layer B-i: Pydantic Literal rejects non-unverified / non-lexicon values."""

    def _base_kwargs(self) -> dict:
        return {
            "concept_name": "humility",
            "created": True,
            "reused_existing": False,
            "lemmas_written": ["ταπεινοφροσύνη"],
            "origin": "lexicon_imported",
            "verification_state": "unverified",
        }

    def test_literal_rejects_human_confirmed_vstate(self) -> None:
        from pydantic import ValidationError

        kwargs = self._base_kwargs()
        kwargs["verification_state"] = "human_confirmed"
        with pytest.raises(ValidationError):
            ConceptCreationOutcome(**kwargs)

    def test_literal_rejects_corpus_observed_vstate(self) -> None:
        from pydantic import ValidationError

        kwargs = self._base_kwargs()
        kwargs["verification_state"] = "corpus_observed"
        with pytest.raises(ValidationError):
            ConceptCreationOutcome(**kwargs)

    def test_literal_rejects_curated_origin(self) -> None:
        from pydantic import ValidationError

        kwargs = self._base_kwargs()
        kwargs["origin"] = "curated"
        with pytest.raises(ValidationError):
            ConceptCreationOutcome(**kwargs)

    def test_literal_rejects_ai_suggested_origin(self) -> None:
        from pydantic import ValidationError

        kwargs = self._base_kwargs()
        kwargs["origin"] = "ai_suggested"
        with pytest.raises(ValidationError):
            ConceptCreationOutcome(**kwargs)


class TestLayerBIIValidatorNamesDEC081:
    """DEC-081 Layer B-ii: round-trip from model_construct produces an explicit error.

    Pydantic's Literal rejection in ``model_validate`` runs BEFORE field-level
    model_validators, so the Layer B-ii validator only fires when a bypass
    skips the Literal check (e.g. ``model_construct``). The documented project
    standard (mirroring Tier-2 ``test_model_validator_b_ii_explicit_dec_081_message``)
    is to assert the round-trip error names EITHER the DEC marker (our
    validator) OR the breached value (Pydantic's Literal message) — both are
    debuggable trails that name what was breached.
    """

    def _base_kwargs(self) -> dict:
        return {
            "concept_name": "humility",
            "created": True,
            "reused_existing": False,
            "lemmas_written": ["ταπεινοφροσύνη"],
            "origin": "lexicon_imported",
            "verification_state": "unverified",
        }

    def test_bypass_round_trip_surfaces_breached_invariant_vstate(self) -> None:
        bad = ConceptCreationOutcome.model_construct(
            **{**self._base_kwargs(), "verification_state": "human_confirmed"}
        )
        with pytest.raises((ValueError, Exception)) as excinfo:
            ConceptCreationOutcome.model_validate(bad.model_dump())
        msg = str(excinfo.value)
        assert "DEC-081" in msg or "human_confirmed" in msg

    def test_bypass_round_trip_surfaces_breached_invariant_origin(self) -> None:
        bad = ConceptCreationOutcome.model_construct(
            **{**self._base_kwargs(), "origin": "curated"}
        )
        with pytest.raises((ValueError, Exception)) as excinfo:
            ConceptCreationOutcome.model_validate(bad.model_dump())
        msg = str(excinfo.value)
        assert "DEC-081" in msg or "curated" in msg

    def test_validator_directly_names_dec_081_on_bad_vstate(self) -> None:
        """Direct invocation of the validator (bypassing Pydantic's Literal entirely)
        must name DEC-081 explicitly — this is the load-bearing assertion for
        Layer B-ii's debuggable trail."""
        bad = ConceptCreationOutcome.model_construct(
            **{**self._base_kwargs(), "verification_state": "human_confirmed"}
        )
        with pytest.raises(ValueError, match="DEC-081"):
            bad._guard_dec_081()

    def test_validator_directly_names_dec_081_on_bad_origin(self) -> None:
        bad = ConceptCreationOutcome.model_construct(
            **{**self._base_kwargs(), "origin": "curated"}
        )
        with pytest.raises(ValueError, match="DEC-081"):
            bad._guard_dec_081()
