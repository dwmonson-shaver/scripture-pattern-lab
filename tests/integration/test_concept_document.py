"""Integration tests for the persisted Conceptual Document (Slice N, Phase N6).

Requires a live Postgres via DATABASE_URL with 02_concept_registry.sql +
04_concept_documents.sql applied. The document FK references concepts(name), so
a concept row must exist first. Gated by ``@pytest.mark.integration``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ontology.concept_document import (
    ComparativeLexiconSection,
    ConceptDocument,
    EducationalArticleSection,
    LexiconComparisonRow,
    get_document,
    persist_document,
)

pytestmark = pytest.mark.integration

_NAME = "spl_test_doc_concept"


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = get_engine()
    _cleanup(eng)
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO concepts (name, origin, verification_state) "
                "VALUES (:n, 'lexicon_imported', 'unverified') "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"n": _NAME},
        )
    yield eng
    _cleanup(eng)


def _cleanup(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM concepts WHERE name = :n"), {"n": _NAME})


def _doc(*, with_educational: bool = False) -> ConceptDocument:
    comparative = ComparativeLexiconSection(
        english_term=_NAME,
        rows=[
            LexiconComparisonRow(
                lemma="πίστις",
                strongs=["G4102"],
                usual_renderings=["faith"],
                corpus_verse_refs=["1Cor 13:13"],
            )
        ],
        generated_from=["TBESG"],
    )
    educational = (
        EducationalArticleSection(
            prose="An explainer.", cited_sources=["1Cor 13:13"], model_label="claude"
        )
        if with_educational
        else None
    )
    return ConceptDocument(
        concept_name=_NAME,
        short_summary="A short summary.",
        part1_comparative=comparative,
        part1_educational=educational,
    )


def test_persist_then_get_roundtrips(engine: Engine) -> None:
    persist_document(_doc(), engine)
    fetched = get_document(_NAME, engine)
    assert fetched is not None
    assert fetched.concept_name == _NAME
    assert fetched.part1_comparative.rows[0].lemma == "πίστις"
    assert fetched.part1_educational is None
    assert fetched.part2_grouping_placeholder is None


def test_get_returns_none_when_absent(engine: Engine) -> None:
    assert get_document(_NAME, engine) is None


def test_persist_is_store_once_idempotent(engine: Engine) -> None:
    persist_document(_doc(), engine)
    # A second persist with a DIFFERENT summary must not overwrite (store-once).
    second = _doc()
    second = second.model_copy(update={"short_summary": "DIFFERENT"})
    persist_document(second, engine)
    fetched = get_document(_NAME, engine)
    assert fetched is not None
    assert fetched.short_summary == "A short summary."  # original preserved


def test_educational_section_persists_when_present(engine: Engine) -> None:
    persist_document(_doc(with_educational=True), engine)
    fetched = get_document(_NAME, engine)
    assert fetched is not None
    assert fetched.part1_educational is not None
    assert fetched.part1_educational.generated is True
    assert fetched.part1_educational.model_label == "claude"
