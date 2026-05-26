"""DSL parser — compiles DSL text into QueryPlan AST.

Two-phase design: tokenize (scan text into tokens) then parse
(recursive descent over tokens to produce Pydantic AST models).

Interface per docs/canonical/09_backend-service-boundaries.md:
    def parse(dsl: str) -> QueryPlan
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.engine.models import (
        ExpansionDirective,
        GapConstraint,
        InverseExpr,
        MatchMode,
        NodeRef,
        NodeType,
        OptionalExpr,
        OrderOperator,
        QueryPlan,
        ScopeConstraint,
        SequenceExpr,
        StepExpr,
    )

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


class TokenKind(StrEnum):
    """Lexer token types."""

    WORD = "word"
    COLON = "colon"
    GT = "gt"
    GT_GT = "gt_gt"
    TILDE = "tilde"
    PIPE = "pipe"
    LPAREN = "lparen"
    RPAREN = "rparen"
    LBRACKET = "lbracket"
    RBRACKET = "rbracket"
    LBRACE = "lbrace"
    RBRACE = "rbrace"
    COMMA = "comma"
    BANG = "bang"
    PLUS = "plus"
    MINUS = "minus"
    PLUSMINUS = "plusminus"
    ARROW = "arrow"
    EOF = "eof"


class Token(BaseModel):
    """A lexer token with position info."""

    model_config = ConfigDict(frozen=True)

    kind: TokenKind
    value: str
    pos: int


class ParseError(Exception):
    """Raised when DSL text cannot be parsed."""

    def __init__(self, message: str, pos: int, source: str) -> None:
        self.pos = pos
        self.source = source
        super().__init__(f"{message} (at position {pos})")


def tokenize(source: str) -> list[Token]:
    """Scan DSL text into a flat list of tokens."""
    tokens: list[Token] = []
    i = 0
    n = len(source)

    while i < n:
        ch = source[i]

        # Skip whitespace
        if ch.isspace():
            i += 1
            continue

        # Two-character tokens
        if ch == ">" and i + 1 < n and source[i + 1] == ">":
            tokens.append(Token(kind=TokenKind.GT_GT, value=">>", pos=i))
            i += 2
            continue

        if ch == ">" and i + 1 < n and source[i + 1] == "{":
            # Just emit GT — the parser will handle >{min,max} by reading LBRACE next
            tokens.append(Token(kind=TokenKind.GT, value=">", pos=i))
            i += 1
            continue

        if ch == "=" and i + 1 < n and source[i + 1] == ">":
            tokens.append(Token(kind=TokenKind.ARROW, value="=>", pos=i))
            i += 2
            continue

        # ± (multi-byte UTF-8)
        if ch == "±":
            tokens.append(Token(kind=TokenKind.PLUSMINUS, value="±", pos=i))
            i += 1
            continue

        # Single-character tokens
        single = {
            ">": TokenKind.GT,
            "~": TokenKind.TILDE,
            "|": TokenKind.PIPE,
            "(": TokenKind.LPAREN,
            ")": TokenKind.RPAREN,
            "[": TokenKind.LBRACKET,
            "]": TokenKind.RBRACKET,
            "{": TokenKind.LBRACE,
            "}": TokenKind.RBRACE,
            ",": TokenKind.COMMA,
            "!": TokenKind.BANG,
            "+": TokenKind.PLUS,
            "-": TokenKind.MINUS,
            ":": TokenKind.COLON,
        }

        if ch in single:
            tokens.append(Token(kind=single[ch], value=ch, pos=i))
            i += 1
            continue

        # Wildcard — emitted as WORD so _parse_typed_value's `word_tok.value == "*"`
        # branch is reachable (NodeType.WILDCARD is part of the v0.1 spec).
        if ch == "*":
            tokens.append(Token(kind=TokenKind.WORD, value="*", pos=i))
            i += 1
            continue

        # Words: letters, digits, underscores, dots, Unicode (for Hebrew/Greek)
        if _is_word_char(ch):
            start = i
            while i < n and _is_word_char(source[i]):
                i += 1
            tokens.append(Token(kind=TokenKind.WORD, value=source[start:i], pos=start))
            continue

        raise ParseError(f"Unexpected character: {ch!r}", pos=i, source=source)

    tokens.append(Token(kind=TokenKind.EOF, value="", pos=n))
    return tokens


def _is_word_char(ch: str) -> bool:
    """Check if a character can be part of a word token."""
    if ch.isalnum() or ch == "_" or ch == ".":
        return True
    # Allow Unicode letters (Greek, Hebrew, etc.)
    if ch.isalpha():
        return True
    # Allow specific Unicode characters common in Hebrew
    cat = _unicode_category(ch)
    return cat.startswith("L") or cat.startswith("M")  # Letters and marks


def _unicode_category(ch: str) -> str:
    """Get the Unicode general category of a character."""
    import unicodedata

    return unicodedata.category(ch)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Node type prefixes recognized by the parser
_NODE_TYPE_PREFIXES = {"lemma", "concept", "root", "morph", "domain", "token"}

# Directive keywords (trailing scope/mode/expansion)
_DIRECTIVE_KEYWORDS = {"within", "lang", "corpus", "book", "mode"}


def _distribute_polarity(step: "StepExpr", polarity: str) -> "StepExpr":
    """Apply polarity to each NodeRef inside a group/alternative.

    Per docs/canonical/05_dsl-ast.md:252-271, `+(concept:hope | concept:expectation)`
    expands to an AlternativeExpr where each NodeRef option carries polarity '+'.
    Recurses into nested groups/alternatives so polarity on `+((a | b) | c)` reaches
    every leaf NodeRef.
    """
    from src.engine.models import AlternativeExpr, GroupExpr, NodeRef

    if isinstance(step, NodeRef):
        return step.model_copy(update={"polarity": polarity})
    if isinstance(step, AlternativeExpr):
        return step.model_copy(
            update={"options": [_distribute_polarity(opt, polarity) for opt in step.options]}
        )
    if isinstance(step, GroupExpr):
        new_steps = [_distribute_polarity(s, polarity) for s in step.sequence.steps]
        new_seq = step.sequence.model_copy(update={"steps": new_steps})
        return step.model_copy(update={"sequence": new_seq})
    return step


class _Parser:
    """Recursive descent parser consuming a token list."""

    def __init__(self, tokens: list[Token], source: str) -> None:
        self.tokens = tokens
        self.source = source
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind: TokenKind) -> Token:
        tok = self.peek()
        if tok.kind != kind:
            self._error(f"Expected {kind.value}, got {tok.kind.value}")
        return self.advance()

    def at(self, kind: TokenKind) -> bool:
        return self.peek().kind == kind

    def at_word(self, value: str) -> bool:
        return self.at(TokenKind.WORD) and self.peek().value == value

    def _error(self, message: str) -> None:
        raise ParseError(message, pos=self.peek().pos, source=self.source)

    # --- Sequence parsing ---

    def parse_sequence(self) -> "SequenceExpr":
        from src.engine.models import SequenceExpr

        steps = [self.parse_step()]
        operators = []

        while self._at_operator():
            operators.append(self.parse_operator())
            steps.append(self.parse_step())

        return SequenceExpr(steps=steps, operators=operators)

    def _at_operator(self) -> bool:
        return self.peek().kind in (TokenKind.GT, TokenKind.GT_GT, TokenKind.TILDE)

    def parse_operator(self) -> "OrderOperator":
        from src.engine.models import OperatorType, OrderOperator

        tok = self.advance()

        if tok.kind == TokenKind.GT_GT:
            return OrderOperator(type=OperatorType.ADJACENCY)

        if tok.kind == TokenKind.TILDE:
            # Slice L Decision #7: ~ accepts the same optional ``{min,max}``
            # gap as ``>``; semantics drop the ordering predicate (executor
            # uses ``abs(next - prev)`` rather than ``next - prev``).
            gap = None
            if self.at(TokenKind.LBRACE):
                gap = self.parse_gap()
            return OrderOperator(type=OperatorType.COOCCURRENCE, gap=gap)

        if tok.kind == TokenKind.GT:
            gap = None
            if self.at(TokenKind.LBRACE):
                gap = self.parse_gap()
            return OrderOperator(type=OperatorType.PRECEDENCE, gap=gap)

        self._error(f"Expected operator, got {tok.kind.value}")

    def parse_gap(self) -> "GapConstraint":
        from src.engine.models import GapConstraint

        self.expect(TokenKind.LBRACE)
        min_tok = self.expect(TokenKind.WORD)
        self.expect(TokenKind.COMMA)
        max_tok = self.expect(TokenKind.WORD)
        self.expect(TokenKind.RBRACE)
        return GapConstraint(min=int(min_tok.value), max=int(max_tok.value))

    # --- Step parsing ---

    def parse_step(self) -> "StepExpr":
        # Polarity prefix on a parenthesized alternative/group:
        # `+(concept:hope | concept:expectation)` distributes polarity to each
        # NodeRef option per docs/canonical/05_dsl-ast.md:252-271.
        if (
            self.peek().kind in (TokenKind.PLUS, TokenKind.MINUS, TokenKind.PLUSMINUS)
            and self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].kind == TokenKind.LPAREN
        ):
            polarity = self._parse_polarity()
            assert polarity is not None
            return _distribute_polarity(self.parse_group_or_alternative(), polarity)

        # Optional: [step]
        if self.at(TokenKind.LBRACKET):
            return self.parse_optional()

        # Group or alternative: (...)
        if self.at(TokenKind.LPAREN):
            return self.parse_group_or_alternative()

        # Negated node: !node
        if self.at(TokenKind.BANG):
            self.advance()
            node = self.parse_node_ref()
            from src.engine.models import NodeRef

            return NodeRef(
                type=node.type,
                value=node.value,
                polarity=node.polarity,
                morph_filters=node.morph_filters,
                negated=True,
            )

        # Node reference (possibly with polarity prefix)
        return self.parse_node_ref()

    def parse_node_ref(self) -> "NodeRef":
        from src.engine.models import MorphFilter, NodeRef

        polarity = self._parse_polarity()
        node_type, value = self._parse_typed_value()

        # Check for compound morph filter: +morph:NOUN
        morph_filters = []
        while self.at(TokenKind.PLUS) and self._lookahead_is_morph_compound():
            self.advance()  # consume +
            _, morph_value = self._parse_typed_value()
            morph_filters.append(MorphFilter(feature=morph_value))

        return NodeRef(
            type=node_type,
            value=value,
            polarity=polarity,
            morph_filters=morph_filters,
        )

    def _parse_polarity(self) -> str | None:
        if self.at(TokenKind.PLUS):
            self.advance()
            return "+"
        if self.at(TokenKind.MINUS):
            self.advance()
            return "-"
        if self.at(TokenKind.PLUSMINUS):
            self.advance()
            return "±"
        return None

    def _parse_typed_value(self) -> tuple["NodeType", str]:
        from src.engine.models import NodeType

        word_tok = self.expect(TokenKind.WORD)

        # Check for type:value pattern
        if self.at(TokenKind.COLON) and word_tok.value in _NODE_TYPE_PREFIXES:
            self.advance()  # consume :
            value_tok = self.expect(TokenKind.WORD)
            return NodeType(word_tok.value), value_tok.value

        # Wildcard
        if word_tok.value == "*":
            return NodeType.WILDCARD, "*"

        # Bare word -> concept
        return NodeType.CONCEPT, word_tok.value

    def _lookahead_is_morph_compound(self) -> bool:
        """Check if + is followed by morph: (compound syntax)."""
        if self.pos + 2 >= len(self.tokens):
            return False
        return (
            self.tokens[self.pos + 1].kind == TokenKind.WORD
            and self.tokens[self.pos + 1].value == "morph"
            and self.pos + 2 < len(self.tokens)
            and self.tokens[self.pos + 2].kind == TokenKind.COLON
        )

    def parse_optional(self) -> "OptionalExpr":
        from src.engine.models import OptionalExpr

        self.expect(TokenKind.LBRACKET)
        inner = self.parse_step()
        self.expect(TokenKind.RBRACKET)
        return OptionalExpr(inner=inner)

    def parse_group_or_alternative(self) -> "StepExpr":
        from src.engine.models import AlternativeExpr, GroupExpr

        self.expect(TokenKind.LPAREN)
        first = self.parse_step()

        # Check if this is an alternative (has |)
        if self.at(TokenKind.PIPE):
            options = [first]
            while self.at(TokenKind.PIPE):
                self.advance()
                options.append(self.parse_step())
            self.expect(TokenKind.RPAREN)
            return AlternativeExpr(options=options)

        # Otherwise it's a group containing a sequence
        # We already parsed the first step; continue parsing operators and steps
        from src.engine.models import SequenceExpr

        steps = [first]
        operators = []
        while self._at_operator():
            operators.append(self.parse_operator())
            steps.append(self.parse_step())

        self.expect(TokenKind.RPAREN)
        seq = SequenceExpr(steps=steps, operators=operators)
        return GroupExpr(sequence=seq)

    # --- Directives parsing ---

    def parse_directives(
        self,
    ) -> tuple["ScopeConstraint", "MatchMode | None", "ExpansionDirective | None"]:
        from src.engine.models import (
            ScopeConstraint,
            ScopeUnitVerse,
            ScopeUnitWindow,
        )

        corpus = None
        language = None
        books = None
        unit = None
        mode = None
        expansion = None

        while self.at(TokenKind.WORD) or self.at(TokenKind.ARROW):
            if self.at(TokenKind.ARROW):
                expansion = self._parse_expansion()
                continue

            word = self.peek().value

            if word not in _DIRECTIVE_KEYWORDS:
                break

            self.advance()  # consume keyword
            self.expect(TokenKind.COLON)

            if word == "within":
                unit_tok = self.expect(TokenKind.WORD)
                if unit_tok.value == "verse":
                    unit = ScopeUnitVerse()
                elif unit_tok.value == "window":
                    # ``within:window(N)`` per Slice L Decision #2. The parens
                    # + integer are required — ``within:window`` alone is an
                    # error so the user must declare N explicitly.
                    self.expect(TokenKind.LPAREN)
                    n_tok = self.expect(TokenKind.WORD)
                    try:
                        n_value = int(n_tok.value)
                    except ValueError:
                        self._error(
                            f"window size must be an integer, got {n_tok.value!r}"
                        )
                    if n_value <= 0:
                        # Decision #8: window(0) is degenerate (matches base
                        # token only); reject at parse time before the
                        # executor sees it.
                        self._error(
                            f"window size must be >= 1, got {n_value}"
                        )
                    self.expect(TokenKind.RPAREN)
                    unit = ScopeUnitWindow(n=n_value)
                else:
                    # ``clause | sentence | pericope | chapter`` etc. used to
                    # parse into the old StrEnum as inert kinds the executor
                    # rejected at runtime. Slice L deliberately moves the
                    # rejection up to parse time so the failure is local to
                    # the surface; future slices that ship execution will
                    # add the corresponding sibling here.
                    self._error(
                        f"unsupported scope unit: {unit_tok.value!r} "
                        "(supported: verse, window(N))"
                    )
            elif word == "lang":
                lang_tok = self.expect(TokenKind.WORD)
                language = lang_tok.value
            elif word == "corpus":
                corpus_tok = self.expect(TokenKind.WORD)
                corpus = corpus_tok.value
            elif word == "book":
                book_list = [self.expect(TokenKind.WORD).value]
                while self.at(TokenKind.COMMA):
                    self.advance()
                    book_list.append(self.expect(TokenKind.WORD).value)
                books = book_list
            elif word == "mode":
                mode_tok = self.expect(TokenKind.WORD)
                mode = mode_tok.value

        scope = ScopeConstraint(
            corpus=corpus, language=language, books=books, unit=unit
        )
        return scope, mode, expansion

    def _parse_expansion(self) -> "ExpansionDirective":
        from src.engine.models import ExpansionDirection, ExpansionDirective

        self.expect(TokenKind.ARROW)
        dir_tok = self.expect(TokenKind.WORD)
        self.expect(TokenKind.COLON)
        depth_tok = self.expect(TokenKind.WORD)

        direction_map = {
            "forward": ExpansionDirection.FORWARD,
            "backward": ExpansionDirection.BACKWARD,
            "expand": ExpansionDirection.BOTH,
            "both": ExpansionDirection.BOTH,
        }
        direction = direction_map.get(dir_tok.value)
        if direction is None:
            self._error(f"Unknown expansion direction: {dir_tok.value}")

        return ExpansionDirective(direction=direction, depth=int(depth_tok.value))

    # --- Top-level parse ---

    def parse_query(self) -> "QueryPlan":
        from src.engine.models import (
            QueryPlan,
        )

        # Check for inverse() wrapper
        if self.at_word("inverse") and self._lookahead_is_lparen():
            sequence = self._parse_inverse()
        else:
            sequence = self.parse_sequence()

        scope, mode, expansion = self.parse_directives()

        if not self.at(TokenKind.EOF):
            self._error(f"Unexpected token: {self.peek().value!r}")

        # Default mode based on node types if not explicitly specified
        if mode is None:
            mode = self._infer_mode(sequence)

        return QueryPlan(
            version="0.1",
            source=self.source,
            sequence=sequence,
            scope=scope,
            mode=mode,
            expansion=expansion,
        )

    def _parse_inverse(self) -> "InverseExpr":
        from src.engine.models import InverseExpr

        self.expect(TokenKind.WORD)  # consume "inverse"
        self.expect(TokenKind.LPAREN)
        seq = self.parse_sequence()
        self.expect(TokenKind.RPAREN)
        return InverseExpr(inner=seq)

    def _lookahead_is_lparen(self) -> bool:
        return (
            self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].kind == TokenKind.LPAREN
        )

    def _infer_mode(self, sequence: "SequenceExpr | InverseExpr") -> str:
        from src.engine.models import InverseExpr, NodeRef, NodeType

        if isinstance(sequence, InverseExpr):
            return "conceptual"

        has_concept = False
        for step in sequence.steps:
            if isinstance(step, NodeRef):
                if step.type in (NodeType.CONCEPT, NodeType.DOMAIN):
                    has_concept = True
                elif step.type in (NodeType.LEMMA, NodeType.TOKEN):
                    pass  # exact-favoring

        return "conceptual" if has_concept else "exact"


def parse(dsl: str) -> "QueryPlan":
    """Parse DSL text into a QueryPlan AST.

    Raises ParseError with position info on invalid syntax.
    """
    if not dsl.strip():
        raise ParseError("Empty query", pos=0, source=dsl)

    tokens = tokenize(dsl)
    parser = _Parser(tokens, dsl)
    return parser.parse_query()
