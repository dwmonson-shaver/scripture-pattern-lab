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
    ConceptNotMapped,
    GapConstraint,
    InverseExpr,
    MorphFilter,
    NodeRef,
    NodeType,
    OperatorType,
    OptionalExpr,
    OrderOperator,
    QueryPlan,
    RegistryRequired,
    ScopeConstraint,
    ScopeUnitVerse,
    ScopeUnitWindow,
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


def test_cooccurrence_operator_passes_shape_validation() -> None:
    """Slice L Phase 2: COOCCURRENCE is now accepted at validate_plan_shape.

    Prior to Slice L, ``~`` was rejected at shape time. Now it executes via
    the unordered branch (Decision #7). The shape gate accepts it; this test
    confirms the rejection has been lifted. Execution semantics are covered
    by the integration suite (cross-verse 3 John fixture).
    """
    from src.engine.executor import validate_plan_shape

    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[OrderOperator(type=OperatorType.COOCCURRENCE)],
    )
    plan = _make_plan(seq)
    validated = validate_plan_shape(plan, plan.scope)
    assert validated.operators[0].type == OperatorType.COOCCURRENCE


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
    # context never enters because we raise from resolve_step_lemmas.
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


def test_window_scope_passes_shape_validation() -> None:
    """Slice L Phase 2: ScopeUnitWindow now executes through the
    global_position path. The shape gate accepts it; execution semantics
    are covered in the integration suite.
    """
    from src.engine.executor import validate_plan_shape

    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
    )
    plan = _make_plan(seq, scope=ScopeConstraint(unit=ScopeUnitWindow(n=50)))
    validated = validate_plan_shape(plan, plan.scope)
    assert len(validated.steps) == 2


def test_raises_unsupported_on_negated_node() -> None:
    """C-CLOSE-001: a negated NodeRef must not silently flow through.

    Exclusion semantics are not yet designed; until they are, the executor
    must reject ``NodeRef.negated=True`` rather than resolve the underlying
    lemma/concept positively.
    """
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="x", negated=True)],
        operators=[],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "negated" in str(excinfo.value).lower()
    assert excinfo.value.path == "$.sequence.steps[0]"


def test_raises_unsupported_on_negated_concept_node() -> None:
    """A negated CONCEPT step is also rejected (same path as lemma case)."""
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.CONCEPT, value="faith", negated=True)],
        operators=[],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "negated" in str(excinfo.value).lower()


def test_raises_unsupported_on_morph_filter() -> None:
    """C-CLOSE-002: morph_filters are ignored by resolution; reject them."""
    seq = SequenceExpr(
        steps=[
            NodeRef(
                type=NodeType.LEMMA,
                value="πίστις",
                morph_filters=[MorphFilter(feature="NOUN")],
            )
        ],
        operators=[],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "morph_filters" in str(excinfo.value)
    assert excinfo.value.path == "$.sequence.steps[0]"


def test_raises_unsupported_on_operator_count_mismatch_too_few() -> None:
    """C-CLOSE-002: 2 steps + 0 operators is malformed (need exactly 1)."""
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "operator count" in str(excinfo.value).lower()
    assert excinfo.value.path == "$.sequence.operators"


def test_raises_unsupported_on_operator_count_mismatch_too_many() -> None:
    """C-CLOSE-002: 2 steps + 2 operators is malformed (need exactly 1)."""
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[
            OrderOperator(type=OperatorType.PRECEDENCE),
            OrderOperator(type=OperatorType.PRECEDENCE),
        ],
    )
    plan = _make_plan(seq)
    with pytest.raises(UnsupportedPlanShape) as excinfo:
        execute(plan, plan.scope, _make_engine())
    assert "operator count" in str(excinfo.value).lower()


