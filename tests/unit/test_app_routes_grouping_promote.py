"""Slice P Phase 6 — POST /api/v1/concepts/{name}/grouping/promote.

DB-free: overrides get_engine and monkeypatches the route module's
read_grouping_for_anchor / compute_grouping_evidence / promote_grouping so the
HTTP contract (status codes, body, error mapping) is exercised without a DB.
Live behaviour is covered by tests/integration/test_grouping_promotions.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.app.dependencies import get_engine
from src.app.main import create_app
from src.ontology.concept_grouping import GroupingMember, Tier2Grouping
from src.retrieval.grouping_evidence import GroupingEvidence


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_engine] = lambda: MagicMock(name="engine")
    return TestClient(app)


def _grouping() -> Tier2Grouping:
    return Tier2Grouping(
        anchor_name="humility",
        members=[
            GroupingMember(concept_name="humility", confidence=0.9),
            GroupingMember(concept_name="meekness", confidence=0.8),
        ],
        rationale="r",
        created_at=datetime.now(tz=UTC),
    )


def _patch(monkeypatch, *, grouping, promote):
    monkeypatch.setattr(
        "src.app.routes.concepts.read_grouping_for_anchor",
        lambda name, engine: grouping,
    )
    monkeypatch.setattr(
        "src.app.routes.concepts.compute_grouping_evidence",
        lambda g, engine: GroupingEvidence(anchor_name="humility", window_n=50),
    )
    monkeypatch.setattr("src.app.routes.concepts.promote_grouping", promote)


class TestPromoteRoute:
    def test_happy_path_returns_new_state(self, client, monkeypatch) -> None:
        def fake_promote(name, **kw):
            assert kw["to_state"] == "corpus_observed"
            assert kw["actor"]  # an actor is always recorded
            assert kw["evidence_snapshot"]["anchor_name"] == "humility"
            return SimpleNamespace(from_state="unverified", to_state="corpus_observed", id=7)

        _patch(monkeypatch, grouping=_grouping(), promote=fake_promote)
        resp = client.post(
            "/api/v1/concepts/humility/grouping/promote",
            json={"to_state": "corpus_observed", "rationale": "members co-occur"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["anchor_name"] == "humility"
        assert body["from_state"] == "unverified"
        assert body["curator_state"] == "corpus_observed"
        assert body["audit_id"] == 7

    def test_404_when_no_grouping(self, client, monkeypatch) -> None:
        _patch(monkeypatch, grouping=None, promote=lambda *a, **k: None)
        resp = client.post(
            "/api/v1/concepts/unknown/grouping/promote",
            json={"to_state": "corpus_observed", "rationale": "x"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "grouping_not_found"

    def test_409_on_illegal_transition(self, client, monkeypatch) -> None:
        def fake_promote(name, **kw):
            raise ValueError("illegal curator transition 'unverified' -> 'human_confirmed'")

        _patch(monkeypatch, grouping=_grouping(), promote=fake_promote)
        resp = client.post(
            "/api/v1/concepts/humility/grouping/promote",
            json={"to_state": "human_confirmed", "rationale": "skip attempt"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "illegal_promotion"

    def test_422_on_invalid_target_state(self, client, monkeypatch) -> None:
        # 'unverified' is not an allowed promotion target — schema rejects it.
        _patch(monkeypatch, grouping=_grouping(), promote=lambda *a, **k: None)
        resp = client.post(
            "/api/v1/concepts/humility/grouping/promote",
            json={"to_state": "unverified", "rationale": "x"},
        )
        assert resp.status_code == 422

    def test_422_on_empty_rationale(self, client, monkeypatch) -> None:
        _patch(monkeypatch, grouping=_grouping(), promote=lambda *a, **k: None)
        resp = client.post(
            "/api/v1/concepts/humility/grouping/promote",
            json={"to_state": "corpus_observed", "rationale": ""},
        )
        assert resp.status_code == 422
