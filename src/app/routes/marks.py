"""Span-annotation (mark) CRUD HTTP surface (Slice 1, DEC-129/143/145).

POST creates a mark over a (possibly cross-verse) span tied to 0..n concepts.
GET lists a chapter's marks for a version. PATCH adjusts the span and/or replaces
the concept set. DELETE removes a mark. Writes are bearer-gated by the
BearerAuthMiddleware when a token is configured.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine

from src.app.dependencies import get_engine
from src.app.schemas import (
    ErrorResponse,
    MarkCreateRequest,
    MarkOut,
    MarksResponse,
    MarkUpdateRequest,
)
from src.ontology.book_codes import book_abbrev_to_bb
from src.ontology.marks import (
    Mark,
    MarkNotFound,
    UnknownConcept,
    create_mark,
    delete_mark,
    list_marks_for_chapter,
    update_mark,
)

router = APIRouter()


def _to_out(mark: Mark) -> MarkOut:
    return MarkOut(
        id=mark.id,
        corpus_id=mark.corpus_id,
        book=mark.book,
        chapter=mark.chapter,
        verse_start=mark.verse_start,
        verse_end=mark.verse_end,
        char_start=mark.char_start,
        char_end=mark.char_end,
        version_code=mark.version_code,
        actor=mark.actor,
        concept_names=mark.concept_names,
    )


def _resolve_book(book: str) -> str:
    try:
        return book_abbrev_to_bb(book)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="book_not_found",
                message=f"unknown book abbreviation {book!r}",
                details={"book": book},
            ).model_dump(),
        ) from exc


@router.post("/api/v1/marks", response_model=MarkOut, status_code=201)
def create_mark_route(
    body: MarkCreateRequest,
    engine: Engine = Depends(get_engine),
) -> MarkOut:
    """Create a span annotation (422 unknown_concept if a name is unknown)."""
    book_bb = _resolve_book(body.book)
    try:
        mark = create_mark(
            engine,
            corpus_id=body.corpus_id,
            book=book_bb,
            chapter=body.chapter,
            verse_start=body.verse_start,
            verse_end=body.verse_end,
            char_start=body.char_start,
            char_end=body.char_end,
            version_code=body.version_code,
            concept_names=body.concept_names,
        )
    except UnknownConcept as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="unknown_concept",
                message=str(exc),
                details={"concept_names": body.concept_names},
            ).model_dump(),
        ) from exc
    return _to_out(mark)


@router.get("/api/v1/marks", response_model=MarksResponse)
def list_marks_route(
    corpus: str = "nt",
    book: str = "",
    chapter: int = 0,
    version: str = "kjv",
    engine: Engine = Depends(get_engine),
) -> MarksResponse:
    """List a chapter's marks for one version (book given as an abbreviation)."""
    book_bb = _resolve_book(book)
    marks = list_marks_for_chapter(
        engine,
        corpus_id=corpus,
        book=book_bb,
        chapter=chapter,
        version_code=version,
    )
    return MarksResponse(marks=[_to_out(m) for m in marks])


@router.patch("/api/v1/marks/{mark_id}", response_model=MarkOut)
def update_mark_route(
    mark_id: int,
    body: MarkUpdateRequest,
    engine: Engine = Depends(get_engine),
) -> MarkOut:
    """Adjust a mark's span and/or replace its concept set.

    Only fields present in the request change; ``concept_names`` (when present)
    replaces the set wholesale. 404 mark_not_found; 422 unknown_concept.
    """
    provided = body.model_dump(include=body.model_fields_set)
    try:
        mark = update_mark(engine, mark_id, **provided)
    except MarkNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="mark_not_found",
                message=str(exc),
                details={"mark_id": mark_id},
            ).model_dump(),
        ) from exc
    except UnknownConcept as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="unknown_concept",
                message=str(exc),
                details={"mark_id": mark_id},
            ).model_dump(),
        ) from exc
    return _to_out(mark)


@router.delete("/api/v1/marks/{mark_id}", status_code=204)
def delete_mark_route(
    mark_id: int,
    engine: Engine = Depends(get_engine),
) -> None:
    """Delete a mark (204 on success, 404 mark_not_found)."""
    try:
        delete_mark(engine, mark_id)
    except MarkNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="mark_not_found",
                message=str(exc),
                details={"mark_id": mark_id},
            ).model_dump(),
        ) from exc
