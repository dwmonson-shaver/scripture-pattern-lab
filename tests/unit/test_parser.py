"""Tests for DSL parser (src/engine/parser.py)."""

import pytest

from src.engine.models import (
    AlternativeExpr,
    ExpansionDirection,
    GapConstraint,
    InverseExpr,
    NodeRef,
    NodeType,
    OperatorType,
    OptionalExpr,
    ScopeUnitVerse,
    ScopeUnitWindow,
    SequenceExpr,
)
from src.engine.parser import ParseError, TokenKind, _Parser, parse, tokenize

# ---------------------------------------------------------------------------
# Phase 1: Tokenizer
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_simple_sequence(self) -> None:
        tokens = tokenize("faith > hope > love")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.WORD, TokenKind.GT,
            TokenKind.WORD, TokenKind.GT,
            TokenKind.WORD, TokenKind.EOF,
        ]
        assert tokens[0].value == "faith"
        assert tokens[2].value == "hope"
        assert tokens[4].value == "love"

    def test_typed_node(self) -> None:
        tokens = tokenize("lemma:pistis")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.WORD, TokenKind.COLON, TokenKind.WORD, TokenKind.EOF,
        ]
        assert tokens[0].value == "lemma"
        assert tokens[2].value == "pistis"

    def test_gap_constraint(self) -> None:
        tokens = tokenize(">{0,3}")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.GT, TokenKind.LBRACE,
            TokenKind.WORD, TokenKind.COMMA,
            TokenKind.WORD, TokenKind.RBRACE, TokenKind.EOF,
        ]
        assert tokens[2].value == "0"
        assert tokens[4].value == "3"

    def test_polarity_plus(self) -> None:
        tokens = tokenize("+concept:faith")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.PLUS, TokenKind.WORD, TokenKind.COLON,
            TokenKind.WORD, TokenKind.EOF,
        ]

    def test_polarity_minus(self) -> None:
        tokens = tokenize("-concept:faith")
        assert tokens[0].kind == TokenKind.MINUS

    def test_polarity_plusminus(self) -> None:
        tokens = tokenize("±concept:faith")
        assert tokens[0].kind == TokenKind.PLUSMINUS

    def test_adjacency_operator(self) -> None:
        tokens = tokenize("faith >> hope")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.WORD, TokenKind.GT_GT, TokenKind.WORD, TokenKind.EOF,
        ]

    def test_cooccurrence_operator(self) -> None:
        tokens = tokenize("faith ~ hope")
        assert tokens[1].kind == TokenKind.TILDE

    def test_alternatives(self) -> None:
        tokens = tokenize("(hope | expectation)")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.LPAREN, TokenKind.WORD, TokenKind.PIPE,
            TokenKind.WORD, TokenKind.RPAREN, TokenKind.EOF,
        ]

    def test_optional(self) -> None:
        tokens = tokenize("[endurance]")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.LBRACKET, TokenKind.WORD, TokenKind.RBRACKET, TokenKind.EOF,
        ]

    def test_bang(self) -> None:
        tokens = tokenize("!concept:sin")
        assert tokens[0].kind == TokenKind.BANG

    def test_arrow(self) -> None:
        tokens = tokenize("=> forward:2")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.ARROW, TokenKind.WORD, TokenKind.COLON,
            TokenKind.WORD, TokenKind.EOF,
        ]

    def test_inverse_function(self) -> None:
        tokens = tokenize("inverse(faith > hope)")
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.WORD, TokenKind.LPAREN,
            TokenKind.WORD, TokenKind.GT, TokenKind.WORD,
            TokenKind.RPAREN, TokenKind.EOF,
        ]
        assert tokens[0].value == "inverse"

    def test_hebrew_characters(self) -> None:
        tokens = tokenize("root:אמן")
        assert tokens[0].value == "root"
        assert tokens[2].value == "אמן"

    def test_greek_characters(self) -> None:
        tokens = tokenize("lemma:πίστις")
        assert tokens[2].value == "πίστις"

    def test_position_tracking(self) -> None:
        tokens = tokenize("faith > hope")
        assert tokens[0].pos == 0
        assert tokens[1].pos == 6
        assert tokens[2].pos == 8

    def test_complex_query(self) -> None:
        dsl = "lemma:pistis >{0,3} lemma:elpis within:verse lang:grc corpus:nt"
        tokens = tokenize(dsl)
        words = [t.value for t in tokens if t.kind == TokenKind.WORD]
        assert "lemma" in words
        assert "pistis" in words
        assert "within" in words
        assert "verse" in words

    def test_empty_input(self) -> None:
        tokens = tokenize("")
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.EOF

    def test_whitespace_only(self) -> None:
        tokens = tokenize("   ")
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.EOF

    def test_unexpected_character(self) -> None:
        with pytest.raises(ParseError) as exc_info:
            tokenize("faith @ hope")
        assert exc_info.value.pos == 6

    def test_book_list(self) -> None:
        tokens = tokenize("book:rom,1cor,2cor")
        words = [t.value for t in tokens if t.kind == TokenKind.WORD]
        assert words == ["book", "rom", "1cor", "2cor"]

    def test_wildcard_star(self) -> None:
        tokens = tokenize("*")
        non_eof = [t for t in tokens if t.kind != TokenKind.EOF]
        assert len(non_eof) == 1
        assert non_eof[0].kind == TokenKind.WORD
        assert non_eof[0].value == "*"


