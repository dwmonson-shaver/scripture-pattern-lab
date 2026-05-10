"""GET /api/v1/concepts — return the seeded concept registry.

Per canonical-09 §1, this route exposes the concept registry contents so UI
clients can render autocomplete + show which concepts are registered with
their verification states. DEC-076: flat list of `ConceptSummary` with
embedded lemma lists; not paginated at MVP scale (Bucket 9 — pagination
trigger when registry grows past ~500 rows).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.app.dependencies import get_concept_registry
from src.app.schemas import ConceptsResponse
from src.ontology.registry import ConceptRegistry

router = APIRouter()


@router.get("/api/v1/concepts", response_model=ConceptsResponse)
def get_concepts(
    registry: ConceptRegistry = Depends(get_concept_registry),
    language: str = "grc",
) -> ConceptsResponse:
    """Return all registered concepts with their lemma lists."""
    return ConceptsResponse(concepts=registry.list_all_concepts(language=language))
