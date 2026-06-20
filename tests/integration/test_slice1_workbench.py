"""Slice 1 exit gate — the workbench round-trip (DEC-127..150).

DATABASE_URL-gated. Exercises the full concept-identification loop against a
live DB with schemas 06+07 applied and a KJV chapter ingested:

    ingest a KJV chapter (if not present)
      → create a concept (curated/unverified, authored color+polarity)
      → create a mark over a CROSS-VERSE span tied to that concept
      → list marks for the chapter → the mark + its concept come back
      → read the chapter → English + aligned Greek

Requires: ./scripts/db/apply_schemas.sh, the Greek corpus ingested, and a KJV
translation ingested (./scripts/ingest/fetch_kjv.sh + ingest_translation.py).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.app.main import create_app
from src.ingestion.db import get_engine
from src.ontology.concept_editor import create_concept, update_concept
from src.ontology.marks import (
    create_mark,
    delete_mark,
    list_marks_for_chapter,
)

pytestmark = pytest.mark.integration

_TEST_CONCEPT = "SliceOneTestConcept"


@pytest.fixture
def engine():  # noqa: ANN201
    return get_engine()


def _ensure_concept(engine) -> None:  # noqa: ANN001
    try:
        create_concept(
            engine,
            name=_TEST_CONCEPT,
            description="ephemeral test concept",
            authored_color="#E0A12E",
            authored_polarity="+",
            authored_opposite_name="Despair",
        )
    except Exception:  # noqa: BLE001 — already exists; ensure authored fields set
        update_concept(engine, _TEST_CONCEPT, authored_color="#E0A12E")


def test_workbench_round_trip(engine) -> None:  # noqa: ANN001
    _ensure_concept(engine)

    # Cross-verse mark (DEC-143): Romans 8:24–25, tied to the test concept.
    mark = create_mark(
        engine,
        corpus_id="nt",
        book="06",
        chapter=8,
        verse_start=24,
        verse_end=25,
        char_start=0,
        char_end=12,
        version_code="kjv",
        concept_names=[_TEST_CONCEPT],
    )
    try:
        assert mark.verse_start == 24 and mark.verse_end == 25
        assert mark.concept_names == [_TEST_CONCEPT]

        listed = list_marks_for_chapter(
            engine, corpus_id="nt", book="06", chapter=8, version_code="kjv"
        )
        assert any(
            m.id == mark.id and _TEST_CONCEPT in m.concept_names for m in listed
        )

        # Read the chapter via the live app: English + aligned Greek.
        with TestClient(create_app()) as client:
            resp = client.get("/api/v1/read/nt/rom/8?version=kjv")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert any(v["verse"] == 24 for v in body["verses"])
        assert any(len(v["greek_tokens"]) > 0 for v in body["verses"])
    finally:
        delete_mark(engine, mark.id)
