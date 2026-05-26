"""HTTP request/response schemas for src/app/ routes.

These models compose existing project models (`ValidationResult`,
`RetrievalResult`, `ExplainedResultSet`) verbatim — no wrapping or
re-derivation. JSON serialization uses Pydantic v2 defaults: nullable
fields emit as `null` rather than being omitted (DEC-G8 in
thoughts/design-slice-g-fastapi-route-2026-05-09.md).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.engine.models import ExplainedResultSet, RetrievalResult
from src.ontology.registry import ConceptSummary
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


class QueryDSLRequest(BaseModel):
    """Request body for POST /api/v1/query/dsl."""

    model_config = ConfigDict(frozen=True)

    dsl: str = Field(min_length=1)


class QueryDSLResponse(BaseModel):
    """Response envelope: query echo + validation + result + explanation.

    Always emits all four fields. The CLI's `--no-prose` affordance is
    a CLI concept; service-layer consumers who want raw counts read
    `result` and ignore `explanation.summary`.
    """

    model_config = ConfigDict(frozen=True)

    query: str
    validation: ValidationResult
    result: RetrievalResult
    explanation: ExplainedResultSet


class QueryNLRequest(BaseModel):
    """Request body for POST /api/v1/query/nl."""

    model_config = ConfigDict(frozen=True)

    # 2000 chars accommodates real research questions (longest seen in practice
    # is ~200 chars) while bounding adversarial / accidentally-pasted-prose
    # inputs that would otherwise propagate to the LLM unchecked. H-CLOSE-002.
    nl_query: str = Field(min_length=1, max_length=2000)


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
