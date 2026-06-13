"""Slice P Phase 2 — corpus-evidence finder against a live corpus.

Seeds two concepts whose lemmas are known to co-occur in the NT (πίστις /
ἀγάπη, e.g. 1Cor 13:13) plus one member with no lemma, then asserts
compute_grouping_evidence reports real co-occurrence for the resolved pair and
zero-evidence for the unresolved one (Bucket-N3 case).

Requires DATABASE_URL + corpus + lexicon loaded. Gated by
``@pytest.mark.integration``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ontology.concept_grouping import GroupingMember, Tier2Grouping
from src.retrieval.grouping_evidence import compute_grouping_evidence

pytestmark = pytest.mark.integration

_FAITH = "spl_ev_faith"
_LOVE = "spl_ev_love"
_ORPHAN = "spl_ev_orphan"  # seeded with no lemma → unresolved
_NAMES = (_FAITH, _LOVE, _ORPHAN)
_LEMMAS = {_FAITH: "πίστις", _LOVE: "ἀγάπη"}  # _ORPHAN intentionally absent


@pytest.fixture()
def engine() -> Iterator[Engine]:
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
    yield eng
    _cleanup(eng)


def _cleanup(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM concepts WHERE name = ANY(:names)"),
            {"names": list(_NAMES)},
        )


def _grouping() -> Tier2Grouping:
    return Tier2Grouping(
        anchor_name=_FAITH,
        members=[GroupingMember(concept_name=n, confidence=0.9) for n in _NAMES],
        rationale="evidence integration cluster",
        created_at=datetime.now(tz=UTC),
    )


def test_resolved_pair_has_corpus_cooccurrence(engine: Engine) -> None:
    ev = compute_grouping_evidence(_grouping(), engine, window_n=50)
    assert ev.anchor_name == _FAITH
    assert len(ev.pairs) == 3  # C(3,2)
    faith_love = next(
        p for p in ev.pairs
        if {p.member_a, p.member_b} == {_FAITH, _LOVE}
    )
    assert faith_love.lemma_a is not None and faith_love.lemma_b is not None
    # πίστις and ἀγάπη co-occur within a 50-token window (e.g. 1Cor 13:13).
    assert faith_love.match_count >= 1
    assert faith_love.sample_refs  # at least one verse ref


def test_unresolved_member_yields_zero_evidence(engine: Engine) -> None:
    ev = compute_grouping_evidence(_grouping(), engine, window_n=50)
    orphan_pairs = [p for p in ev.pairs if _ORPHAN in (p.member_a, p.member_b)]
    assert orphan_pairs  # the orphan participates in pairs
    for p in orphan_pairs:
        # Bucket-N3: a member with no corpus lemma surfaces as zero-evidence.
        assert (p.lemma_a is None) or (p.lemma_b is None)
        assert p.match_count == 0
        assert p.cooccurrence_threshold_met is False
