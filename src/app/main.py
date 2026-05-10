"""FastAPI app factory + lifespan for the Scripture Pattern Lab service.

The lifespan reads `DATABASE_URL` and `ANTHROPIC_API_KEY` once at process
startup, builds the `Engine`, `ConceptRegistry`, `LLMClient`, and
`TranslationContext`, and stashes them on `app.state`. The route
handlers obtain them via `Depends()` providers in
`src/app/dependencies.py`.

Independent-degradation contract (H-H3H4-001 clarification):
The two env vars degrade independently *on absence*. Missing DATABASE_URL
makes /api/v1/query/dsl + /api/v1/query/nl return 503; missing
ANTHROPIC_API_KEY only makes /api/v1/query/nl return 503 (the DSL
route is still serviceable). *Construction failures* (e.g.,
`build_engine_from_env()` raises because Postgres is unreachable) are
intentionally fail-fast: the lifespan startup raises, and uvicorn does
not start serving. We do not catch construction errors and continue —
that would mask deployment problems behind a runtime 503. If you want
construction-time independent degradation, that is a separate design
decision.

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

from src.app.routes import capabilities as capabilities_routes
from src.app.routes import concepts as concepts_routes
from src.app.routes import health as health_routes
from src.app.routes import nl as nl_routes
from src.app.routes import query as query_routes
from src.app.routes import validate as validate_routes
from src.ingestion.db import get_engine as build_engine_from_env
from src.nlp.llm_client import build_anthropic_client_from_env
from src.nlp.translator import TranslationContext
from src.ontology.registry import ConceptRegistry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build process-scoped resources on startup; dispose on shutdown.

    If `DATABASE_URL` is unset, `app.state.engine` and
    `app.state.registry` are left as `None`. The dependency providers
    will then raise 503 on any request that hits them — but tests can
    install `dependency_overrides` to bypass that.

    The local `engine` reference is captured outside the try/finally so
    that if any startup step after `build_engine_from_env()` raises
    (e.g., a future registry pre-warm), `engine.dispose()` still runs.
    """
    engine = None
    try:
        url = os.environ.get("DATABASE_URL")
        if url:
            engine = build_engine_from_env()
            registry = ConceptRegistry(engine)
            app.state.engine = engine
            app.state.registry = registry
            logger.info("lifespan startup: engine + registry constructed")
        else:
            app.state.engine = None
            app.state.registry = None
            logger.warning(
                "lifespan startup: DATABASE_URL unset; engine + registry left as None"
            )

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            app.state.llm_client = build_anthropic_client_from_env()
            app.state.translation_context = TranslationContext(
                capability_registry_summary=(
                    "MVP capability registry — see docs/canonical/06_capability-validator.md "
                    "for the executable subset."
                ),
                concept_registry_summary=(
                    "Concept registry seeded from data/concepts/ — see "
                    "docs/canonical/08_mvp-corpus-scope.md for verification states."
                ),
            )
            logger.info("lifespan startup: llm_client + translation_context constructed")
        else:
            app.state.llm_client = None
            app.state.translation_context = None
            logger.warning(
                "lifespan startup: ANTHROPIC_API_KEY unset; "
                "llm_client + translation_context left as None"
            )
        yield
    finally:
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
    fastapi_app.include_router(query_routes.router)
    fastapi_app.include_router(nl_routes.router)
    fastapi_app.include_router(capabilities_routes.router)
    fastapi_app.include_router(concepts_routes.router)
    fastapi_app.include_router(validate_routes.router)
    return fastapi_app


app = create_app()
