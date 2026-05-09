"""GET /api/v1/health — process liveness check.

Returns {"status": "ok"} unconditionally. Per DEC-G10, this is
liveness only — it does not ping the database or check that the
registry is seeded. Deeper health checks (DB connectivity,
registry-non-empty) are deferred to a follow-up endpoint slice.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/health")
def health() -> dict[str, str]:
    """Return process-liveness status."""
    return {"status": "ok"}
