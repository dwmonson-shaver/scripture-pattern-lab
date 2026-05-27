"""Tests for the Tier-1 auto-create-and-rerun loop (Slice N, Phase N5).

The dead-end killer: a query referencing an unmapped term auto-creates a
machine/lexicon-sourced concept and re-runs once, surfacing an inline note. An
unresolvable term re-raises ConceptNotMapped (the honest 422). These tests stub
the retrieve + auto-create seams so no DB is needed; the live end-to-end is the
DATABASE_URL-gated integration exit gate.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.app import orchestration
from src.app.orchestration import run_dsl_query
from src.app.schemas import AutoCreatedConceptNote
from src.engine.models import (
    ConceptNotMapped,
    Contextualization,
    RetrievalResult,
)


@pytest.fixture
def empty_registry():  # type: ignore[no-untyped-def]
    from src.ontology.registry import ConceptRegistry

    return ConceptRegistry.empty()


@pytest.fixture
def fake_engine() -> MagicMock:
    return MagicMock(name="fake_engine")


def _fake_result() -> RetrievalResult:
    """A valid empty RetrievalResult — the auto-create loop's success is about
    the retry + note, not the candidate payload (covered elsewhere)."""
    return RetrievalResult(
        candidates=[],
        stages_used=["pattern_engine"],
        contextualization=Contextualization(
            observed_count=0,
            node_baselines=[],
            alternative_orderings=[],
            alternative_orderings_capped=False,
            null_distribution=None,
        ),
    )


class TestAutoCreateAndRerun:
    def test_unmapped_term_auto_creates_and_reruns(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        # retrieve raises ConceptNotMapped on the first call, succeeds on retry.
        calls = {"n": 0}

        def flaky_retrieve(*args: object, **kwargs: object) -> RetrievalResult:
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConceptNotMapped("humility")
            return _fake_result()

        def fake_auto_create(
            name: str, engine: object, *, article_llm: object = None
        ) -> AutoCreatedConceptNote:
            return AutoCreatedConceptNote(
                concept_name=name,
                lemmas=["ταπεινοφροσύνη"],
                summary="auto-created",
                document_available=True,
            )

        monkeypatch.setattr("src.app.orchestration.retrieve", flaky_retrieve)
        monkeypatch.setattr(
            orchestration, "_attempt_auto_create_concept", fake_auto_create
        )

        response = run_dsl_query("humility", fake_engine, empty_registry)
        assert calls["n"] == 2  # exactly one retry
        assert response.auto_created_concept is not None
        assert response.auto_created_concept.concept_name == "humility"
        assert "ταπεινοφροσύνη" in response.auto_created_concept.lemmas

    def test_unresolvable_term_reraises_concept_not_mapped(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def always_unmapped(*args: object, **kwargs: object) -> None:
            raise ConceptNotMapped("zzzznonsense")

        def cannot_resolve(name: str, engine: object, *, article_llm: object = None) -> None:
            return None  # unresolvable

        monkeypatch.setattr("src.app.orchestration.retrieve", always_unmapped)
        monkeypatch.setattr(
            orchestration, "_attempt_auto_create_concept", cannot_resolve
        )

        with pytest.raises(ConceptNotMapped) as exc_info:
            run_dsl_query("zzzznonsense", fake_engine, empty_registry)
        assert exc_info.value.concept_name == "zzzznonsense"

    def test_retry_is_bounded_to_one_attempt(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        # If auto-create "succeeds" but retrieve STILL raises (e.g. a different
        # unmapped concept), the loop must not spin — it re-raises after one retry.
        def always_unmapped(*args: object, **kwargs: object) -> None:
            raise ConceptNotMapped("first")

        attempts = {"n": 0}

        def fake_auto_create(
            name: str, engine: object, *, article_llm: object = None
        ) -> AutoCreatedConceptNote:
            attempts["n"] += 1
            return AutoCreatedConceptNote(
                concept_name=name, lemmas=["x"], summary="s", document_available=True
            )

        monkeypatch.setattr("src.app.orchestration.retrieve", always_unmapped)
        monkeypatch.setattr(
            orchestration, "_attempt_auto_create_concept", fake_auto_create
        )

        with pytest.raises(ConceptNotMapped):
            run_dsl_query("first", fake_engine, empty_registry)
        assert attempts["n"] == 1  # auto-create attempted exactly once


class TestArticleLLMOptIn:
    """The Part 1 §2 educational article LLM is opt-in and layered on top — it
    never gates auto-creation. The /dsl path never threads an article LLM."""

    def test_dsl_path_passes_no_article_llm(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        captured: dict[str, object] = {}

        def fake_auto_create(
            name: str, engine: object, *, article_llm: object = None
        ) -> AutoCreatedConceptNote:
            captured["article_llm"] = article_llm
            return AutoCreatedConceptNote(
                concept_name=name, lemmas=["x"], summary="s", document_available=True
            )

        calls = {"n": 0}

        def flaky_retrieve(*args: object, **kwargs: object) -> RetrievalResult:
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConceptNotMapped("humility")
            return _fake_result()

        monkeypatch.setattr("src.app.orchestration.retrieve", flaky_retrieve)
        monkeypatch.setattr(
            orchestration, "_attempt_auto_create_concept", fake_auto_create
        )
        run_dsl_query("humility", fake_engine, empty_registry)
        # The /dsl surface stays article-LLM-free.
        assert captured["article_llm"] is None

    def test_opt_in_env_helper_reads_truthy(self, monkeypatch) -> None:
        monkeypatch.setenv("SPL_CONCEPT_ARTICLE_LLM", "1")
        assert orchestration._concept_article_llm_opted_in() is True
        monkeypatch.setenv("SPL_CONCEPT_ARTICLE_LLM", "false")
        assert orchestration._concept_article_llm_opted_in() is False
        monkeypatch.delenv("SPL_CONCEPT_ARTICLE_LLM", raising=False)
        assert orchestration._concept_article_llm_opted_in() is False
