"""Tests for GET /api/v1/concepts (src/app/routes/concepts.py).

Uses dependency_overrides to inject a stubbed ConceptRegistry whose
list_all_concepts() returns canned ConceptSummary instances. Live-DB
verification covered at the integration exit gate.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.dependencies import get_concept_registry
from src.app.main import create_app
from src.ontology.registry import ConceptRegistry, ConceptSummary


class _StubRegistry(ConceptRegistry):
    """ConceptRegistry stub returning canned summaries."""

    def __init__(self, summaries: list[ConceptSummary]) -> None:
        super().__init__(engine=None)
        self._summaries = summaries
        self.last_language: str | None = None

    def list_all_concepts(self, language: str = "grc") -> list[ConceptSummary]:
        self.last_language = language
        return self._summaries


def _stub_summaries() -> list[ConceptSummary]:
    return [
        ConceptSummary(
            name="faith",
            description="trust + assurance",
            verification_state="unverified",
            lemma_count=2,
            lemmas=["πίστις", "πιστεύω"],
        ),
        ConceptSummary(
            name="hope",
            description="expectation",
            verification_state="unverified",
            lemma_count=1,
            lemmas=["ἐλπίς"],
        ),
        ConceptSummary(
            name="love",
            description="agape",
            verification_state="corpus_observed",
            lemma_count=2,
            lemmas=["ἀγάπη", "ἀγαπάω"],
        ),
    ]


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fastapi_app = create_app()
    fastapi_app.dependency_overrides[get_concept_registry] = (
        lambda: _StubRegistry(_stub_summaries())
    )
    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


class TestConceptsRoute:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/concepts")
        assert resp.status_code == 200

    def test_body_lists_three_concepts(self, client: TestClient) -> None:
        body = client.get("/api/v1/concepts").json()
        assert len(body["concepts"]) == 3
        names = {c["name"] for c in body["concepts"]}
        assert names == {"faith", "hope", "love"}

    def test_body_includes_lemmas_and_verification_state(
        self, client: TestClient
    ) -> None:
        body = client.get("/api/v1/concepts").json()
        love = next(c for c in body["concepts"] if c["name"] == "love")
        assert love["verification_state"] == "corpus_observed"
        assert "ἀγάπη" in love["lemmas"]
        assert love["lemma_count"] == 2

    def test_body_lemma_count_matches_lemmas(self, client: TestClient) -> None:
        body = client.get("/api/v1/concepts").json()
        for c in body["concepts"]:
            assert c["lemma_count"] == len(c["lemmas"])


class TestConceptsRouteEmptyRegistry:
    def test_empty_registry_returns_empty_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        fastapi_app = create_app()
        fastapi_app.dependency_overrides[get_concept_registry] = (
            lambda: _StubRegistry([])
        )
        with TestClient(fastapi_app) as c:
            resp = c.get("/api/v1/concepts")
        assert resp.status_code == 200
        assert resp.json() == {"concepts": []}


class TestConceptsRouteLanguageQuery:
    def test_default_language_is_grc(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        stub = _StubRegistry(_stub_summaries())
        fastapi_app = create_app()
        fastapi_app.dependency_overrides[get_concept_registry] = lambda: stub
        with TestClient(fastapi_app) as c:
            c.get("/api/v1/concepts")
        assert stub.last_language == "grc"

    def test_explicit_language_propagates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        stub = _StubRegistry(_stub_summaries())
        fastapi_app = create_app()
        fastapi_app.dependency_overrides[get_concept_registry] = lambda: stub
        with TestClient(fastapi_app) as c:
            c.get("/api/v1/concepts?language=heb")
        assert stub.last_language == "heb"


class TestConceptsRouteProvider503:
    def test_missing_registry_returns_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No DI override; lifespan saw no DATABASE_URL → state.registry = None.
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        fastapi_app = create_app()
        with TestClient(fastapi_app) as c:
            resp = c.get("/api/v1/concepts")
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "registry_unavailable"