def test_step0_query_includes_corpus_and_language_filters() -> None:
    """C-CLOSE-003: step-0 SELECT receives corpus + language WHERE clauses.

    Stub engine returns no rows so we never reach step 1 — but the step-0
    statement was assembled and dispatched. We snapshot its compiled string
    and assert the scope columns appear as filters.
    """
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )
    plan = _make_plan(
        seq,
        scope=ScopeConstraint(
            unit=ScopeUnitVerse(),
            corpus="nt",
            language="grc",
        ),
    )
    fake_conn = MagicMock()
    fake_conn.execute.return_value.all.return_value = []
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = fake_conn
    engine.connect.return_value.__exit__.return_value = False

    result = execute(plan, plan.scope, engine)

    assert result == []
    # Inspect the actual compiled SQL passed to the connection.
    assert fake_conn.execute.call_count == 1
    stmt = fake_conn.execute.call_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "corpus_id" in compiled
    assert "language" in compiled


def test_every_step_query_includes_scope_filters() -> None:
    """C-CLOSE-003: later-step batched SELECT also carries scope filters.

    Two-step plan; stub engine returns one row for step 0 (so chains is
    non-empty) and zero rows for step 1. Verify both compiled statements
    contain the corpus + language predicates.
    """
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.LEMMA, value="πίστις"),
            NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
        ],
        operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
    )
    plan = _make_plan(
        seq,
        scope=ScopeConstraint(
            unit=ScopeUnitVerse(),
            corpus="nt",
            language="grc",
        ),
    )

    # Step 0 returns one row; step 1 returns []. Use a side_effect on
    # ``connection.execute`` so we can inspect both calls.
    step0_row = MagicMock()
    step0_row.id = 1
    step0_row.book = "01"
    step0_row.chapter = 1
    step0_row.verse = 1
    step0_row.position = 1
    step0_row.global_position = 1
    step0_row.surface_form = "πίστιν"
    step0_row.normalized_form = "πιστιν"
    step0_row.lemma = "πίστις"
    step0_row.pos = "N"

    step0_result = MagicMock()
    step0_result.all.return_value = [step0_row]
    step1_result = MagicMock()
    step1_result.all.return_value = []

    fake_conn = MagicMock()
    fake_conn.execute.side_effect = [step0_result, step1_result]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = fake_conn
    engine.connect.return_value.__exit__.return_value = False

    result = execute(plan, plan.scope, engine)

    assert result == []
    assert fake_conn.execute.call_count == 2
    for call in fake_conn.execute.call_args_list:
        stmt = call.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "corpus_id" in compiled, (
            f"expected corpus_id filter in step query: {compiled!r}"
        )
        assert "language" in compiled, (
            f"expected language filter in step query: {compiled!r}"
        )


def test_raises_concept_not_mapped_when_registry_returns_empty() -> None:
    """C-CLOSE-006: a concept that resolves to [] raises ConceptNotMapped.

    The registry handle exists but returns no lemmas for the concept name.
    The executor must distinguish this from RegistryRequired (no handle).
    """
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.CONCEPT, value="zzznotreal")],
        operators=[],
    )
    plan = _make_plan(seq)

    fake_registry = MagicMock()
    fake_registry.get_lemmas_for_concept.return_value = []

    with pytest.raises(ConceptNotMapped) as excinfo:
        execute(plan, plan.scope, _make_engine(), concept_registry=fake_registry)
    assert excinfo.value.concept_name == "zzznotreal"


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


# ---------------------------------------------------------------------------
# Slice L Phase 2: ~ (cooccurrence) gap arithmetic and window predicate
# ---------------------------------------------------------------------------


class TestGapSatisfiedUnordered:
    """Unit tests for ``_gap_satisfied_unordered`` (the ``~`` arithmetic).

    Mirrors ``_gap_satisfied``'s behavior but with ``abs(next - prev)``.
    """

    def test_either_direction_passes_without_gap(self) -> None:
        from src.engine.executor import _gap_satisfied_unordered

        assert _gap_satisfied_unordered(10, 7, None) is True
        assert _gap_satisfied_unordered(7, 10, None) is True

    def test_same_position_rejected(self) -> None:
        from src.engine.executor import _gap_satisfied_unordered

        assert _gap_satisfied_unordered(5, 5, None) is False

    def test_min_gap_either_direction(self) -> None:
        from src.engine.executor import _gap_satisfied_unordered

        # distance=2, gap.min=2 → exactly the minimum is NOT satisfied
        # (we require distance > min_gap, same as ordered variant).
        gap = GapConstraint(min=2, max=None)
        assert _gap_satisfied_unordered(10, 12, gap) is False
        assert _gap_satisfied_unordered(12, 10, gap) is False
        assert _gap_satisfied_unordered(10, 13, gap) is True
        assert _gap_satisfied_unordered(13, 10, gap) is True

    def test_max_gap_either_direction(self) -> None:
        from src.engine.executor import _gap_satisfied_unordered

        # distance <= max + 1 passes
        gap = GapConstraint(min=0, max=5)
        assert _gap_satisfied_unordered(10, 15, gap) is True  # distance=5
        assert _gap_satisfied_unordered(15, 10, gap) is True  # distance=5
        assert _gap_satisfied_unordered(10, 16, gap) is True  # distance=6, == max+1
        assert _gap_satisfied_unordered(10, 17, gap) is False  # distance=7


