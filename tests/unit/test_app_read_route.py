"""Tests for the chapter-read routes (src/app/routes/read.py, Slice 1).

TestClient with get_engine overridden so no real DB is touched; the reader
functions are monkeypatched at the route module to drive each branch.
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
from src.retrieval.reader import (
    ChapterNotFound,
    ChapterRead,
    ChapterVerse,
    GreekToken,
    VersionInfo,
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


def test_engine_unavailable_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    fastapi_app = create_app()  # no engine override → app.state.engine is None
    with TestClient(fastapi_app) as c:
        resp = c.get("/api/v1/read/versions")
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "engine_unavailable"


def test_versions_happy(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.app.routes.read.list_versions",
        lambda _engine: [
            VersionInfo(code="kjv", name="King James Version", is_public_domain=True)
        ],
    )
    resp = client.get("/api/v1/read/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["versions"][0]["code"] == "kjv"


def test_unknown_book_returns_404(client: TestClient) -> None:
    resp = client.get("/api/v1/read/nt/genesis/1")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "book_not_found"


def test_empty_chapter_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*_args: object, **_kwargs: object) -> ChapterRead:
        raise ChapterNotFound("no verses")

    monkeypatch.setattr("src.app.routes.read.read_chapter", _raise)
    resp = client.get("/api/v1/read/nt/rom/99")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "chapter_empty"


def test_chapter_happy(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _read(*_args: object, **_kwargs: object) -> ChapterRead:
        return ChapterRead(
            corpus_id="nt",
            book="06",
            book_display="Rom",
            chapter=8,
            version_code="kjv",
            verses=[
                ChapterVerse(
                    verse=24,
                    reference="Rom 8:24",
                    english_text="For we are saved by hope:",
                    greek_tokens=[
                        GreekToken(
                            position=1,
                            surface_form="ἐλπίς",
                            normalized_form="ἐλπίς",
                            lemma="ἐλπίς",
                            morph_code="N-",
                            pos="N-",
                        )
                    ],
                )
            ],
        )

    monkeypatch.setattr("src.app.routes.read.read_chapter", _read)
    resp = client.get("/api/v1/read/nt/rom/8?version=kjv")
    assert resp.status_code == 200
    body = resp.json()
    assert body["book_display"] == "Rom"
    assert body["verses"][0]["reference"] == "Rom 8:24"
    assert body["verses"][0]["greek_tokens"][0]["lemma"] == "ἐλπίς"
