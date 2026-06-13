"""HTTP request/response schemas for src/app/ routes.

These models compose existing project models (`ValidationResult`,
`RetrievalResult`, `ExplainedResultSet`) verbatim — no wrapping or
re-derivation. JSON serialization uses Pydantic v2 defaults: nullable
fields emit as `null` rather than being omitted (DEC-G8 in
thoughts/design-slice-g-fastapi-route-2026-05-09.md).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.engine.models import ExplainedResultSet, RetrievalResult
from src.ontology.concept_document import ConceptDocument
from src.ontology.registry import ConceptSummary
from src.retrieval.grouping_evidence import GroupingEvidence
from src.validation.validator import ValidationResult


class TranslationMetadata(BaseModel):
    """Translator-side metadata surfaced on the NL response envelope.

    Sibling to the DSL pipeline's existing fields. `confidence` and
    `alternatives` come from the translator (DEC-072: not used to gate
    execution; surfaced for the caller to decide). `explanation` is the
    translator's prose justification, distinct from the result-side
    `ExplainedResultSet.summary`.
    """

    model_config = ConfigDict(frozen=True)

    confidence: float
    alternatives: list[str]
    explanation: str


class ClarificationPayload(BaseModel):
    """Slice L Decision #6: the response payload when the translator emits
    a ``Clarification:`` instead of ``DSL:``.

    The route returns a 200 with this set and the other fields (``result``,
    ``validation``, ``explanation``, ``translation``) absent. No query
    executed. The frontend (follow-up scope) renders the question + the
    suggested windows as a choice surface.
    """

    model_config = ConfigDict(frozen=True)

    question: str
    suggested_windows: list[int]
    nl_source: str


class AutoCreatedConceptNote(BaseModel):
    """Short inline summary surfaced when a query auto-created a Tier-1 concept.

    Slice N (DEC-102/DEC-104): when a query references a term with no registry
    mapping, the system auto-generates a machine/lexicon-sourced, unverified
    concept and re-runs. This note tells the caller it happened, names the
    lemmas, and flags that a fuller persisted document is available — so the
    auto-creation is never silent (resolved OQ-1: not-silent output).
    """

    model_config = ConfigDict(frozen=True)

    concept_name: str
    lemmas: list[str]
    summary: str
    document_available: bool


class QueryDSLRequest(BaseModel):
    """Request body for POST /api/v1/query/dsl."""

    model_config = ConfigDict(frozen=True)

    dsl: str = Field(min_length=1)


class QueryDSLResponse(BaseModel):
    """Response envelope: query echo + validation + result + explanation.

    Always emits the four pipeline fields. `auto_created_concept` is set only
    when this query triggered a Tier-1 concept auto-creation (Slice N); None
    otherwise. The CLI's `--no-prose` affordance is a CLI concept; service-layer
    consumers who want raw counts read `result` and ignore `explanation.summary`.
    """

    model_config = ConfigDict(frozen=True)

    query: str
    validation: ValidationResult
    result: RetrievalResult
    explanation: ExplainedResultSet
    auto_created_concept: AutoCreatedConceptNote | None = None


class ConversationTurn(BaseModel):
    """One turn of a refinement conversation, echoed back by the client each
    request per the stateless-echo-back design (DEC-098)."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


_MAX_PRIOR_TURNS_CONTENT_CHARS = 16000


class QueryNLRequest(BaseModel):
    """Request body for POST /api/v1/query/nl."""

    model_config = ConfigDict(frozen=True)

    # 2000 chars accommodates real research questions (longest seen in practice
    # is ~200 chars) while bounding adversarial / accidentally-pasted-prose
    # inputs that would otherwise propagate to the LLM unchecked. H-CLOSE-002.
    nl_query: str = Field(min_length=1, max_length=2000)
    prior_turns: list[ConversationTurn] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _validate_conversation_shape(self) -> QueryNLRequest:
        """Deterministic (AI-free) validation of the refinement conversation.

        Anthropic requires the messages array to start with a user turn and
        alternate roles. ``run_nl_query`` rebuilds ``prior_turns[0]`` as the
        original user query and appends the current ``nl_query`` as the final
        user turn, so ``prior_turns`` must begin with "user", strictly
        alternate, and end with "assistant" (the latest clarification).
        Otherwise the assembled array has two consecutive same-role messages,
        Anthropic returns 400, it propagates raw, and the route returns a
        caller-triggerable 500. Catching it here makes a malformed conversation
        a clean 422 instead (M-CLOSE-001).
        """
        turns = self.prior_turns
        if not turns:
            return self
        if turns[0].role != "user":
            raise ValueError("prior_turns must begin with a 'user' turn")
        if turns[-1].role != "assistant":
            raise ValueError(
                "prior_turns must end with an 'assistant' turn (the latest "
                "clarification); the current nl_query is the next user turn"
            )
        for earlier, later in zip(turns, turns[1:]):
            if earlier.role == later.role:
                raise ValueError(
                    "prior_turns roles must alternate between 'user' and "
                    "'assistant'"
                )
        # Aggregate content cap (resource guard, M-CLOSE-002): per-turn 2000 ×
        # 20 turns is a ~40 KB worst case to the metered LLM on each stateless
        # echo-back request. Bound the sum so a single request can't balloon the
        # per-call token cost; 16000 is generous headroom for a real refinement
        # conversation (original question + many short Q&A turns).
        total_content = sum(len(turn.content) for turn in turns)
        if total_content > _MAX_PRIOR_TURNS_CONTENT_CHARS:
            raise ValueError(
                "prior_turns total content exceeds "
                f"{_MAX_PRIOR_TURNS_CONTENT_CHARS} characters"
            )
        return self