class TestWindowExecution:
    """Unit tests that ``ScopeUnitWindow(n)`` routes through the
    global_position path. Verifies the SQL has the right predicate shape
    without requiring a live DB.
    """

    def _stub_engine(
        self, step0_rows: list[Any], step1_rows: list[Any]
    ) -> tuple[Any, Any]:
        fake_conn = MagicMock()
        step0_result = MagicMock()
        step0_result.all.return_value = step0_rows
        step1_result = MagicMock()
        step1_result.all.return_value = step1_rows
        fake_conn.execute.side_effect = [step0_result, step1_result]
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = fake_conn
        engine.connect.return_value.__exit__.return_value = False
        return engine, fake_conn

    def _row(self, **kwargs: Any) -> Any:
        defaults = {
            "id": 1,
            "book": "45",
            "chapter": 5,
            "verse": 1,
            "position": 1,
            "global_position": 100,
            "surface_form": "x",
            "normalized_form": "x",
            "lemma": "x",
            "pos": "N",
        }
        defaults.update(kwargs)
        row = MagicMock()
        for k, v in defaults.items():
            setattr(row, k, v)
        return row

    def test_window_step_query_uses_global_position_predicate(self) -> None:
        """Window-mode step-N SELECT contains a global_position BETWEEN
        clause anchored on step-0's global_position (not the verse tuple).
        """
        seq = SequenceExpr(
            steps=[
                NodeRef(type=NodeType.LEMMA, value="πίστις"),
                NodeRef(type=NodeType.LEMMA, value="ἐλπίς"),
            ],
            operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
        )
        plan = _make_plan(seq, scope=ScopeConstraint(unit=ScopeUnitWindow(n=50)))
        step0 = self._row(global_position=100, lemma="πίστις")
        # No step-1 rows; we only need to inspect the step-1 SQL shape.
        engine, fake_conn = self._stub_engine([step0], [])
        execute(plan, plan.scope, engine)

        # The second execute() call is the step-1 SELECT.
        assert fake_conn.execute.call_count == 2
        step1_stmt = fake_conn.execute.call_args_list[1].args[0]
        compiled = str(step1_stmt.compile(compile_kwargs={"literal_binds": True}))
        # The window predicate: book = '45' AND global_position BETWEEN 100 AND 150.
        assert "global_position >= 100" in compiled
        assert "global_position <= 150" in compiled
        assert "tokens.book = '45'" in compiled
        # The verse-tuple predicate (legacy path) must NOT be present.
        # tuple_(book, chapter, verse) IN (...) is the marker; SELECT-list
        # references to chapter/verse columns are unavoidable.
        assert "(tokens.book, tokens.chapter, tokens.verse) IN" not in compiled

    def test_window_cooccurrence_passes_shape(self) -> None:
        seq = SequenceExpr(
            steps=[
                NodeRef(type=NodeType.LEMMA, value="πίστις"),
                NodeRef(type=NodeType.LEMMA, value="ἀγάπη"),
            ],
            operators=[OrderOperator(type=OperatorType.COOCCURRENCE)],
        )
        plan = _make_plan(seq, scope=ScopeConstraint(unit=ScopeUnitWindow(n=30)))
        engine, fake_conn = self._stub_engine([], [])
        result = execute(plan, plan.scope, engine)
        assert result == []
