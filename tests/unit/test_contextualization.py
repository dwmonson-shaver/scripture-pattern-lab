"""Unit tests for ``src/retrieval/contextualization.py``.

Shape-failure tests use a MagicMock engine — connect() never opens for
plans rejected by ``validate_plan_shape``. The happy-path tests stub
``connection.execute().scalar_one()`` to fixed counts so baselines round-trip
through the function without a real Postgres. Real SQL exercise is in
``tests/integration/test_contextualization.py``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.engine.models import (
    AlternativeExpr,
    ConceptNotMapped,
    InverseExpr,
    NodeBaseline,
    NodeRef,
    NodeType,
    OperatorType,
    OrderOperator,
    QueryPlan,
    RegistryRequired,
    ScopeConstraint,
    SequenceExpr,
    UnsupportedPlanShape,
)
from src.retrieval.contextualization import compute_node_baselines


def _make_engine_returning(*counts: int) -> Any:
    """Build a MagicMock engine whose connection.execute().scalar_one() yields counts in order."""
    engine = MagicMock()
    connection = MagicMock()
    connection_cm = MagicMock()
    connection_cm.__enter__.return_value = connection
    connection_cm.__exit__.return_value = False
    engine.connect.return_value = connection_cm

    results = [MagicMock() for _ in counts]
    for result, value in zip(results, counts):
        result.scalar_one.return_value = value
    connection.execute.side_effect = results
    return engine


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


# ---------------------------------------------------------------------------
# Shape failures — SQL never runs
# ---------------------------------------------------------------------------


def test_raises_unsupported_on_inverse_plan() -> None:
    inner = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
    )
    plan = _make_plan(InverseExpr(inner=inner))
    with pytest.raises(UnsupportedPlanShape):
        compute_node_baselines(plan, plan.scope, MagicMock())


def test_raises_unsupported_on_alternative_step() -> None:
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
    with pytest.raises(UnsupportedPlanShape):
        compute_node_baselines(plan, plan.scope, MagicMock())


def test_raises_unsupported_on_negated_step() -> None:
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις", negated=True)],
        operators=[],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape):
        compute_node_baselines(plan, plan.scope, MagicMock())


def test_raises_registry_required_on_concept_without_registry() -> None:
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.CONCEPT, value="faith")],
        operators=[],
    )
    plan = _make_plan(seq)
    with pytest.raises(RegistryRequired) as excinfo:
        compute_node_baselines(plan, plan.scope, MagicMock(), registry=None)
    assert excinfo.value.concept_name == "faith"


def test_raises_concept_not_mapped_on_empty_resolution() -> None:
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.CONCEPT, value="phlogiston")],
        operators=[],
    )
    plan = _make_plan(seq)
    registry = MagicMock()
    registry.get_lemmas_for_concept.return_value = []
    with pytest.raises(ConceptNotMapped) as excinfo:
        compute_node_baselines(plan, plan.scope, MagicMock(), registry=registry)
    assert excinfo.value.concept_name == "phlogiston"


# ---------------------------------------------------------------------------
# Happy path — stubbed connection.execute()
# ---------------------------------------------------------------------------


def test_lemma_baseline_returns_self_resolution() -> None:
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )
    plan = _make_plan(seq)
    engine = _make_engine_returning(243)

    baselines = compute_node_baselines(plan, plan.scope, engine)

    assert len(baselines) == 1
    nb = baselines[0]
    assert isinstance(nb, NodeBaseline)
    assert nb.node_index == 0
    assert nb.node_type == NodeType.LEMMA
    assert nb.node_value == "πίστις"
    assert nb.resolved_lemmas == ["πίστις"]
    assert nb.count == 243


def test_concept_baseline_uses_registry_resolution() -> None:
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.CONCEPT, value="faith")],
        operators=[],
    )
    plan = _make_plan(seq)
    registry = MagicMock()
    registry.get_lemmas_for_concept.return_value = ["πίστις", "πιστεύω"]
    engine = _make_engine_returning(486)

    baselines = compute_node_baselines(plan, plan.scope, engine, registry=registry)

    assert len(baselines) == 1
    nb = baselines[0]
    assert nb.node_type == NodeType.CONCEPT
    assert nb.node_value == "faith"
    assert nb.resolved_lemmas == ["πίστις", "πιστεύω"]
    assert nb.count == 486
    registry.get_lemmas_for_concept.assert_called_once_with("faith", "grc")


def test_concept_baseline_passes_scope_language_to_registry() -> None:
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.CONCEPT, value="faith")],
        operators=[],
    )
    plan = _make_plan(seq, scope=ScopeConstraint(language="hbo"))
    registry = MagicMock()
    registry.get_lemmas_for_concept.return_value = ["אמן"]
    engine = _make_engine_returning(0)

    compute_node_baselines(plan, plan.scope, engine, registry=registry)

    registry.get_lemmas_for_concept.assert_called_once_with("faith", "hbo")


def test_three_step_baselines_preserve_order() -> None:
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.CONCEPT, value="faith"),
            NodeRef(type=NodeType.CONCEPT, value="hope"),
            NodeRef(type=NodeType.CONCEPT, value="love"),
        ],
        operators=[
            OrderOperator(type=OperatorType.PRECEDENCE),
            OrderOperator(type=OperatorType.PRECEDENCE),
        ],
    )
    plan = _make_plan(seq)

    registry = MagicMock()
    registry.get_lemmas_for_concept.side_effect = lambda name, _lang: {
        "faith": ["πίστις", "πιστεύω"],
        "hope": ["ἐλπίς", "ἐλπίζω"],
        "love": ["ἀγάπη", "ἀγαπάω"],
    }[name]
    engine = _make_engine_returning(486, 122, 374)

    baselines = compute_node_baselines(plan, plan.scope, engine, registry=registry)

    assert [nb.node_value for nb in baselines] == ["faith", "hope", "love"]
    assert [nb.node_index for nb in baselines] == [0, 1, 2]
    assert [nb.count for nb in baselines] == [486, 122, 374]


def test_zero_count_returned_when_no_matches() -> None:
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="not_a_real_lemma")],
        operators=[],
    )
    plan = _make_plan(seq)
    engine = _make_engine_returning(0)

    baselines = compute_node_baselines(plan, plan.scope, engine)

    assert baselines[0].count == 0
