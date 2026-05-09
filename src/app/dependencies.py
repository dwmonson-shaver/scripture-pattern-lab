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
