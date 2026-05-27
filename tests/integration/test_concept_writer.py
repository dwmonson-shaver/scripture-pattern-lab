"""Integration tests for the auto-create-cited-concept writer (Slice N, N4).

Requires a live Postgres via DATABASE_URL with 02_concept_registry.sql applied.
The epistemic invariants (origin='lexicon_imported', verification_state always
'unverified', never auto-promoted, idempotent, dedup) are asserted here against
real rows. Gated by ``@pytest.mark.integration``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ontology.concept_writer import (
    auto_create_cited_concept,
    concept_verification_states,
    find_existing_concept_id,
)
from src.ontology.lexicon_resolver import LexiconResolution, ResolvedLemma

pytestmark = pytest.mark.integration

_TEST_CONCEPT = "spl_test_autoconcept"


def _resolution() -> LexiconResolution:
    return LexiconResolution(
        english_term=_TEST_CONCEPT,
        resolved_lemmas=[
            ResolvedLemma(
                lemma="πίστις", strongs=["G4102"], glosses=["faith"], corpus_token_count=3
            ),
            ResolvedLemma(
                lemma="ἐλπίς", strongs=["G1680"], glosses=["hope"], corpus_token_count=2
            ),
        ],
    )


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = get_engine()
    _cleanup(eng)
    yield eng
    _cleanup(eng)


def _cleanup(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM concepts WHERE name = :n"), {"n": _TEST_CONCEPT}
        )


def test_create_writes_lexicon_imported_unverified(engine: Engine) -> None:
    outcome = auto_create_cited_concept(_resolution(), engine)
    assert outcome.created is True
    assert outcome.reused_existing is False
    assert outcome.origin == "lexicon_imported"
    assert outcome.verification_state == "unverified"
    assert set(outcome.lemmas_written) == {"πίστις", "ἐλπίς"}


def test_corpus_is_ground_truth_invariant(engine: Engine) -> None:
    auto_create_cited_concept(_resolution(), engine)
    # Mirrors the Slice C exit gate: nothing auto-promotes.
    states = concept_verification_states(_TEST_CONCEPT, engine)
    assert states == {"unverified"}


def test_origin_persisted_on_rows(engine: Engine) -> None:
    auto_create_cited_concept(_resolution(), engine)
    with engine.connect() as conn:
        concept_origin = conn.execute(
            text("SELECT origin FROM concepts WHERE name = :n"),
            {"n": _TEST_CONCEPT},
        ).scalar_one()
        lemma_origins = set(
            conn.execute(
                text(
                    "SELECT DISTINCT cl.origin FROM concept_lemmas cl "
                    "JOIN concepts c ON c.id = cl.concept_id WHERE c.name = :n"
                ),
                {"n": _TEST_CONCEPT},
            ).scalars()
        )
    assert concept_origin == "lexicon_imported"
    assert lemma_origins == {"lexicon_imported"}


def test_dedup_reuses_existing_concept(engine: Engine) -> None:
    first = auto_create_cited_concept(_resolution(), engine)
    assert first.created is True
    second = auto_create_cited_concept(_resolution(), engine)
    assert second.created is False
    assert second.reused_existing is True
    # No duplicate concept rows.
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM concepts WHERE name = :n"),
            {"n": _TEST_CONCEPT},
        ).scalar_one()
    assert n == 1


def test_find_existing_returns_none_before_create(engine: Engine) -> None:
    assert find_existing_concept_id(_TEST_CONCEPT, engine) is None
    auto_create_cited_concept(_resolution(), engine)
    assert find_existing_concept_id(_TEST_CONCEPT, engine) is not None


def test_idempotent_lemma_rows(engine: Engine) -> None:
    auto_create_cited_concept(_resolution(), engine)
    with engine.connect() as conn:
        n = conn.execute(
            text(
                "SELECT count(*) FROM concept_lemmas cl "
                "JOIN concepts c ON c.id = cl.concept_id WHERE c.name = :n"
            ),
            {"n": _TEST_CONCEPT},
        ).scalar_one()
    assert n == 2