# ---------------------------------------------------------------------------
# Phase 2: Core parser — sequences, steps, operators
# ---------------------------------------------------------------------------


def _make_parser(dsl: str) -> _Parser:
    return _Parser(tokenize(dsl), dsl)


class TestParseNodeRef:
    def test_bare_word(self) -> None:
        p = _make_parser("faith")
        node = p.parse_node_ref()
        assert isinstance(node, NodeRef)
        assert node.type == NodeType.CONCEPT
        assert node.value == "faith"

    def test_typed_node(self) -> None:
        p = _make_parser("lemma:pistis")
        node = p.parse_node_ref()
        assert node.type == NodeType.LEMMA
        assert node.value == "pistis"

    def test_polarity_plus(self) -> None:
        p = _make_parser("+concept:faith")
        node = p.parse_node_ref()
        assert node.polarity == "+"
        assert node.type == NodeType.CONCEPT
        assert node.value == "faith"

    def test_polarity_minus(self) -> None:
        p = _make_parser("-concept:unbelief")
        node = p.parse_node_ref()
        assert node.polarity == "-"

    def test_polarity_plusminus(self) -> None:
        p = _make_parser("±concept:faith")
        node = p.parse_node_ref()
        assert node.polarity == "±"

    def test_wildcard(self) -> None:
        p = _make_parser("*")
        node = p.parse_node_ref()
        assert isinstance(node, NodeRef)
        assert node.type == NodeType.WILDCARD
        assert node.value == "*"


class TestParseSequence:
    def test_simple_three_step(self) -> None:
        p = _make_parser("faith > hope > love")
        seq = p.parse_sequence()
        assert len(seq.steps) == 3
        assert len(seq.operators) == 2
        assert all(isinstance(s, NodeRef) for s in seq.steps)
        assert all(o.type == OperatorType.PRECEDENCE for o in seq.operators)

    def test_with_gap(self) -> None:
        p = _make_parser("lemma:pistis >{0,3} lemma:elpis")
        seq = p.parse_sequence()
        assert len(seq.steps) == 2
        assert seq.operators[0].gap is not None
        assert seq.operators[0].gap.min == 0
        assert seq.operators[0].gap.max == 3

    def test_adjacency(self) -> None:
        p = _make_parser("faith >> hope")
        seq = p.parse_sequence()
        assert seq.operators[0].type == OperatorType.ADJACENCY

    def test_cooccurrence(self) -> None:
        p = _make_parser("faith ~ hope")
        seq = p.parse_sequence()
        assert seq.operators[0].type == OperatorType.COOCCURRENCE
        assert seq.operators[0].gap is None

    def test_cooccurrence_with_gap(self) -> None:
        """Slice L Decision #7: ``~{m,n}`` carries a step-level gap, same
        syntax as ``>{m,n}``. Executor uses ``abs(next - prev)``.
        """
        p = _make_parser("faith ~{0,5} hope")
        seq = p.parse_sequence()
        assert seq.operators[0].type == OperatorType.COOCCURRENCE
        assert seq.operators[0].gap == GapConstraint(min=0, max=5)

    def test_wildcard_in_sequence(self) -> None:
        p = _make_parser("* > concept:faith")
        seq = p.parse_sequence()
        assert len(seq.steps) == 2
        assert isinstance(seq.steps[0], NodeRef)
        assert seq.steps[0].type == NodeType.WILDCARD
        assert isinstance(seq.steps[1], NodeRef)
        assert seq.steps[1].type == NodeType.CONCEPT
        assert seq.steps[1].value == "faith"


