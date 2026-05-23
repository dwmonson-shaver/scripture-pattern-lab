"""Bearer-token authentication middleware for inter-service auth.

Slice J1 ships the FastAPI service as a Render-hosted backend accessed
only via a same-account Cloudflare Worker proxy (the `scripture-pattern-lab-web`
Nuxt app). The proxy carries a shared bearer token in
`Authorization: Bearer <token>`; this middleware enforces it.

The middleware is a no-op when `SPL_BEARER_TOKEN` is unset, preserving
local-dev ergonomics (run uvicorn, hit TestClient, no auth headers
needed). It activates only when the env var is present, which is the
case in the Render deployment.

`/api/v1/health` is exempt — Render's healthcheck pings it unauthenticated.

The 401 response uses the project-wide `ErrorResponse` envelope so the
Worker proxy can dispatch UI off `body.detail.error` the same way it
does for parse/validation/registry errors.
"""

from __future__ import annotations

import secrets

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.app.schemas import ErrorResponse

_HEALTH_PATH = "/api/v1/health"
_BEARER_SCHEME = "bearer"


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without a matching `Authorization: Bearer <token>` header.

    Activation is gated on `expected_token`:
    - `None` → middleware is a no-op (every request passes through).
    - non-`None` → every request except `GET /api/v1/health` must carry
      `Authorization: Bearer <expected_token>` (case-insensitive scheme).

    Comparison uses `secrets.compare_digest` to avoid timing oracles.
    """

    def __init__(
        self,
        app,  # noqa: ANN001 — Starlette accepts any ASGI callable here
        *,
        expected_token: str | None,
    ) -> None:
        super().__init__(app)
        self._expected_token = expected_token

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if self._expected_token is None:
            return await call_next(request)

        if request.url.path == _HEALTH_PATH:
            return await call_next(request)

        header = request.headers.get("authorization")
        if not header:
            return _unauthorized("authorization header missing")

        scheme, _, token = header.partition(" ")
        if scheme.lower() != _BEARER_SCHEME:
            return _unauthorized("authorization scheme must be Bearer")

        if not secrets.compare_digest(token, self._expected_token):
            return _unauthorized("bearer token does not match")

        return await call_next(request)


def _unauthorized(message: str) -> JSONResponse:
    """Render a 401 in the project's ErrorResponse envelope."""
    body = ErrorResponse(error="unauthorized", message=message).model_dump()
    return JSONResponse(status_code=401, content={"detail": body})
