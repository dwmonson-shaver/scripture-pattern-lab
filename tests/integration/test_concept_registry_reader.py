"""Integration tests for the ``ConceptRegistry`` reader.

Phase 4 of registry-epistemics. The reader is a read-only view over the four
registry tables (``concepts``, ``concept_lemmas``, ``polarity_claims``,
``inverse_claims``). Each test seeds a small canned set directly via
``connection.execute(insert(...))``, exercises one reader method, and cleans
up the inserted rows. The cleanup pattern mirrors
``tests/integration/test_apply_schemas.py::test_origin_and_verification_state_defaults``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ontology.registry import (
    Concept,
    ConceptRegistry,
    InverseClaim,
    PolarityClaim,
    concept_lemmas_table,
    concepts_table,
    inverse_claims_table,
    polarity_claims_table,
)

pytestmark = pytest.mark.integration


def _wipe_registry(engine: Engine) -> None:
    """Delete every registry row in FK-safe order."""
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM inverse_claims"))
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concept_lemmas"))
        connection.execute(text("DELETE FROM concepts"))


@pytest.fixture
def clean_engine() -> Iterator[Engine]:
    """Yield an engine bound to a wiped registry; wipe again on teardown."""
    engine = get_engine()
    _wipe_registry(engine)
    try:
        yield engine
    finally:
        _wipe_registry(engine)


def _insert_concept(engine: Engine, name: str, description: str | None = None) -> int:
    with engine.begin() as connection:
        return connection.execute(
            concepts_table.insert()
            .values(name=name, description=description)
            .returning(concepts_table.c.id)
        ).scalar_one()


def _insert_lemma(
    engine: Engine,
    concept_id: int,
    lemma: str,
    language: str = "grc",
) -> int:
    with engine.begin() as connection:
        return connection.execute(
            concept_lemmas_table.insert()
            .values(concept_id=concept_id, lemma=lemma, language=language)
            .returning(concept_lemmas_table.c.id)
        ).scalar_one()


def _insert_polarity_claim(
    engine: Engine,
    concept_id: int,
    polarity: str,
    verification_state: str = "unverified",
) -> int:
    with engine.begin() as connection:
        return connection.execute(
            polarity_claims_table.insert()
            .values(
                concept_id=concept_id,
                polarity=polarity,
                verification_state=verification_state,
            )
            .returning(polarity_claims_table.c.id)
        ).scalar_one()


def _insert_inverse_claim(
    engine: Engine,
    concept_id: int,
    inverse_concept_id: int,
) -> int:
    with engine.begin() as connection:
        return connection.execute(
            inverse_claims_table.insert()
            .values(
                concept_id=concept_id,
                inverse_concept_id=inverse_concept_id,
            )
            .returning(inverse_claims_table.c.id)
        ).scalar_one()


def test_get_by_lemma_returns_parent_concept(clean_engine: Engine) -> None:
    """Seeding (faith, πίστις) and looking up πίστις returns the faith concept."""
    faith_id = _insert_concept(clean_engine, "faith", "trust / faithfulness")
    _insert_lemma(clean_engine, faith_id, "πίστις", "grc")

    registry = ConceptRegistry(clean_engine)
    results = registry.get_by_lemma("πίστις")

    assert len(results) == 1
    concept = results[0]
    assert isinstance(concept, Concept)
    assert concept.name == "faith"
    assert concept.id == faith_id
    assert concept.verification_state == "unverified"
    assert concept.origin == "curated"


def test_get_by_lemma_unknown_returns_empty(clean_engine: Engine) -> None:
    """Lookup of a lemma not in the registry returns an empty list."""
    registry = ConceptRegistry(clean_engine)
    assert registry.get_by_lemma("nonexistent") == []


def test_get_by_lemma_language_filter(clean_engine: Engine) -> None:
    """Two language variants of the same surface lemma are filtered by language."""
    grc_concept_id = _insert_concept(clean_engine, "grc_concept")
    hbo_concept_id = _insert_concept(clean_engine, "hbo_concept")
    _insert_lemma(clean_engine, grc_concept_id, "shared", "grc")
    _insert_lemma(clean_engine, hbo_concept_id, "shared", "hbo")

    registry = ConceptRegistry(clean_engine)

    grc_results = registry.get_by_lemma("shared", "grc")
    hbo_results = registry.get_by_lemma("shared", "hbo")

    assert [c.name for c in grc_results] == ["grc_concept"]
    assert [c.name for c in hbo_results] == ["hbo_concept"]


def test_get_polarity_claims_returns_claims(clean_engine: Engine) -> None:
    """A seeded polarity claim is returned in PolarityClaim shape."""
    faith_id = _insert_concept(clean_engine, "faith")
    claim_id = _insert_polarity_claim(clean_engine, faith_id, "+")

    registry = ConceptRegistry(clean_engine)
    claims = registry.get_polarity_claims(faith_id)

    assert len(claims) == 1
    claim = claims[0]
    assert isinstance(claim, PolarityClaim)
    assert claim.id == claim_id
    assert claim.concept_id == faith_id
    assert claim.polarity == "+"
    assert claim.verification_state == "unverified"
    assert claim.evidence_count == 0


def test_get_inverse_claims_returns_claims(clean_engine: Engine) -> None:
    """A seeded faith ↔ unbelief inverse pair returns one row."""
    faith_id = _insert_concept(clean_engine, "faith")
    unbelief_id = _insert_concept(clean_engine, "unbelief")
    claim_id = _insert_inverse_claim(clean_engine, faith_id, unbelief_id)

    registry = ConceptRegistry(clean_engine)
    claims = registry.get_inverse_claims(faith_id)

    assert len(claims) == 1
    claim = claims[0]
    assert isinstance(claim, InverseClaim)
    assert claim.id == claim_id
    assert claim.concept_id == faith_id
    assert claim.inverse_concept_id == unbelief_id


def test_is_prior_grounded_unverified_true(clean_engine: Engine) -> None:
    """An unverified polarity claim flags the concept as prior-grounded."""
    faith_id = _insert_concept(clean_engine, "faith")
    _insert_polarity_claim(clean_engine, faith_id, "+", verification_state="unverified")

    registry = ConceptRegistry(clean_engine)
    assert registry.is_prior_grounded("faith", "+") is True


def test_is_prior_grounded_corpus_observed_false(clean_engine: Engine) -> None:
    """A corpus_observed claim is NOT prior-grounded — it's evidence-grounded."""
    faith_id = _insert_concept(clean_engine, "faith")
    _insert_polarity_claim(
        clean_engine, faith_id, "+", verification_state="corpus_observed"
    )

    registry = ConceptRegistry(clean_engine)
    assert registry.is_prior_grounded("faith", "+") is False


def test_is_prior_grounded_unknown_concept_false(clean_engine: Engine) -> None:
    """A concept absent from the registry returns False — no claim, nothing to flag."""
    registry = ConceptRegistry(clean_engine)
    assert registry.is_prior_grounded("nonexistent", "+") is False


def test_is_prior_grounded_polarity_none_inspects_any(clean_engine: Engine) -> None:
    """polarity=None checks ALL polarity_claims for the concept."""
    faith_id = _insert_concept(clean_engine, "faith")
    _insert_polarity_claim(
        clean_engine, faith_id, "+", verification_state="unverified"
    )

    registry = ConceptRegistry(clean_engine)
    assert registry.is_prior_grounded("faith", None) is True


def test_empty_registry_returns_empty() -> None:
    """ConceptRegistry.empty() short-circuits every read without touching a DB."""
    registry = ConceptRegistry.empty()
    assert registry.get_by_lemma("anything") == []
    assert registry.get_polarity_claims(1) == []
    assert registry.get_inverse_claims(1) == []
    assert registry.is_prior_grounded("x", "+") is False
    assert registry.is_prior_grounded("x", None) is False