class TestParseAlternative:
    def test_two_options(self) -> None:
        p = _make_parser("(concept:hope | concept:expectation)")
        step = p.parse_step()
        assert isinstance(step, AlternativeExpr)
        assert len(step.options) == 2
        assert step.options[0].value == "hope"
        assert step.options[1].value == "expectation"

    def test_three_options(self) -> None:
        p = _make_parser("(faith | hope | love)")
        step = p.parse_step()
        assert isinstance(step, AlternativeExpr)
        assert len(step.options) == 3

    def test_polarity_distributes_to_alternative_options(self) -> None:
        # Per docs/canonical/05_dsl-ast.md:252-271, `+(...)` distributes polarity
        # to every NodeRef option.
        p = _make_parser("+(concept:hope | concept:expectation)")
        step = p.parse_step()
        assert isinstance(step, AlternativeExpr)
        assert len(step.options) == 2
        assert all(isinstance(opt, NodeRef) for opt in step.options)
        assert step.options[0].polarity == "+"
        assert step.options[1].polarity == "+"
        assert step.options[0].value == "hope"
        assert step.options[1].value == "expectation"

    def test_minus_polarity_before_alternative(self) -> None:
        p = _make_parser("-(concept:doubt | concept:fear)")
        step = p.parse_step()
        assert isinstance(step, AlternativeExpr)
        assert step.options[0].polarity == "-"
        assert step.options[1].polarity == "-"

    def test_canonical_05_polarity_alternatives_sequence(self) -> None:
        # The exact DSL on docs/canonical/05_dsl-ast.md:252.
        p = _make_parser("+concept:faith > +(concept:hope | concept:expectation) > +concept:love")
        seq = p.parse_sequence()
        assert len(seq.steps) == 3
        assert isinstance(seq.steps[0], NodeRef) and seq.steps[0].polarity == "+"
        assert isinstance(seq.steps[1], AlternativeExpr)
        assert all(opt.polarity == "+" for opt in seq.steps[1].options)
        assert isinstance(seq.steps[2], NodeRef) and seq.steps[2].polarity == "+"


class TestParseOptional:
    def test_optional_node(self) -> None:
        p = _make_parser("[concept:endurance]")
        step = p.parse_step()
        assert isinstance(step, OptionalExpr)
        assert isinstance(step.inner, NodeRef)
        assert step.inner.value == "endurance"


class TestParseNegation:
    def test_negated_node(self) -> None:
        p = _make_parser("!concept:sin")
        step = p.parse_step()
        assert isinstance(step, NodeRef)
        assert step.negated is True
        assert step.value == "sin"


# ---------------------------------------------------------------------------
# Phase 3: Directives, inverse, and top-level parse()
# ---------------------------------------------------------------------------


