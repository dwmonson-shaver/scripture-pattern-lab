"""Slice P Phase 1 — evidence + promotion models (types only).

Covers the descriptive corpus-evidence models (EvidencePair, GroupingEvidence)
and the curator-promotion record + forward-only lifecycle map. No DB, no engine.

Epistemic invariants asserted here (DEC-120):
  * cooccurrence_threshold_met is a plain bool, NOT a verification/curator state.
  * GroupingEvidence carries no curator_state field — evidence never promotes.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.ontology.concept_grouping import (
    _ALLOWED_ADVANCE,
    CuratorState,
    PromotionRecord,
)
from src.retrieval.grouping_evidence import (
    DEFAULT_EVIDENCE_WINDOW_N,
    EVIDENCE_NOTE,
    EvidencePair,
    GroupingEvidence,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


class TestEvidencePair:
    def test_minimal_construction(self) -> None:
        p = EvidencePair(
            member_a="humility",
            member_b="meekness",
            lemma_a="ταπεινοφροσύνη",
            lemma_b="πραΰτης",
            match_count=3,
            sample_refs=["MAT 11:29", "EPH 4:2"],
            window_n=50,
        )
        assert p.match_count == 3
        assert p.is_declared_inverse is False
        assert p.cooccurrence_threshold_met is False

    def test_unresolved_member_carries_none_lemma_and_zero_count(self) -> None:
        # Bucket-N3 case: a member that resolved to no corpus lemma.
        p = EvidencePair(
            member_a="humility",
            member_b="lowliness",
            lemma_a="ταπεινοφροσύνη",
            lemma_b=None,
            match_count=0,
            window_n=50,
        )
        assert p.lemma_b is None
        assert p.match_count == 0
        assert p.sample_refs == []

    def test_negative_match_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EvidencePair(member_a="a", member_b="b", match_count=-1, window_n=50)

    def test_window_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            EvidencePair(member_a="a", member_b="b", match_count=0, window_n=0)

    def test_frozen(self) -> None:
        p = EvidencePair(member_a="a", member_b="b", match_count=0, window_n=50)
        with pytest.raises(ValidationError):
            p.match_count = 5  # type: ignore[misc]

    def test_threshold_met_is_a_plain_bool_not_a_state(self) -> None:
        # DEC-120: the deterministic signal is OFF the lifecycle axis.
        p = EvidencePair(
            member_a="a", member_b="b", match_count=9, window_n=50,
            cooccurrence_threshold_met=True,
        )
        assert isinstance(p.cooccurrence_threshold_met, bool)
        assert not hasattr(p, "curator_state")
        assert not hasattr(p, "verification_state")

    def test_json_round_trip(self) -> None:
        p = EvidencePair(
            member_a="humility", member_b="meekness", lemma_a="x", lemma_b="y",
            match_count=2, sample_refs=["MAT 11:29"], window_n=50,
            is_declared_inverse=True, cooccurrence_threshold_met=True,
        )
        assert EvidencePair.model_validate(p.model_dump(mode="json")) == p


class TestGroupingEvidence:
    def test_default_note_is_the_honest_framing(self) -> None:
        ev = GroupingEvidence(anchor_name="humility", window_n=DEFAULT_EVIDENCE_WINDOW_N)
        assert ev.computed_note == EVIDENCE_NOTE
        assert "NOT confirmation" in ev.computed_note
        assert ev.pairs == []

    def test_carries_no_curator_or_verification_state(self) -> None:
        ev = GroupingEvidence(anchor_name="humility", window_n=50)
        assert not hasattr(ev, "curator_state")
        assert not hasattr(ev, "verification_state")

    def test_frozen(self) -> None:
        ev = GroupingEvidence(anchor_name="humility", window_n=50)
        with pytest.raises(ValidationError):
            ev.window_n = 20  # type: ignore[misc]

    def test_json_round_trip_with_pairs(self) -> None:
        ev = GroupingEvidence(
            anchor_name="humility",
            window_n=50,
            pairs=[
                EvidencePair(member_a="humility", member_b="meekness",
                             match_count=3, window_n=50),
            ],
        )
        assert GroupingEvidence.model_validate(ev.model_dump(mode="json")) == ev


class TestPromotionRecord:
    def test_construction(self) -> None:
        rec = PromotionRecord(
            anchor_name="humility",
            from_state="unverified",
            to_state="corpus_observed",
            actor="curator:bearer-subject",
            rationale="Members co-occur in Eph 4:2 etc.; relevant.",
            evidence_snapshot={"anchor_name": "humility", "pairs": []},
            created_at=_now(),
        )
        assert rec.to_state == "corpus_observed"
        assert rec.evidence_snapshot["anchor_name"] == "humility"

    def test_empty_actor_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PromotionRecord(
                anchor_name="humility", from_state="unverified",
                to_state="corpus_observed", actor="", rationale="x",
                evidence_snapshot={}, created_at=_now(),
            )

    def test_empty_rationale_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PromotionRecord(
                anchor_name="humility", from_state="unverified",
                to_state="corpus_observed", actor="a", rationale="",
                evidence_snapshot={}, created_at=_now(),
            )

    def test_frozen(self) -> None:
        rec = PromotionRecord(
            anchor_name="humility", from_state="unverified",
            to_state="corpus_observed", actor="a", rationale="r",
            evidence_snapshot={}, created_at=_now(),
        )
        with pytest.raises(ValidationError):
            rec.to_state = "human_confirmed"  # type: ignore[misc]

    def test_json_round_trip(self) -> None:
        rec = PromotionRecord(
            anchor_name="humility", from_state="corpus_observed",
            to_state="human_confirmed", actor="a", rationale="r",
            evidence_snapshot={"k": "v"}, created_at=_now(),
        )
        assert PromotionRecord.model_validate(rec.model_dump(mode="json")) == rec


class TestAllowedAdvanceMap:
    def test_forward_only_chain(self) -> None:
        assert _ALLOWED_ADVANCE["unverified"] == {"corpus_observed"}
        assert _ALLOWED_ADVANCE["corpus_observed"] == {"human_confirmed"}
        assert _ALLOWED_ADVANCE["human_confirmed"] == set()

    def test_no_skip_unverified_to_human_confirmed(self) -> None:
        assert "human_confirmed" not in _ALLOWED_ADVANCE["unverified"]

    def test_no_demotion(self) -> None:
        for src, targets in _ALLOWED_ADVANCE.items():
            order = ["unverified", "corpus_observed", "human_confirmed"]
            for tgt in targets:
                assert order.index(tgt) > order.index(src)

    def test_covers_every_curator_state(self) -> None:
        # CuratorState is a Literal alias; its args are the three states.
        states = set(CuratorState.__args__)  # type: ignore[attr-defined]
        assert set(_ALLOWED_ADVANCE.keys()) == states
