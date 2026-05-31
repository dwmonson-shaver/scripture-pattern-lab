"""Tests for GET /api/v1/concepts/{name}/document (Slice N).

Overrides get_engine and monkeypatches the module-level get_document so no DB
is needed. Live-DB verification is the integration exit gate.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.app.dependencies import get_engine
from src.app.main import create_app
from src.ontology.concept_document import (
    ComparativeLexiconSection,
    ConceptDocument,
    LexiconComparisonRow,
)


def _document() -> ConceptDocument:
    return ConceptDocument(
        concept_name="humility",
        short_summary="Auto-created concept 'humility' ... unverified.",
        part1_comparative=ComparativeLexiconSection(
            english_term="humility",
            rows=[
                LexiconComparisonRow(
                    lemma="ταπεινοφροσύνη",
                    strongs=["G5012"],
                    usual_renderings=["humility"],
                    corpus_verse_refs=["Php 2:3"],
                )
            ],
            generated_from=["STEPBible TBESG (CC BY 4.0)"],
        ),
    )


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_engine] = lambda: MagicMock(name="engine")
    return TestClient(app)


class TestDocumentRoute:
    def test_returns_document_when_present(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.app.routes.concepts.get_document", lambda name, engine: _document()
        )
        resp = client.get("/api/v1/concepts/humility/document")
        assert resp.status_code == 200
        body = resp.json()
        assert body["concept_name"] == "humility"
        assert body["part1_comparative"]["rows"][0]["lemma"] == "ταπεινοφροσύνη"
        # Part 1 §2 (LLM) absent on the deterministic path; Part 2 absent.
        assert body["part1_educational"] is None
        assert body["part2_grouping"] is None
        assert body["part2_grouping_pointer"] is None

    def test_404_when_no_document(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.app.routes.concepts.get_document", lambda name, engine: None
        )
        resp = client.get("/api/v1/concepts/unknown/document")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "document_not_found"