class TestParseDirectives:
    def test_scope_within(self) -> None:
        plan = parse("faith > hope within:verse")
        assert isinstance(plan.scope.unit, ScopeUnitVerse)

    def test_scope_within_window(self) -> None:
        """Slice L: ``within:window(N)`` parses to ``ScopeUnitWindow(n=N)``."""
        plan = parse("faith > hope within:window(50)")
        assert isinstance(plan.scope.unit, ScopeUnitWindow)
        assert plan.scope.unit.n == 50

    def test_scope_within_window_rejects_zero(self) -> None:
        """Slice L Decision #8: ``window(0)`` is degenerate; parser rejects it."""
        with pytest.raises(ParseError) as excinfo:
            parse("faith > hope within:window(0)")
        assert "window size must be >= 1" in str(excinfo.value)

    def test_scope_within_window_requires_parens(self) -> None:
        """``within:window`` without ``(N)`` is an error — N must be explicit."""
        with pytest.raises(ParseError):
            parse("faith > hope within:window")

    def test_scope_within_rejects_unsupported_unit(self) -> None:
        """Slice L: ``clause | sentence | pericope | chapter`` previously parsed
        into the inert StrEnum and were rejected at execute; now rejected at parse.
        """
        with pytest.raises(ParseError) as excinfo:
            parse("faith > hope within:chapter")
        assert "chapter" in str(excinfo.value)

    def test_scope_lang(self) -> None:
        plan = parse("lemma:pistis > lemma:elpis lang:grc")
        assert plan.scope.language == "grc"

    def test_scope_corpus(self) -> None:
        plan = parse("faith > hope corpus:nt")
        assert plan.scope.corpus == "nt"

    def test_scope_book_list(self) -> None:
        plan = parse("faith > hope book:rom,1cor,2cor")
        assert plan.scope.books == ["rom", "1cor", "2cor"]

    def test_multiple_directives(self) -> None:
        plan = parse("lemma:pistis > lemma:elpis within:verse lang:grc corpus:nt")
        assert isinstance(plan.scope.unit, ScopeUnitVerse)
        assert plan.scope.language == "grc"
        assert plan.scope.corpus == "nt"

    def test_mode_directive(self) -> None:
        plan = parse("faith > hope mode:exact")
        assert plan.mode == "exact"

    def test_expansion_forward(self) -> None:
        plan = parse("faith > hope > love => forward:2")
        assert plan.expansion is not None
        assert plan.expansion.direction == ExpansionDirection.FORWARD
        assert plan.expansion.depth == 2

    def test_expansion_expand(self) -> None:
        plan = parse("faith > hope => expand:3")
        assert plan.expansion.direction == ExpansionDirection.BOTH
        assert plan.expansion.depth == 3


class TestParseInverse:
    def test_inverse_wrapper(self) -> None:
        plan = parse("inverse(faith > hope > love) corpus:nt")
        assert isinstance(plan.sequence, InverseExpr)
        assert len(plan.sequence.inner.steps) == 3
        assert plan.scope.corpus == "nt"
        assert plan.mode == "conceptual"


