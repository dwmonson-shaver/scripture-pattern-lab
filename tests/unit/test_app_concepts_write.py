"""Tests for the concept create/edit routes (src/app/routes/concepts.py, Slice 1).

TestClient with get_engine overridden; the editor functions are monkeypatched
at the route module to drive each branch.
"""

from __future__ import annotations

from typing import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from src.app.dependencies import get_engine
from src.app.main import create_app
from src.ontology.concept_editor import ConceptExists, ConceptNotFound
from src.ontology.registry import Concept


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    fastapi_app = create_app()
    fastapi_app.dependency_overrides[get_engine] = lambda: MagicMock(
        spec=Engine, name="fake_engine"
    )
    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _concept(**kw: object) -> Concept:
    return Concept(
        id=kw.get("id", 1),  # type: ignore[arg-type]
        name=kw.get("name", "Hope"),  # type: ignore[arg-type]
        description=kw.get("description"),  # type: ignore[arg-type]
        origin="curated",
        verification_state="unverified",
        authored_color=kw.get("authored_color"),  # type: ignore[arg-type]
        authored_polarity=kw.get("authored_polarity"),  # type: ignore[arg-type]
        authored_opposite_name=kw.get("authored_opposite_name"),  # type: ignore[arg-type]
    )


class TestCreateRoute:
    def test_create_returns_201(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "src.app.routes.concepts.create_concept",
            lambda *_a, **_k: _concept(name="Hope", authored_polarity="+"),
        )
        resp = client.post(
            "/api/v1/concepts",
            json={"name": "Hope", "authored_polarity": "+", "authored_color": "#E0A12E"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Hope"
        assert body["verification_state"] == "unverified"

    def test_duplicate_returns_409(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_a: object, **_k: object) -> Concept:
            raise ConceptExists("concept 'Hope' already exists")

        monkeypatch.setattr("src.app.routes.concepts.create_concept", _raise)
        resp = client.post("/api/v1/concepts", json={"name": "Hope"})
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "concept_exists"

    def test_invalid_polarity_rejected_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/concepts", json={"name": "Hope", "authored_polarity": "x"}
        )
        assert resp.status_code == 422  # Pydantic Literal rejection


class TestUpdateRoute:
    def test_update_returns_200(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def _update(_engine: object, name: str, **fields: object) -> Concept:
            captured["name"] = name
            captured["fields"] = fields
            return _concept(name=name, authored_color="#fff")

        monkeypatch.setattr("src.app.routes.concepts.update_concept", _update)
        resp = client.patch("/api/v1/concepts/Hope", json={"authored_color": "#fff"})
        assert resp.status_code == 200
        # Only the provided field is forwarded (model_fields_set).
        assert captured["fields"] == {"authored_color": "#fff"}

    def test_update_missing_returns_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_a: object, **_k: object) -> Concept:
            raise ConceptNotFound("concept 'Nope' does not exist")

        monkeypatch.setattr("src.app.routes.concepts.update_concept", _raise)
        resp = client.patch("/api/v1/concepts/Nope", json={"description": "x"})
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "concept_not_found"
