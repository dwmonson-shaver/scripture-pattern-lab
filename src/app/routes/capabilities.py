"""GET /api/v1/capabilities — return the current MVP capability registry.

Per canonical-09 §1, this route exposes the engine's declarative capability
manifest so UI clients can render "what does the DSL currently support" without
making test queries. No DI: the MVP registry is a static, in-process Pydantic
model (`CapabilityRegistry.mvp()`).

DEC-075: response_model is `CapabilityRegistry` directly — no envelope wrapping.
The model is already a frozen Pydantic v2 with JSON-native fields; UI clients
can branch on the `version` field for forward compatibility.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.validation.registry import CapabilityRegistry

router = APIRouter()


@router.get("/api/v1/capabilities", response_model=CapabilityRegistry)
def get_capabilities() -> CapabilityRegistry:
    """Return the MVP capability registry."""
    return CapabilityRegistry.mvp()
