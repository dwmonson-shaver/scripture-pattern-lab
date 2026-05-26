"""DSL Abstract Syntax Tree types.

Pydantic models representing the internal query representation defined in
docs/canonical/05_dsl-ast.md. These are the contract between the parser,
capability validator, and pattern engine.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    Tag,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NodeType(StrEnum):
    """Node types from the ontology (docs/canonical/04_node-ontology.md)."""

    TOKEN = "token"
    LEMMA = "lemma"
    ROOT = "root"
    CONCEPT = "concept"
    DOMAIN = "domain"
    MORPH = "morph"
    WILDCARD = "wildcard"


class OperatorType(StrEnum):
    """Order operators between sequence steps."""

    PRECEDENCE = "precedence"
    ADJACENCY = "adjacency"
    COOCCURRENCE = "cooccurrence"


class RankingFactor(StrEnum):
    """Factors for scoring and ranking matches."""

    LEXICAL_ALIGNMENT = "lexical_alignment"
    MORPHOLOGY_ALIGNMENT = "morphology_alignment"
    SEMANTIC_OVERLAP = "semantic_overlap"
    POLARITY_FIDELITY = "polarity_fidelity"
    RARITY = "rarity"
    CONTEXTUAL_COHERENCE = "contextual_coherence"


class ExpansionDirection(StrEnum):
    """Directions for expansion directives."""

    FORWARD = "forward"
    BACKWARD = "backward"
    BOTH = "both"


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Polarity = Literal["+", "-", "±"]
MatchMode = Literal["exact", "variant", "conceptual", "hybrid"]


# ---------------------------------------------------------------------------
# ScopeUnit — discriminated union (Slice L)
#
# Replaces the prior ``ScopeUnit(StrEnum)`` flat enum. Two siblings ship:
# ``ScopeUnitVerse`` (legacy single-verse boundary) and ``ScopeUnitWindow(n)``
# (cross-verse window of N tokens, addressed via ``global_position``). Adding
# ``ScopeUnitSentence`` / ``ScopeUnitClause`` etc. later is just another
# sibling with a unique ``kind`` tag.
# ---------------------------------------------------------------------------


class ScopeUnitVerse(BaseModel):
    """Single-verse scope (legacy MVP unit; default when ``unit is None``)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["verse"] = "verse"


