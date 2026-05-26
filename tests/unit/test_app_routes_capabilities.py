"""Tests for GET /api/v1/capabilities (src/app/routes/capabilities.py).

Engine-free, registry-free, no DI overrides needed — the route returns
CapabilityRegistry.mvp() directly.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.main import create_app


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """App with all env vars unset; capabilities route doesn't need them."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


class TestCapabilitiesRoute:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/capabilities")
        assert resp.status_code == 200

    def test_body_contains_version(self, client: TestClient) -> None:
        resp = client.get("/api/v1/capabilities")
        body = resp.json()
        assert body["version"] == "0.1"

    def test_body_contains_mvp_field_values(self, client: TestClient) -> None:
        resp = client.get("/api/v1/capabilities")
        body = resp.json()
        assert body["polarity_support"] is True
        assert body["inverse_support"] is False
        assert body["expansion_support"] is False
        assert body["compound_node_support"] is False
        assert body["max_sequence_length"] == 10
        assert body["max_gap"] is None
        assert body["corpora"] == ["nt"]
        assert body["languages"] == ["grc"]
        assert "lemma" in body["node_types"]
        assert "concept" in body["node_types"]
        assert "precedence" in body["operators"]

    def test_body_contains_slice_l_proximity_fields(
        self, client: TestClient
    ) -> None:
        """Slice L: capabilities now advertises scope_units, window_max_tokens,
        and ``cooccurrence`` in operators (Decision #5)."""
        resp = client.get("/api/v1/capabilities")
        body = resp.json()
        assert body["scope_units"] == ["verse", "window"]
        assert body["window_max_tokens"] == 50
        assert "cooccurrence" in body["operators"]

    def test_json_content_type(self, client: TestClient) -> None:
        resp = client.get("/api/v1/capabilities")
        assert resp.headers["content-type"].startswith("application/json")

    def test_no_database_url_required(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The route must not depend on DATABASE_URL, so this works
        # even with the env var stripped.
        monkeypatch.delenv("DATABASE_URL", raising=False)
        resp = client.get("/api/v1/capabilities")
        assert resp.status_code == 200
