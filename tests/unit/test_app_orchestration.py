"""Tests for the FastAPI route orchestration helper (src/app/orchestration.py)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.app.orchestration import (
    ValidationUnsupported,
    run_dsl_query,
    run_nl_query,
    run_validate_only,
)
from src.app.schemas import QueryDSLResponse, QueryNLResponse, TranslationMetadata
from src.engine.models import (
    ConceptNotMapped,
    Contextualization,
    MatchCandidate,
    MatchedToken,
    NodeType,
    RegistryRequired,
    RetrievalResult,
    StepMatch,
    UnsupportedPlanShape,
)
from src.engine.parser import ParseError
from src.nlp.llm_client import LLMClient, LLMUnavailable
from src.nlp.translator import (
    NLCompileError,
    TranslationContext,
    TranslationResult,
)
from src.ontology.registry import ConceptRegistry
from src.validation.validator import ValidationFinding, ValidationResult


@pytest.fixture
def empty_registry() -> ConceptRegistry:
    return ConceptRegistry.empty()


@pytest.fixture
def fake_engine() -> MagicMock:
    """Stand-in for sqlalchemy.Engine. The real engine is only consulted
    by retrieve(), which we monkey-patch in these tests."""
    return MagicMock(name="fake_engine")


class TestParseError:
    def test_parse_error_propagates(self, fake_engine, empty_registry) -> None:
        # Empty operator triple is malformed.
        with pytest.raises(ParseError):
            run_dsl_query("faith > > > hope", fake_engine, empty_registry)


class TestValidationUnsupported:
    def test_inverse_is_unsupported_in_mvp(
        self, fake_engine, empty_registry
    ) -> None:
        # MVP capability registry has inverse_support=False (DEC pattern,
        # see canonical-06 and tests/unit/test_validator.py:208-226).
        with pytest.raises(ValidationUnsupported) as exc_info:
            run_dsl_query("inverse(faith > hope)", fake_engine, empty_registry)
        validation = exc_info.value.validation
        assert validation.status == "unsupported"
        assert any(
            f.code == "UNSUPPORTED_INVERSE" for f in validation.findings
        ), f"expected UNSUPPORTED_INVERSE in {[f.code for f in validation.findings]}"


class TestPipelineExceptionsPropagate:
    """retrieve() exceptions must propagate unchanged for the route handler
    to catch and map to HTTP status."""

    def test_unsupported_plan_shape_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise UnsupportedPlanShape("boom", path="$.sequence.steps[0]")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        with pytest.raises(UnsupportedPlanShape) as exc_info:
            run_dsl_query("faith > hope", fake_engine, empty_registry)
        assert exc_info.value.path == "$.sequence.steps[0]"

    def test_concept_not_mapped_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise ConceptNotMapped("foo")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        with pytest.raises(ConceptNotMapped) as exc_info:
            run_dsl_query("faith > hope", fake_engine, empty_registry)
        assert exc_info.value.concept_name == "foo"

    def test_registry_required_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise RegistryRequired("faith")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        with pytest.raises(RegistryRequired) as exc_info:
            run_dsl_query("faith > hope", fake_engine, empty_registry)
        assert exc_info.value.concept_name == "faith"


class TestHappyPathWithMockedRetrieve:
    """Verify the response envelope shape using a stubbed retrieve()
    so we don't need a real DB. End-to-end against real corpus is in G6."""

    def test_returns_query_dsl_response(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        # Stub retrieve to return an empty result (no matches).
        empty_result = RetrievalResult(
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
        monkeypatch.setattr(
            "src.app.orchestration.retrieve", lambda *a, **kw: empty_result
        )

        # Use a lemma-only DSL so the empty registry doesn't matter for
        # validation (lemma nodes don't need registry lookup).
        resp = run_dsl_query("πίστις > ἐλπίς", fake_engine, empty_registry)

        assert isinstance(resp, QueryDSLResponse)
        assert resp.query == "πίστις > ἐλπίς"
        assert resp.validation.status in ("supported", "partial")
        assert resp.result is empty_result
        assert resp.explanation.summary  # non-empty deterministic prose
        assert resp.explanation.results == []  # no candidates

    def test_response_carries_match_candidate(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        token = MatchedToken(
            id=1,
            book="40",
            chapter=1,
            verse=1,
            position=0,
            global_position=0,
            surface_form="πίστις",
            normalized_form="πίστις",
            lemma="πίστις",
            pos="N",
        )
        candidate = MatchCandidate(
            tokens=[token],
            reference="Mat 1:1",
            match_type="exact",
            alignment=[
                StepMatch(
                    step_index=0,
                    node_type=NodeType.LEMMA,
                    node_value="πίστις",
                    resolved_lemmas=["πίστις"],
                    token=token,
                )
            ],
        )
        result = RetrievalResult(
            candidates=[candidate],
            stages_used=["pattern_engine"],
            contextualization=Contextualization(
                observed_count=1,
                node_baselines=[],
                alternative_orderings=[],
                alternative_orderings_capped=False,
                null_distribution=None,
            ),
        )
        monkeypatch.setattr(
            "src.app.orchestration.retrieve", lambda *a, **kw: result
        )

        resp = run_dsl_query("πίστις", fake_engine, empty_registry)

        assert len(resp.result.candidates) == 1
        assert resp.result.candidates[0].reference == "Mat 1:1"
        assert len(resp.explanation.results) == 1


class TestPartialValidationPath:
    """When validate() returns status='partial', the orchestrator must
    proceed with validation.executable_plan and surface the partial
    findings on the response envelope (so HTTP consumers can render
    warnings)."""

    def test_partial_status_threads_findings_into_response(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        # Stub validate() to return status="partial" with one warning.
        warning = ValidationFinding(
            severity="warning",
            code="PARTIAL_REDUCTION",
            path="$.sequence.steps[1]",
            message="reduced expansion directive",
            remediation=None,
        )

        def stub_validate(plan, *args: object, **kwargs: object) -> ValidationResult:
            return ValidationResult(
                status="partial",
                executable_plan=plan,
                findings=[warning],
                engine_version="0.1.0",
                grounding=None,
            )

        empty_result = RetrievalResult(
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

        monkeypatch.setattr("src.app.orchestration.validate", stub_validate)
        monkeypatch.setattr(
            "src.app.orchestration.retrieve", lambda *a, **kw: empty_result
        )

        resp = run_dsl_query("πίστις", fake_engine, empty_registry)

        assert resp.validation.status == "partial"
        assert len(resp.validation.findings) == 1
        assert resp.validation.findings[0].code == "PARTIAL_REDUCTION"
        assert resp.result is empty_result


# -- run_nl_query tests (Slice H) ---------------------------------------


class _FakeLLMClient(LLMClient):
    """LLMClient stub for run_nl_query tests; returns canned text."""

    def __init__(self, canned: str) -> None:
        self.canned = canned

    def complete(self, system_prompt: str, user_message: str) -> str:
        return self.canned


def _ctx() -> TranslationContext:
    return TranslationContext(
        capability_registry_summary="cap-summary",
        concept_registry_summary="concepts: faith, hope, love",
    )


class TestRunNLQueryHappyPath:
    def test_composes_translator_and_dsl_pipeline(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        # Stub the translator to avoid real LLM call.
        translation = TranslationResult(
            dsl="faith",
            confidence=0.9,
            alternatives=["love"],
            explanation="conceptual single-step query",
        )
        monkeypatch.setattr(
            "src.app.orchestration.translate",
            lambda *a, **kw: translation,
        )

        # Stub retrieve so we don't need a real engine.
        empty_result = RetrievalResult(
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
        monkeypatch.setattr(
            "src.app.orchestration.retrieve", lambda *a, **kw: empty_result
        )

        resp = run_nl_query(
            nl_query="what does Paul say about faith?",
            engine=fake_engine,
            registry=empty_registry,
            llm_client=_FakeLLMClient(canned="ignored — translate is stubbed"),
            context=_ctx(),
        )

        assert isinstance(resp, QueryNLResponse)
        # query field carries the *compiled* DSL, not the NL.
        assert resp.query == "faith"
        # translation block surfaces metadata.
        assert isinstance(resp.translation, TranslationMetadata)
        assert resp.translation.confidence == 0.9
        assert resp.translation.alternatives == ["love"]
        assert resp.translation.explanation == "conceptual single-step query"
        # downstream envelope intact.
        assert resp.result is empty_result


class TestRunNLQueryTranslatorFailures:
    def test_llm_unavailable_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def boom(*a: object, **kw: object) -> None:
            raise LLMUnavailable("simulated outage")

        monkeypatch.setattr("src.app.orchestration.translate", boom)

        with pytest.raises(LLMUnavailable, match="simulated outage"):
            run_nl_query(
                nl_query="any",
                engine=fake_engine,
                registry=empty_registry,
                llm_client=_FakeLLMClient(canned=""),
                context=_ctx(),
            )

    def test_nl_compile_error_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        def boom(*a: object, **kw: object) -> None:
            raise NLCompileError(
                nl_query="vague",
                attempted_output="...",
                reason="LLM did not emit DSL",
            )

        monkeypatch.setattr("src.app.orchestration.translate", boom)

        with pytest.raises(NLCompileError):
            run_nl_query(
                nl_query="vague",
                engine=fake_engine,
                registry=empty_registry,
                llm_client=_FakeLLMClient(canned=""),
                context=_ctx(),
            )


class TestRunNLQueryDownstreamFailures:
    def test_parse_error_from_translator_dsl_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        # Translator emits "valid"-looking DSL that fails parse.
        translation = TranslationResult(dsl="faith > > > hope")
        monkeypatch.setattr(
            "src.app.orchestration.translate", lambda *a, **kw: translation
        )

        with pytest.raises(ParseError):
            run_nl_query(
                nl_query="any",
                engine=fake_engine,
                registry=empty_registry,
                llm_client=_FakeLLMClient(canned=""),
                context=_ctx(),
            )

    def test_validation_unsupported_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        translation = TranslationResult(dsl="inverse(faith)")
        monkeypatch.setattr(
            "src.app.orchestration.translate", lambda *a, **kw: translation
        )

        with pytest.raises(ValidationUnsupported):
            run_nl_query(
                nl_query="any",
                engine=fake_engine,
                registry=empty_registry,
                llm_client=_FakeLLMClient(canned=""),
                context=_ctx(),
            )

    def test_concept_not_mapped_propagates(
        self, monkeypatch, fake_engine, empty_registry
    ) -> None:
        translation = TranslationResult(dsl="faith > hope")
        monkeypatch.setattr(
            "src.app.orchestration.translate", lambda *a, **kw: translation
        )

        def boom(*a: object, **kw: object) -> None:
            raise ConceptNotMapped(concept_name="faith")

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)

        with pytest.raises(ConceptNotMapped):
            run_nl_query(
                nl_query="any",
                engine=fake_engine,
                registry=empty_registry,
                llm_client=_FakeLLMClient(canned=""),
                context=_ctx(),
            )


# -- run_validate_only (Slice I) ----------------------------------------


class TestRunValidateOnly:
    def test_supported_path_returns_validation_result(
        self, empty_registry
    ) -> None:
        result = run_validate_only("πίστις > ἐλπίς", empty_registry)
        assert result.status in ("supported", "partial")
        assert isinstance(result.findings, list)

    def test_parse_error_propagates(self, empty_registry) -> None:
        with pytest.raises(ParseError):
            run_validate_only("faith > > > hope", empty_registry)

    def test_unsupported_returns_result_not_raises(self, empty_registry) -> None:
        # DEC-079: validator-rejected plan must NOT raise from
        # run_validate_only — it returns a ValidationResult with
        # status='unsupported'. (Distinct from run_dsl_query which
        # raises ValidationUnsupported.)
        result = run_validate_only("inverse(faith)", empty_registry)
        assert result.status == "unsupported"
        assert any(f.code == "UNSUPPORTED_INVERSE" for f in result.findings)

    def test_no_retrieve_or_explain_called(
        self, monkeypatch, empty_registry
    ) -> None:
        # Verify run_validate_only doesn't call retrieve() or explain()
        # by setting them to raise — if either is called, test fails.
        def boom(*a: object, **kw: object) -> None:
            raise AssertionError(
                "run_validate_only must not call retrieve/explain"
            )

        monkeypatch.setattr("src.app.orchestration.retrieve", boom)
        monkeypatch.setattr("src.app.orchestration.explain", boom)
        # Real lemma DSL — validator runs without registry; retrieve and
        # explain are not called by run_validate_only.
        result = run_validate_only("πίστις", empty_registry)
        assert result is not None
