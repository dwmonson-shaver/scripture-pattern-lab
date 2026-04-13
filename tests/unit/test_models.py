"""Tests for DSL AST types (src/engine/models.py)."""

import pytest
from pydantic import TypeAdapter, ValidationError

from src.engine.models import (
    AlternativeExpr,
    ExpansionDirection,
    ExpansionDirective,
    GapConstraint,
    InverseExpr,
    MorphFilter,
    NodeRef,
    NodeType,
    OperatorType,
    OptionalExpr,
    OrderOperator,
    QueryMetadata,
    QueryPlan,
    RankingFactor,
    RankingPrefs,
    ScopeConstraint,
    ScopeUnit,
    SequenceExpr,
    StepExpr,
)

# ---------------------------------------------------------------------------
# Phase 1: Enums and leaf models
# ---------------------------------------------------------------------------


class TestEnums:
    def test_node_type_values(self) -> None:
        assert set(NodeType) == {
            "token", "lemma", "root", "concept", "domain", "morph", "wildcard"
        }

    def test_operator_type_values(self) -> None:
        assert set(OperatorType) == {"precedence", "adjacency", "cooccurrence"}

    def test_ranking_factor_values(self) -> None:
        assert len(RankingFactor) == 6

    def test_scope_unit_values(self) -> None:
        assert set(ScopeUnit) == {
            "token", "clause", "verse", "sentence", "pericope", "chapter"
        }

    def test_expansion_direction_values(self) -> None:
        assert set(ExpansionDirection) == {"forward", "backward", "both"}


class TestMorphFilter:
    def test_construct(self) -> None:
        mf = MorphFilter(feature="NOUN")
        assert mf.feature == "NOUN"

    def test_frozen(self) -> None:
        mf = MorphFilter(feature="NOUN")
        with pytest.raises(ValidationError):
            mf.feature = "VERB"

    def test_dump(self) -> None:
        mf = MorphFilter(feature="IMPERATIVE")
        assert mf.model_dump() == {"feature": "IMPERATIVE"}


class TestGapConstraint:
    def test_defaults(self) -> None:
        gc = GapConstraint()
        assert gc.min == 0
        assert gc.max is None

    def test_explicit(self) -> None:
        gc = GapConstraint(min=0, max=5)
        assert gc.max == 5

    def test_frozen(self) -> None:
        gc = GapConstraint(min=0, max=3)
        with pytest.raises(ValidationError):
            gc.min = 1


class TestOrderOperator:
    def test_precedence_no_gap(self) -> None:
        op = OrderOperator(type=OperatorType.PRECEDENCE)
        assert op.type == "precedence"
        assert op.gap is None

    def test_precedence_with_gap(self) -> None:
        op = OrderOperator(
            type=OperatorType.PRECEDENCE,
            gap=GapConstraint(min=0, max=3),
        )
        assert op.gap.max == 3

    def test_dump(self) -> None:
        op = OrderOperator(type=OperatorType.ADJACENCY)
        d = op.model_dump()
        assert d == {"type": "adjacency", "gap": None}


class TestScopeConstraint:
    def test_all_none(self) -> None:
        sc = ScopeConstraint()
        assert sc.corpus is None
        assert sc.language is None
        assert sc.books is None
        assert sc.unit is None

    def test_full(self) -> None:
        sc = ScopeConstraint(
            corpus="nt",
            language="grc",
            books=["rom", "1cor"],
            unit=ScopeUnit.VERSE,
        )
        assert sc.books == ["rom", "1cor"]
        assert sc.unit == "verse"

    def test_dump(self) -> None:
        sc = ScopeConstraint(corpus="nt", unit=ScopeUnit.VERSE)
        d = sc.model_dump()
        assert d["corpus"] == "nt"
        assert d["unit"] == "verse"


class TestExpansionDirective:
    def test_construct(self) -> None:
        ed = ExpansionDirective(direction=ExpansionDirection.FORWARD, depth=2)
        assert ed.direction == "forward"
        assert ed.depth == 2

    def test_dump(self) -> None:
        ed = ExpansionDirective(direction=ExpansionDirection.BOTH, depth=3)
        assert ed.model_dump() == {"direction": "both", "depth": 3}


class TestRankingPrefs:
    def test_construct(self) -> None:
        rp = RankingPrefs(weights={
            RankingFactor.LEXICAL_ALIGNMENT: 1.0,
            RankingFactor.RARITY: 0.5,
        })
        assert rp.weights[RankingFactor.LEXICAL_ALIGNMENT] == 1.0

    def test_dump(self) -> None:
        rp = RankingPrefs(weights={RankingFactor.RARITY: 0.8})
        d = rp.model_dump()
        assert d == {"weights": {"rarity": 0.8}}


class TestQueryMetadata:
    def test_defaults(self) -> None:
        qm = QueryMetadata()
        assert qm.nl_source is None
        assert qm.parse_timestamp is None

    def test_with_source(self) -> None:
        qm = QueryMetadata(nl_source="Does faith come before love?")
        assert qm.nl_source == "Does faith come before love?"


