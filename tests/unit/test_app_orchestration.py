"""Tests for the FastAPI route orchestration helper (src/app/orchestration.py)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.app.orchestration import ValidationUnsupported, run_dsl_query
from src.app.schemas import QueryDSLResponse
from src.engine.models import (
    ConceptNotMapped,
    Contextualization,
    MatchCandidate,
    MatchedToken,
    NodeType,
    RegistryRequired,
    RetrievalResult,
    StepMatch,
    UnsupportedPlanShape,
)
from src.engine.parser import ParseError
from src.ontology.registry import ConceptRegistry


@pytest.fixture
def empty_registry() -> ConceptRegistry:
    return ConceptRegistry.empty()


@pytest.fixture
def fake_engine() -> MagicMock:
    """Stand-in for sqlalchemy.Engine. The real engine is only consulted
    by retrieve(), which we monkey-patch in these tests."""
    return MagicMock(name="fake_engine")


class TestParseError:
    def test_parse_error_propagates(self, fake_engine, empty_registry) -> None:
        # Empty operator triple is malformed.
        with pytest.raises(ParseError):
            run_dsl_query("faith > > > hope", fake_engine, empty_registry)


class TestValidationUnsupported:
    def test_inverse_is_unsupported_in_mvp(
        self, fake_engine, empty_registry
    ) -> None:
        # MVP capability registry has inverse_support=False (DEC pattern,
        # see canonical-06 and tests/unit/test_validator.py:208-226).
        with pytest.raises(ValidationUnsupported) as exc_info:
            run_dsl_query("inverse(faith > hope)", fake_engine, empty_registry)
        validation = exc_info.value.validation
        assert validation.status == "unsupported"
        assert any(
            f.code == "UNSUPPORTED_INVERSE" for f in validation.findings
        ), f"expected UNSUPPORTED_INVERSE in {[f.code for f in validation.findings]}"


class TestPipelineExceptionsPropagate:
    """retrieve() exceptions must propagate unchanged for the route handler
    to catch and map to HTTP status."""

    def test_unsupported_plan_shape_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def boom(*args, **kwargs):
            raise UnsupportedPlanShape("boom", path="$.sequence.steps[0]")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        with pytest.raises(UnsupportedPlanShape) as exc_info:
            run_dsl_query("faith > hope", fake_engine, empty_registry)
        assert exc_info.value.path == "$.sequence.steps[0]"

    def test_concept_not_mapped_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def boom(*args, **kwargs):
            raise ConceptNotMapped("foo")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        with pytest.raises(ConceptNotMapped) as exc_info:
            run_dsl_query("faith > hope", fake_engine, empty_registry)
        assert exc_info.value.concept_name == "foo"

    def test_registry_required_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def boom(*args, **kwargs):
            raise RegistryRequired("faith")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        with pytest.raises(RegistryRequired) as exc_info:
            run_dsl_query("faith > hope", fake_engine, empty_registry)
        assert exc_info.value.concept_name == "faith"


class TestHappyPathWithMockedRetrieve:
    """Verify the response envelope shape using a stubbed retrieve()
    so we don't need a real DB. End-to-end against real corpus is in G6."""

    def test_returns_query_dsl_response(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        # Stub retrieve to return an empty result (no matches).
        empty_result = RetrievalResult(
            candidates=[],
            stages_used=["pattern_engine"],
            contextualization=Contextualization(
                observed_count=0,
                node_baselines=[],
                alternative_orderings=[],
                alternative_orderings_capped=False,
                null_distribution=None,
            ),
        )
        monkeypatch.setattr(
            "src.app.orchestration.retrieve", lambda *a, **kw: empty_result
        )

        # Use a lemma-only DSL so the empty registry doesn't matter for
        # validation (lemma nodes don't need registry lookup).
        resp = run_dsl_query("πίστις > ἐλπίς", fake_engine, empty_registry)

        assert isinstance(resp, QueryDSLResponse)
        assert resp.query == "πίστις > ἐλπίς"
        assert resp.validation.status in ("supported", "partial")
        assert resp.result is empty_result
        assert resp.explanation.summary  # non-empty deterministic prose
        assert resp.explanation.results == []  # no candidates

    def test_response_carries_match_candidate(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        token = MatchedToken(
            id=1,
            book="40",
            chapter=1,
            verse=1,
            position=0,
            global_position=0,
            surface_form="πίστις",
            normalized_form="πίστις",
            lemma="πίστις",
            pos="N",
        )
        candidate = MatchCandidate(
            tokens=[token],
            reference="Mat 1:1",
            match_type="exact",
            alignment=[
                StepMatch(
                    step_index=0,
                    node_type=NodeType.LEMMA,
                    node_value="πίστις",
                    resolved_lemmas=["πίστις"],
                    token=token,
                )
            ],
        )
        result = RetrievalResult(
            candidates=[candidate],
            stages_used=["pattern_engine"],
            contextualization=Contextualization(
                observed_count=1,
                node_baselines=[],
                alternative_orderings=[],
                alternative_orderings_capped=False,
                null_distribution=None,
            ),
        )
        monkeypatch.setattr(
            "src.app.orchestration.retrieve", lambda *a, **kw: result
        )

        resp = run_dsl_query("πίστις", fake_engine, empty_registry)

        assert len(resp.result.candidates) == 1
        assert resp.result.candidates[0].reference == "Mat 1:1"
        assert len(resp.explanation.results) == 1
