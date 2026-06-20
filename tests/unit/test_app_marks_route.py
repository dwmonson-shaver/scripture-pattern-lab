"""Tests for the mark CRUD routes (src/app/routes/marks.py, Slice 1).

TestClient with get_engine overridden; marks service functions monkeypatched at
the route module.
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
from src.ontology.marks import Mark, MarkNotFound, UnknownConcept


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


def _mark(**kw: object) -> Mark:
    base = dict(
        id=1, corpus_id="nt", book="06", chapter=8, verse_start=24, verse_end=25,
        char_start=0, char_end=10, version_code="kjv", actor="local",
        concept_names=["Hope"],
    )
    base.update(kw)
    return Mark(**base)  # type: ignore[arg-type]


class TestCreate:
    def test_create_201(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.app.routes.marks.create_mark", lambda *_a, **_k: _mark())
        resp = client.post(
            "/api/v1/marks",
            json={
                "book": "rom", "chapter": 8, "verse_start": 24, "verse_end": 25,
                "char_start": 0, "char_end": 10, "version_code": "kjv",
                "concept_names": ["Hope"],
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["concept_names"] == ["Hope"]

    def test_unknown_book_404(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/marks",
            json={"book": "genesis", "chapter": 1, "verse_start": 1, "verse_end": 1,
                  "char_start": 0, "char_end": 5},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "book_not_found"

    def test_bad_span_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/marks",
            json={"book": "rom", "chapter": 1, "verse_start": 2, "verse_end": 1,
                  "char_start": 0, "char_end": 5},
        )
        assert resp.status_code == 422  # verse_end < verse_start

    def test_unknown_concept_422(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*_a: object, **_k: object) -> Mark:
            raise UnknownConcept("unknown concept name(s): ['Nope']")

        monkeypatch.setattr("src.app.routes.marks.create_mark", _raise)
        resp = client.post(
            "/api/v1/marks",
            json={"book": "rom", "chapter": 1, "verse_start": 1, "verse_end": 1,
                  "char_start": 0, "char_end": 5, "concept_names": ["Nope"]},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "unknown_concept"


class TestList:
    def test_list_marks(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "src.app.routes.marks.list_marks_for_chapter",
            lambda *_a, **_k: [_mark()],
        )
        resp = client.get("/api/v1/marks?corpus=nt&book=rom&chapter=8&version=kjv")
        assert resp.status_code == 200
        assert resp.json()["marks"][0]["id"] == 1


class TestUpdateDelete:
    def test_update_forwards_only_provided(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def _update(_engine: object, mark_id: int, **fields: object) -> Mark:
            captured["fields"] = fields
            return _mark(concept_names=["Love"])

        monkeypatch.setattr("src.app.routes.marks.update_mark", _update)
        resp = client.patch("/api/v1/marks/1", json={"concept_names": ["Love"]})
        assert resp.status_code == 200
        assert captured["fields"] == {"concept_names": ["Love"]}

    def test_update_missing_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*_a: object, **_k: object) -> Mark:
            raise MarkNotFound("mark 99 does not exist")

        monkeypatch.setattr("src.app.routes.marks.update_mark", _raise)
        resp = client.patch("/api/v1/marks/99", json={"char_end": 20})
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "mark_not_found"

    def test_delete_204(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.app.routes.marks.delete_mark", lambda *_a, **_k: None)
        resp = client.delete("/api/v1/marks/1")
        assert resp.status_code == 204

    def test_delete_missing_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*_a: object, **_k: object) -> None:
            raise MarkNotFound("mark 99 does not exist")

        monkeypatch.setattr("src.app.routes.marks.delete_mark", _raise)
        resp = client.delete("/api/v1/marks/99")
        assert resp.status_code == 404
