"""Tests for GET /api/v1/concepts/{name}/document (Slice N).

Overrides get_engine and monkeypatches the module-level get_document so no DB
is needed. Live-DB verification is the integration exit gate.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
from src.ontology.concept_grouping import (
    GroupingMember,
    GroupingPointer,
    Tier2Grouping,
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


def _anchor_document() -> ConceptDocument:
    """A document for the grouping anchor — carries the full Tier2Grouping."""
    base = _document()
    grouping = Tier2Grouping(
        anchor_name="humility",
        members=[
            GroupingMember(concept_name="humility", confidence=0.95),
            GroupingMember(concept_name="meekness", confidence=0.85),
            GroupingMember(concept_name="lowliness", confidence=0.75),
        ],
        rationale="Humility cluster",
        created_at=datetime.now(tz=UTC),
    )
    return base.model_copy(update={"part2_grouping": grouping})


def _member_document() -> ConceptDocument:
    """A document for a non-anchor member — carries a GroupingPointer."""
    base = _document()
    pointer = GroupingPointer(grouping_anchors=["humility"])
    return base.model_copy(
        update={"concept_name": "meekness", "part2_grouping_pointer": pointer}
    )


class TestTier2GroupingThroughRoute:
    """Slice O Phase O3: existing route handler surfaces the new Tier-2 fields."""

    def test_anchor_doc_carries_full_grouping_in_response(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.app.routes.concepts.get_document",
            lambda name, engine: _anchor_document(),
        )
        resp = client.get("/api/v1/concepts/humility/document")
        assert resp.status_code == 200
        body = resp.json()
        assert body["part2_grouping"] is not None
        assert body["part2_grouping_pointer"] is None
        assert body["part2_grouping"]["anchor_name"] == "humility"
        assert {m["concept_name"] for m in body["part2_grouping"]["members"]} == {
            "humility",
            "meekness",
            "lowliness",
        }
        # Epistemic line over the wire: DEC-081 unverified ALWAYS.
        assert body["part2_grouping"]["verification_state"] == "unverified"

    def test_member_doc_carries_pointer_in_response(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.app.routes.concepts.get_document",
            lambda name, engine: _member_document(),
        )
        resp = client.get("/api/v1/concepts/meekness/document")
        assert resp.status_code == 200
        body = resp.json()
        assert body["part2_grouping"] is None
        assert body["part2_grouping_pointer"] is not None
        assert body["part2_grouping_pointer"]["grouping_anchors"] == ["humility"]

    def test_tier1_only_doc_returns_both_null(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Backward-compat: concepts not in any grouping return both fields null."""
        monkeypatch.setattr(
            "src.app.routes.concepts.get_document", lambda name, engine: _document()
        )
        resp = client.get("/api/v1/concepts/humility/document")
        assert resp.status_code == 200
        body = resp.json()
        assert body["part2_grouping"] is None
        assert body["part2_grouping_pointer"] is None
