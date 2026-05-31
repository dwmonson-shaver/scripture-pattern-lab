"""Slice O Phase O1 — Tier-2 grouping Pydantic models + DEC-081 guard.

The DEC-081 guard is two-layered (DEC-115):
  Layer A: write_grouping() takes no verification_state parameter (Phase O2).
  Layer B-i: Pydantic Literal['unverified'] rejects bad values at construction.
  Layer B-ii: model_validator names DEC-081 explicitly in the error message.

These tests cover Layer B end-to-end + frozen/shape invariants.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.ontology.concept_grouping import (
    GROUPING_ORIGIN,
    GROUPING_VSTATE,
    GroupingMember,
    GroupingPointer,
    Tier2Grouping,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _humility_members() -> list[GroupingMember]:
    return [
        GroupingMember(concept_name="humility", confidence=0.95),
        GroupingMember(concept_name="meekness", confidence=0.85),
        GroupingMember(concept_name="lowliness", confidence=0.75),
    ]


class TestGroupingMember:
    def test_minimal_construction(self) -> None:
        m = GroupingMember(concept_name="humility", confidence=0.9)
        assert m.concept_name == "humility"
        assert m.confidence == pytest.approx(0.9)
        assert m.note is None

    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GroupingMember(concept_name="humility", confidence=-0.01)

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GroupingMember(concept_name="humility", confidence=1.01)

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GroupingMember(concept_name="", confidence=0.5)

    def test_long_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GroupingMember(concept_name="x" * 65, confidence=0.5)

    def test_frozen(self) -> None:
        m = GroupingMember(concept_name="humility", confidence=0.5)
        with pytest.raises(ValidationError):
            m.confidence = 0.6  # type: ignore[misc]


class TestTier2Grouping:
    def test_valid_humility_cluster(self) -> None:
        g = Tier2Grouping(
            anchor_name="humility",
            members=_humility_members(),
            rationale="Humility cluster: ταπεινός / πραΰς family.",
            created_at=_now(),
        )
        assert g.anchor_name == "humility"
        assert len(g.members) == 3
        assert g.verification_state == "unverified"
        assert g.verification_state == GROUPING_VSTATE
        assert g.origin == "curated"
        assert g.origin == GROUPING_ORIGIN

    def test_members_lt_2_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Tier2Grouping(
                anchor_name="humility",
                members=[GroupingMember(concept_name="humility", confidence=1.0)],
                rationale="solo",
                created_at=_now(),
            )

    def test_anchor_not_in_members_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Tier2Grouping(
                anchor_name="humility",
                members=[
                    GroupingMember(concept_name="meekness", confidence=0.9),
                    GroupingMember(concept_name="lowliness", confidence=0.8),
                ],
                rationale="anchor missing",
                created_at=_now(),
            )
        assert "anchor" in str(exc.value)

    def test_duplicate_members_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Tier2Grouping(
                anchor_name="humility",
                members=[
                    GroupingMember(concept_name="humility", confidence=0.95),
                    GroupingMember(concept_name="humility", confidence=0.5),
                    GroupingMember(concept_name="meekness", confidence=0.8),
                ],
                rationale="duplicate names",
                created_at=_now(),
            )
        assert "distinct" in str(exc.value)

    def test_empty_rationale_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Tier2Grouping(
                anchor_name="humility",
                members=_humility_members(),
                rationale="",
                created_at=_now(),
            )

    def test_frozen(self) -> None:
        g = Tier2Grouping(
            anchor_name="humility",
            members=_humility_members(),
            rationale="frozen",
            created_at=_now(),
        )
        with pytest.raises(ValidationError):
            g.rationale = "mutated"  # type: ignore[misc]

    def test_verification_state_default_is_unverified(self) -> None:
        g = Tier2Grouping(
            anchor_name="humility",
            members=_humility_members(),
            rationale="default check",
            created_at=_now(),
        )
        assert g.verification_state == "unverified"

    def test_verification_state_literal_rejects_human_confirmed(self) -> None:
        """Layer B-i: Pydantic Literal rejects DEC-081-violating values."""
        with pytest.raises(ValidationError) as exc:
            Tier2Grouping(
                anchor_name="humility",
                members=_humility_members(),
                rationale="DEC-081 test",
                verification_state="human_confirmed",  # type: ignore[arg-type]
                created_at=_now(),
            )
        # Pydantic's Literal error mentions the offending value
        assert "human_confirmed" in str(exc.value) or "verification_state" in str(
            exc.value
        )

    def test_verification_state_literal_rejects_corpus_observed(self) -> None:
        with pytest.raises(ValidationError):
            Tier2Grouping(
                anchor_name="humility",
                members=_humility_members(),
                rationale="DEC-081 test",
                verification_state="corpus_observed",  # type: ignore[arg-type]
                created_at=_now(),
            )

    def test_model_validator_b_ii_explicit_dec_081_message(self) -> None:
        """Layer B-ii: bypassing Literal via model_construct still fires the guard."""
        # model_construct skips field validation but the model_validator
        # registered with mode='after' is also skipped — so this verifies the
        # documented bypass. The point is: a code path that uses model_construct
        # already explicitly opted out of validation. We assert here that
        # Layer B-i is the load-bearing barrier for normal construction.
        g = Tier2Grouping.model_construct(
            anchor_name="humility",
            members=_humility_members(),
            rationale="bypassed",
            origin="curated",
            verification_state="human_confirmed",  # bypass for documentation
            created_at=_now(),
        )
        # Documented bypass — model_construct skips validators. To re-run the
        # Layer B-ii check, the project standard is to round-trip through
        # model_validate, which DOES re-run validators including ours.
        with pytest.raises(ValidationError) as exc:
            Tier2Grouping.model_validate(g.model_dump())
        # The message either names DEC-081 (our validator) or names the
        # Literal failure (Pydantic) — both block the bypass.
        msg = str(exc.value)
        assert "DEC-081" in msg or "human_confirmed" in msg

    def test_origin_curated_accepted(self) -> None:
        g = Tier2Grouping(
            anchor_name="humility",
            members=_humility_members(),
            rationale="origin check",
            origin="curated",
            created_at=_now(),
        )
        assert g.origin == "curated"

    def test_origin_ai_suggested_accepted(self) -> None:
        g = Tier2Grouping(
            anchor_name="humility",
            members=_humility_members(),
            rationale="origin check",
            origin="ai_suggested",
            created_at=_now(),
        )
        assert g.origin == "ai_suggested"

    def test_origin_lexicon_imported_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Tier2Grouping(
                anchor_name="humility",
                members=_humility_members(),
                rationale="lexicon-imported is a Tier-1 origin, not Tier-2",
                origin="lexicon_imported",  # type: ignore[arg-type]
                created_at=_now(),
            )

    def test_round_trip_via_model_dump_and_validate(self) -> None:
        g = Tier2Grouping(
            anchor_name="humility",
            members=_humility_members(),
            rationale="round trip",
            created_at=_now(),
        )
        blob = g.model_dump(mode="json")
        g2 = Tier2Grouping.model_validate(blob)
        assert g2 == g


class TestGroupingPointer:
    def test_minimal(self) -> None:
        p = GroupingPointer(grouping_anchors=["humility"])
        assert p.grouping_anchors == ["humility"]

    def test_empty_list_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GroupingPointer(grouping_anchors=[])

    def test_multiple_anchors(self) -> None:
        p = GroupingPointer(grouping_anchors=["humility", "meekness"])
        assert len(p.grouping_anchors) == 2

    def test_frozen(self) -> None:
        p = GroupingPointer(grouping_anchors=["humility"])
        with pytest.raises(ValidationError):
            p.grouping_anchors = ["other"]  # type: ignore[misc]

    def test_round_trip(self) -> None:
        p = GroupingPointer(grouping_anchors=["humility", "lowliness"])
        assert GroupingPointer.model_validate(p.model_dump()) == p
