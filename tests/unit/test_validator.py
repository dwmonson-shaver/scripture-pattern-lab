"""Tests for capability validator (src/validation/)."""


from src.engine.models import (
    ExpansionDirection,
    ExpansionDirective,
    InverseExpr,
    MorphFilter,
    NodeRef,
    NodeType,
    OperatorType,
    OrderOperator,
    QueryPlan,
    ScopeConstraint,
    SequenceExpr,
)
from src.engine.parser import parse
from src.validation.registry import CapabilityRegistry
from src.validation.validator import validate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mvp() -> CapabilityRegistry:
    return CapabilityRegistry.mvp()


def _simple_plan(
    *values: str,
    node_type: NodeType = NodeType.CONCEPT,
    mode: str = "conceptual",
    scope: ScopeConstraint | None = None,
) -> QueryPlan:
    """Build a simple QueryPlan with concept nodes."""
    steps = [NodeRef(type=node_type, value=v) for v in values]
    operators = [OrderOperator(type=OperatorType.PRECEDENCE)] * (len(values) - 1)
    return QueryPlan(
        version="0.1",
        source=" > ".join(values),
        sequence=SequenceExpr(steps=steps, operators=operators),
        scope=scope or ScopeConstraint(),
        mode=mode,
    )


# ---------------------------------------------------------------------------
# Phase 1: Registry and output types
# ---------------------------------------------------------------------------


class TestCapabilityRegistry:
    def test_mvp_version(self) -> None:
        reg = _mvp()
        assert reg.version == "0.1"

    def test_mvp_node_types(self) -> None:
        reg = _mvp()
        assert set(reg.node_types) == {"token", "lemma", "concept", "morph", "wildcard"}

    def test_mvp_operators(self) -> None:
        """Slice L: cooccurrence is now executable; adjacency still advertised
        for parser-shape parity (rejected at the executor's second wall)."""
        reg = _mvp()
        assert set(reg.operators) == {"precedence", "adjacency", "cooccurrence"}

    def test_mvp_scope_units(self) -> None:
        """Slice L: scope_units enumerates the kinds the executor runs."""
        reg = _mvp()
        assert reg.scope_units == ["verse", "window"]
        assert reg.window_max_tokens == 50

    def test_mvp_corpora(self) -> None:
        reg = _mvp()
        assert reg.corpora == ["nt"]
        assert reg.languages == ["grc"]

    def test_mvp_flags(self) -> None:
        reg = _mvp()
        assert reg.polarity_support is True
        assert reg.inverse_support is False
        assert reg.expansion_support is False
        assert reg.compound_node_support is False


class TestValidationResult:
    def test_supported(self) -> None:
        plan = _simple_plan("faith", "hope")
        result = validate(plan, _mvp())
        assert result.status == "supported"
        assert result.executable_plan is not None
        assert result.findings == []


# ---------------------------------------------------------------------------
# Phase 2: Rules 1-8
# ---------------------------------------------------------------------------


class TestRule1Version:
    def test_compatible(self) -> None:
        result = validate(_simple_plan("faith", "hope"), _mvp())
        codes = {f.code for f in result.findings}
        assert "INCOMPATIBLE_VERSION" not in codes

    def test_incompatible(self) -> None:
        plan = QueryPlan(
            version="0.9",
            source="faith > hope",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                ],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "INCOMPATIBLE_VERSION" in codes


class TestRule2NodeTypes:
    def test_supported_types(self) -> None:
        result = validate(_simple_plan("faith", "hope"), _mvp())
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_NODE_TYPE" not in codes

    def test_root_unsupported(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="root:אמן > root:אהב",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.ROOT, value="אמן"),
                    NodeRef(type=NodeType.ROOT, value="אהב"),
                ],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            ),
            scope=ScopeConstraint(),
            mode="exact",
        )
        result = validate(plan, _mvp())
        codes = [f.code for f in result.findings]
        assert codes.count("UNSUPPORTED_NODE_TYPE") == 2

    def test_domain_unsupported(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="domain:trust",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.DOMAIN, value="trust"),
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                ],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        result = validate(plan, _mvp())
        codes = [f.code for f in result.findings]
        assert "UNSUPPORTED_NODE_TYPE" in codes


class TestRule3Operators:
    def test_precedence_supported(self) -> None:
        result = validate(_simple_plan("faith", "hope"), _mvp())
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_OPERATOR" not in codes

    def test_cooccurrence_supported_in_slice_l(self) -> None:
        """Slice L: cooccurrence is now in the MVP registry's operators
        list (Decision #7). Previously rejected as UNSUPPORTED_OPERATOR."""
        plan = QueryPlan(
            version="0.1",
            source="faith ~ hope",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                ],
                operators=[OrderOperator(type=OperatorType.COOCCURRENCE)],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_OPERATOR" not in codes


