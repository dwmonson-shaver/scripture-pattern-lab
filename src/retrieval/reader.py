"""Chapter-read orchestration: English verses + aligned Greek tokens.

Slice 1 (DEC-148). The reader is the read surface behind the scripture-marking
workbench. It joins the English translation layer (``translation_verses``) to the
Greek corpus (``tokens``) by (corpus_id, book BB, chapter, verse) and assembles a
per-verse view: English text plus the ordered Greek tokens beneath it (for the
interlinear). This lives in ``src/retrieval`` because corpus reads are
retrieval's job — it imports the engine/ingestion table mirrors, never the app.

Greek↔English word-level alignment (BSB) is a later slice; Slice 1 surfaces the
Greek tokens of the verse as a whole (interlinear chips), not per-word mapping.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, select

from src.engine._schema import tokens_table
from src.ingestion.translations.db import (
    translation_verses_table,
    translations_table,
)
from src.ontology.book_codes import bb_to_display


class GreekToken(BaseModel):
    """One Greek corpus token surfaced under a verse for the interlinear."""

    model_config = ConfigDict(frozen=True)

    position: int
    surface_form: str
    normalized_form: str
    lemma: str
    morph_code: str
    pos: str


class ChapterVerse(BaseModel):
    """One verse of a chapter read: English text + the verse's Greek tokens."""

    model_config = ConfigDict(frozen=True)

    verse: int
    reference: str  # e.g. "Rom 8:24"
    english_text: str
    greek_tokens: list[GreekToken]


class ChapterRead(BaseModel):
    """A full chapter read for one English version."""

    model_config = ConfigDict(frozen=True)

    corpus_id: str
    book: str  # 2-digit BB code
    book_display: str  # e.g. "Rom"
    chapter: int
    version_code: str
    verses: list[ChapterVerse]


class VersionInfo(BaseModel):
    """One ingested translation, for the version switcher."""

    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    is_public_domain: bool


class ChapterNotFound(Exception):  # noqa: N818 — name parallels ConceptNotMapped
    """Raised when a chapter has no English verses for the requested version."""


def list_versions(engine: Engine | None) -> list[VersionInfo]:
    """Return all ingested translations, ordered by code.

    Returns an empty list when no engine is configured (mirrors the registry's
    ``empty()`` short-circuit so the route can degrade rather than 500).
    """
    if engine is None:
        return []
    stmt = select(
        translations_table.c.code,
        translations_table.c.name,
        translations_table.c.is_public_domain,
    ).order_by(translations_table.c.code)
    with engine.connect() as connection:
        rows = connection.execute(stmt).all()
    return [
        VersionInfo(
            code=r.code, name=r.name, is_public_domain=bool(r.is_public_domain)
        )
        for r in rows
    ]


def read_chapter(
    engine: Engine,
    *,
    corpus_id: str,
    book_bb: str,
    chapter: int,
    version_code: str,
) -> ChapterRead:
    """Assemble a chapter read: English verses + each verse's Greek tokens.

    Issues one SELECT for the English verses (joined to the version registry)
    and one SELECT for the chapter's Greek tokens, then groups tokens under
    their verse in Python. Raises ``ChapterNotFound`` when the version has no
    verses for the chapter (so the route can return an honest 404 rather than an
    empty body). ``book_bb`` is the 2-digit BB code; the caller normalizes any
    abbreviation via ``book_codes.book_abbrev_to_bb``.
    """
    english_stmt = (
        select(
            translation_verses_table.c.verse,
            translation_verses_table.c.text,
        )
        .select_from(
            translation_verses_table.join(
                translations_table,
                translations_table.c.id
                == translation_verses_table.c.translation_id,
            )
        )
        .where(
            translations_table.c.code == version_code,
            translation_verses_table.c.corpus_id == corpus_id,
            translation_verses_table.c.book == book_bb,
            translation_verses_table.c.chapter == chapter,
        )
        .order_by(translation_verses_table.c.verse)
    )
    greek_stmt = (
        select(
            tokens_table.c.verse,
            tokens_table.c.position,
            tokens_table.c.surface_form,
            tokens_table.c.normalized_form,
            tokens_table.c.lemma,
            tokens_table.c.morph_code,
            tokens_table.c.pos,
        )
        .where(
            tokens_table.c.corpus_id == corpus_id,
            tokens_table.c.book == book_bb,
            tokens_table.c.chapter == chapter,
        )
        .order_by(tokens_table.c.verse, tokens_table.c.position)
    )

    with engine.connect() as connection:
        english_rows = connection.execute(english_stmt).all()
        greek_rows = connection.execute(greek_stmt).all()

    if not english_rows:
        raise ChapterNotFound(
            f"no {version_code!r} verses for {corpus_id}/{book_bb}/{chapter}"
        )

    greek_by_verse: dict[int, list[GreekToken]] = {}
    for r in greek_rows:
        greek_by_verse.setdefault(r.verse, []).append(
            GreekToken(
                position=r.position,
                surface_form=r.surface_form,
                normalized_form=r.normalized_form,
                lemma=r.lemma,
                morph_code=r.morph_code,
                pos=r.pos,
            )
        )

    book_display = bb_to_display(book_bb)
    verses = [
        ChapterVerse(
            verse=r.verse,
            reference=f"{book_display} {chapter}:{r.verse}",
            english_text=r.text,
            greek_tokens=greek_by_verse.get(r.verse, []),
        )
        for r in english_rows
    ]
    return ChapterRead(
        corpus_id=corpus_id,
        book=book_bb,
        book_display=book_display,
        chapter=chapter,
        version_code=version_code,
        verses=verses,
    )
