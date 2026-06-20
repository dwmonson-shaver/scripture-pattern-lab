"""Tests for src/ontology/registry.py — Pydantic models + Table mirrors.

Pure unit tests: no DB, no SQL execution. Exercises construction defaults,
frozen-instance discipline, JSON round-trip, Literal validation, and asserts
that the SQLAlchemy ``MetaData`` exposes the four tables with the expected
column names. The corresponding integration coverage (DDL apply, FK / UNIQUE
/ CHECK constraints) lives in tests/integration/test_apply_schemas.py.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.ontology.registry import (
    Concept,
    ConceptLemma,
    InverseClaim,
    PolarityClaim,
    concept_lemmas_table,
    concepts_table,
    inverse_claims_table,
    metadata,
    polarity_claims_table,
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TestConcept:
    def test_construct_minimal(self) -> None:
        c = Concept(id=1, name="faith")
        assert c.id == 1
        assert c.name == "faith"
        assert c.description is None
        assert c.origin == "curated"
        assert c.verification_state == "unverified"

    def test_construct_full(self) -> None:
        c = Concept(
            id=7,
            name="faith",
            description="trust grounded in evidence",
            origin="ai_suggested",
            verification_state="corpus_observed",
        )
        assert c.description == "trust grounded in evidence"
        assert c.origin == "ai_suggested"
        assert c.verification_state == "corpus_observed"

    def test_frozen(self) -> None:
        c = Concept(id=1, name="faith")
        with pytest.raises(ValidationError):
            c.name = "hope"

    def test_json_round_trip(self) -> None:
        c = Concept(
            id=3,
            name="faith",
            description="trust",
            origin="curated",
            verification_state="human_confirmed",
        )
        restored = Concept.model_validate_json(c.model_dump_json())
        assert restored == c

    def test_origin_literal_rejects_bogus(self) -> None:
        with pytest.raises(ValidationError):
            Concept(id=1, name="faith", origin="bogus")  # type: ignore[arg-type]

    def test_verification_state_literal_rejects_bogus(self) -> None:
        with pytest.raises(ValidationError):
            Concept(id=1, name="faith", verification_state="maybe")  # type: ignore[arg-type]


class TestConceptLemma:
    def test_construct_minimal(self) -> None:
        cl = ConceptLemma(id=1, concept_id=42, lemma="πίστις")
        assert cl.lemma == "πίστις"
        assert cl.language == "grc"
        assert cl.confidence is None
        assert cl.origin == "curated"
        assert cl.verification_state == "unverified"

    def test_confidence_optional_none_default(self) -> None:
        cl = ConceptLemma(id=1, concept_id=1, lemma="x")
        assert cl.confidence is None

    def test_confidence_explicit_none_accepted(self) -> None:
        cl = ConceptLemma(id=1, concept_id=1, lemma="x", confidence=None)
        assert cl.confidence is None

    def test_confidence_float_accepted(self) -> None:
        cl = ConceptLemma(id=1, concept_id=1, lemma="x", confidence=0.5)
        assert cl.confidence == 0.5

    def test_frozen(self) -> None:
        cl = ConceptLemma(id=1, concept_id=1, lemma="x")
        with pytest.raises(ValidationError):
            cl.lemma = "y"

    def test_json_round_trip(self) -> None:
        cl = ConceptLemma(
            id=9,
            concept_id=42,
            lemma="πίστις",
            language="grc",
            confidence=0.75,
            origin="lexicon_imported",
            verification_state="corpus_observed",
        )
        restored = ConceptLemma.model_validate_json(cl.model_dump_json())
        assert restored == cl


class TestPolarityClaim:
    def test_construct_minimal(self) -> None:
        pc = PolarityClaim(id=1, concept_id=1, polarity="+")
        assert pc.polarity == "+"
        assert pc.origin == "curated"
        assert pc.evidence_count == 0
        assert pc.verification_state == "unverified"
        assert pc.confidence is None

    def test_polarity_plus_accepted(self) -> None:
        pc = PolarityClaim(id=1, concept_id=1, polarity="+")
        assert pc.polarity == "+"

    def test_polarity_minus_accepted(self) -> None:
        pc = PolarityClaim(id=1, concept_id=1, polarity="-")
        assert pc.polarity == "-"

    def test_polarity_plusminus_accepted(self) -> None:
        pc = PolarityClaim(id=1, concept_id=1, polarity="±")
        assert pc.polarity == "±"

    def test_polarity_neutral_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PolarityClaim(id=1, concept_id=1, polarity="neutral")  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        pc = PolarityClaim(id=1, concept_id=1, polarity="+")
        with pytest.raises(ValidationError):
            pc.polarity = "-"

    def test_json_round_trip(self) -> None:
        pc = PolarityClaim(
            id=4,
            concept_id=42,
            polarity="±",
            origin="ai_suggested",
            evidence_count=12,
            verification_state="corpus_observed",
            confidence=0.6,
        )
        restored = PolarityClaim.model_validate_json(pc.model_dump_json())
        assert restored == pc


class TestInverseClaim:
    def test_construct_minimal(self) -> None:
        ic = InverseClaim(id=1, concept_id=1, inverse_concept_id=2)
        assert ic.concept_id == 1
        assert ic.inverse_concept_id == 2
        assert ic.origin == "curated"
        assert ic.evidence_count == 0
        assert ic.verification_state == "unverified"
        assert ic.confidence is None

    def test_frozen(self) -> None:
        ic = InverseClaim(id=1, concept_id=1, inverse_concept_id=2)
        with pytest.raises(ValidationError):
            ic.inverse_concept_id = 3

    def test_json_round_trip(self) -> None:
        ic = InverseClaim(
            id=5,
            concept_id=1,
            inverse_concept_id=2,
            origin="curated",
            evidence_count=3,
            verification_state="human_confirmed",
            confidence=0.9,
        )
        restored = InverseClaim.model_validate_json(ic.model_dump_json())
        assert restored == ic


# ---------------------------------------------------------------------------
# SQLAlchemy Core table mirrors
# ---------------------------------------------------------------------------


# Mirrors tests/integration/test_apply_schemas.py::EXPECTED_REGISTRY_TABLES so
# the Python schema mirror and the canonical SQL stay column-aligned.
EXPECTED_REGISTRY_TABLES: dict[str, set[str]] = {
    "concepts": {
        "id",
        "name",
        "description",
        "origin",
        "verification_state",
        # Slice 1 authored display metadata (DEC-146).
        "authored_color",
        "authored_polarity",
        "authored_opposite_name",
    },
    "concept_lemmas": {
        "id",
        "concept_id",
        "lemma",
        "language",
        "confidence",
        "origin",
        "verification_state",
    },
    "polarity_claims": {
        "id",
        "concept_id",
        "polarity",
        "origin",
        "evidence_count",
        "verification_state",
        "confidence",
    },
    "inverse_claims": {
        "id",
        "concept_id",
        "inverse_concept_id",
        "origin",
        "evidence_count",
        "verification_state",
        "confidence",
    },
}


class TestTableMirrors:
    def test_metadata_contains_exactly_four_tables(self) -> None:
        assert set(metadata.tables.keys()) == set(EXPECTED_REGISTRY_TABLES.keys())

    def test_concepts_columns(self) -> None:
        assert (
            set(concepts_table.columns.keys())
            == EXPECTED_REGISTRY_TABLES["concepts"]
        )

    def test_concept_lemmas_columns(self) -> None:
        assert (
            set(concept_lemmas_table.columns.keys())
            == EXPECTED_REGISTRY_TABLES["concept_lemmas"]
        )

    def test_polarity_claims_columns(self) -> None:
        assert (
            set(polarity_claims_table.columns.keys())
            == EXPECTED_REGISTRY_TABLES["polarity_claims"]
        )

    def test_inverse_claims_columns(self) -> None:
        assert (
            set(inverse_claims_table.columns.keys())
            == EXPECTED_REGISTRY_TABLES["inverse_claims"]
        )


# -- ConceptSummary + list_all_concepts (Slice I) ----------------------


class TestConceptSummary:
    def test_construct_minimal(self) -> None:
        from src.ontology.registry import ConceptSummary
        s = ConceptSummary(name="faith")
        assert s.name == "faith"
        assert s.lemma_count == 0
        assert s.lemmas == []
        assert s.verification_state == "unverified"

    def test_construct_full(self) -> None:
        from src.ontology.registry import ConceptSummary
        s = ConceptSummary(
            name="love",
            description="agape",
            verification_state="corpus_observed",
            lemma_count=2,
            lemmas=["ἀγάπη", "ἀγαπάω"],
        )
        assert s.lemma_count == 2
        assert s.lemmas == ["ἀγάπη", "ἀγαπάω"]

    def test_frozen(self) -> None:
        from pydantic import ValidationError

        from src.ontology.registry import ConceptSummary
        s = ConceptSummary(name="faith")
        with pytest.raises(ValidationError):
            s.name = "hope"

    def test_invalid_verification_state_rejected(self) -> None:
        from pydantic import ValidationError

        from src.ontology.registry import ConceptSummary
        with pytest.raises(ValidationError):
            ConceptSummary(name="faith", verification_state="invalid")  # type: ignore[arg-type]


class TestListAllConceptsEmptyRegistry:
    def test_empty_returns_empty_list(self) -> None:
        from src.ontology.registry import ConceptRegistry
        assert ConceptRegistry.empty().list_all_concepts() == []


def _mock_engine_returning(rows: list) -> object:  # noqa: ANN401
    """Chain-mock SQLAlchemy engine.connect().execute().all() → rows.

    Mirrors the pattern in tests/unit/test_contextualization.py.
    """
    from unittest.mock import MagicMock

    engine = MagicMock()
    connection = MagicMock()
    connection_cm = MagicMock()
    connection_cm.__enter__.return_value = connection
    connection_cm.__exit__.return_value = False
    engine.connect.return_value = connection_cm

    result = MagicMock()
    result.all.return_value = rows
    connection.execute.return_value = result
    return engine


def _row(name: str, description: str | None, vstate: str, lemma: str | None,
         language: str | None) -> object:  # noqa: ANN401
    """Mock a SQLAlchemy Row whose .name / .description / etc. match the SELECT."""
    from unittest.mock import MagicMock
    r = MagicMock()
    r.name = name
    r.description = description
    r.verification_state = vstate
    r.lemma = lemma
    r.language = language
    # Slice 1 authored columns (DEC-146) — None unless a test sets them.
    r.authored_color = None
    r.authored_polarity = None
    r.authored_opposite_name = None
    return r


class TestListAllConceptsSqlPath:
    """Table-backed unit tests for list_all_concepts using MagicMock chaining
    (no live DB). I-MID-001 closure: cover the SQL path that the empty-registry
    test alone could not exercise.
    """

    def test_concept_with_no_lemma_rows_appears_with_empty_lemmas(self) -> None:
        from src.ontology.registry import ConceptRegistry
        # Single concept, no JOINed lemma row: LEFT JOIN emits a row with
        # NULL lemma + NULL language.
        rows = [
            _row("solitude", "no lemmas yet", "unverified", None, None),
        ]
        registry = ConceptRegistry(engine=_mock_engine_returning(rows))
        result = registry.list_all_concepts()
        assert len(result) == 1
        assert result[0].name == "solitude"
        assert result[0].lemmas == []
        assert result[0].lemma_count == 0
        assert result[0].verification_state == "unverified"

    def test_multilanguage_lemmas_filtered_by_language(self) -> None:
        from src.ontology.registry import ConceptRegistry
        # Same concept in two languages; default language=grc filter must
        # drop the heb lemma without dropping the concept.
        rows = [
            _row("faith", "trust", "unverified", "πίστις", "grc"),
            _row("faith", "trust", "unverified", "אמונה", "heb"),
        ]
        registry = ConceptRegistry(engine=_mock_engine_returning(rows))
        result = registry.list_all_concepts(language="grc")
        assert len(result) == 1
        assert result[0].lemmas == ["πίστις"]
        assert result[0].lemma_count == 1

    def test_language_filter_with_no_matches_keeps_concept_with_empty_lemmas(
        self,
    ) -> None:
        from src.ontology.registry import ConceptRegistry
        # Concept has only heb lemmas; grc filter must NOT drop the concept —
        # it must surface with lemmas=[]. Forward-compat invariant for
        # multi-language registry growth.
        rows = [
            _row("hesed", "loyalty", "unverified", "חסד", "heb"),
        ]
        registry = ConceptRegistry(engine=_mock_engine_returning(rows))
        result = registry.list_all_concepts(language="grc")
        assert len(result) == 1
        assert result[0].name == "hesed"
        assert result[0].lemmas == []
        assert result[0].lemma_count == 0

    def test_aggregates_multiple_concepts(self) -> None:
        from src.ontology.registry import ConceptRegistry
        rows = [
            _row("faith", "trust", "unverified", "πίστις", "grc"),
            _row("faith", "trust", "unverified", "πιστεύω", "grc"),
            _row("hope", "expectation", "corpus_observed", "ἐλπίς", "grc"),
        ]
        registry = ConceptRegistry(engine=_mock_engine_returning(rows))
        result = registry.list_all_concepts()
        names = [c.name for c in result]
        assert names == ["faith", "hope"]
        faith = next(c for c in result if c.name == "faith")
        assert faith.lemma_count == 2
        assert faith.lemmas == ["πίστις", "πιστεύω"]
        hope = next(c for c in result if c.name == "hope")
        assert hope.lemma_count == 1
        assert hope.verification_state == "corpus_observed"
