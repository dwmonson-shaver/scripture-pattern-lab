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
from src.validation.validator import ValidationResult


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
