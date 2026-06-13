"""Slice P exit gate — corpus-evidence + human curator promotion end-to-end.

The slice's observable runnable surface: a written grouping gets corpus
evidence surfaced on the document read, a human promotes it through
unverified -> corpus_observed -> human_confirmed via the HTTP API, the
document reflects the new curator_state with an audit trail, AND the grouping
blob's own verification_state stays 'unverified' over the wire (DEC-119/126).

Requires DATABASE_URL + corpus + lexicon loaded + the 05_grouping_promotions
schema applied. Gated by ``@pytest.mark.integration``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from src.app.dependencies import get_engine as get_engine_dep
from src.app.main import create_app
from src.ingestion.db import get_engine
from src.ontology.concept_document import (
    ComparativeLexiconSection,
    ConceptDocument,
    persist_document,
)
from src.ontology.concept_grouping import (
    GroupingMember,
    Tier2Grouping,
    write_grouping,
)

pytestmark = pytest.mark.integration

# Real NT lemmas so the evidence finder has something to measure.
_ANCHOR = "spl_p_faith"
_MEMBER = "spl_p_love"
_NAMES = (_ANCHOR, _MEMBER)
_LEMMAS = {_ANCHOR: "πίστις", _MEMBER: "ἀγάπη"}


@pytest.fixture()
def client() -> Iterator[TestClient]:
    eng = get_engine()
    _cleanup(eng)
    with eng.begin() as conn:
        for name in _NAMES:
            conn.execute(
                text(
                    "INSERT INTO concepts (name, origin, verification_state) "
                    "VALUES (:n, 'lexicon_imported', 'unverified') "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {"n": name},
            )
        for name, lemma in _LEMMAS.items():
            conn.execute(
                text(
                    "INSERT INTO concept_lemmas (concept_id, lemma, language, "
                    "origin, verification_state) SELECT id, :l, 'grc', "
                    "'lexicon_imported', 'unverified' FROM concepts WHERE name = :n "
                    "ON CONFLICT (lemma, language, concept_id) DO NOTHING"
                ),
                {"l": lemma, "n": name},
            )
    for name in _NAMES:
        persist_document(
            ConceptDocument(
                concept_name=name,
                short_summary=f"slice-P exit doc for {name}",
                part1_comparative=ComparativeLexiconSection(
                    english_term=name, rows=[], generated_from=[]
                ),
            ),
            eng,
        )
    write_grouping(
        Tier2Grouping(
            anchor_name=_ANCHOR,
            members=[
                GroupingMember(concept_name=_ANCHOR, confidence=0.9),
                GroupingMember(concept_name=_MEMBER, confidence=0.8),
            ],
            rationale="slice-P exit-gate cluster",
            created_at=datetime.now(tz=UTC),
        ),
        eng,
    )
    app = create_app()
    app.dependency_overrides[get_engine_dep] = lambda: eng
    yield TestClient(app)
    _cleanup(eng)


def _cleanup(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM grouping_promotions WHERE anchor_name = ANY(:n)"),
            {"n": list(_NAMES)},
        )
        conn.execute(
            text("DELETE FROM concepts WHERE name = ANY(:n)"), {"n": list(_NAMES)}
        )


def test_evidence_then_human_promotion_end_to_end(client: TestClient) -> None:
    # 1. Document read carries corpus evidence + born-unverified curator state.
    doc = client.get(f"/api/v1/concepts/{_ANCHOR}/document").json()
    assert doc["curator_state"] == "unverified"
    assert doc["grouping_evidence"] is not None
    assert doc["grouping_evidence"]["anchor_name"] == _ANCHOR
    assert "NOT confirmation" in doc["grouping_evidence"]["computed_note"]

    # 2. A human promotes one step at a time.
    r1 = client.post(
        f"/api/v1/concepts/{_ANCHOR}/grouping/promote",
        json={"to_state": "corpus_observed", "rationale": "members co-occur; relevant"},
    )
    assert r1.status_code == 200
    assert r1.json()["curator_state"] == "corpus_observed"
    assert r1.json()["audit_id"] is not None

    r2 = client.post(
        f"/api/v1/concepts/{_ANCHOR}/grouping/promote",
        json={"to_state": "human_confirmed", "rationale": "endorse the grouping"},
    )
    assert r2.status_code == 200
    assert r2.json()["curator_state"] == "human_confirmed"

    # 3. Document reflects the promoted curator_state...
    doc2 = client.get(f"/api/v1/concepts/{_ANCHOR}/document").json()
    assert doc2["curator_state"] == "human_confirmed"
    # ...but the grouping blob's OWN verification_state stays unverified (DEC-119/126).
    assert doc2["part2_grouping"]["verification_state"] == "unverified"


def test_illegal_skip_transition_is_409(client: TestClient) -> None:
    # Fresh grouping is 'unverified'; skipping straight to human_confirmed is illegal.
    resp = client.post(
        f"/api/v1/concepts/{_ANCHOR}/grouping/promote",
        json={"to_state": "human_confirmed", "rationale": "skip attempt"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "illegal_promotion"
