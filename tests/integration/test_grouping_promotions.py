"""Slice P Phase 4–5 — curator promotion audit store + promotion writer.

Phase 4 covers current_curator_state derivation from the append-only audit
log. Phase 5 (added below) covers the promote_grouping writer + its
anti-regression guards (DEC-126).

Requires DATABASE_URL + the 05_grouping_promotions schema applied. Gated by
``@pytest.mark.integration``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ontology.concept_document import (
    ComparativeLexiconSection,
    ConceptDocument,
    persist_document,
)
from src.ontology.concept_grouping import (
    GroupingMember,
    Tier2Grouping,
    current_curator_state,
    promote_grouping,
    read_grouping_for_anchor,
    write_grouping,
)

pytestmark = pytest.mark.integration

_ANCHOR = "spl_promo_anchor"
# A second, fully-written grouping for the promotion-behaviour tests.
_G_ANCHOR = "spl_promo_g_anchor"
_G_MEMBER = "spl_promo_g_member"
_G_NAMES = (_G_ANCHOR, _G_MEMBER)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = get_engine()
    _cleanup(eng)
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO concepts (name, origin, verification_state) "
                "VALUES (:n, 'lexicon_imported', 'unverified') "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"n": _ANCHOR},
        )
    yield eng
    _cleanup(eng)


def _cleanup(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM grouping_promotions WHERE anchor_name = :n"),
            {"n": _ANCHOR},
        )
        conn.execute(text("DELETE FROM concepts WHERE name = :n"), {"n": _ANCHOR})


def _insert_promotion(engine: Engine, frm: str, to: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO grouping_promotions "
                "(anchor_name, from_state, to_state, actor, rationale, evidence_snapshot) "
                "VALUES (:a, :f, :t, 'tester', 'r', '{}'::jsonb)"
            ),
            {"a": _ANCHOR, "f": frm, "t": to},
        )


class TestCuratorStateDerivation:
    def test_no_rows_returns_unverified(self, engine: Engine) -> None:
        assert current_curator_state(_ANCHOR, engine) == "unverified"

    def test_single_promotion_reflected(self, engine: Engine) -> None:
        _insert_promotion(engine, "unverified", "corpus_observed")
        assert current_curator_state(_ANCHOR, engine) == "corpus_observed"

    def test_latest_row_wins(self, engine: Engine) -> None:
        _insert_promotion(engine, "unverified", "corpus_observed")
        _insert_promotion(engine, "corpus_observed", "human_confirmed")
        assert current_curator_state(_ANCHOR, engine) == "human_confirmed"


# ---------------------------------------------------------------------------
# Phase 5 — promote_grouping behaviour against a real written grouping.
# ---------------------------------------------------------------------------


@pytest.fixture()
def grouping_engine() -> Iterator[Engine]:
    eng = get_engine()
    _cleanup_grouping(eng)
    with eng.begin() as conn:
        for name in _G_NAMES:
            conn.execute(
                text(
                    "INSERT INTO concepts (name, origin, verification_state) "
                    "VALUES (:n, 'lexicon_imported', 'unverified') "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {"n": name},
            )
    for name in _G_NAMES:
        persist_document(
            ConceptDocument(
                concept_name=name,
                short_summary=f"promo doc for {name}",
                part1_comparative=ComparativeLexiconSection(
                    english_term=name, rows=[], generated_from=[]
                ),
            ),
            eng,
        )
    write_grouping(
        Tier2Grouping(
            anchor_name=_G_ANCHOR,
            members=[
                GroupingMember(concept_name=_G_ANCHOR, confidence=0.9),
                GroupingMember(concept_name=_G_MEMBER, confidence=0.8),
            ],
            rationale="promotion behaviour fixture",
            created_at=datetime.now(tz=UTC),
        ),
        eng,
    )
    yield eng
    _cleanup_grouping(eng)


def _cleanup_grouping(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM grouping_promotions WHERE anchor_name = ANY(:n)"),
            {"n": list(_G_NAMES)},
        )
        conn.execute(
            text("DELETE FROM concepts WHERE name = ANY(:n)"), {"n": list(_G_NAMES)}
        )


def _snapshot() -> dict:
    return {"anchor_name": _G_ANCHOR, "window_n": 50, "pairs": []}


class TestPromoteGrouping:
    def test_promote_through_both_states(self, grouping_engine: Engine) -> None:
        rec1 = promote_grouping(
            _G_ANCHOR, to_state="corpus_observed", actor="curator:test",
            rationale="members co-occur; relevant", evidence_snapshot=_snapshot(),
            engine=grouping_engine,
        )
        assert rec1.from_state == "unverified"
        assert rec1.to_state == "corpus_observed"
        assert current_curator_state(_G_ANCHOR, grouping_engine) == "corpus_observed"

        rec2 = promote_grouping(
            _G_ANCHOR, to_state="human_confirmed", actor="curator:test",
            rationale="endorse the grouping", evidence_snapshot=_snapshot(),
            engine=grouping_engine,
        )
        assert rec2.from_state == "corpus_observed"
        assert current_curator_state(_G_ANCHOR, grouping_engine) == "human_confirmed"

    def test_illegal_skip_transition_rejected(self, grouping_engine: Engine) -> None:
        with pytest.raises(ValueError, match="illegal curator transition"):
            promote_grouping(
                _G_ANCHOR, to_state="human_confirmed", actor="c",
                rationale="r", evidence_snapshot=_snapshot(), engine=grouping_engine,
            )

    def test_promote_nonexistent_grouping_rejected(self, grouping_engine: Engine) -> None:
        with pytest.raises(ValueError, match="no grouping anchored"):
            promote_grouping(
                _G_MEMBER, to_state="corpus_observed", actor="c", rationale="r",
                evidence_snapshot={"anchor_name": _G_MEMBER}, engine=grouping_engine,
            )

    def test_dec126_blob_verification_state_stays_unverified(
        self, grouping_engine: Engine
    ) -> None:
        # The promotion must NEVER touch the grouping blob (DEC-119/126).
        promote_grouping(
            _G_ANCHOR, to_state="corpus_observed", actor="c", rationale="r",
            evidence_snapshot=_snapshot(), engine=grouping_engine,
        )
        blob = read_grouping_for_anchor(_G_ANCHOR, grouping_engine)
        assert blob is not None
        assert blob.verification_state == "unverified"  # provenance unchanged