# ---------------------------------------------------------------------------
# Phase 2: Step expression models (discriminated union)
# ---------------------------------------------------------------------------

_step_adapter = TypeAdapter(StepExpr)


class TestNodeRef:
    def test_construct(self) -> None:
        nr = NodeRef(type=NodeType.CONCEPT, value="faith")
        assert nr.expr_type == "node_ref"
        assert nr.type == "concept"
        assert nr.value == "faith"
        assert nr.polarity is None
        assert nr.morph_filters == []
        assert nr.negated is False

    def test_with_polarity(self) -> None:
        nr = NodeRef(type=NodeType.CONCEPT, value="faith", polarity="+")
        assert nr.polarity == "+"

    def test_with_morph_filters(self) -> None:
        nr = NodeRef(
            type=NodeType.LEMMA,
            value="pistis",
            morph_filters=[MorphFilter(feature="NOUN")],
        )
        assert len(nr.morph_filters) == 1
        assert nr.morph_filters[0].feature == "NOUN"

    def test_negated(self) -> None:
        nr = NodeRef(type=NodeType.CONCEPT, value="sin", negated=True)
        assert nr.negated is True

    def test_frozen(self) -> None:
        nr = NodeRef(type=NodeType.CONCEPT, value="faith")
        with pytest.raises(ValidationError):
            nr.value = "hope"

    def test_json_round_trip(self) -> None:
        nr = NodeRef(type=NodeType.CONCEPT, value="faith", polarity="+")
        json_str = nr.model_dump_json()
        restored = _step_adapter.validate_json(json_str)
        assert isinstance(restored, NodeRef)
        assert restored.value == "faith"
        assert restored.polarity == "+"


class TestAlternativeExpr:
    def test_construct(self) -> None:
        alt = AlternativeExpr(options=[
            NodeRef(type=NodeType.CONCEPT, value="hope"),
            NodeRef(type=NodeType.CONCEPT, value="expectation"),
        ])
        assert alt.expr_type == "alternative"
        assert len(alt.options) == 2

    def test_json_round_trip(self) -> None:
        alt = AlternativeExpr(options=[
            NodeRef(type=NodeType.CONCEPT, value="hope"),
            NodeRef(type=NodeType.CONCEPT, value="expectation"),
        ])
        json_str = alt.model_dump_json()
        restored = _step_adapter.validate_json(json_str)
        assert isinstance(restored, AlternativeExpr)
        assert len(restored.options) == 2


class TestOptionalExpr:
    def test_construct(self) -> None:
        opt = OptionalExpr(inner=NodeRef(type=NodeType.CONCEPT, value="endurance"))
        assert opt.expr_type == "optional"
        assert isinstance(opt.inner, NodeRef)

    def test_json_round_trip(self) -> None:
        opt = OptionalExpr(inner=NodeRef(type=NodeType.CONCEPT, value="endurance"))
        json_str = opt.model_dump_json()
        restored = _step_adapter.validate_json(json_str)
        assert isinstance(restored, OptionalExpr)


# ---------------------------------------------------------------------------
# Phase 3: Composite models and QueryPlan
# ---------------------------------------------------------------------------


class TestSequenceExpr:
    def test_simple_sequence(self) -> None:
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
        assert len(seq.steps) == 3
        assert len(seq.operators) == 2


class TestInverseExpr:
    def test_construct(self) -> None:
        inv = InverseExpr(
            inner=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                ],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            )
        )
        assert len(inv.inner.steps) == 2


class TestQueryPlan:
    def test_example_1_simple_sequence(self) -> None:
        """Doc 07, Example 1: faith > hope > love."""
        plan = QueryPlan(
            version="0.1",
            source="faith > hope > love",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                    NodeRef(type=NodeType.CONCEPT, value="love"),
                ],
                operators=[
                    OrderOperator(type=OperatorType.PRECEDENCE),
                    OrderOperator(type=OperatorType.PRECEDENCE),
                ],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        assert plan.version == "0.1"
        assert plan.source == "faith > hope > love"
        assert len(plan.sequence.steps) == 3
        assert plan.mode == "conceptual"
        assert plan.expansion is None
        assert plan.ranking is None

    def test_dump_structure(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="faith > hope > love",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                ],
                operators=[],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        d = plan.model_dump()
        assert d["version"] == "0.1"
        assert d["sequence"]["steps"][0]["type"] == "concept"
        assert d["sequence"]["steps"][0]["expr_type"] == "node_ref"


# ---------------------------------------------------------------------------
# Phase 4: JSON serialization round-trip tests (doc 07 examples)
# ---------------------------------------------------------------------------


