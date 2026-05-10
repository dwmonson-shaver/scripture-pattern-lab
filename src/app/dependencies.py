"""FastAPI dependency providers for engine + concept registry.

The lifespan in `src/app/main.py` constructs the `Engine` and
`ConceptRegistry` once at startup and stashes them on `app.state`.
These `Depends()` providers read from app state. Tests bypass them
via `app.dependency_overrides` (no app-state mutation required).
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from sqlalchemy.engine import Engine

from src.app.schemas import ErrorResponse
from src.nlp.llm_client import LLMClient
from src.nlp.translator import TranslationContext
from src.ontology.registry import ConceptRegistry


def get_engine(request: Request) -> Engine:
    """Return the process-scoped Engine stashed on app.state.engine.

    Raises 503 if the lifespan didn't construct one (DATABASE_URL
    unset in production). Tests typically override this provider via
    `app.dependency_overrides[get_engine]`.
    """
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="engine_unavailable",
                message=(
                    "Database engine is not configured. "
                    "Set DATABASE_URL and restart the service."
                ),
            ).model_dump(),
        )
    return engine


def get_concept_registry(request: Request) -> ConceptRegistry:
    """Return the process-scoped ConceptRegistry stashed on app.state.registry.

    Raises 503 if the lifespan didn't construct one. Tests typically
    override this provider via `app.dependency_overrides`.
    """
    registry = getattr(request.app.state, "registry", None)
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="registry_unavailable",
                message=(
                    "Concept registry is not configured. "
                    "Set DATABASE_URL and restart the service."
                ),
            ).model_dump(),
        )
    return registry


def get_llm_client(request: Request) -> LLMClient:
    """Return the process-scoped LLMClient stashed on app.state.llm_client.

    Raises 503 `llm_unavailable` if the lifespan didn't construct one
    (ANTHROPIC_API_KEY unset at startup). Tests typically override this
    provider via `app.dependency_overrides[get_llm_client]`. (DEC-074.)
    """
    llm_client = getattr(request.app.state, "llm_client", None)
    if llm_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="llm_unavailable",
                message=(
                    "LLM client is not configured. "
                    "Set ANTHROPIC_API_KEY and restart the service."
                ),
            ).model_dump(),
        )
    return llm_client


def get_translation_context(request: Request) -> TranslationContext:
    """Return the process-scoped TranslationContext stashed on app.state.

    The context is built once at startup from the live capability +
    concept registries. Raises 503 if the lifespan didn't construct it
    (which happens iff the LLM client also wasn't built — they share
    the ANTHROPIC_API_KEY gate).
    """
    context = getattr(request.app.state, "translation_context", None)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="translation_context_unavailable",
                message=(
                    "Translation context is not configured. "
                    "Set ANTHROPIC_API_KEY and restart the service."
                ),
            ).model_dump(),
        )
    return context