class TestParseFull:
    def test_default_mode_concept(self) -> None:
        plan = parse("faith > hope > love")
        assert plan.mode == "conceptual"

    def test_default_mode_exact(self) -> None:
        plan = parse("lemma:pistis > lemma:elpis")
        assert plan.mode == "exact"

    def test_version(self) -> None:
        plan = parse("faith > hope")
        assert plan.version == "0.1"

    def test_source_preserved(self) -> None:
        dsl = "faith > hope > love"
        plan = parse(dsl)
        assert plan.source == dsl

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ParseError):
            parse("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ParseError):
            parse("   ")

    def test_trailing_junk_raises(self) -> None:
        with pytest.raises(ParseError):
            parse("faith > hope > love @@@")


# ---------------------------------------------------------------------------
# Phase 4: Doc 07 integration tests
# ---------------------------------------------------------------------------


class TestDoc07Examples:
    def test_example_1_simple_concept_sequence(self) -> None:
        """faith > hope > love"""
        plan = parse("faith > hope > love")
        assert isinstance(plan.sequence, SequenceExpr)
        assert len(plan.sequence.steps) == 3
        assert all(isinstance(s, NodeRef) for s in plan.sequence.steps)
        assert all(s.type == NodeType.CONCEPT for s in plan.sequence.steps)
        vals = [s.value for s in plan.sequence.steps]
        assert vals == ["faith", "hope", "love"]
        assert all(
            o.type == OperatorType.PRECEDENCE for o in plan.sequence.operators
        )
        assert all(o.gap is None for o in plan.sequence.operators)
        assert plan.mode == "conceptual"
        assert plan.expansion is None

    def test_example_2_typed_lemma_with_gap_and_scope(self) -> None:
        dsl = (
            "lemma:pistis >{0,3} lemma:elpis > lemma:agape"
            " within:verse lang:grc corpus:nt"
        )
        plan = parse(dsl)
        assert len(plan.sequence.steps) == 3
        assert all(s.type == NodeType.LEMMA for s in plan.sequence.steps)
        assert plan.sequence.operators[0].gap is not None
        assert plan.sequence.operators[0].gap.min == 0
        assert plan.sequence.operators[0].gap.max == 3
        assert plan.sequence.operators[1].gap is None
        assert plan.scope.corpus == "nt"
        assert plan.scope.language == "grc"
        assert isinstance(plan.scope.unit, ScopeUnitVerse)
        assert plan.mode == "exact"

    def test_example_3_polarity_marked(self) -> None:
        dsl = (
            "+concept:faith > +concept:hope > +concept:love"
            " within:verse corpus:nt"
        )
        plan = parse(dsl)
        assert all(s.polarity == "+" for s in plan.sequence.steps)
        assert plan.scope.corpus == "nt"
        assert isinstance(plan.scope.unit, ScopeUnitVerse)
        assert plan.mode == "conceptual"

    def test_example_4_alternatives_and_optional(self) -> None:
        dsl = (
            "concept:faith > (concept:hope | concept:expectation)"
            " > [concept:endurance] > concept:love"
        )
        plan = parse(dsl)
        assert len(plan.sequence.steps) == 4
        assert isinstance(plan.sequence.steps[0], NodeRef)
        assert isinstance(plan.sequence.steps[1], AlternativeExpr)
        assert len(plan.sequence.steps[1].options) == 2
        assert isinstance(plan.sequence.steps[2], OptionalExpr)
        assert isinstance(plan.sequence.steps[3], NodeRef)
        assert len(plan.sequence.operators) == 3

    def test_example_5_inverse(self) -> None:
        dsl = "inverse(faith > hope > love) within:verse corpus:nt"
        plan = parse(dsl)
        assert isinstance(plan.sequence, InverseExpr)
        assert len(plan.sequence.inner.steps) == 3
        vals = [s.value for s in plan.sequence.inner.steps]
        assert vals == ["faith", "hope", "love"]
        assert plan.scope.corpus == "nt"
        assert isinstance(plan.scope.unit, ScopeUnitVerse)
        assert plan.mode == "conceptual"

    def test_example_6_expansion(self) -> None:
        dsl = (
            "lemma:pistis > lemma:elpis > lemma:agape"
            " => forward:2 within:verse corpus:nt lang:grc"
        )
        plan = parse(dsl)
        assert len(plan.sequence.steps) == 3
        assert plan.expansion is not None
        assert plan.expansion.direction == ExpansionDirection.FORWARD
        assert plan.expansion.depth == 2
        assert plan.scope.corpus == "nt"
        assert plan.scope.language == "grc"

    def test_example_7_root_nodes(self) -> None:
        dsl = (
            "root:אמן > root:תקו > root:אהב"
            " within:verse corpus:ot lang:heb"
        )
        plan = parse(dsl)
        assert all(s.type == NodeType.ROOT for s in plan.sequence.steps)
        assert plan.scope.corpus == "ot"
        assert plan.scope.language == "heb"

    def test_example_8_nl_sourced_with_book_list(self) -> None:
        dsl = (
            "lemma:pistis > lemma:elpis > lemma:agape"
            " within:verse lang:grc corpus:nt"
            " book:rom,1cor,2cor,gal,eph,php,col,1th,2th,1ti,2ti,tit,phm"
        )
        plan = parse(dsl)
        assert len(plan.sequence.steps) == 3
        assert plan.scope.books is not None
        assert len(plan.scope.books) == 13
        assert "rom" in plan.scope.books
        assert "phm" in plan.scope.books
        assert plan.scope.language == "grc"
        assert plan.scope.corpus == "nt"
