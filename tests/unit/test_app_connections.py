"""Tests for the connection routes (src/app/routes/connections.py, Slice 2).

TestClient with get_engine overridden; the editor functions are monkeypatched at
the route module to drive each branch.
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
from src.ontology.connections import (
    Connection,
    ConnectionNotFound,
    InvalidConnection,
    UnknownConcept,
)


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


def _conn(**kw: object) -> Connection:
    return Connection(
        id=kw.get("id", 7),  # type: ignore[arg-type]
        note=kw.get("note"),  # type: ignore[arg-type]
        actor="local",
        members=kw.get("members", ["righteousness", "faith"]),  # type: ignore[arg-type]
        types=kw.get("types", ["interchange"]),  # type: ignore[arg-type]
    )


class TestCreateRoute:
    def test_create_returns_201(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def _create(_engine: object, **kw: object) -> Connection:
            captured.update(kw)
            return _conn()

        monkeypatch.setattr("src.app.routes.connections.create_connection", _create)
        resp = client.post(
            "/api/v1/connections",
            json={
                "member_names": ["righteousness", "faith"],
                "types": ["interchange"],
                "note": "Rom 1:17",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["members"] == ["righteousness", "faith"]
        assert body["types"] == ["interchange"]
        assert captured["member_names"] == ["righteousness", "faith"]

    def test_fewer_than_two_members_rejected_422_by_schema(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/api/v1/connections",
            json={"member_names": ["faith"], "types": ["sequence"]},
        )
        assert resp.status_code == 422

    def test_no_types_rejected_422_by_schema(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/connections",
            json={"member_names": ["faith", "hope"], "types": []},
        )
        assert resp.status_code == 422

    def test_invalid_connection_returns_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_a: object, **_k: object) -> Connection:
            raise InvalidConnection("unknown connection type(s): ['causation']")

        monkeypatch.setattr("src.app.routes.connections.create_connection", _raise)
        resp = client.post(
            "/api/v1/connections",
            json={"member_names": ["faith", "hope"], "types": ["causation"]},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "invalid_connection"

    def test_unknown_concept_returns_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_a: object, **_k: object) -> Connection:
            raise UnknownConcept("unknown concept name(s): ['hope']")

        monkeypatch.setattr("src.app.routes.connections.create_connection", _raise)
        resp = client.post(
            "/api/v1/connections",
            json={"member_names": ["faith", "hope"], "types": ["sequence"]},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "unknown_concept"


class TestListRoute:
    def test_list_returns_connections(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.app.routes.connections.list_connections",
            lambda _engine: [_conn(id=7), _conn(id=8, types=["sequence", "prerequisite"])],
        )
        resp = client.get("/api/v1/connections")
        assert resp.status_code == 200
        conns = resp.json()["connections"]
        assert len(conns) == 2
        assert conns[1]["types"] == ["sequence", "prerequisite"]


class TestDeleteRoute:
    def test_delete_returns_204(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def _delete(_engine: object, connection_id: int) -> None:
            captured["id"] = connection_id

        monkeypatch.setattr("src.app.routes.connections.delete_connection", _delete)
        resp = client.delete("/api/v1/connections/7")
        assert resp.status_code == 204
        assert resp.content == b""
        assert captured["id"] == 7

    def test_delete_missing_returns_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_a: object, **_k: object) -> None:
            raise ConnectionNotFound("connection 999 does not exist")

        monkeypatch.setattr("src.app.routes.connections.delete_connection", _raise)
        resp = client.delete("/api/v1/connections/999")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "connection_not_found"