class TestRule5Polarity:
    def test_polarity_supported_in_mvp(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="+concept:faith > +concept:hope",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith", polarity="+"),
                    NodeRef(type=NodeType.CONCEPT, value="hope", polarity="+"),
                ],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_POLARITY" not in codes


class TestRule6Inverse:
    def test_inverse_unsupported(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="inverse(faith > hope)",
            sequence=InverseExpr(
                inner=SequenceExpr(
                    steps=[
                        NodeRef(type=NodeType.CONCEPT, value="faith"),
                        NodeRef(type=NodeType.CONCEPT, value="hope"),
                    ],
                    operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
                )
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        result = validate(plan, _mvp())
        assert result.status == "unsupported"
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_INVERSE" in codes


class TestRule7Expansion:
    def test_expansion_unsupported(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="faith > hope => forward:2",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                ],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
            expansion=ExpansionDirective(
                direction=ExpansionDirection.FORWARD, depth=2
            ),
        )
        result = validate(plan, _mvp())
        assert result.status == "partial"
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_EXPANSION" in codes
        assert result.executable_plan is not None
        assert result.executable_plan.expansion is None


class TestRule8CompoundNodes:
    def test_compound_unsupported(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="lemma:pistis+morph:NOUN > concept:hope",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(
                        type=NodeType.LEMMA,
                        value="pistis",
                        morph_filters=[MorphFilter(feature="NOUN")],
                    ),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                ],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_COMPOUND_NODE" in codes


# ---------------------------------------------------------------------------
# Phase 3: Rules 9-12 + partial reduction
# ---------------------------------------------------------------------------


class TestRule10Scope:
    def test_unknown_corpus(self) -> None:
        plan = _simple_plan(
            "faith", "hope",
            scope=ScopeConstraint(corpus="ot"),
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "UNKNOWN_CORPUS" in codes

    def test_unknown_language(self) -> None:
        plan = _simple_plan(
            "faith", "hope",
            scope=ScopeConstraint(language="heb"),
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "UNKNOWN_LANGUAGE" in codes

    def test_valid_scope(self) -> None:
        plan = _simple_plan(
            "faith", "hope",
            scope=ScopeConstraint(corpus="nt", language="grc"),
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "UNKNOWN_CORPUS" not in codes
        assert "UNKNOWN_LANGUAGE" not in codes


class TestRule10WindowConstraints:
    """Slice L Decision #5 + #10: WINDOW_EXCEEDS_MAX and
    GAP_NARROWED_BY_WINDOW are emitted from rule 10's scope check."""

    def test_window_within_limit(self) -> None:
        from src.engine.models import ScopeUnitWindow

        plan = _simple_plan(
            "faith", "hope",
            scope=ScopeConstraint(unit=ScopeUnitWindow(n=50)),
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "WINDOW_EXCEEDS_MAX" not in codes
        assert result.status == "supported"

    def test_window_exceeds_max(self) -> None:
        from src.engine.models import ScopeUnitWindow

        plan = _simple_plan(
            "faith", "hope",
            scope=ScopeConstraint(unit=ScopeUnitWindow(n=100)),
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "WINDOW_EXCEEDS_MAX" in codes
        # An error code → status is partial (reduction strips nothing here)
        # or unsupported. Either way, status is not "supported".
        assert result.status != "supported"

    def test_gap_narrowed_by_window_warning(self) -> None:
        """Decision #10: when step-level gap.max > outer window.n, emit a
        GAP_NARROWED_BY_WINDOW warning. Status stays ``supported`` — the
        narrowing is informational, the executor handles AND-composition
        natively."""
        from src.engine.models import GapConstraint, ScopeUnitWindow

        plan = QueryPlan(
            version="0.1",
            source="faith >{0,80} hope within:window(50)",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                ],
                operators=[
                    OrderOperator(
                        type=OperatorType.PRECEDENCE,
                        gap=GapConstraint(min=0, max=80),
                    )
                ],
            ),
            scope=ScopeConstraint(unit=ScopeUnitWindow(n=50)),
            mode="conceptual",
        )
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "GAP_NARROWED_BY_WINDOW" in codes
        assert result.status == "supported"


class TestRule11SequenceLength:
    def test_within_limit(self) -> None:
        plan = _simple_plan("a", "b", "c")
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "SEQUENCE_TOO_LONG" not in codes

    def test_exceeds_limit(self) -> None:
        values = [f"c{i}" for i in range(12)]
        plan = _simple_plan(*values)
        result = validate(plan, _mvp())
        codes = {f.code for f in result.findings}
        assert "SEQUENCE_TOO_LONG" in codes


class TestPartialReduction:
    def test_expansion_stripped(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="faith > hope => forward:2",
            sequence=SequenceExpr(
                steps=[
                    NodeRef(type=NodeType.CONCEPT, value="faith"),
                    NodeRef(type=NodeType.CONCEPT, value="hope"),
                ],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
            expansion=ExpansionDirective(
                direction=ExpansionDirection.FORWARD, depth=2
            ),
        )
        result = validate(plan, _mvp())
        assert result.status == "partial"
        assert result.executable_plan is not None
        assert result.executable_plan.expansion is None
        assert len(result.executable_plan.sequence.steps) == 2

    def test_unsupported_node_inside_alternative_collapses(self) -> None:
        # `root` is not in the MVP node_types registry. The alternative should
        # drop the unsupported option; with one survivor it collapses to a NodeRef.
        plan = parse("(root:foo | concept:faith) > concept:hope")
        result = validate(plan, _mvp())
        assert result.status == "partial"
        assert result.executable_plan is not None
        steps = result.executable_plan.sequence.steps
        assert len(steps) == 2
        assert isinstance(steps[0], NodeRef)
        assert steps[0].type == NodeType.CONCEPT
        assert steps[0].value == "faith"
        assert isinstance(steps[1], NodeRef)
        assert steps[1].value == "hope"

    def test_alternative_dropped_when_all_options_unsupported(self) -> None:
        # Both alternative options use `root` (unsupported). The whole alternative
        # step is dropped, leaving the surrounding sequence to collapse to 2 steps.
        plan = parse("concept:faith > (root:a | root:b) > concept:hope")
        result = validate(plan, _mvp())
        assert result.status == "partial"
        assert result.executable_plan is not None
        steps = result.executable_plan.sequence.steps
        assert len(steps) == 2
        assert all(isinstance(s, NodeRef) and s.type == NodeType.CONCEPT for s in steps)
        assert [s.value for s in steps] == ["faith", "hope"]

    def test_unsupported_inside_optional_dropped(self) -> None:
        # `[root:foo]` should be dropped because its inner NodeRef is unsupported;
        # the surrounding sequence reduces to two concept nodes.
        plan = parse("concept:faith > [root:foo] > concept:hope")
        result = validate(plan, _mvp())
        assert result.status == "partial"
        assert result.executable_plan is not None
        steps = result.executable_plan.sequence.steps
        assert len(steps) == 2
        assert all(isinstance(s, NodeRef) and s.type == NodeType.CONCEPT for s in steps)


# ---------------------------------------------------------------------------
# Phase 4: Doc 07 integration tests
# ---------------------------------------------------------------------------


class TestDoc07Validation:
    def test_example_1_supported(self) -> None:
        plan = parse("faith > hope > love")
        result = validate(plan, _mvp())
        assert result.status == "supported"

    def test_example_2_supported(self) -> None:
        plan = parse(
            "lemma:pistis >{0,3} lemma:elpis > lemma:agape"
            " within:verse lang:grc corpus:nt"
        )
        result = validate(plan, _mvp())
        assert result.status == "supported"

    def test_example_3_supported(self) -> None:
        plan = parse(
            "+concept:faith > +concept:hope > +concept:love"
            " within:verse corpus:nt"
        )
        result = validate(plan, _mvp())
        assert result.status == "supported"

    def test_example_4_supported(self) -> None:
        plan = parse(
            "concept:faith > (concept:hope | concept:expectation)"
            " > [concept:endurance] > concept:love"
        )
        result = validate(plan, _mvp())
        assert result.status == "supported"

    def test_example_5_unsupported_inverse(self) -> None:
        plan = parse("inverse(faith > hope > love) within:verse corpus:nt")
        result = validate(plan, _mvp())
        assert result.status == "unsupported"
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_INVERSE" in codes

    def test_example_6_partial_expansion(self) -> None:
        plan = parse(
            "lemma:pistis > lemma:elpis > lemma:agape"
            " => forward:2 within:verse corpus:nt lang:grc"
        )
        result = validate(plan, _mvp())
        assert result.status == "partial"
        codes = {f.code for f in result.findings}
        assert "UNSUPPORTED_EXPANSION" in codes
        assert result.executable_plan is not None
        assert result.executable_plan.expansion is None

    def test_example_7_unsupported_root_hebrew(self) -> None:
        plan = parse(
            "root:אמן > root:תקו > root:אהב"
            " within:verse corpus:ot lang:heb"
        )
        result = validate(plan, _mvp())
        assert result.status == "unsupported"
        codes = [f.code for f in result.findings]
        assert "UNSUPPORTED_NODE_TYPE" in codes
        assert "UNKNOWN_CORPUS" in codes
        assert "UNKNOWN_LANGUAGE" in codes

    def test_example_8_supported_nl_sourced(self) -> None:
        plan = parse(
            "lemma:pistis > lemma:elpis > lemma:agape"
            " within:verse lang:grc corpus:nt"
            " book:rom,1cor,2cor,gal,eph,php,col,1th,2th,1ti,2ti,tit,phm"
        )
        result = validate(plan, _mvp())
        assert result.status == "supported"
