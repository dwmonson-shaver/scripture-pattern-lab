"""Tests for DSL AST types (src/engine/models.py)."""

import pytest
from pydantic import TypeAdapter, ValidationError

from src.engine.models import (
    AlternativeExpr,
    AlternativeOrderingCount,
    Contextualization,
    ExpansionDirection,
    ExpansionDirective,
    GapConstraint,
    InverseExpr,
    MatchCandidate,
    MatchedToken,
    MorphFilter,
    NodeBaseline,
    NodeRef,
    NodeType,
    NullDistribution,
    OperatorType,
    OptionalExpr,
    OrderOperator,
    QueryMetadata,
    QueryPlan,
    RankingFactor,
    RankingPrefs,
    RegistryRequired,
    RetrievalResult,
    ScopeConstraint,
    ScopeUnit,
    SequenceExpr,
    StepExpr,
    StepMatch,
    UnsupportedPlanShape,
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


# ---------------------------------------------------------------------------
# Phase 5: Executor result types and exceptions
# ---------------------------------------------------------------------------


def _sample_matched_token(**overrides: object) -> MatchedToken:
    defaults: dict[str, object] = {
        "id": 42,
        "book": "07",
        "chapter": 13,
        "verse": 13,
        "position": 4,
        "global_position": 100_001,
        "surface_form": "πίστις,",
        "normalized_form": "πίστις",
        "lemma": "πίστις",
        "pos": "N-",
    }
    defaults.update(overrides)
    return MatchedToken(**defaults)  # type: ignore[arg-type]


class TestMatchedToken:
    def test_construct(self) -> None:
        mt = _sample_matched_token()
        assert mt.book == "07"
        assert mt.chapter == 13
        assert mt.verse == 13
        assert mt.position == 4
        assert mt.lemma == "πίστις"
        assert mt.pos == "N-"

    def test_frozen(self) -> None:
        mt = _sample_matched_token()
        with pytest.raises(ValidationError):
            mt.position = 5

    def test_json_round_trip(self) -> None:
        mt = _sample_matched_token()
        json_str = mt.model_dump_json()
        restored = MatchedToken.model_validate_json(json_str)
        assert restored == mt


class TestStepMatch:
    def test_construct(self) -> None:
        token = _sample_matched_token()
        sm = StepMatch(
            step_index=0,
            node_type=NodeType.LEMMA,
            node_value="πίστις",
            resolved_lemmas=["πίστις"],
            token=token,
        )
        assert sm.step_index == 0
        assert sm.node_type == NodeType.LEMMA
        assert sm.node_value == "πίστις"
        assert sm.resolved_lemmas == ["πίστις"]
        assert sm.token == token

    def test_frozen(self) -> None:
        sm = StepMatch(
            step_index=0,
            node_type=NodeType.LEMMA,
            node_value="πίστις",
            resolved_lemmas=["πίστις"],
            token=_sample_matched_token(),
        )
        with pytest.raises(ValidationError):
            sm.step_index = 1

    def test_concept_step_with_resolved_lemmas(self) -> None:
        sm = StepMatch(
            step_index=0,
            node_type=NodeType.CONCEPT,
            node_value="faith",
            resolved_lemmas=["πίστις", "πιστεύω"],
            token=_sample_matched_token(),
        )
        assert sm.resolved_lemmas == ["πίστις", "πιστεύω"]


class TestMatchCandidate:
    def test_construct_empty_alignment(self) -> None:
        mc = MatchCandidate(
            tokens=[_sample_matched_token()],
            reference="1Cor 13:13",
            match_type="exact",
            alignment=[],
        )
        assert mc.reference == "1Cor 13:13"
        assert mc.match_type == "exact"
        assert mc.alignment == []
        assert len(mc.tokens) == 1

    def test_frozen(self) -> None:
        mc = MatchCandidate(
            tokens=[_sample_matched_token()],
            reference="1Cor 13:13",
            match_type="exact",
            alignment=[],
        )
        with pytest.raises(ValidationError):
            mc.reference = "Rom 1:1"

    def test_match_type_literal_validation(self) -> None:
        with pytest.raises(ValidationError):
            MatchCandidate(
                tokens=[],
                reference="1Cor 13:13",
                match_type="not-a-real-type",  # type: ignore[arg-type]
                alignment=[],
            )

    def test_match_type_conceptual_accepted(self) -> None:
        mc = MatchCandidate(
            tokens=[],
            reference="1Cor 13:13",
            match_type="conceptual",
            alignment=[],
        )
        assert mc.match_type == "conceptual"


class TestExecutorExceptions:
    def test_unsupported_plan_shape_carries_path(self) -> None:
        err = UnsupportedPlanShape("alt step", path="$.steps[0]")
        assert err.path == "$.steps[0]"
        assert "alt step" in str(err)

    def test_unsupported_plan_shape_default_path(self) -> None:
        err = UnsupportedPlanShape("nope")
        assert err.path == ""

    def test_registry_required_carries_concept_name(self) -> None:
        err = RegistryRequired("faith")
        assert err.concept_name == "faith"
        assert "faith" in str(err)


# ---------------------------------------------------------------------------
# Result-set contextualization (REQ:09.contextualization)
# ---------------------------------------------------------------------------


def _sample_node_baseline() -> NodeBaseline:
    return NodeBaseline(
        node_index=0,
        node_type=NodeType.CONCEPT,
        node_value="faith",
        resolved_lemmas=["πίστις", "πιστεύω"],
        count=243,
    )


def _sample_alt_ordering(
    *, permutation: list[int], label: str, count: int, observed: bool
) -> AlternativeOrderingCount:
    return AlternativeOrderingCount(
        permutation=permutation,
        sequence_label=label,
        count=count,
        is_observed=observed,
    )


class TestNodeBaseline:
    def test_construct(self) -> None:
        nb = _sample_node_baseline()
        assert nb.node_index == 0
        assert nb.node_type == NodeType.CONCEPT
        assert nb.resolved_lemmas == ["πίστις", "πιστεύω"]
        assert nb.count == 243

    def test_frozen(self) -> None:
        nb = _sample_node_baseline()
        with pytest.raises(ValidationError):
            nb.count = 99

    def test_json_round_trip(self) -> None:
        nb = _sample_node_baseline()
        restored = NodeBaseline.model_validate_json(nb.model_dump_json())
        assert restored == nb

    def test_lemma_node_baseline(self) -> None:
        nb = NodeBaseline(
            node_index=1,
            node_type=NodeType.LEMMA,
            node_value="πίστις",
            resolved_lemmas=["πίστις"],
            count=243,
        )
        assert nb.node_type == NodeType.LEMMA
        assert nb.resolved_lemmas == ["πίστις"]

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NodeBaseline(
                node_index=0,
                node_type=NodeType.LEMMA,
                node_value="πίστις",
                resolved_lemmas=["πίστις"],
                count=-1,
            )

    def test_negative_node_index_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NodeBaseline(
                node_index=-1,
                node_type=NodeType.LEMMA,
                node_value="πίστις",
                resolved_lemmas=["πίστις"],
                count=0,
            )


class TestAlternativeOrderingCount:
    def test_construct_observed(self) -> None:
        alt = _sample_alt_ordering(
            permutation=[0, 1, 2],
            label="faith > hope > love",
            count=2,
            observed=True,
        )
        assert alt.is_observed is True
        assert alt.permutation == [0, 1, 2]
        assert alt.count == 2

    def test_construct_alternative(self) -> None:
        alt = _sample_alt_ordering(
            permutation=[1, 0, 2],
            label="hope > faith > love",
            count=0,
            observed=False,
        )
        assert alt.is_observed is False
        assert alt.count == 0

    def test_frozen(self) -> None:
        alt = _sample_alt_ordering(
            permutation=[0, 1, 2],
            label="faith > hope > love",
            count=2,
            observed=True,
        )
        with pytest.raises(ValidationError):
            alt.count = 99

    def test_json_round_trip(self) -> None:
        alt = _sample_alt_ordering(
            permutation=[2, 1, 0],
            label="love > hope > faith",
            count=0,
            observed=False,
        )
        restored = AlternativeOrderingCount.model_validate_json(alt.model_dump_json())
        assert restored == alt

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AlternativeOrderingCount(
                permutation=[0, 1, 2],
                sequence_label="faith > hope > love",
                count=-1,
                is_observed=True,
            )

    def test_negative_permutation_index_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AlternativeOrderingCount(
                permutation=[0, -1, 2],
                sequence_label="faith > ? > love",
                count=0,
                is_observed=False,
            )


class TestNullDistribution:
    def test_construct(self) -> None:
        nd = NullDistribution(sample_size=50, mean=12.4, std=3.7, seed=20260509)
        assert nd.sample_size == 50
        assert nd.mean == 12.4
        assert nd.std == 3.7
        assert nd.seed == 20260509

    def test_frozen(self) -> None:
        nd = NullDistribution(sample_size=50, mean=12.4, std=3.7, seed=1)
        with pytest.raises(ValidationError):
            nd.mean = 0.0

    def test_json_round_trip(self) -> None:
        nd = NullDistribution(sample_size=100, mean=5.0, std=1.5, seed=42)
        restored = NullDistribution.model_validate_json(nd.model_dump_json())
        assert restored == nd

    def test_negative_sample_size_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NullDistribution(sample_size=-1, mean=0.0, std=0.0, seed=0)

    def test_negative_std_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NullDistribution(sample_size=10, mean=0.0, std=-0.5, seed=0)


class TestContextualization:
    def test_construct_minimum(self) -> None:
        ctx = Contextualization(
            observed_count=2,
            node_baselines=[_sample_node_baseline()],
            alternative_orderings=[
                _sample_alt_ordering(
                    permutation=[0],
                    label="faith",
                    count=243,
                    observed=True,
                )
            ],
            alternative_orderings_capped=False,
        )
        assert ctx.observed_count == 2
        assert ctx.alternative_orderings_capped is False
        assert ctx.null_distribution is None

    def test_null_distribution_default_is_none(self) -> None:
        ctx = Contextualization(
            observed_count=0,
            node_baselines=[],
            alternative_orderings=[],
            alternative_orderings_capped=False,
        )
        assert ctx.null_distribution is None

    def test_null_distribution_can_be_populated(self) -> None:
        ctx = Contextualization(
            observed_count=2,
            node_baselines=[_sample_node_baseline()],
            alternative_orderings=[],
            alternative_orderings_capped=False,
            null_distribution=NullDistribution(
                sample_size=50, mean=1.5, std=0.7, seed=42
            ),
        )
        assert ctx.null_distribution is not None
        assert ctx.null_distribution.sample_size == 50

    def test_frozen(self) -> None:
        ctx = Contextualization(
            observed_count=2,
            node_baselines=[],
            alternative_orderings=[],
            alternative_orderings_capped=False,
        )
        with pytest.raises(ValidationError):
            ctx.observed_count = 99

    def test_json_round_trip(self) -> None:
        ctx = Contextualization(
            observed_count=2,
            node_baselines=[_sample_node_baseline()],
            alternative_orderings=[
                _sample_alt_ordering(
                    permutation=[0, 1, 2],
                    label="faith > hope > love",
                    count=2,
                    observed=True,
                ),
                _sample_alt_ordering(
                    permutation=[2, 1, 0],
                    label="love > hope > faith",
                    count=0,
                    observed=False,
                ),
            ],
            alternative_orderings_capped=False,
        )
        restored = Contextualization.model_validate_json(ctx.model_dump_json())
        assert restored == ctx

    def test_negative_observed_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Contextualization(
                observed_count=-1,
                node_baselines=[],
                alternative_orderings=[],
                alternative_orderings_capped=False,
            )


class TestRetrievalResult:
    def test_construct_without_contextualization(self) -> None:
        rr = RetrievalResult(
            candidates=[
                MatchCandidate(
                    tokens=[],
                    reference="1Cor 13:13",
                    match_type="conceptual",
                    alignment=[],
                )
            ],
            stages_used=["symbolic"],
        )
        assert len(rr.candidates) == 1
        assert rr.stages_used == ["symbolic"]
        assert rr.contextualization is None

    def test_construct_with_contextualization(self) -> None:
        rr = RetrievalResult(
            candidates=[],
            stages_used=["symbolic"],
            contextualization=Contextualization(
                observed_count=0,
                node_baselines=[],
                alternative_orderings=[],
                alternative_orderings_capped=False,
            ),
        )
        assert rr.contextualization is not None
        assert rr.contextualization.observed_count == 0

    def test_frozen(self) -> None:
        rr = RetrievalResult(candidates=[], stages_used=[])
        with pytest.raises(ValidationError):
            rr.stages_used = ["other"]

    def test_json_round_trip(self) -> None:
        rr = RetrievalResult(
            candidates=[
                MatchCandidate(
                    tokens=[],
                    reference="1Cor 13:13",
                    match_type="conceptual",
                    alignment=[],
                )
            ],
            stages_used=["symbolic"],
            contextualization=Contextualization(
                observed_count=2,
                node_baselines=[_sample_node_baseline()],
                alternative_orderings=[],
                alternative_orderings_capped=False,
            ),
        )
        restored = RetrievalResult.model_validate_json(rr.model_dump_json())
        assert restored == rr