class ScopeUnitWindow(BaseModel):
    """Cross-verse window of ``n`` tokens, anchored on the first match's
    ``global_position``. Book boundary blocked; chapter boundary crossable
    (Decision #3). ``n == 0`` is rejected at parse time (Decision #8); the
    capability validator emits ``WINDOW_EXCEEDS_MAX`` when ``n`` exceeds
    ``CapabilityRegistry.window_max_tokens`` (Decision #5).
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["window"] = "window"
    n: int


ScopeUnit = Annotated[
    Union[ScopeUnitVerse, ScopeUnitWindow],
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Leaf models
# ---------------------------------------------------------------------------


class MorphFilter(BaseModel):
    """A morphological feature filter (e.g., NOUN, VERB, IMPERATIVE)."""

    model_config = ConfigDict(frozen=True)

    feature: str


class GapConstraint(BaseModel):
    """Limits the token distance between two sequence steps."""

    model_config = ConfigDict(frozen=True)

    min: int = 0
    max: int | None = None


class OrderOperator(BaseModel):
    """Defines the relationship between adjacent steps in a sequence."""

    model_config = ConfigDict(frozen=True)

    type: OperatorType
    gap: GapConstraint | None = None


class ScopeConstraint(BaseModel):
    """Search boundaries for a query."""

    model_config = ConfigDict(frozen=True)

    corpus: str | None = None
    language: str | None = None
    books: list[str] | None = None
    unit: ScopeUnit | None = None


class ExpansionDirective(BaseModel):
    """Instructs the engine to explore beyond the stated sequence."""

    model_config = ConfigDict(frozen=True)

    direction: ExpansionDirection
    depth: int


class RankingPrefs(BaseModel):
    """User-specified ranking weight preferences."""

    model_config = ConfigDict(frozen=True)

    weights: dict[RankingFactor, float]


class QueryMetadata(BaseModel):
    """Metadata attached to a compiled query plan."""

    model_config = ConfigDict(frozen=True)

    nl_source: str | None = None
    parse_timestamp: datetime | None = None


# ---------------------------------------------------------------------------
# Step expression models (discriminated union)
# ---------------------------------------------------------------------------


class NodeRef(BaseModel):
    """A typed reference to a node in the ontology."""

    model_config = ConfigDict(frozen=True)

    expr_type: Literal["node_ref"] = "node_ref"
    type: NodeType
    value: str
    polarity: Polarity | None = None
    morph_filters: list[MorphFilter] = []
    negated: bool = False


class GroupExpr(BaseModel):
    """A parenthesized sub-sequence treated as a single step."""

    model_config = ConfigDict(frozen=True)

    expr_type: Literal["group"] = "group"
    sequence: SequenceExpr
    negated: bool = False


class AlternativeExpr(BaseModel):
    """A choice between two or more options at a single step position."""

    model_config = ConfigDict(frozen=True)

    expr_type: Literal["alternative"] = "alternative"
    options: list[StepExpr]
    negated: bool = False


class OptionalExpr(BaseModel):
    """A step that may or may not be present in a match."""

    model_config = ConfigDict(frozen=True)

    expr_type: Literal["optional"] = "optional"
    inner: StepExpr


def _get_expr_type(v: dict | BaseModel) -> str:
    if isinstance(v, dict):
        return v.get("expr_type", "")
    return getattr(v, "expr_type", "")


StepExpr = Annotated[
    Union[
        Annotated[NodeRef, Tag("node_ref")],
        Annotated[GroupExpr, Tag("group")],
        Annotated[AlternativeExpr, Tag("alternative")],
        Annotated[OptionalExpr, Tag("optional")],
    ],
    Discriminator(_get_expr_type),
]


# ---------------------------------------------------------------------------
# Composite models
# ---------------------------------------------------------------------------


class SequenceExpr(BaseModel):
    """An ordered list of steps with operators between them."""

    model_config = ConfigDict(frozen=True)

    steps: list[StepExpr]
    operators: list[OrderOperator]


class InverseExpr(BaseModel):
    """Wraps a sequence for inverse-pole resolution at execution time."""

    model_config = ConfigDict(frozen=True)

    inner: SequenceExpr


# ---------------------------------------------------------------------------
# Top-level query plan
# ---------------------------------------------------------------------------


class QueryPlan(BaseModel):
    """Top-level compiled query — the contract between parser and engine."""

    model_config = ConfigDict(frozen=True)

    version: str
    source: str
    sequence: SequenceExpr | InverseExpr
    scope: ScopeConstraint
    mode: MatchMode
    expansion: ExpansionDirective | None = None
    ranking: RankingPrefs | None = None
    metadata: QueryMetadata = QueryMetadata()


# Rebuild models that reference forward-declared types
GroupExpr.model_rebuild()
AlternativeExpr.model_rebuild()
OptionalExpr.model_rebuild()


# ---------------------------------------------------------------------------
# Pattern engine output models (executor result types)
#
# Co-located with the AST per the executor design (decision #2): keeps
# src/engine/ self-contained and avoids an extra module for three small
# frozen value objects.
# ---------------------------------------------------------------------------


class MatchedToken(BaseModel):
    """A token row projection used in executor results.

    Intentionally drops ``morph_code``, ``language``, and ``corpus_id`` from
    the underlying ``tokens`` row (decision #3 in
    ``thoughts/design-pattern-engine-executor-2026-05-09.md``). MVP does not
    need them and the extra fields invite premature feature scope.
    """

    model_config = ConfigDict(frozen=True)

    id: int
    book: str
    chapter: int
    verse: int
    position: int
    global_position: int
    surface_form: str
    normalized_form: str
    lemma: str
    pos: str


class StepMatch(BaseModel):
    """How one DSL step lined up with one matched token."""

    model_config = ConfigDict(frozen=True)

    step_index: int
    node_type: NodeType
    node_value: str
    resolved_lemmas: list[str]
    token: MatchedToken


class ProximityInfo(BaseModel):
    """Cross-verse proximity envelope attached to a ``MatchCandidate`` produced
    by a ``ScopeUnitWindow(n)`` query (Slice L Decision #4).

    Layered onto the existing ``match_type`` axis — a conceptual hit at
    ``window=50`` is ``match_type="conceptual"`` AND
    ``proximity=ProximityInfo(window_n=50, …)``. ``None`` on verse-scope
    queries.

    Carries the full window's tokens (matched + non-matched) so consumers can
    inspect the "scaffolding" — what else appeared between the matches.
    ``intervening_lemmas`` is capped at the top 20 by count (Decision #9);
    the remaining tail is summed into ``other_count``.
    """

    model_config = ConfigDict(frozen=True)

    window_n: int
    span_tokens: int
    crosses_verse: bool
    crosses_chapter: bool
    window_tokens: list[MatchedToken]
    intervening_lemmas: dict[str, int]
    other_count: int = 0


class MatchCandidate(BaseModel):
    """One verse-grouped candidate produced by ``execute()``.

    Per canonical-09 §5: ``tokens`` is the ordered list of matched tokens,
    ``reference`` is the human-readable verse pointer (``"1Cor 13:13"``),
    ``match_type`` distinguishes exact / variant / conceptual (DEC-007), and
    ``alignment`` carries the per-step provenance.

    Slice L: ``proximity`` carries a :class:`ProximityInfo` envelope when the
    candidate was produced by a ``ScopeUnitWindow(n)`` query; ``None`` for
    verse-scope candidates. The ``match_type`` axis (how it matched) and the
    ``proximity`` axis (where it landed) are orthogonal — Decision #4.
    """

    model_config = ConfigDict(frozen=True)

    tokens: list[MatchedToken]
    reference: str
    match_type: Literal["exact", "variant", "conceptual"]
    alignment: list[StepMatch]
    proximity: ProximityInfo | None = None


# ---------------------------------------------------------------------------
# Executor exceptions
#
# Co-located with the executor result types per the design (decision #12).
# ``UnsupportedPlanShape.path`` mirrors the validator's
# ``ValidationFinding.path`` so error messages can point at offending AST
# nodes; ``RegistryRequired`` carries the concept name that triggered it so
# callers can render a helpful error.
# ---------------------------------------------------------------------------


class UnsupportedPlanShape(Exception):  # noqa: N818 — name spec'd in design decision #12
    """Raised when the executor is asked to run a plan shape outside MVP.

    ``path`` mirrors ``ValidationFinding.path`` (e.g. ``"$.steps[0]"``).
    The validator is the first wall (``_reduce_plan``); the executor is the
    second wall and fails loudly rather than coerce.
    """

    def __init__(self, message: str, *, path: str = "") -> None:
        super().__init__(message)
        self.path: str = path


class RegistryRequired(Exception):  # noqa: N818 — name spec'd in design decision #12
    """Raised when a concept node appears but no concept_registry was supplied.

    ``concept_name`` is the offending concept so callers can render a
    targeted error message.
    """

    def __init__(self, concept_name: str) -> None:
        self.concept_name: str = concept_name
        super().__init__(
            f"concept registry is required to resolve concept node "
            f"{concept_name!r} but none was supplied"
        )


class ConceptNotMapped(Exception):  # noqa: N818 — name parallels RegistryRequired
    """Raised when a concept node resolves to zero lemmas in the registry.

    Distinct from :class:`RegistryRequired` (which fires when the registry
    handle itself is ``None``). ``ConceptNotMapped`` fires when the registry
    is connected but has no ``concept_lemmas`` rows for the named concept —
    i.e. the concept is unknown or not yet seeded. The CLI maps this to
    exit code 3 so users can distinguish "concept not in registry" from
    "concept in registry but no corpus matches".

    ``concept_name`` carries the offending concept for error rendering.
    """

    def __init__(self, concept_name: str) -> None:
        self.concept_name: str = concept_name
        super().__init__(
            f"concept {concept_name!r} has no lemma mapping in the registry"
        )


# ---------------------------------------------------------------------------
# Result-set contextualization (REQ:09.contextualization)
#
# Calibrates a result set against (a) constituent-node baselines, (b) sibling
# permutations of the same node-set, and (c) a null distribution (schema slot
# only in MVP). The envelope hangs on ``RetrievalResult``; the explainer slice
# will surface it on ``ExplainedResultSet`` when it lands.
# ---------------------------------------------------------------------------


class NodeBaseline(BaseModel):
    """How often a single constituent node fires alone in the scoped corpus.

    Lemma nodes resolve to themselves; concept nodes resolve to all lemmas in
    the registry mapping (per REQ:04.matching-rules). ``count`` is a scoped
    SELECT COUNT(*) against the tokens table; ``node_index`` is the 0-based
    position in the original sequence — both non-negative invariants are
    encoded in the schema (Codex D-D1D2-002).
    """

    model_config = ConfigDict(frozen=True)

    node_index: NonNegativeInt
    node_type: NodeType
    node_value: str
    resolved_lemmas: list[str]
    count: NonNegativeInt


class AlternativeOrderingCount(BaseModel):
    """Match count for one permutation of the original node sequence.

    The original ordering is included in the list with ``is_observed=True``
    so consumers can render it alongside its siblings without comparing
    permutations themselves. ``permutation`` indices and ``count`` are
    schema-enforced non-negative.
    """

    model_config = ConfigDict(frozen=True)

    permutation: list[NonNegativeInt]
    sequence_label: str
    count: NonNegativeInt
    is_observed: bool


class NullDistribution(BaseModel):
    """Sampling-based null baseline.

    MVP reserves the schema slot but never populates it (per design OQ #3
    resolution: the sampling protocol needs its own design pass — what
    counts as a "comparable-frequency" lemma, how comparability is defined,
    and how the seed propagates). Exposed as ``Contextualization.null_distribution``;
    always ``None`` until a future slice ships the sampling code. ``mean``
    is unconstrained (counts can have any non-negative mean but allowing
    floats here keeps the schema flexible for future computed statistics);
    ``sample_size`` and ``std`` are schema-enforced non-negative.
    """

    model_config = ConfigDict(frozen=True)

    sample_size: NonNegativeInt
    mean: float
    std: NonNegativeFloat
    seed: int


class Contextualization(BaseModel):
    """Calibration envelope for a single result set.

    Per canonical-09 §8: contextualization runs after retrieval, before
    scoring. It does not modify per-match scores; it calibrates the result
    set as a whole against constituent-node baselines and sibling permutations.
    """

    model_config = ConfigDict(frozen=True)

    observed_count: NonNegativeInt
    node_baselines: list[NodeBaseline]
    alternative_orderings: list[AlternativeOrderingCount]
    alternative_orderings_capped: bool
    null_distribution: NullDistribution | None = None


class RetrievalResult(BaseModel):
    """Top-level envelope returned by ``retrieve()``.

    Per canonical-09 §6. ``contextualization`` is populated only when the
    caller requested it (engine-layer default ``False``; CLI/API default
    ``True`` per OQ #1 middle-path resolution).
    """

    model_config = ConfigDict(frozen=True)

    candidates: list[MatchCandidate]
    stages_used: list[str]
    contextualization: Contextualization | None = None


# -- ExplainedResult / ExplainedResultSet -------------------------------------
#
# Per canonical-09 §9 (REQ:09.result-explainer): the user-facing prose envelope
# returned by ``src/nlp/explainer.py::explain``. The MVP explainer is
# deterministic / template-based for all match types (DEC-061 amends the
# canonical "LLM explanation for conceptual matches" sentence — LLM-backed
# prose is deferred to a named bucket). ``score`` is optional because the
# scoring layer has not shipped; populated when scoring lands.


class ExplainedResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    reference: str
    text_display: str
    match_type: Literal["exact", "variant", "conceptual"]
    score: float | None = None
    explanation: str


class ExplainedResultSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_shown: str
    nl_source: str | None = None
    validation_notes: list[str]
    results: list[ExplainedResult]
    contextualization: Contextualization | None = None
    summary: str
