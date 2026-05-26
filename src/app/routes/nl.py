"""POST /api/v1/query/nl — accept natural-language, compile to DSL, run pipeline.

Per canonical-09 §2 + §1 request-lifecycle, this route is the second
consumer of `run_dsl_query()`. It composes the LLM-backed translator
(REQ:09.nl-to-dsl) with the existing DSL pipeline.

Status code mapping (extends canonical-09 §1's table):
  - 200 — supported or partial; QueryNLResponse with translation.dsl set
          to the compiled DSL string and translation metadata populated
  - 422 — translator-side compile failure (NLCompileError) OR any of the
          DSL-pipeline 422 codes (parse_error, validation_unsupported,
          unsupported_plan_shape, concept_not_mapped) firing on the
          translator's compiled DSL
  - 503 — LLMUnavailable (LLM API outage / auth / rate-limit / 5xx) or
          RegistryRequired (server-side state issue)
  - 500 — any uncaught exception, including 4xx anthropic.* errors
          (BadRequestError etc. — translator-side request bug per
          DEC-070, H-H1H2-001)
"""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine

from src.app.dependencies import (
    get_concept_registry,
    get_engine,
    get_llm_client,
    get_translation_context,
)
from src.app.orchestration import ValidationUnsupported, run_nl_query
from src.app.schemas import ErrorResponse, QueryNLRequest, QueryNLResponse
from src.engine.models import (
    ConceptNotMapped,
    RegistryRequired,
    UnsupportedPlanShape,
)
from src.engine.parser import ParseError
from src.nlp.llm_client import LLMClient, LLMUnavailable
from src.nlp.translator import NLCompileError, TranslationContext
from src.ontology.registry import ConceptRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/v1/query/nl", response_model=QueryNLResponse)
def post_query_nl(
    body: QueryNLRequest,
    engine: Engine = Depends(get_engine),
    registry: ConceptRegistry = Depends(get_concept_registry),
    llm_client: LLMClient = Depends(get_llm_client),
    context: TranslationContext = Depends(get_translation_context),
) -> QueryNLResponse:
    """Accept NL query; compile to DSL via LLM; run pipeline; return JSON."""
    try:
        return run_nl_query(
            nl_query=body.nl_query,
            engine=engine,
            registry=registry,
            llm_client=llm_client,
            context=context,
            prior_turns=body.prior_turns,
        )

    except LLMUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="llm_unavailable",
                message=(
                    "LLM API call failed (network, auth, rate-limit, or 5xx). "
                    "Retry shortly; if the issue persists, contact an operator."
                ),
                details={"reason": exc.reason},
            ).model_dump(),
        ) from exc

    except NLCompileError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="nl_compile_error",
                message=(
                    "the LLM did not emit DSL in the expected format. "
                    "Try rewording the query."
                ),
                details={
                    "nl_query": exc.nl_query,
                    "attempted_output": exc.attempted_output,
                    "reason": exc.reason,
                },
            ).model_dump(),
        ) from exc

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
        # Includes 4xx anthropic.* errors that propagate raw (DEC-070).
        logger.exception("uncaught error in POST /api/v1/query/nl")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="internal_error",
                message="an unexpected error occurred",
            ).model_dump(),
        ) from exc
