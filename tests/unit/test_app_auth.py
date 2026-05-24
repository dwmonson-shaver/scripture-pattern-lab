"""Tests for the bearer-token auth middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.main import create_app


@pytest.fixture
def app_no_token(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """App with SPL_BEARER_TOKEN unset; middleware is a no-op."""
    monkeypatch.delenv("SPL_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return create_app()


@pytest.fixture
def app_with_token(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """App with SPL_BEARER_TOKEN configured; middleware enforces auth."""
    monkeypatch.setenv("SPL_BEARER_TOKEN", "test-token-abc123")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return create_app()


class TestBearerAuthMiddlewareNoToken:
    """When SPL_BEARER_TOKEN is unset, the middleware is a no-op."""

    def test_health_passes_without_auth_header(self, app_no_token: FastAPI) -> None:
        with TestClient(app_no_token) as client:
            response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_capabilities_passes_without_auth_header(
        self, app_no_token: FastAPI
    ) -> None:
        with TestClient(app_no_token) as client:
            response = client.get("/api/v1/capabilities")
        # /capabilities returns 200 even with no DB (capabilities are static).
        assert response.status_code == 200


class TestBearerAuthMiddlewareWithToken:
    """When SPL_BEARER_TOKEN is set, every non-health route requires it."""

    def test_health_always_unauthenticated(self, app_with_token: FastAPI) -> None:
        """Render's healthcheck must not need a token."""
        with TestClient(app_with_token) as client:
            response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_openapi_json_always_unauthenticated(self, app_with_token: FastAPI) -> None:
        """OpenAPI schema is conventionally public; the frontend's CI
        gen:types step depends on fetching it without a token."""
        with TestClient(app_with_token) as client:
            response = client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        assert body["openapi"].startswith("3.")
        assert "paths" in body

    def test_missing_authorization_header_returns_401(
        self, app_with_token: FastAPI
    ) -> None:
        with TestClient(app_with_token) as client:
            response = client.get("/api/v1/capabilities")
        assert response.status_code == 401
        body = response.json()
        assert body["detail"]["error"] == "unauthorized"
        assert "missing" in body["detail"]["message"].lower()

    def test_wrong_scheme_returns_401(self, app_with_token: FastAPI) -> None:
        with TestClient(app_with_token) as client:
            response = client.get(
                "/api/v1/capabilities",
                headers={"Authorization": "Basic dGVzdDp0ZXN0"},
            )
        assert response.status_code == 401
        body = response.json()
        assert body["detail"]["error"] == "unauthorized"
        assert "bearer" in body["detail"]["message"].lower()

    def test_wrong_token_returns_401(self, app_with_token: FastAPI) -> None:
        with TestClient(app_with_token) as client:
            response = client.get(
                "/api/v1/capabilities",
                headers={"Authorization": "Bearer wrong-token"},
            )
        assert response.status_code == 401
        body = response.json()
        assert body["detail"]["error"] == "unauthorized"
        assert "match" in body["detail"]["message"].lower()

    def test_matching_token_allows_request(self, app_with_token: FastAPI) -> None:
        with TestClient(app_with_token) as client:
            response = client.get(
                "/api/v1/capabilities",
                headers={"Authorization": "Bearer test-token-abc123"},
            )
        assert response.status_code == 200

    def test_lowercase_bearer_scheme_accepted(self, app_with_token: FastAPI) -> None:
        """Case-insensitive scheme match per RFC 7235."""
        with TestClient(app_with_token) as client:
            response = client.get(
                "/api/v1/capabilities",
                headers={"Authorization": "bearer test-token-abc123"},
            )
        assert response.status_code == 200

    def test_uppercase_bearer_scheme_accepted(self, app_with_token: FastAPI) -> None:
        with TestClient(app_with_token) as client:
            response = client.get(
                "/api/v1/capabilities",
                headers={"Authorization": "BEARER test-token-abc123"},
            )
        assert response.status_code == 200

    def test_401_uses_error_response_envelope(
        self, app_with_token: FastAPI
    ) -> None:
        """The 401 must match the project-wide error shape so the Worker
        proxy can dispatch UI off body.detail.error without special-casing.
        """
        with TestClient(app_with_token) as client:
            response = client.get("/api/v1/capabilities")
        body = response.json()
        assert "detail" in body
        assert set(body["detail"].keys()) == {"error", "message", "details"}
        assert body["detail"]["error"] == "unauthorized"
        assert body["detail"]["details"] is None
