"""Integration tests for the worked-example Tier-2 grouping seed (Slice O Phase O4).

Requires a live Postgres via DATABASE_URL with corpus + lexicon loaded.
Gated by ``@pytest.mark.integration``.

These tests stand UP a real grouping against real lexicon recall — they
exercise Bucket-N3's narrow-recall reality and show the seed degrades
gracefully when individual members can't be resolved.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from scripts.db.seed_humility_grouping import HUMILITY_CLUSTER, seed_humility_grouping
from src.ingestion.db import get_engine
from src.ontology.concept_grouping import read_grouping_for_anchor

pytestmark = pytest.mark.integration

# Names match the seed script's intended cluster. We clean these between runs
# so the test is hermetic (matches the unique-per-test pattern used by the
# Slice-N integration tests).
_ALL_NAMES = [t for (t, _) in HUMILITY_CLUSTER]


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = get_engine()
    _cleanup(eng)
    yield eng
    _cleanup(eng)


def _cleanup(engine: Engine) -> None:
    # concept_documents has FK ON DELETE CASCADE → concepts deletes cover both.
    # concept_lemmas same.
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM concepts WHERE name = ANY(:names)"),
            {"names": _ALL_NAMES},
        )


def test_seed_runs_and_persists_grouping(engine: Engine) -> None:
    """End-to-end: seed runs, anchor doc carries the grouping."""
    result = seed_humility_grouping(engine)
    # Anchor must be reachable; even with Bucket-N3 narrow recall the lexicon
    # MUST resolve "humility" itself or the test environment is broken.
    assert result is not None, (
        "seed returned None — anchor 'humility' not in lexicon; "
        "is the lexicon loaded?"
    )
    anchor_name = HUMILITY_CLUSTER[0][0]
    assert result.anchor_name == anchor_name
    assert result.verification_state == "unverified"
    # Re-read from DB to confirm persistence.
    persisted = read_grouping_for_anchor(anchor_name, engine)
    assert persisted is not None
    assert persisted.anchor_name == anchor_name
    assert {m.concept_name for m in persisted.members} == {
        m.concept_name for m in result.members
    }


def test_seed_is_idempotent(engine: Engine) -> None:
    """Second run with same members is a documented no-op."""
    first = seed_humility_grouping(engine)
    assert first is not None
    second = seed_humility_grouping(engine)
    assert second is not None
    # Same member set; same anchor.
    assert {m.concept_name for m in first.members} == {
        m.concept_name for m in second.members
    }
    assert first.anchor_name == second.anchor_name
