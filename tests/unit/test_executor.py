"""Unit tests for ``src/engine/executor.py``.

Pure unit tests with stub engine / stub registry — no DB. The shape
validation in ``execute()`` raises before any SQL is issued, so these
tests exercise the validation contract without a real Postgres.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.engine.executor import execute
from src.engine.models import (
    AlternativeExpr,
    GapConstraint,
    InverseExpr,
    NodeRef,
    NodeType,
    OperatorType,
    OptionalExpr,
    OrderOperator,
    QueryPlan,
    RegistryRequired,
    ScopeConstraint,
    ScopeUnit,
    SequenceExpr,
    UnsupportedPlanShape,
)


def _make_engine() -> Any:
    """Stub engine — connect() context never opens for shape failures."""
    return MagicMock()


def _make_plan(
    sequence: SequenceExpr | InverseExpr,
    scope: ScopeConstraint | None = None,
) -> QueryPlan:
    return QueryPlan(
        version="0.1",
        source="<test>",
        sequence=sequence,
        scope=scope or ScopeConstraint(),
        mode="exact",
    )


def test_raises_unsupported_on_inverse_plan() -> None:
    """InverseExpr at the top level is rejected outright."""
    inner = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
    )
    plan = _make_plan(InverseExpr(inner=inner))
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "InverseExpr" in str(excinfo.value)
    assert excinfo.value.path == "$.sequence"


def test_raises_unsupported_on_alternative_step() -> None:
    """AlternativeExpr step is outside the MVP contract."""
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            AlternativeExpr(
                options=[
                    NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
                    NodeRef(type=NodeType.LEMMA, value="μακροθυμία"),
                ]
            ),
        ],
        operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert excinfo.value.path == "$.sequence.steps[1]"


def test_raises_unsupported_on_optional_step() -> None:
    """OptionalExpr step is outside the MVP contract."""
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            OptionalExpr(inner=NodeRef(type=NodeType.LEMMA, value="ἐλπίς")),
        ],
        operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape):
        execute(plan, plan.scope, _make_engine())


def test_raises_unsupported_on_wildcard_node() -> None:
    """NodeType.WILDCARD is not supported — only LEMMA and CONCEPT."""
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.WILDCARD, value="*"),
        ],
        operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "wildcard" in str(excinfo.value).lower()


def test_raises_unsupported_on_root_node() -> None:
    """NodeType.ROOT is not supported either."""
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.ROOT, value="אמן")],
        operators=[],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape):
        execute(plan, plan.scope, _make_engine())


def test_raises_unsupported_on_adjacency_operator() -> None:
    """OperatorType.ADJACENCY is not supported by the MVP executor."""
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[OrderOperator(type=OperatorType.ADJACENCY)],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "adjacency" in str(excinfo.value).lower()
    assert excinfo.value.path == "$.sequence.operators[0]"


def test_raises_unsupported_on_cooccurrence_operator() -> None:
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[OrderOperator(type=OperatorType.COOCCURRENCE)],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape):
        execute(plan, plan.scope, _make_engine())


def test_raises_registry_required_on_concept_without_registry() -> None:
    """A CONCEPT step with no concept_registry raises RegistryRequired."""
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.CONCEPT, value="faith")],
        operators=[],
    )
    plan = _make_plan(seq)
    # Engine connect() will be invoked AFTER resolution attempts,
    # but RegistryRequired raises during resolution. We still need a
    # context-manager-compatible mock for safety — but the connect()
    # context never enters because we raise from _resolve_step_lemmas.
    engine = _make_engine()
    with pytest.raises(RegistryRequired) as excinfo:
        execute(plan, plan.scope, engine, concept_registry=None)
    assert excinfo.value.concept_name == "faith"


def test_raises_unsupported_on_unknown_book_abbreviation() -> None:
    """An unknown book abbreviation in scope.books raises UnsupportedPlanShape."""
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )
    plan = _make_plan(
        seq,
        scope=ScopeConstraint(books=["xyz"]),
    )
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "xyz" in str(excinfo.value)
    assert excinfo.value.path == "$.scope.books[0]"


def test_raises_unsupported_on_unsupported_scope_unit() -> None:
    """ScopeUnit.CHAPTER is rejected (only VERSE / None supported)."""
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
    )
    plan = _make_plan(seq, scope=ScopeConstraint(unit=ScopeUnit.CHAPTER))
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert excinfo.value.path == "$.scope.unit"


def test_gap_constraint_with_min_zero_does_not_disable_ordering() -> None:
    """Sanity: a gap constraint of {0,3} is accepted at the shape layer."""
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[
            OrderOperator(
                type=OperatorType.PRECEDENCE,
                gap=GapConstraint(min=0, max=3),
            )
        ],
    )
    plan = _make_plan(seq)
    # We don't run real SQL — we just need to confirm shape validation
    # passes for a precedence-with-gap plan. Build a stub engine whose
    # connect() yields a context manager that returns a fake connection
    # whose execute() returns no rows.
    fake_conn = MagicMock()
    fake_conn.execute.return_value.all.return_value = []
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = fake_conn
    engine.connect.return_value.__exit__.return_value = False
    result = execute(plan, plan.scope, engine)
    assert result == []
