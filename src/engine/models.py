"""DSL Abstract Syntax Tree types.

Pydantic models representing the internal query representation defined in
docs/canonical/05_dsl-ast.md. These are the contract between the parser,
capability validator, and pattern engine.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Tag

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


class ScopeUnit(StrEnum):
    """Structural units for scope constraints."""

    TOKEN = "token"
    CLAUSE = "clause"
    VERSE = "verse"
    SENTENCE = "sentence"
    PERICOPE = "pericope"
    CHAPTER = "chapter"


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
