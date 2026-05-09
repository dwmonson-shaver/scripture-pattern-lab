"""Unit tests for ``src/retrieval/contextualization.py``.

Shape-failure tests use a MagicMock engine — connect() never opens for
plans rejected by ``validate_plan_shape``. The baseline happy-path tests
stub ``connection.execute().scalar_one()`` to fixed counts. The
alternative-ordering tests monkey-patch the ``execute`` import so each
permutation re-entry returns a predetermined candidate list — the
permutation-generation contract is exercised without a real Postgres.
Real SQL exercise is in ``tests/integration/test_contextualization.py``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.engine.models import (
    AlternativeExpr,
    ConceptNotMapped,
    InverseExpr,
    MatchCandidate,
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
from src.retrieval.contextualization import (
    _fallback_permutations,
    _format_sequence_label,
    compute_alternative_orderings,
    compute_node_baselines,
)


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


# ---------------------------------------------------------------------------
# Permutation generation (private helpers)
# ---------------------------------------------------------------------------


class TestFallbackPermutations:
    def test_n_5_yields_six_permutations(self) -> None:
        # identity + reverse + 4 adjacent swaps = 6
        perms = _fallback_permutations(5)
        assert len(perms) == 6
        assert perms[0] == [0, 1, 2, 3, 4]  # identity
        assert perms[1] == [4, 3, 2, 1, 0]  # reverse
        assert perms[2] == [1, 0, 2, 3, 4]  # swap (0,1)
        assert perms[3] == [0, 2, 1, 3, 4]  # swap (1,2)
        assert perms[4] == [0, 1, 3, 2, 4]  # swap (2,3)
        assert perms[5] == [0, 1, 2, 4, 3]  # swap (3,4)

    def test_n_6_yields_seven_permutations(self) -> None:
        # identity + reverse + 5 adjacent swaps = 7
        perms = _fallback_permutations(6)
        assert len(perms) == 7
        assert perms[0] == list(range(6))
        assert perms[1] == list(reversed(range(6)))

    def test_all_permutations_distinct(self) -> None:
        perms = _fallback_permutations(7)
        as_tuples = [tuple(p) for p in perms]
        assert len(set(as_tuples)) == len(as_tuples)

    def test_truncates_at_24_for_very_long_sequences(self) -> None:
        # N=30: identity + reverse + 29 adjacent swaps would be 31 perms;
        # honoring canonical-09 §8 ceiling truncates to 24 (Codex D-D3D4-001).
        perms = _fallback_permutations(30)
        assert len(perms) == 24
        assert perms[0] == list(range(30))
        assert perms[1] == list(reversed(range(30)))


class TestFormatSequenceLabel:
    def test_three_step_label(self) -> None:
        steps = [
            NodeRef(type=NodeType.CONCEPT, value="faith"),
            NodeRef(type=NodeType.CONCEPT, value="hope"),
            NodeRef(type=NodeType.CONCEPT, value="love"),
        ]
        assert _format_sequence_label(steps) == "faith > hope > love"

    def test_single_step_label(self) -> None:
        steps = [NodeRef(type=NodeType.LEMMA, value="πίστις")]
        assert _format_sequence_label(steps) == "πίστις"


# ---------------------------------------------------------------------------
# Alternative orderings — execute() is monkey-patched to a stub
# ---------------------------------------------------------------------------


def _stub_execute(
    counts_by_label: dict[str, int],
) -> Any:
    """Build a stub execute() that returns N MatchCandidates per (label → count) lookup."""

    def _make_candidates(reference_count: int) -> list[MatchCandidate]:
        return [
            MatchCandidate(
                tokens=[],
                reference=f"Stub {i}:0",
                match_type="exact",
                alignment=[],
            )
            for i in range(reference_count)
        ]

    def _stub(
        plan: QueryPlan,
        scope: ScopeConstraint,
        engine: Any,
        **_kw: Any,
    ) -> list[MatchCandidate]:
        # Reconstruct the label from the plan's sequence to look up the count.
        steps = list(plan.sequence.steps)  # type: ignore[union-attr]
        label = " > ".join(step.value for step in steps)  # type: ignore[union-attr]
        return _make_candidates(counts_by_label.get(label, 0))

    return _stub


class TestComputeAlternativeOrderings:
    def test_one_step_yields_identity_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seq = SequenceExpr(
            steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
            operators=[],
        )
        plan = _make_plan(seq)
        monkeypatch.setattr(
            "src.retrieval.contextualization.execute",
            _stub_execute({"πίστις": 243}),
        )

        orderings, capped = compute_alternative_orderings(plan, plan.scope, MagicMock())

        assert capped is False
        assert len(orderings) == 1
        assert orderings[0].permutation == [0]
        assert orderings[0].count == 243
        assert orderings[0].is_observed is True
        assert orderings[0].sequence_label == "πίστις"

    def test_two_steps_enumerate_full_factorial(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seq = SequenceExpr(
            steps=[
                NodeRef(type=NodeType.LEMMA, value="πίστις"),
                NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
            ],
            operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
        )
        plan = _make_plan(seq)
        monkeypatch.setattr(
            "src.retrieval.contextualization.execute",
            _stub_execute({"πίστις > ἐλπίς": 5, "ἐλπίς > πίστις": 2}),
        )

        orderings, capped = compute_alternative_orderings(plan, plan.scope, MagicMock())

        assert capped is False
        assert len(orderings) == 2
        observed = [o for o in orderings if o.is_observed]
        alternative = [o for o in orderings if not o.is_observed]
        assert len(observed) == 1
        assert observed[0].count == 5
        assert observed[0].permutation == [0, 1]
        assert len(alternative) == 1
        assert alternative[0].count == 2
        assert alternative[0].permutation == [1, 0]
        assert alternative[0].sequence_label == "ἐλπίς > πίστις"

    def test_three_steps_yields_six_permutations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        monkeypatch.setattr(
            "src.retrieval.contextualization.execute",
            _stub_execute({"faith > hope > love": 2}),
        )

        orderings, capped = compute_alternative_orderings(plan, plan.scope, MagicMock())

        assert capped is False
        assert len(orderings) == 6  # 3! = 6
        # Identity must be present and marked observed
        identity = [o for o in orderings if o.permutation == [0, 1, 2]]
        assert len(identity) == 1
        assert identity[0].is_observed is True
        assert identity[0].count == 2
        # Non-identity orderings have count=0 (stub returns 0 for unknown labels)
        non_observed = [o for o in orderings if not o.is_observed]
        assert len(non_observed) == 5
        assert all(o.count == 0 for o in non_observed)

    def test_four_steps_enumerate_24_perms_uncapped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seq = SequenceExpr(
            steps=[
                NodeRef(type=NodeType.LEMMA, value=f"l{i}") for i in range(4)
            ],
            operators=[OrderOperator(type=OperatorType.PRECEDENCE) for _ in range(3)],
        )
        plan = _make_plan(seq)
        monkeypatch.setattr(
            "src.retrieval.contextualization.execute",
            _stub_execute({}),  # all counts default to 0
        )

        orderings, capped = compute_alternative_orderings(plan, plan.scope, MagicMock())

        assert capped is False
        assert len(orderings) == 24  # 4! = 24

    def test_five_steps_uses_fallback_capped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seq = SequenceExpr(
            steps=[
                NodeRef(type=NodeType.LEMMA, value=f"l{i}") for i in range(5)
            ],
            operators=[OrderOperator(type=OperatorType.PRECEDENCE) for _ in range(4)],
        )
        plan = _make_plan(seq)
        monkeypatch.setattr(
            "src.retrieval.contextualization.execute",
            _stub_execute({}),
        )

        orderings, capped = compute_alternative_orderings(plan, plan.scope, MagicMock())

        assert capped is True
        # identity + reverse + 4 adjacent swaps = 6 (not 5! = 120)
        assert len(orderings) == 6
        # Identity is observed
        identity = [o for o in orderings if o.permutation == [0, 1, 2, 3, 4]]
        assert len(identity) == 1
        assert identity[0].is_observed is True
        # Reverse is in the set but not observed
        reverse = [o for o in orderings if o.permutation == [4, 3, 2, 1, 0]]
        assert len(reverse) == 1
        assert reverse[0].is_observed is False

    def test_inverse_plan_rejected(self) -> None:
        inner = SequenceExpr(
            steps=[
                NodeRef(type=NodeType.LEMMA, value="πίστις"),
                NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
            ],
            operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
        )
        plan = _make_plan(InverseExpr(inner=inner))
        with pytest.raises(UnsupportedPlanShape):
            compute_alternative_orderings(plan, plan.scope, MagicMock())
