"""Tests for GET /api/v1/health (src/app/routes/health.py)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.app.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return TestClient(create_app())


class TestHealthEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_returns_status_ok_body(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.json() == {"status": "ok"}

    def test_health_does_not_require_database(
        self, client: TestClient
    ) -> None:
        # Per DEC-G10, /health is liveness only — no DB ping. So
        # it must return 200 even with DATABASE_URL unset (covered
        # by the fixture's monkeypatch.delenv).
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_response_content_type(
        self, client: TestClient
    ) -> None:
        resp = client.get("/api/v1/health")
        assert resp.headers["content-type"] == "application/json"
