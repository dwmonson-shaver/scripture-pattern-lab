"""Tests for HTTP wire schemas (src/app/schemas.py)."""

import pytest
from pydantic import ValidationError

from src.app.schemas import (
    ErrorResponse,
    QueryDSLRequest,
    QueryDSLResponse,
    QueryNLRequest,
    QueryNLResponse,
    TranslationMetadata,
)
from src.engine.models import ExplainedResultSet, RetrievalResult
from src.validation.validator import ValidationResult


class TestQueryDSLRequest:
    def test_construct(self) -> None:
        req = QueryDSLRequest(dsl="faith > hope > love")
        assert req.dsl == "faith > hope > love"

    def test_frozen(self) -> None:
        req = QueryDSLRequest(dsl="x")
        with pytest.raises(ValidationError):
            req.dsl = "y"

    def test_rejects_empty_dsl(self) -> None:
        with pytest.raises(ValidationError):
            QueryDSLRequest(dsl="")

    def test_rejects_missing_dsl(self) -> None:
        with pytest.raises(ValidationError):
            QueryDSLRequest()  # type: ignore[call-arg]

    def test_round_trip(self) -> None:
        req = QueryDSLRequest(dsl="faith > hope > love")
        restored = QueryDSLRequest.model_validate_json(req.model_dump_json())
        assert restored == req


class TestErrorResponse:
    def test_construct_minimal(self) -> None:
        err = ErrorResponse(error="parse_error", message="Unexpected token at position 5")
        assert err.error == "parse_error"
        assert err.details is None

    def test_construct_with_details(self) -> None:
        err = ErrorResponse(
            error="concept_not_mapped",
            message="Concept 'foo' has no lemmas",
            details={"concept_name": "foo"},
        )
        assert err.details == {"concept_name": "foo"}

    def test_frozen(self) -> None:
        err = ErrorResponse(error="x", message="y")
        with pytest.raises(ValidationError):
            err.error = "z"

    def test_dump_emits_null_details(self) -> None:
        # DEC-G8: nullable fields emit as null, not omitted.
        err = ErrorResponse(error="x", message="y")
        dumped = err.model_dump()
        assert dumped == {"error": "x", "message": "y", "details": None}

    def test_round_trip(self) -> None:
        err = ErrorResponse(
            error="unsupported_plan_shape",
            message="negation not allowed",
            details={"path": "$.sequence.steps[0]"},
        )
        restored = ErrorResponse.model_validate_json(err.model_dump_json())
        assert restored == err


class TestQueryDSLResponse:
    """The response envelope composes existing project models verbatim."""

    def _stub_validation(self) -> ValidationResult:
        return ValidationResult(
            status="supported",
            executable_plan=None,
            findings=[],
            engine_version="0.1.0",
            grounding=None,
        )

    def _stub_result(self) -> RetrievalResult:
        return RetrievalResult(
            candidates=[],
            stages_used=["pattern_engine"],
            contextualization=None,
        )

    def _stub_explanation(self) -> ExplainedResultSet:
        return ExplainedResultSet(
            query_shown="faith > hope > love",
            nl_source=None,
            validation_notes=[],
            results=[],
            contextualization=None,
            summary="No matches found.",
        )

    def test_compose(self) -> None:
        resp = QueryDSLResponse(
            query="faith > hope > love",
            validation=self._stub_validation(),
            result=self._stub_result(),
            explanation=self._stub_explanation(),
        )
        assert resp.query == "faith > hope > love"
        assert resp.validation.status == "supported"
        assert resp.result.stages_used == ["pattern_engine"]
        assert resp.explanation.summary == "No matches found."

    def test_frozen(self) -> None:
        resp = QueryDSLResponse(
            query="x",
            validation=self._stub_validation(),
            result=self._stub_result(),
            explanation=self._stub_explanation(),
        )
        with pytest.raises(ValidationError):
            resp.query = "y"

    def test_dump_emits_null_for_nullable_nested(self) -> None:
        # DEC-G8: null_distribution, contextualization, nl_source, grounding
        # all emit as `null` in the JSON body, not omitted keys.
        resp = QueryDSLResponse(
            query="x",
            validation=self._stub_validation(),
            result=self._stub_result(),
            explanation=self._stub_explanation(),
        )
        dumped = resp.model_dump()
        assert dumped["validation"]["grounding"] is None
        assert dumped["result"]["contextualization"] is None
        assert dumped["explanation"]["nl_source"] is None
        assert dumped["explanation"]["contextualization"] is None

    def test_round_trip(self) -> None:
        resp = QueryDSLResponse(
            query="x",
            validation=self._stub_validation(),
            result=self._stub_result(),
            explanation=self._stub_explanation(),
        )
        restored = QueryDSLResponse.model_validate_json(resp.model_dump_json())
        assert restored == resp


# -- NL-route schemas (Slice H) -----------------------------------------


class TestQueryNLRequest:
    def test_construct(self) -> None:
        req = QueryNLRequest(nl_query="what does Paul say about love?")
        assert req.nl_query == "what does Paul say about love?"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            QueryNLRequest(nl_query="")

    def test_rejects_over_max_length(self) -> None:
        # H-CLOSE-002: 2000-char cap on nl_query input bounds the unbounded
        # input that would otherwise reach the LLM unchecked.
        with pytest.raises(ValidationError):
            QueryNLRequest(nl_query="a" * 2001)

    def test_accepts_at_max_length(self) -> None:
        req = QueryNLRequest(nl_query="a" * 2000)
        assert len(req.nl_query) == 2000

    def test_frozen(self) -> None:
        req = QueryNLRequest(nl_query="x")
        with pytest.raises(ValidationError):
            req.nl_query = "y"


class TestTranslationMetadata:
    def test_construct(self) -> None:
        meta = TranslationMetadata(
            confidence=0.85,
            alternatives=["faith > hope", "hope > love"],
            explanation="three-step concept sequence",
        )
        assert meta.confidence == 0.85
        assert meta.alternatives == ["faith > hope", "hope > love"]
        assert meta.explanation == "three-step concept sequence"

    def test_frozen(self) -> None:
        meta = TranslationMetadata(confidence=1.0, alternatives=[], explanation="")
        with pytest.raises(ValidationError):
            meta.confidence = 0.5


class TestQueryNLResponseInheritance:
    @staticmethod
    def _stub_validation() -> ValidationResult:
        return ValidationResult(
            status="supported",
            executable_plan=None,
            findings=[],
            engine_version="0.1.0",
            grounding="prior-grounded",
        )

    def test_inherits_dsl_response_fields(self) -> None:
        # QueryNLResponse(QueryDSLResponse) — must accept the same query,
        # validation, result, explanation fields verbatim.
        from src.engine.models import Contextualization

        empty = RetrievalResult(
            candidates=[],
            stages_used=[],
            contextualization=Contextualization(
                observed_count=0,
                node_baselines=[],
                alternative_orderings=[],
                alternative_orderings_capped=False,
                null_distribution=None,
            ),
        )
        explanation = ExplainedResultSet(
            query_shown="faith",
            nl_source=None,
            validation_notes=[],
            results=[],
            contextualization=None,
            summary="empty",
        )
        meta = TranslationMetadata(confidence=0.9, alternatives=[], explanation="")

        resp = QueryNLResponse(
            query="faith",
            validation=self._stub_validation(),
            result=empty,
            explanation=explanation,
            translation=meta,
        )

        assert resp.query == "faith"
        assert resp.translation is meta
        assert resp.translation.confidence == 0.9
        # Subclass relation:
        assert isinstance(resp, QueryDSLResponse)
