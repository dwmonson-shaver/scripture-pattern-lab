"""POST /api/v1/query/dsl — accept raw DSL, run the pipeline, return JSON.

Per canonical-09 §1, this route accepts raw DSL (skipping the NL→DSL
translation step). It threads the request through `run_dsl_query()` and
maps each pipeline exception to an HTTP status per the slice's design
mapping table (DEC-G6, DEC-G7).

Status code mapping:
  - 200 — supported or partial (warnings carried in `validation.findings`)
  - 422 — ParseError, validator status='unsupported', UnsupportedPlanShape,
          ConceptNotMapped (all client-fixable)
  - 503 — RegistryRequired (server-side state issue)
  - 500 — uncaught (logs traceback server-side, returns generic message)
"""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine

from src.app.dependencies import get_concept_registry, get_engine
from src.app.orchestration import ValidationUnsupported, run_dsl_query
from src.app.schemas import ErrorResponse, QueryDSLRequest, QueryDSLResponse
from src.engine.models import (
    ConceptNotMapped,
    RegistryRequired,
    UnsupportedPlanShape,
)
from src.engine.parser import ParseError
from src.ontology.registry import ConceptRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/v1/query/dsl", response_model=QueryDSLResponse)
def post_query_dsl(
    body: QueryDSLRequest,
    engine: Engine = Depends(get_engine),
    registry: ConceptRegistry = Depends(get_concept_registry),
) -> QueryDSLResponse:
    """Accept raw DSL; return validation + result + explanation as JSON."""
    try:
        return run_dsl_query(body.dsl, engine, registry)

    except ParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="parse_error",
                message=str(exc),
                details={"position": exc.pos, "source": exc.source},
            ).model_dump(),
        ) from exc

    except ValidationUnsupported as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="validation_unsupported",
                message=str(exc),
                details={
                    "findings": [
                        f.model_dump() for f in exc.validation.findings
                    ],
                },
            ).model_dump(),
        ) from exc

    except UnsupportedPlanShape as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="unsupported_plan_shape",
                message=str(exc),
                details={"path": exc.path},
            ).model_dump(),
        ) from exc

    except ConceptNotMapped as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="concept_not_mapped",
                message=(
                    f"concept {exc.concept_name!r} is not present in the "
                    "concept registry (no lemma rows). Add it to the "
                    "registry or correct the query."
                ),
                details={"concept_name": exc.concept_name},
            ).model_dump(),
        ) from exc

    except RegistryRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="registry_required",
                message=(
                    f"registry not seeded: concept {exc.concept_name!r} "
                    "has no lemma mapping. Seed the concept registry "
                    "before retrying."
                ),
                details={"concept_name": exc.concept_name},
            ).model_dump(),
        ) from exc

    except Exception as exc:
        # Log full traceback server-side; return generic message.
        logger.exception("uncaught error in POST /api/v1/query/dsl")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="internal_error",
                message="an unexpected error occurred",
            ).model_dump(),
        ) from exc