class QueryNLResponse(BaseModel):
    """Response envelope for POST /api/v1/query/nl.

    Two shapes (Slice L Decision #6):
    - Executed: ``query`` (compiled DSL) + ``validation`` + ``result`` +
      ``explanation`` + ``translation`` populated; ``clarification`` is None.
    - Clarification: ``query`` (the original NL) + ``clarification``
      populated; the four pipeline fields are None.

    The discriminating signal is presence/absence of ``clarification``.
    Always returned as HTTP 200.
    """

    model_config = ConfigDict(frozen=True)

    query: str
    validation: ValidationResult | None = None
    result: RetrievalResult | None = None
    explanation: ExplainedResultSet | None = None
    translation: TranslationMetadata | None = None
    clarification: ClarificationPayload | None = None
    auto_created_concept: AutoCreatedConceptNote | None = None


class QueryValidateRequest(BaseModel):
    """Request body for POST /api/v1/query/validate."""

    model_config = ConfigDict(frozen=True)

    dsl: str = Field(min_length=1, max_length=10000)


class QueryValidateResponse(BaseModel):
    """Response body for POST /api/v1/query/validate.

    Mirrors `QueryDSLResponse` shape (echoes the input + carries
    structured output) but omits `result` and `explanation` — the
    /validate path does not execute the engine. Per DEC-079, all
    `validation.status` values (supported/partial/unsupported) return
    HTTP 200; the only 422 path on this route is `parse_error` raised
    on malformed DSL.
    """

    model_config = ConfigDict(frozen=True)

    query: str
    validation: ValidationResult


class ConceptsResponse(BaseModel):
    """Response body for GET /api/v1/concepts.

    Contains the seeded registry's concepts with embedded lemma lists per
    DEC-076 (no pagination at MVP scale; revisit when registry grows past
    Bucket 9's trigger).
    """

    model_config = ConfigDict(frozen=True)

    concepts: list[ConceptSummary]


class ConceptDocumentResponse(ConceptDocument):
    """GET /api/v1/concepts/{name}/document body (Slice P, Scope C).

    Subclasses the ontology ``ConceptDocument`` so its fields stay at the top
    level (frontend-compatible) and adds read-only corpus evidence. The field
    lives in the app layer — NOT on the ontology model — because
    ``src.ontology`` must never import ``src.retrieval`` (architecture
    boundary, design OQ-6).

    ``grouping_evidence`` is populated only for anchor documents (those that
    carry a full Tier-2 grouping); ``None`` for member/pointer or Tier-1-only
    documents. Evidence REPORTS corpus co-occurrence; it NEVER advances a
    grouping's curator state (DEC-120).

    ``curator_state`` is the human-curated state derived from the append-only
    promotion log (DEC-124) — distinct from the grouping blob's
    ``verification_state``, which stays ``'unverified'`` forever (DEC-119).
    ``'unverified'`` when the grouping has never been promoted.
    """

    grouping_evidence: GroupingEvidence | None = None
    curator_state: str = "unverified"


class GroupingPromoteRequest(BaseModel):
    """POST .../grouping/promote body (Slice P, Scope B).

    ``to_state`` is restricted to the two real advance targets; the lifecycle's
    born state ('unverified') is not a promotion target. Promotion is
    forward-only and single-step — the writer rejects illegal transitions.
    """

    model_config = ConfigDict(frozen=True)

    to_state: Literal["corpus_observed", "human_confirmed"]
    rationale: str = Field(min_length=1)


class GroupingPromoteResponse(BaseModel):
    """Result of a successful curator promotion."""

    model_config = ConfigDict(frozen=True)

    anchor_name: str
    from_state: str
    curator_state: str
    audit_id: int | None = None


class ErrorResponse(BaseModel):
    """Error envelope returned via `HTTPException(detail=...)`.

    `error` is a stable machine-readable code (e.g., `"parse_error"`,
    `"concept_not_mapped"`). `details` carries error-type-specific
    context (parse position, concept name, plan path).
    """

    model_config = ConfigDict(frozen=True)

    error: str
    message: str
    details: dict | None = None
