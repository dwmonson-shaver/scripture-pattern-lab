"""Tests for POST /api/v1/query/validate (src/app/routes/validate.py).

Validates DSL→ValidationResult mapping at the HTTP layer. Per DEC-079,
status="unsupported" is a 200 response (not 422) — only ParseError
on malformed DSL is a 422 path on this route.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.dependencies import get_concept_registry
from src.app.main import create_app
from src.ontology.registry import ConceptRegistry
from src.validation.validator import ValidationFinding, ValidationResult


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fastapi_app = create_app()
    fastapi_app.dependency_overrides[get_concept_registry] = (
        lambda: ConceptRegistry.empty()
    )
    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _stub_validation(
    status_value: str, findings: list[ValidationFinding] | None = None
) -> ValidationResult:
    return ValidationResult(
        status=status_value,  # type: ignore[arg-type]
        executable_plan=None,
        findings=findings or [],
        engine_version="0.1.0",
        grounding=None,
    )


class TestValidateHappyPath:
    def test_supported_status_returns_200(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.app.routes.validate.run_validate_only",
            lambda *a, **kw: _stub_validation("supported"),
        )
        resp = client.post("/api/v1/query/validate", json={"dsl": "πίστις"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "πίστις"
        assert body["validation"]["status"] == "supported"

    def test_partial_status_returns_200_with_findings(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        finding = ValidationFinding(
            severity="warning",
            code="UNSUPPORTED_EXPANSION",
            path="$.sequence",
            message="expansion not supported",
            remediation=None,
        )
        monkeypatch.setattr(
            "src.app.routes.validate.run_validate_only",
            lambda *a, **kw: _stub_validation("partial", [finding]),
        )
        resp = client.post(
            "/api/v1/query/validate", json={"dsl": "expand(faith)"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["validation"]["status"] == "partial"
        assert len(body["validation"]["findings"]) == 1
        assert body["validation"]["findings"][0]["code"] == "UNSUPPORTED_EXPANSION"


class TestValidateUnsupportedReturnsTwoHundredNotFourTwentyTwo:
    """DEC-079 — validate's contract is 'always return the verdict.'

    Status='unsupported' is information, not an HTTP error. The route
    must not translate it into 422; the caller branches on
    `body.validation.status`, not on HTTP code.
    """

    def test_unsupported_returns_200(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        finding = ValidationFinding(
            severity="error",
            code="UNSUPPORTED_INVERSE",
            path="$.sequence",
            message="inverse() is not supported in MVP",
            remediation=None,
        )
        monkeypatch.setattr(
            "src.app.routes.validate.run_validate_only",
            lambda *a, **kw: _stub_validation("unsupported", [finding]),
        )
        resp = client.post(
            "/api/v1/query/validate", json={"dsl": "inverse(faith)"}
        )
        assert resp.status_code == 200, (
            "DEC-079 violation: unsupported must be 200, not 422"
        )
        body = resp.json()
        assert body["validation"]["status"] == "unsupported"


class TestValidateParseError:
    def test_parse_error_returns_422(self, client: TestClient) -> None:
        # Real malformed DSL — exercise the actual parser, not a stub.
        resp = client.post(
            "/api/v1/query/validate", json={"dsl": "faith > > > hope"}
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error"] == "parse_error"
        assert "position" in body["detail"]["details"]


class TestValidateRequestValidation:
    def test_empty_dsl_rejected(self, client: TestClient) -> None:
        resp = client.post("/api/v1/query/validate", json={"dsl": ""})
        assert resp.status_code == 422

    def test_oversize_dsl_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/query/validate", json={"dsl": "a" * 10001}
        )
        assert resp.status_code == 422


class TestValidateNoExecutionFields:
    """Verify the response shape does NOT carry `result` or `explanation`.

    The /validate route is validation-only — including those fields
    would muddy the contract.
    """

    def test_response_shape_omits_result_and_explanation(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.app.routes.validate.run_validate_only",
            lambda *a, **kw: _stub_validation("supported"),
        )
        resp = client.post("/api/v1/query/validate", json={"dsl": "faith"})
        body = resp.json()
        assert set(body.keys()) == {"query", "validation"}
        assert "result" not in body
        assert "explanation" not in body
