"""Concept registry HTTP surface.

`GET /api/v1/concepts` exposes the registry contents (DEC-076: flat list of
`ConceptSummary` with embedded lemma lists; not paginated at MVP scale —
Bucket 9). `GET /api/v1/concepts/{name}/document` (Slice N) returns the
persisted two-part Conceptual Document for a concept (the comparative lexicon
section + optional LLM educational section + Tier-2 placeholder), stored once
and retrieved later — never regenerated per query.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine

from src.app.dependencies import get_concept_registry, get_engine
from src.app.schemas import ConceptsResponse, ErrorResponse
from src.ontology.concept_document import ConceptDocument, get_document
from src.ontology.registry import ConceptRegistry

router = APIRouter()


@router.get("/api/v1/concepts", response_model=ConceptsResponse)
def get_concepts(
    registry: ConceptRegistry = Depends(get_concept_registry),
    language: str = "grc",
) -> ConceptsResponse:
    """Return all registered concepts with their lemma lists."""
    return ConceptsResponse(concepts=registry.list_all_concepts(language=language))


@router.get(
    "/api/v1/concepts/{name}/document",
    response_model=ConceptDocument,
)
def get_concept_document(
    name: str,
    engine: Engine = Depends(get_engine),
) -> ConceptDocument:
    """Return the persisted Conceptual Document for ``name``.

    404 if no document has been generated for the concept yet (e.g. a curated
    seed concept that was never auto-created, or an unknown name). The document
    is the deterministic comparative section plus an optional, clearly-labeled
    LLM educational section — the article persists, never regenerated per query.
    """
    document = get_document(name, engine)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="document_not_found",
                message=(
                    f"no Conceptual Document exists for concept {name!r}. "
                    "Documents are generated when a term is auto-created via a "
                    "query; seed concepts may not have one yet."
                ),
                details={"concept_name": name},
            ).model_dump(),
        )
    return document
