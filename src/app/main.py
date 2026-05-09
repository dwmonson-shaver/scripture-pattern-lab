"""FastAPI app factory + lifespan for the Scripture Pattern Lab service.

The lifespan reads `DATABASE_URL` once at process startup, builds the
`Engine` and `ConceptRegistry`, and stashes them on `app.state`. The
route handlers obtain them via `Depends()` providers in
`src/app/dependencies.py`.

Run in production with:
    uvicorn src.app.main:app --host 0.0.0.0 --port 8000

Tests bypass the lifespan-built objects via `app.dependency_overrides`.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.app.routes import health as health_routes
from src.ingestion.db import get_engine as build_engine_from_env
from src.ontology.registry import ConceptRegistry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build process-scoped resources on startup; dispose on shutdown.

    If `DATABASE_URL` is unset, `app.state.engine` and
    `app.state.registry` are left as `None`. The dependency providers
    will then raise 503 on any request that hits them — but tests can
    install `dependency_overrides` to bypass that.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        engine = build_engine_from_env()
        app.state.engine = engine
        app.state.registry = ConceptRegistry(engine)
        logger.info("lifespan startup: engine + registry constructed")
    else:
        app.state.engine = None
        app.state.registry = None
        logger.warning(
            "lifespan startup: DATABASE_URL unset; engine + registry left as None"
        )

    try:
        yield
    finally:
        engine = getattr(app.state, "engine", None)
        if engine is not None:
            engine.dispose()
            logger.info("lifespan shutdown: engine disposed")


def create_app() -> FastAPI:
    """Build and return a FastAPI application instance.

    Tests should call this rather than importing the module-level
    `app`, so each test gets an isolated dependency-overrides
    namespace.
    """
    fastapi_app = FastAPI(
        title="Scripture Pattern Lab",
        version="0.1.0",
        description=(
            "AI-assisted original-language hypothesis exploration "
            "platform for Judeo-Christian scripture."
        ),
        lifespan=lifespan,
    )
    fastapi_app.include_router(health_routes.router)
    # Query route registered in G5.
    return fastapi_app


app = create_app()
