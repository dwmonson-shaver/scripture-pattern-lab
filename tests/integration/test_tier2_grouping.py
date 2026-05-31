"""Slice O exit gate — Tier-2 conceptual groupings end-to-end.

The slice's observable runnable surface: a Tier-2 grouping is written,
persisted, read back through the API, and the runtime DEC-081 guard
structurally blocks promotion to ``human_confirmed``.

Requires DATABASE_URL + corpus + lexicon loaded. Gated by
``@pytest.mark.integration``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
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

_NAMES = ("spl_exit_humility", "spl_exit_meekness", "spl_exit_lowliness")


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = get_engine()
    _cleanup(eng)
    # Seed three concepts + their (minimal) documents.
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
    for name in _NAMES:
        persist_document(
            ConceptDocument(
                concept_name=name,
                short_summary=f"exit-gate doc for {name}",
                part1_comparative=ComparativeLexiconSection(
                    english_term=name, rows=[], generated_from=[]
                ),
            ),
            eng,
        )
    yield eng
    _cleanup(eng)


def _cleanup(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM concepts WHERE name = ANY(:names)"),
            {"names": list(_NAMES)},
        )


def test_humility_grouping_persists_and_renders(engine: Engine) -> None:
    """The Slice O exit gate.

    1. Write a Tier-2 grouping with anchor + 2 members.
    2. Read it back through GET /api/v1/concepts/{anchor}/document — assert
       the response carries part2_grouping with all 3 members.
    3. Read a non-anchor member's document — assert it carries a pointer.
    4. Assert verification_state is 'unverified' on the persisted blob.
    5. Assert constructing a grouping with 'human_confirmed' raises
       ValidationError (Layer B-i DEC-081 guard).
    """
    # 1. write the grouping
    grouping = Tier2Grouping(
        anchor_name=_NAMES[0],
        members=[
            GroupingMember(concept_name=_NAMES[0], confidence=0.95),
            GroupingMember(concept_name=_NAMES[1], confidence=0.85),
            GroupingMember(concept_name=_NAMES[2], confidence=0.75),
        ],
        rationale="exit-gate humility cluster",
        created_at=datetime.now(tz=UTC),
    )
    write_grouping(grouping, engine)

    # 2. GET /api/v1/concepts/{anchor}/document carries the full grouping
    app = create_app()
    app.dependency_overrides[get_engine_dep] = lambda: engine
    client = TestClient(app)
    resp = client.get(f"/api/v1/concepts/{_NAMES[0]}/document")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["part2_grouping"] is not None
    assert body["part2_grouping_pointer"] is None
    assert body["part2_grouping"]["anchor_name"] == _NAMES[0]
    assert {m["concept_name"] for m in body["part2_grouping"]["members"]} == set(_NAMES)

    # 4. epistemic line over the wire
    assert body["part2_grouping"]["verification_state"] == "unverified"

    # 3. non-anchor member doc carries a pointer
    resp_member = client.get(f"/api/v1/concepts/{_NAMES[1]}/document")
    assert resp_member.status_code == 200, resp_member.text
    member_body = resp_member.json()
    assert member_body["part2_grouping"] is None
    assert member_body["part2_grouping_pointer"] is not None
    assert _NAMES[0] in member_body["part2_grouping_pointer"]["grouping_anchors"]


def test_dec_081_guard_rejects_human_confirmed_at_construction() -> None:
    """Layer B-i DEC-081 guard: Pydantic Literal blocks 'human_confirmed'.

    No DB needed — this is a pure model-validation invariant. It runs in the
    integration suite to document the slice exit gate end-to-end (the guard
    is the SLICE'S load-bearing epistemic invariant, not a unit-only concern).
    """
    with pytest.raises(ValidationError):
        Tier2Grouping(
            anchor_name="x",
            members=[
                GroupingMember(concept_name="x", confidence=0.5),
                GroupingMember(concept_name="y", confidence=0.5),
            ],
            rationale="must fail at construction",
            verification_state="human_confirmed",  # type: ignore[arg-type]
            created_at=datetime.now(tz=UTC),
        )
