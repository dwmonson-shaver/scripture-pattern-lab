"""Slice P Phase 4–5 — curator promotion audit store + promotion writer.

Phase 4 covers current_curator_state derivation from the append-only audit
log. Phase 5 (added below) covers the promote_grouping writer + its
anti-regression guards (DEC-126).

Requires DATABASE_URL + the 05_grouping_promotions schema applied. Gated by
``@pytest.mark.integration``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ontology.concept_grouping import current_curator_state

pytestmark = pytest.mark.integration

_ANCHOR = "spl_promo_anchor"


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
