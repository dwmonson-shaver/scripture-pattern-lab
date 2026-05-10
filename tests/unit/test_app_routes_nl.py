"""Tests for POST /api/v1/query/nl (src/app/routes/nl.py).

Pattern matches tests/unit/test_app_routes.py: FastAPI TestClient with
app.dependency_overrides for the four DI providers (engine, registry,
llm_client, translation_context) plus monkeypatch.setattr against the
import-binding inside src.app.orchestration for run_nl_query's deeper
calls.

End-to-end against a real LLM is covered by
tests/integration/test_app_nl_route_live_llm.py (H5; gated by live_llm
marker + ANTHROPIC_API_KEY).
"""

from __future__ import annotations

from typing import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from src.app.dependencies import (
    get_concept_registry,
    get_engine,
    get_llm_client,
    get_translation_context,
)
from src.app.main import create_app
from src.app.orchestration import ValidationUnsupported
from src.app.schemas import QueryNLResponse, TranslationMetadata
from src.engine.models import (
    ConceptNotMapped,
    Contextualization,
    ExplainedResultSet,
    RegistryRequired,
    RetrievalResult,
    UnsupportedPlanShape,
)
from src.engine.parser import ParseError
from src.nlp.llm_client import LLMClient, LLMUnavailable
from src.nlp.translator import (
    NLCompileError,
    TranslationContext,
)
from src.ontology.registry import ConceptRegistry
from src.validation.validator import ValidationFinding, ValidationResult


def _stub_translation_context() -> TranslationContext:
    return TranslationContext(
        capability_registry_summary="cap-summary",
        concept_registry_summary="concepts: faith, hope, love",
    )


def _stub_validation() -> ValidationResult:
    return ValidationResult(
        status="supported",
        executable_plan=None,
        findings=[],
        engine_version="0.1.0",
        grounding="prior-grounded",
    )