class TestJsonRoundTrips:
    """Verify QueryPlan serializes to JSON and deserializes back identically."""

    def test_example_1_simple_concept_sequence(self) -> None:
        """Doc 07 Example 1: faith > hope > love."""
        plan = QueryPlan(
            version="0.1",
            source="faith > hope > love",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                    NodeRef(type=NodeType.CONCEPT, value="love"),
                ],
                operators=[
                    OrderOperator(type=OperatorType.PRECEDENCE),
                    OrderOperator(type=OperatorType.PRECEDENCE),
                ],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        json_str = plan.model_dump_json()
        restored = QueryPlan.model_validate_json(json_str)
        assert restored == plan

    def test_example_2_typed_lemma_with_gap_and_scope(self) -> None:
        """Doc 07 Example 2: lemma:pistis >{0,3} lemma:elpis > lemma:agape."""
        plan = QueryPlan(
            version="0.1",
            source="lemma:pistis >{0,3} lemma:elpis > lemma:agape within:verse lang:grc corpus:nt",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.LEMMA, value="pistis"),
                    NodeRef(type=NodeType.LEMMA, value="elpis"),
                    NodeRef(type=NodeType.LEMMA, value="agape"),
                ],
                operators=[
                    OrderOperator(
                        type=OperatorType.PRECEDENCE,
                        gap=GapConstraint(min=0, max=3),
                    ),
                    OrderOperator(type=OperatorType.PRECEDENCE),
                ],
            ),
            scope=ScopeConstraint(
                corpus="nt",
                language="grc",
                unit=ScopeUnit.VERSE,
            ),
            mode="exact",
        )
        json_str = plan.model_dump_json()
        restored = QueryPlan.model_validate_json(json_str)
        assert restored == plan
        assert restored.scope.corpus == "nt"
        assert restored.sequence.operators[0].gap.max == 3

    def test_example_3_polarity_marked(self) -> None:
        """Doc 07 Example 3: +concept:faith > +concept:hope > +concept:love."""
        plan = QueryPlan(
            version="0.1",
            source="+concept:faith > +concept:hope > +concept:love within:verse corpus:nt",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith", polarity="+"),
                    NodeRef(type=NodeType.CONCEPT, value="hope", polarity="+"),
                    NodeRef(type=NodeType.CONCEPT, value="love", polarity="+"),
                ],
                operators=[
                    OrderOperator(type=OperatorType.PRECEDENCE),
                    OrderOperator(type=OperatorType.PRECEDENCE),
                ],
            ),
            scope=ScopeConstraint(corpus="nt", unit=ScopeUnit.VERSE),
            mode="conceptual",
        )
        json_str = plan.model_dump_json()
        restored = QueryPlan.model_validate_json(json_str)
        assert restored == plan
        assert restored.sequence.steps[0].polarity == "+"

    def test_example_4_alternatives_and_optional(self) -> None:
        """Doc 07 Example 4: faith > (hope | expectation) > [endurance] > love."""
        plan = QueryPlan(
            version="0.1",
            source=(
                "concept:faith > (concept:hope | concept:expectation)"
                " > [concept:endurance] > concept:love"
            ),
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    AlternativeExpr(options=[
                        NodeRef(type=NodeType.CONCEPT, value="hope"),
                        NodeRef(type=NodeType.CONCEPT, value="expectation"),
                    ]),
                    OptionalExpr(
                        inner=NodeRef(type=NodeType.CONCEPT, value="endurance"),
                    ),
                    NodeRef(type=NodeType.CONCEPT, value="love"),
                ],
                operators=[
                    OrderOperator(type=OperatorType.PRECEDENCE),
                    OrderOperator(type=OperatorType.PRECEDENCE),
                    OrderOperator(type=OperatorType.PRECEDENCE),
                ],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        json_str = plan.model_dump_json()
        restored = QueryPlan.model_validate_json(json_str)
        assert restored == plan
        assert isinstance(restored.sequence.steps[1], AlternativeExpr)
        assert isinstance(restored.sequence.steps[2], OptionalExpr)

    def test_example_5_inverse(self) -> None:
        """Doc 07 Example 5: inverse(faith > hope > love)."""
        plan = QueryPlan(
            version="0.1",
            source="inverse(faith > hope > love) within:verse corpus:nt",
            sequence=InverseExpr(
                inner=SequenceExpr(
                    steps=[
                        NodeRef(type=NodeType.CONCEPT, value="faith"),
                        NodeRef(type=NodeType.CONCEPT, value="hope"),
                        NodeRef(type=NodeType.CONCEPT, value="love"),
                    ],
                    operators=[
                        OrderOperator(type=OperatorType.PRECEDENCE),
                        OrderOperator(type=OperatorType.PRECEDENCE),
                    ],
                ),
            ),
            scope=ScopeConstraint(corpus="nt", unit=ScopeUnit.VERSE),
            mode="conceptual",
        )
        json_str = plan.model_dump_json()
        restored = QueryPlan.model_validate_json(json_str)
        assert restored == plan
        assert isinstance(restored.sequence, InverseExpr)
        assert len(restored.sequence.inner.steps) == 3
