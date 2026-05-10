"""Unit tests for src.nlp.translator and src.nlp.prompts.system_prompt.

Uses a FakeLLMClient that returns a canned string per call — no API tokens.
"""

from __future__ import annotations

import pytest

from src.nlp.llm_client import LLMClient, LLMUnavailable
from src.nlp.prompts.system_prompt import (
    DEFAULT_COOKBOOK_PATH,
    SYSTEM_PROMPT,
    build_system_prompt,
)
from src.nlp.translator import (
    NLCompileError,
    TranslationContext,
    TranslationResult,
    translate,
)


class FakeLLMClient(LLMClient):
    """Returns canned_response on .complete(); records the args."""

    def __init__(self, canned_response: str) -> None:
        self.canned_response = canned_response
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.last_system = system_prompt
        self.last_user = user_message
        return self.canned_response


class FailingLLMClient(LLMClient):
    """Raises LLMUnavailable on every call."""

    def complete(self, system_prompt: str, user_message: str) -> str:
        raise LLMUnavailable("simulated failure")


def _ctx() -> TranslationContext:
    return TranslationContext(
        capability_registry_summary="ops: > , >> ; max-steps: 10",
        concept_registry_summary="faith, hope, love",
    )


class TestSystemPromptBuild:
    def test_default_module_constant_is_non_empty(self) -> None:
        assert SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 1000

    def test_default_module_constant_includes_cookbook(self) -> None:
        assert "DSL Cookbook for Agents" in SYSTEM_PROMPT
        assert "BEGIN DSL COOKBOOK" in SYSTEM_PROMPT
        assert "END DSL COOKBOOK" in SYSTEM_PROMPT

    def test_default_module_constant_includes_translator_framing(self) -> None:
        assert "DSL compiler" in SYSTEM_PROMPT
        assert "DSL: <one DSL string" in SYSTEM_PROMPT

    def test_build_with_explicit_text_skips_disk(self) -> None:
        result = build_system_prompt(cookbook_text="MOCK COOKBOOK CONTENT")
        assert "MOCK COOKBOOK CONTENT" in result
        assert "DSL compiler" in result

    def test_default_cookbook_path_exists(self) -> None:
        assert DEFAULT_COOKBOOK_PATH.exists()


class TestTranslateHappyPath:
    def test_minimal_response_parses(self) -> None:
        client = FakeLLMClient(
            canned_response=(
                "DSL: faith > hope > love\n"
                "Confidence: 0.92\n"
                "Alternatives:\n"
                "- faith > love > hope\n"
                "- love > faith > hope\n"
                "Explanation: A linear sequence of three concept matches.\n"
            )
        )
        result = translate("paths from faith to love through hope", _ctx(), client)
        assert isinstance(result, TranslationResult)
        assert result.dsl == "faith > hope > love"
        assert result.confidence == 0.92
        assert result.alternatives == ["faith > love > hope", "love > faith > hope"]
        assert result.explanation == "A linear sequence of three concept matches."

    def test_system_prompt_passed_to_client(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith\n")
        translate("what is faith?", _ctx(), client)
        assert client.last_system is not None
        assert "DSL compiler" in client.last_system

    def test_user_message_includes_nl_query_and_context_summaries(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith\n")
        translate("nl-question-marker", _ctx(), client)
        assert "nl-question-marker" in client.last_user
        assert "ops: > , >>" in client.last_user
        assert "faith, hope, love" in client.last_user


class TestTranslateOutputParsing:
    def test_missing_dsl_line_raises_nl_compile_error(self) -> None:
        client = FakeLLMClient(canned_response="I cannot translate this query.")
        with pytest.raises(NLCompileError) as exc_info:
            translate("vague query", _ctx(), client)
        assert exc_info.value.nl_query == "vague query"
        assert "did not contain a 'DSL:' line" in exc_info.value.reason
        assert exc_info.value.attempted_output == "I cannot translate this query."

    def test_empty_dsl_line_raises_nl_compile_error(self) -> None:
        client = FakeLLMClient(canned_response="DSL: \nConfidence: 0.5\n")
        with pytest.raises(NLCompileError, match="empty DSL"):
            translate("vague query", _ctx(), client)

    def test_missing_confidence_defaults_to_zero(self) -> None:
        # H-CLOSE-003: when the LLM doesn't volunteer a Confidence: line,
        # default to 0.0 rather than 1.0. We don't claim confidence the
        # LLM didn't claim (DEC-024 corpus-is-ground-truth charter).
        client = FakeLLMClient(canned_response="DSL: faith\n")
        result = translate("q", _ctx(), client)
        assert result.confidence == 0.0

    def test_malformed_confidence_defaults_to_zero(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith\nConfidence: not-a-number\n")
        result = translate("q", _ctx(), client)
        assert result.confidence == 0.0

    def test_out_of_range_confidence_defaults_to_zero(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith\nConfidence: 1.5\n")
        result = translate("q", _ctx(), client)
        assert result.confidence == 0.0

    def test_missing_alternatives_defaults_to_empty_list(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith\n")
        result = translate("q", _ctx(), client)
        assert result.alternatives == []

    def test_missing_explanation_defaults_to_empty_string(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith\n")
        result = translate("q", _ctx(), client)
        assert result.explanation == ""

    def test_alternatives_with_asterisk_bullets(self) -> None:
        client = FakeLLMClient(
            canned_response="DSL: faith\nAlternatives:\n* hope\n* love\n"
        )
        result = translate("q", _ctx(), client)
        assert result.alternatives == ["hope", "love"]


class TestTranslatePropagatesLLMUnavailable:
    def test_failing_client_propagates(self) -> None:
        client = FailingLLMClient()
        with pytest.raises(LLMUnavailable, match="simulated failure"):
            translate("q", _ctx(), client)


class TestTranslationResultFrozen:
    def test_translation_result_is_frozen(self) -> None:
        result = TranslationResult(dsl="faith", confidence=0.5)
        with pytest.raises(Exception):
            result.dsl = "hope"  # type: ignore[misc]

    def test_translation_context_is_frozen(self) -> None:
        ctx = _ctx()
        with pytest.raises(Exception):
            ctx.capability_registry_summary = "x"  # type: ignore[misc]
