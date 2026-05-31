"""Integration tests for Tier-2 grouping writer + readers (Slice O, Phase O2).

Requires a live Postgres via DATABASE_URL with 02_concept_registry.sql +
04_concept_documents.sql applied. Gated by ``@pytest.mark.integration``.

DEC-115 Layer A enforcement is verified by introspecting ``write_grouping``'s
signature — there is no ``verification_state`` parameter. Layer B-i + B-ii
are covered by the unit tests on Tier2Grouping.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ontology.concept_document import (
    ComparativeLexiconSection,
    ConceptDocument,
    get_document,
    persist_document,
)
from src.ontology.concept_grouping import (
    GroupingMember,
    Tier2Grouping,
    read_grouping_for_anchor,
    read_grouping_pointer,
    write_grouping,
)

pytestmark = pytest.mark.integration

_NAMES = ("spl_test_humility", "spl_test_meekness", "spl_test_lowliness")


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = get_engine()
    _cleanup(eng)
    # Seed three concepts + their (minimal) documents up front so
    # write_grouping has a target.
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
    # Persist minimal Tier-1 documents for each (anchor must exist; member
    # pointers also need their doc to exist for the pointer to land).
    for name in _NAMES:
        persist_document(
            ConceptDocument(
                concept_name=name,
                short_summary=f"test doc for {name}",
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
        # concept_documents has FK ON DELETE CASCADE → concepts deletes cover both.
        conn.execute(
            text("DELETE FROM concepts WHERE name = ANY(:names)"),
            {"names": list(_NAMES)},
        )


def _humility_grouping() -> Tier2Grouping:
    return Tier2Grouping(
        anchor_name=_NAMES[0],
        members=[
            GroupingMember(concept_name=_NAMES[0], confidence=0.95),
            GroupingMember(concept_name=_NAMES[1], confidence=0.85),
            GroupingMember(concept_name=_NAMES[2], confidence=0.75),
        ],
        rationale="Humility-cluster test fixture",
        created_at=datetime.now(tz=UTC),
    )


class TestLayerAStructuralGuard:
    def test_write_grouping_has_no_verification_state_parameter(self) -> None:
        """DEC-115 Layer A: writer signature accepts NO verification_state arg."""
        sig = inspect.signature(write_grouping)
        assert "verification_state" not in sig.parameters
        # Sanity: only the documented params.
        assert set(sig.parameters.keys()) == {"grouping", "engine"}


class TestWriteAndRead:
    def test_writes_anchor_blob_round_trip(self, engine: Engine) -> None:
        g = _humility_grouping()
        write_grouping(g, engine)
        fetched = read_grouping_for_anchor(_NAMES[0], engine)
        assert fetched is not None
        assert fetched.anchor_name == _NAMES[0]
        assert {m.concept_name for m in fetched.members} == set(_NAMES)
        assert fetched.verification_state == "unverified"

    def test_non_anchor_members_get_pointer(self, engine: Engine) -> None:
        write_grouping(_humility_grouping(), engine)
        ptr1 = read_grouping_pointer(_NAMES[1], engine)
        ptr2 = read_grouping_pointer(_NAMES[2], engine)
        assert ptr1 is not None
        assert ptr2 is not None
        assert _NAMES[0] in ptr1.grouping_anchors
        assert _NAMES[0] in ptr2.grouping_anchors

    def test_anchor_does_not_get_pointer_to_itself(self, engine: Engine) -> None:
        write_grouping(_humility_grouping(), engine)
        # The anchor reads back its full grouping, NOT a pointer.
        assert read_grouping_pointer(_NAMES[0], engine) is None

    def test_idempotent_rewrite_same_payload(self, engine: Engine) -> None:
        g = _humility_grouping()
        write_grouping(g, engine)
        write_grouping(g, engine)  # no-op semantically; UPDATE in place
        # Pointer doesn't duplicate (we de-dupe anchor_name in pointer list).
        ptr = read_grouping_pointer(_NAMES[1], engine)
        assert ptr is not None
        assert ptr.grouping_anchors.count(_NAMES[0]) == 1

    def test_full_document_carries_grouping_and_pointer(
        self, engine: Engine
    ) -> None:
        """get_document populates the right field per concept role."""
        write_grouping(_humility_grouping(), engine)
        anchor_doc = get_document(_NAMES[0], engine)
        assert anchor_doc is not None
        assert anchor_doc.part2_grouping is not None
        assert anchor_doc.part2_grouping_pointer is None
        assert len(anchor_doc.part2_grouping.members) == 3

        member_doc = get_document(_NAMES[1], engine)
        assert member_doc is not None
        assert member_doc.part2_grouping is None
        assert member_doc.part2_grouping_pointer is not None
        assert _NAMES[0] in member_doc.part2_grouping_pointer.grouping_anchors


class TestErrorPaths:
    def test_missing_member_concept_raises(self, engine: Engine) -> None:
        g = Tier2Grouping(
            anchor_name=_NAMES[0],
            members=[
                GroupingMember(concept_name=_NAMES[0], confidence=0.95),
                GroupingMember(concept_name="spl_test_does_not_exist", confidence=0.5),
            ],
            rationale="missing member",
            created_at=datetime.now(tz=UTC),
        )
        with pytest.raises(ValueError) as exc:
            write_grouping(g, engine)
        assert "spl_test_does_not_exist" in str(exc.value)

    def test_anchor_doc_must_exist(self, engine: Engine) -> None:
        # Delete the anchor's document (concept survives).
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM concept_documents WHERE concept_name = :n"),
                {"n": _NAMES[0]},
            )
        with pytest.raises(ValueError) as exc:
            write_grouping(_humility_grouping(), engine)
        assert "anchor document" in str(exc.value)
