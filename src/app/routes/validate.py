"""POST /api/v1/query/validate — accept DSL, return ValidationResult, no execution.

Per canonical-09 §1, this route exposes the validator output without running
the engine. Useful for client-side what-if checks: "would this DSL pass
validation?" Return shape echoes the input DSL + carries the validator
verdict; no `result` or `explanation` field (those only ship via the /dsl
or /nl routes that actually execute).

DEC-079: all `validation.status` values return HTTP 200. The validator's
contract is "tell the caller everything I found"; an `unsupported` plan is
information, not an error. The only 422 path on this route is `ParseError`
on malformed DSL.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status

from src.app.dependencies import get_concept_registry
from src.app.orchestration import run_validate_only
from src.app.schemas import (
    ErrorResponse,
    QueryValidateRequest,
    QueryValidateResponse,
)
from src.engine.parser import ParseError
from src.ontology.registry import ConceptRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/v1/query/validate", response_model=QueryValidateResponse)
def post_query_validate(
    body: QueryValidateRequest,
    registry: ConceptRegistry = Depends(get_concept_registry),
) -> QueryValidateResponse:
    """Validate DSL without executing; return the verdict + findings."""
    try:
        validation = run_validate_only(body.dsl, registry)
        return QueryValidateResponse(query=body.dsl, validation=validation)

    except ParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="parse_error",
                message=str(exc),
                details={"position": exc.pos, "source": exc.source},
            ).model_dump(),
        ) from exc

    except Exception as exc:
        logger.exception("uncaught error in POST /api/v1/query/validate")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="internal_error",
                message="an unexpected error occurred",
            ).model_dump(),
        ) from exc
