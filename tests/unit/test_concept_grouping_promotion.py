"""Slice P Phase 5 — promote_grouping guards (DEC-126 anti-regression + DEC-120).

These are DB-free: the structural guards use signature introspection and the
argument validations all run BEFORE any DB access, so a sentinel engine is
never touched. The live promotion behaviour is in
tests/integration/test_grouping_promotions.py.

DEC-126: the promotion path must not weaken the auto-create/auto-group DEC-081
guard. Asserted here: write_grouping still takes no verification_state param;
Tier2Grouping still rejects any non-'unverified' literal; promote_grouping has
no parameter that could carry an elevated grouping blob.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.ontology.concept_grouping import (
    GroupingMember,
    Tier2Grouping,
    promote_grouping,
    write_grouping,
)

_VALID_SNAPSHOT = {"anchor_name": "humility", "pairs": []}


class TestDec126GuardNotWeakened:
    def test_write_grouping_has_no_verification_state_param(self) -> None:
        params = inspect.signature(write_grouping).parameters
        assert "verification_state" not in params

    def test_tier2grouping_still_rejects_non_unverified(self) -> None:
        with pytest.raises(ValidationError):
            Tier2Grouping(
                anchor_name="humility",
                members=[
                    GroupingMember(concept_name="humility", confidence=0.9),
                    GroupingMember(concept_name="meekness", confidence=0.9),
                ],
                rationale="r",
                verification_state="human_confirmed",  # type: ignore[arg-type]
                created_at=datetime.now(tz=UTC),
            )

    def test_promote_grouping_cannot_carry_a_grouping_blob(self) -> None:
        # The writer advances curator state via an audit row only; it accepts
        # no Tier2Grouping and no verification_state, so it cannot construct or
        # persist an elevated-state blob.
        params = set(inspect.signature(promote_grouping).parameters)
        assert params == {
            "anchor_name", "to_state", "actor", "rationale",
            "evidence_snapshot", "engine",
        }
        assert "verification_state" not in params
        assert "grouping" not in params


class TestPromoteArgumentValidation:
    """All raise BEFORE any DB access, so the sentinel engine is never used."""

    def test_rejects_unverified_as_target(self) -> None:
        with pytest.raises(ValueError, match="valid advance targets"):
            promote_grouping(
                "humility", to_state="unverified", actor="a", rationale="r",
                evidence_snapshot=_VALID_SNAPSHOT, engine=object(),  # type: ignore[arg-type]
            )

    def test_rejects_empty_actor(self) -> None:
        with pytest.raises(ValueError, match="human action"):
            promote_grouping(
                "humility", to_state="corpus_observed", actor="   ", rationale="r",
                evidence_snapshot=_VALID_SNAPSHOT, engine=object(),  # type: ignore[arg-type]
            )

    def test_rejects_empty_rationale(self) -> None:
        with pytest.raises(ValueError, match="rationale"):
            promote_grouping(
                "humility", to_state="corpus_observed", actor="a", rationale="",
                evidence_snapshot=_VALID_SNAPSHOT, engine=object(),  # type: ignore[arg-type]
            )

    def test_rejects_missing_evidence(self) -> None:
        with pytest.raises(ValueError, match="evidence-gated"):
            promote_grouping(
                "humility", to_state="corpus_observed", actor="a", rationale="r",
                evidence_snapshot={}, engine=object(),  # type: ignore[arg-type]
            )

    def test_rejects_evidence_anchor_mismatch(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            promote_grouping(
                "humility", to_state="corpus_observed", actor="a", rationale="r",
                evidence_snapshot={"anchor_name": "patience", "pairs": []},
                engine=object(),  # type: ignore[arg-type]
            )
