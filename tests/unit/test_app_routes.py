"""Tests for POST /api/v1/query/dsl (src/app/routes/query.py).

All tests use FastAPI's TestClient with `dependency_overrides` so the
route doesn't touch a real database. Each test exercises one branch of
the design's exception→HTTP-status mapping (DEC-G6, DEC-G7).
End-to-end against the real corpus is covered by
tests/integration/test_app_dsl_route.py (G6).
"""

from __future__ import annotations

from typing import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from src.app.dependencies import get_concept_registry, get_engine
from src.app.main import create_app
from src.app.schemas import QueryDSLResponse
from src.engine.models import (
    ConceptNotMapped,
    Contextualization,
    RegistryRequired,
    RetrievalResult,
    UnsupportedPlanShape,
)
from src.ontology.registry import ConceptRegistry
from src.validation.validator import ValidationFinding, ValidationResult


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """App with engine + registry overridden so no DB is required."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    fastapi_app = create_app()
    fastapi_app.dependency_overrides[get_engine] = lambda: MagicMock(
        spec=Engine, name="fake_engine"
    )
    fastapi_app.dependency_overrides[get_concept_registry] = (
        lambda: ConceptRegistry.empty()
    )
    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _stub_response(query: str = "πίστις") -> QueryDSLResponse:
    """Build a minimal valid QueryDSLResponse for happy-path tests."""
    from src.engine.models import ExplainedResultSet

    return QueryDSLResponse(
        query=query,
        validation=ValidationResult(
            status="supported",
            executable_plan=None,
            findings=[],
            engine_version="0.1.0",
            grounding=None,
        ),
        result=RetrievalResult(
            candidates=[],
            stages_used=["pattern_engine"],
            contextualization=Contextualization(
                observed_count=0,
                node_baselines=[],
                alternative_orderings=[],
                alternative_orderings_capped=False,
                null_distribution=None,
            ),
        ),
        explanation=ExplainedResultSet(
            query_shown=query,
            nl_source=None,
            validation_notes=[],
            results=[],
            contextualization=None,
            summary="No matches found.",
        ),
    )


class TestRequestBodyValidation:
    """FastAPI default Pydantic validation for the request body."""

    def test_missing_dsl_returns_422(self, client: TestClient) -> None:
        resp = client.post("/api/v1/query/dsl", json={})
        assert resp.status_code == 422

    def test_empty_dsl_returns_422(self, client: TestClient) -> None:
        resp = client.post("/api/v1/query/dsl", json={"dsl": ""})
        assert resp.status_code == 422

    def test_non_json_body_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/query/dsl",
            content="not json",
            headers={"content-type": "application/json"},
        )
        # FastAPI returns 422 for bad JSON in pydantic v2
        assert resp.status_code in (400, 422)


class TestErrorMapping:
    """Each pipeline exception maps to its design-specified HTTP code."""

    def test_parse_error_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Real ParseError comes from a malformed DSL; the parser raises
        # for triple-operator. Use the real parser path.
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "faith > > > love"}
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "parse_error"
        assert "position" in body["detail"]["details"]
        assert "source" in body["detail"]["details"]

    def test_validation_unsupported_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # MVP capability registry rejects inverse() — natural unsupported.
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "inverse(faith > hope)"}
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "validation_unsupported"
        findings = body["detail"]["details"]["findings"]
        assert any(f["code"] == "UNSUPPORTED_INVERSE" for f in findings)

    def test_unsupported_plan_shape_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise UnsupportedPlanShape(
                "negation not allowed", path="$.sequence.steps[0]"
            )

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "πίστις > ἐλπίς"}
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "unsupported_plan_shape"
        assert body["detail"]["details"]["path"] == "$.sequence.steps[0]"

    def test_concept_not_mapped_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise ConceptNotMapped("fortitude")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "πίστις > ἐλπίς"}
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "concept_not_mapped"
        assert body["detail"]["details"]["concept_name"] == "fortitude"

    def test_registry_required_returns_503(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise RegistryRequired("faith")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "πίστις > ἐλπίς"}
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "registry_required"
        assert body["detail"]["details"]["concept_name"] == "faith"

    def test_uncaught_exception_returns_500(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise RuntimeError("connection refused")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "πίστις > ἐλπίς"}
        )
        assert resp.status_code == 500
        body = resp.json()
        assert body["detail"]["error"] == "internal_error"
        # Generic message — no leak of internal exception text.
        assert "connection refused" not in body["detail"]["message"]


class TestHappyPath:
    """When run_dsl_query succeeds, the route returns 200 + the envelope."""

    def test_returns_200_and_envelope(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        canned = _stub_response(query="πίστις")
        monkeypatch.setattr(
            "src.app.routes.query.run_dsl_query",
            lambda *args, **kwargs: canned,
        )
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "πίστις"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "πίστις"
        assert body["validation"]["status"] == "supported"
        assert body["result"]["stages_used"] == ["pattern_engine"]
        assert body["explanation"]["summary"] == "No matches found."

    def test_response_emits_null_for_nullable_fields(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # DEC-G8: nullable fields emit as null, not omitted.
        canned = _stub_response()
        monkeypatch.setattr(
            "src.app.routes.query.run_dsl_query",
            lambda *args, **kwargs: canned,
        )
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "πίστις"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["validation"]["grounding"] is None
        assert body["result"]["contextualization"]["null_distribution"] is None
        assert body["explanation"]["nl_source"] is None
        assert body["explanation"]["contextualization"] is None

    def test_partial_validation_returns_200_with_findings(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # status='partial' is a 200 with warnings carried in validation.findings.
        canned = _stub_response()
        partial = canned.model_copy(
            update={
                "validation": ValidationResult(
                    status="partial",
                    executable_plan=None,
                    findings=[
                        ValidationFinding(
                            severity="warning",
                            code="PARTIAL_REDUCTION",
                            path="$",
                            message="reduced expansion directive",
                            remediation=None,
                        )
                    ],
                    engine_version="0.1.0",
                    grounding="prior-grounded",
                )
            }
        )
        monkeypatch.setattr(
            "src.app.routes.query.run_dsl_query",
            lambda *args, **kwargs: partial,
        )
        resp = client.post(
            "/api/v1/query/dsl", json={"dsl": "πίστις"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["validation"]["status"] == "partial"
        assert len(body["validation"]["findings"]) == 1
        assert body["validation"]["grounding"] == "prior-grounded"


class TestRouteRegistration:
    def test_route_is_registered(self, app: FastAPI) -> None:
        paths = {route.path for route in app.routes if hasattr(route, "path")}
        assert "/api/v1/query/dsl" in paths
        assert "/api/v1/health" in paths
