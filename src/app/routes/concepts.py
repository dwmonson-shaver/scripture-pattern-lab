"""Concept registry HTTP surface.

`GET /api/v1/concepts` exposes the registry contents (DEC-076: flat list of
`ConceptSummary` with embedded lemma lists; not paginated at MVP scale —
Bucket 9). `GET /api/v1/concepts/{name}/document` (Slice N) returns the
persisted two-part Conceptual Document for a concept: the comparative lexicon
section + optional LLM educational section + optional Tier-2 grouping (Slice O
— either a full grouping on an anchor concept or a pointer on a member),
stored once and retrieved later — never regenerated per query.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine

from src.app.dependencies import get_concept_registry, get_engine
from src.app.schemas import (
    ConceptDocumentResponse,
    ConceptsResponse,
    ErrorResponse,
    GroupingPromoteRequest,
    GroupingPromoteResponse,
)
from src.ontology.concept_document import get_document
from src.ontology.concept_grouping import (
    current_curator_state,
    promote_grouping,
    read_grouping_for_anchor,
)
from src.ontology.registry import ConceptRegistry
from src.retrieval.grouping_evidence import compute_grouping_evidence

router = APIRouter()

# Coarse actor identity for the audit log. Auth is a single shared bearer token
# (BearerAuthMiddleware), so the API cannot identify WHICH human curator acted;
# finer per-curator identity is a tracked follow-up (design Risks section).
_CURATOR_ACTOR = "curator"


@router.get("/api/v1/concepts", response_model=ConceptsResponse)
def get_concepts(
    registry: ConceptRegistry = Depends(get_concept_registry),
    language: str = "grc",
) -> ConceptsResponse:
    """Return all registered concepts with their lemma lists."""
    return ConceptsResponse(concepts=registry.list_all_concepts(language=language))


@router.get(
    "/api/v1/concepts/{name}/document",
    response_model=ConceptDocumentResponse,
)
def get_concept_document(
    name: str,
    engine: Engine = Depends(get_engine),
) -> ConceptDocumentResponse:
    """Return the persisted Conceptual Document for ``name``.

    404 if no document has been generated for the concept yet (e.g. a curated
    seed concept that was never auto-created, or an unknown name). The document
    is the deterministic comparative section plus an optional, clearly-labeled
    LLM educational section — the article persists, never regenerated per query.

    Slice P: for anchor documents (those carrying a full Tier-2 grouping), the
    response also includes read-only ``grouping_evidence`` — deterministic
    corpus co-occurrence measured per member pair. Evidence informs a human
    curator; it never advances the grouping's state (DEC-120).
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
    evidence = None
    if document.part2_grouping is not None:
        evidence = compute_grouping_evidence(document.part2_grouping, engine)
    return ConceptDocumentResponse(
        **document.model_dump(),
        grouping_evidence=evidence,
        curator_state=current_curator_state(name, engine),
    )


@router.post(
    "/api/v1/concepts/{name}/grouping/promote",
    response_model=GroupingPromoteResponse,
)
def promote_concept_grouping(
    name: str,
    body: GroupingPromoteRequest,
    engine: Engine = Depends(get_engine),
) -> GroupingPromoteResponse:
    """Advance a grouping's curator state (Slice P, Scope B).

    The ONLY sanctioned path past DEC-081's auto-promotion ban: a human curator
    (authenticated by the shared bearer token) reviews the corpus evidence and
    advances ``unverified -> corpus_observed -> human_confirmed`` one step at a
    time. The app layer computes the evidence (retrieval) and hands it to the
    ontology promotion writer — ``src.ontology`` never imports ``src.retrieval``.

    404 if no grouping is anchored on ``name``; 409 if the requested transition
    is not a legal single-step forward advance from the current state.
    """
    grouping = read_grouping_for_anchor(name, engine)
    if grouping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="grouping_not_found",
                message=(
                    f"no Tier-2 grouping is anchored on concept {name!r}; only "
                    "an anchor concept's grouping can be promoted."
                ),
                details={"concept_name": name},
            ).model_dump(),
        )
    # Evidence the curator's decision is grounded in (read-only; never promotes).
    evidence = compute_grouping_evidence(grouping, engine)
    try:
        record = promote_grouping(
            name,
            to_state=body.to_state,
            actor=_CURATOR_ACTOR,
            rationale=body.rationale,
            evidence_snapshot=evidence.model_dump(mode="json"),
            engine=engine,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorResponse(
                error="illegal_promotion",
                message=str(exc),
                details={"concept_name": name, "to_state": body.to_state},
            ).model_dump(),
        ) from exc
    return GroupingPromoteResponse(
        anchor_name=name,
        from_state=record.from_state,
        curator_state=record.to_state,
        audit_id=record.id,
    )
