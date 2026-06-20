"""Chapter-read HTTP surface (Slice 1, DEC-128/148).

`GET /api/v1/read/versions` lists ingested translations (the version switcher).
`GET /api/v1/read/{corpus}/{book}/{chapter}?version=kjv` returns a chapter's
English verses with the aligned Greek tokens beneath each (the interlinear).
``book`` accepts a DSL-style abbreviation (e.g. ``rom``, ``1cor``) which is
normalized to the stored BB code via ``book_codes``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine

from src.app.dependencies import get_engine
from src.app.schemas import (
    ChapterReadResponse,
    ErrorResponse,
    VersionInfoOut,
    VersionsResponse,
)
from src.ontology.book_codes import book_abbrev_to_bb
from src.retrieval.reader import ChapterNotFound, list_versions, read_chapter

router = APIRouter()


@router.get("/api/v1/read/versions", response_model=VersionsResponse)
def get_versions(engine: Engine = Depends(get_engine)) -> VersionsResponse:
    """Return all ingested translations for the version switcher."""
    versions = list_versions(engine)
    return VersionsResponse(
        versions=[
            VersionInfoOut(
                code=v.code, name=v.name, is_public_domain=v.is_public_domain
            )
            for v in versions
        ]
    )


@router.get(
    "/api/v1/read/{corpus}/{book}/{chapter}",
    response_model=ChapterReadResponse,
)
def get_chapter(
    corpus: str,
    book: str,
    chapter: int,
    version: str = "kjv",
    engine: Engine = Depends(get_engine),
) -> ChapterReadResponse:
    """Return a chapter's English verses + aligned Greek tokens.

    404 ``book_not_found`` if the book abbreviation is unknown; 404
    ``chapter_empty`` if the version has no verses for the chapter.
    """
    try:
        book_bb = book_abbrev_to_bb(book)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="book_not_found",
                message=f"unknown book abbreviation {book!r}",
                details={"book": book},
            ).model_dump(),
        ) from exc

    try:
        chapter_read = read_chapter(
            engine,
            corpus_id=corpus,
            book_bb=book_bb,
            chapter=chapter,
            version_code=version,
        )
    except ChapterNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="chapter_empty",
                message=str(exc),
                details={
                    "corpus": corpus,
                    "book": book,
                    "chapter": chapter,
                    "version": version,
                },
            ).model_dump(),
        ) from exc

    return ChapterReadResponse(**chapter_read.model_dump())