def _stub_result() -> RetrievalResult:
    return RetrievalResult(
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


def _stub_explanation() -> ExplainedResultSet:
    return ExplainedResultSet(
        query_shown="faith",
        nl_source=None,
        validation_notes=[],
        results=[],
        contextualization=None,
        summary="No matches found.",
    )


def _stub_nl_response(query: str = "faith") -> QueryNLResponse:
    return QueryNLResponse(
        query=query,
        validation=_stub_validation(),
        result=_stub_result(),
        explanation=_stub_explanation(),
        translation=TranslationMetadata(
            confidence=0.9,
            alternatives=[],
            explanation="single-step concept",
        ),
    )


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """App with all four DI providers overridden so no real DB / LLM is needed."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fastapi_app = create_app()
    fastapi_app.dependency_overrides[get_engine] = lambda: MagicMock(
        spec=Engine, name="fake_engine"
    )
    fastapi_app.dependency_overrides[get_concept_registry] = (
        lambda: ConceptRegistry.empty()
    )
    fastapi_app.dependency_overrides[get_llm_client] = (
        lambda: MagicMock(spec=LLMClient, name="fake_llm_client")
    )
    fastapi_app.dependency_overrides[get_translation_context] = _stub_translation_context
    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


class TestHappyPath:
    def test_returns_query_nl_response(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.app.routes.nl.run_nl_query",
            lambda *args, **kwargs: _stub_nl_response("faith"),
        )
        resp = client.post(
            "/api/v1/query/nl",
            json={"nl_query": "what is faith in Paul?"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "faith"
        assert body["translation"]["confidence"] == 0.9
        assert body["translation"]["alternatives"] == []
        assert body["translation"]["explanation"] == "single-step concept"

    def test_request_validation_rejects_empty(self, client: TestClient) -> None:
        # FastAPI default 422 for Pydantic body validation.
        resp = client.post("/api/v1/query/nl", json={"nl_query": ""})
        assert resp.status_code == 422


class TestErrorMappingTranslatorSide:
    def test_llm_unavailable_returns_503(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise LLMUnavailable("APIConnectionError: refused")

        monkeypatch.setattr("src.app.routes.nl.run_nl_query", boom)
        resp = client.post("/api/v1/query/nl", json={"nl_query": "any"})
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "llm_unavailable"
        assert body["detail"]["details"]["reason"] == "APIConnectionError: refused"

    def test_nl_compile_error_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise NLCompileError(
                nl_query="vague",
                attempted_output="I cannot translate this.",
                reason="LLM output did not contain a 'DSL:' line",
            )

        monkeypatch.setattr("src.app.routes.nl.run_nl_query", boom)
        resp = client.post("/api/v1/query/nl", json={"nl_query": "vague"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "nl_compile_error"
        assert body["detail"]["details"]["nl_query"] == "vague"
        assert body["detail"]["details"]["attempted_output"] == (
            "I cannot translate this."
        )


class TestErrorMappingDownstreamPipeline:
    def test_parse_error_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Translator emits "DSL" that fails the parser → ParseError propagates
        # from run_nl_query → route maps to 422 parse_error.
        def boom(*args: object, **kwargs: object) -> None:
            raise ParseError("Unexpected token at position 5", pos=5, source="bad dsl")

        monkeypatch.setattr("src.app.routes.nl.run_nl_query", boom)
        resp = client.post("/api/v1/query/nl", json={"nl_query": "any"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "parse_error"
        assert body["detail"]["details"]["position"] == 5

    def test_validation_unsupported_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Translator emits DSL that parses but is rejected by the validator
        # (e.g., inverse() in MVP). ValidationUnsupported propagates from
        # run_nl_query → route maps to 422 validation_unsupported with the
        # findings list embedded.
        finding = ValidationFinding(
            severity="error",
            code="UNSUPPORTED_INVERSE",
            path="$.sequence",
            message="inverse() is not supported in MVP",
            remediation=None,
        )
        validation = ValidationResult(
            status="unsupported",
            executable_plan=None,
            findings=[finding],
            engine_version="0.1.0",
            grounding=None,
        )

        def boom(*args: object, **kwargs: object) -> None:
            raise ValidationUnsupported(validation)

        monkeypatch.setattr("src.app.routes.nl.run_nl_query", boom)
        resp = client.post("/api/v1/query/nl", json={"nl_query": "any"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "validation_unsupported"
        assert len(body["detail"]["details"]["findings"]) == 1
        assert body["detail"]["details"]["findings"][0]["code"] == "UNSUPPORTED_INVERSE"

    def test_unsupported_plan_shape_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise UnsupportedPlanShape("negation", path="$.sequence.steps[0]")

        monkeypatch.setattr("src.app.routes.nl.run_nl_query", boom)
        resp = client.post("/api/v1/query/nl", json={"nl_query": "any"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "unsupported_plan_shape"
        assert body["detail"]["details"]["path"] == "$.sequence.steps[0]"

    def test_concept_not_mapped_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise ConceptNotMapped(concept_name="floob")

        monkeypatch.setattr("src.app.routes.nl.run_nl_query", boom)
        resp = client.post("/api/v1/query/nl", json={"nl_query": "any"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "concept_not_mapped"
        assert body["detail"]["details"]["concept_name"] == "floob"

    def test_registry_required_returns_503(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise RegistryRequired(concept_name="faith")

        monkeypatch.setattr("src.app.routes.nl.run_nl_query", boom)
        resp = client.post("/api/v1/query/nl", json={"nl_query": "any"})
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "registry_required"
        assert body["detail"]["details"]["concept_name"] == "faith"

    def test_uncaught_exception_returns_500(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise RuntimeError("simulated 4xx anthropic.BadRequestError-equivalent")

        monkeypatch.setattr("src.app.routes.nl.run_nl_query", boom)
        resp = client.post("/api/v1/query/nl", json={"nl_query": "any"})
        assert resp.status_code == 500
        body = resp.json()
        assert body["detail"]["error"] == "internal_error"
        # No traceback leaks in the response.
        assert "RuntimeError" not in body["detail"]["message"]
        assert "simulated" not in body["detail"]["message"]


class TestProvider503WhenStateMissing:
    """If lifespan didn't construct llm_client/context (ANTHROPIC_API_KEY unset),
    the provider raises 503 before run_nl_query is ever called."""

    def test_missing_llm_client_returns_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        fastapi_app = create_app()
        # Override only engine + registry; leave llm_client + context default (None).
        fastapi_app.dependency_overrides[get_engine] = lambda: MagicMock(
            spec=Engine, name="fake_engine"
        )
        fastapi_app.dependency_overrides[get_concept_registry] = (
            lambda: ConceptRegistry.empty()
        )

        with TestClient(fastapi_app) as c:
            resp = c.post("/api/v1/query/nl", json={"nl_query": "any"})

        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "llm_unavailable"
