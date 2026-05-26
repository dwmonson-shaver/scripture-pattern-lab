"""Unit tests for src.nlp.translator and src.nlp.prompts.system_prompt.

Uses a FakeLLMClient that returns a canned string per call — no API tokens.
"""

from __future__ import annotations

import pytest

from src.nlp.llm_client import LLMClient, LLMUnavailable, Message
from src.nlp.prompts.system_prompt import (
    DEFAULT_COOKBOOK_PATH,
    SYSTEM_PROMPT,
    build_system_prompt,
)
from src.nlp.translator import (
    NLCompileError,
    TranslationContext,
    TranslationSuccess,
    translate,
)


class FakeLLMClient(LLMClient):
    """Returns canned_response on .complete()/.complete_turns(); records args.

    ``single_shot_response`` and ``turns_response`` let a test script different
    canned outputs per seam (e.g. a clarification on the single-shot call and a
    DSL on the multi-turn call). When ``turns_response`` is None, both seams
    return ``canned_response``.
    """

    def __init__(
        self,
        canned_response: str,
        *,
        turns_response: str | None = None,
    ) -> None:
        self.canned_response = canned_response
        self.turns_response = turns_response
        self.last_system: str | None = None
        self.last_user: str | None = None
        self.last_turns: list[Message] | None = None
        self.complete_calls = 0
        self.complete_turns_calls = 0

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.complete_calls += 1
        self.last_system = system_prompt
        self.last_user = user_message
        return self.canned_response

    def complete_turns(self, system_prompt: str, turns: list[Message]) -> str:
        self.complete_turns_calls += 1
        self.last_system = system_prompt
        self.last_turns = turns
        if self.turns_response is not None:
            return self.turns_response
        return self.canned_response


class FailingLLMClient(LLMClient):
    """Raises LLMUnavailable on every call (both seams)."""

    def complete(self, system_prompt: str, user_message: str) -> str:
        raise LLMUnavailable("simulated failure")

    def complete_turns(self, system_prompt: str, turns: list[Message]) -> str:
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
        assert isinstance(result, TranslationSuccess)
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
        assert "DSL:" in exc_info.value.reason
        assert "Clarification:" in exc_info.value.reason
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
        result = TranslationSuccess(dsl="faith", confidence=0.5)
        with pytest.raises(Exception):
            result.dsl = "hope"  # type: ignore[misc]

    def test_translation_context_is_frozen(self) -> None:
        ctx = _ctx()
        with pytest.raises(Exception):
            ctx.capability_registry_summary = "x"  # type: ignore[misc]


class TestTranslateClarificationPath:
    """Slice L Decision #6: when the LLM emits ``Clarification:`` instead of
    ``DSL:``, the translator returns ``TranslationNeedsClarification``."""

    def test_clarification_line_returns_clarification_variant(self) -> None:
        from src.nlp.translator import TranslationNeedsClarification

        client = FakeLLMClient(
            canned_response=(
                "Clarification: What window size do you want for proximity? "
                "Common choices: 20, 50, 100 tokens.\n"
            )
        )
        result = translate(
            "Where do faith, hope, love appear near each other?", _ctx(), client
        )
        assert isinstance(result, TranslationNeedsClarification)
        assert "window size" in result.question.lower()
        # Codex P2: defaults must all lie at or below window_max_tokens=50.
        assert result.suggested_windows == [10, 20, 50]
        assert "near each other" in result.nl_source

    def test_dsl_line_takes_precedence_over_clarification(self) -> None:
        """If the LLM emits both ``DSL:`` and ``Clarification:``, the DSL
        wins — the explicit translation is the canonical signal."""
        client = FakeLLMClient(
            canned_response=(
                "DSL: faith > hope > love within:verse\n"
                "Confidence: 0.8\n"
                "Clarification: ambiguous window size\n"
            )
        )
        result = translate("q", _ctx(), client)
        assert isinstance(result, TranslationSuccess)
        assert result.dsl == "faith > hope > love within:verse"


class TestTranslateMultiTurn:
    """Slice M (DEC-098): when ``prior_turns`` is non-empty, ``translate``
    assembles a multi-message array and calls ``complete_turns()`` instead of
    the single-shot ``complete()``. Empty/None preserves the single-shot path
    byte-identically. ``prior_turns`` is the nlp-layer ``Message`` type."""

    def test_none_prior_turns_uses_single_shot(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith\n")
        translate("what is faith?", _ctx(), client)
        assert client.complete_calls == 1
        assert client.complete_turns_calls == 0

    def test_empty_prior_turns_uses_single_shot(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith\n")
        translate("what is faith?", _ctx(), client, prior_turns=[])
        assert client.complete_calls == 1
        assert client.complete_turns_calls == 0

    def test_non_empty_prior_turns_uses_complete_turns(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith within:20\n")
        prior_turns: list[Message] = [
            {"role": "user", "content": "faith, hope, love near each other"},
            {"role": "assistant", "content": "What window size? 10/20/50?"},
        ]
        translate("within 20 tokens", _ctx(), client, prior_turns=prior_turns)
        assert client.complete_turns_calls == 1
        assert client.complete_calls == 0

    def test_multi_turn_role_sequence_and_registry_on_first_turn(self) -> None:
        client = FakeLLMClient(canned_response="DSL: faith within:20\n")
        prior_turns: list[Message] = [
            {"role": "user", "content": "faith, hope, love near each other"},
            {"role": "assistant", "content": "What window size? 10/20/50?"},
        ]
        translate("within 20 tokens", _ctx(), client, prior_turns=prior_turns)
        turns = client.last_turns
        assert turns is not None
        # user / assistant / user
        assert [t["role"] for t in turns] == ["user", "assistant", "user"]
        # turns[0] carries the original NL plus the registry summaries (built
        # exactly like the single-shot user message).
        assert "faith, hope, love near each other" in turns[0]["content"]
        assert "ops: > , >>" in turns[0]["content"]
        assert "faith, hope, love" in turns[0]["content"]
        # The prior assistant turn is carried verbatim.
        assert turns[1] == {"role": "assistant", "content": "What window size? 10/20/50?"}
        # The latest user turn is the bare nl_query (no registry summaries).
        assert turns[2] == {"role": "user", "content": "within 20 tokens"}
        assert "ops: > , >>" not in turns[2]["content"]

    def test_clarification_then_answer_resolves_to_success(self) -> None:
        # Scripted clarification-then-answer turn list: the fake returns Shape A
        # DSL on the multi-turn call → translate returns TranslationSuccess.
        client = FakeLLMClient(
            canned_response="Clarification: pick a window\n",
            turns_response="DSL: faith ~ hope ~ love within:20\nConfidence: 0.9\n",
        )
        prior_turns: list[Message] = [
            {"role": "user", "content": "faith, hope, love near each other"},
            {"role": "assistant", "content": "What window size? 10/20/50?"},
        ]
        result = translate("20 tokens", _ctx(), client, prior_turns=prior_turns)
        assert isinstance(result, TranslationSuccess)
        assert result.dsl == "faith ~ hope ~ love within:20"
        assert result.confidence == 0.9

    def test_llm_unavailable_propagates_from_multi_turn(self) -> None:
        client = FailingLLMClient()
        prior_turns: list[Message] = [
            {"role": "user", "content": "faith near hope"},
            {"role": "assistant", "content": "What window size?"},
        ]
        with pytest.raises(LLMUnavailable, match="simulated failure"):
            translate("within 20", _ctx(), client, prior_turns=prior_turns)

    def test_system_prompt_byte_identical_across_paths(self) -> None:
        # Cache-prefix guard (DEC-071): the SYSTEM_PROMPT constant passed to the
        # client is the identical object on both the single-shot and multi-turn
        # paths.
        single = FakeLLMClient(canned_response="DSL: faith\n")
        translate("faith", _ctx(), single)

        multi = FakeLLMClient(canned_response="DSL: faith\n")
        prior_turns: list[Message] = [
            {"role": "user", "content": "faith near hope"},
            {"role": "assistant", "content": "What window size?"},
        ]
        translate("within 20", _ctx(), multi, prior_turns=prior_turns)

        assert single.last_system is SYSTEM_PROMPT
        assert multi.last_system is SYSTEM_PROMPT
        assert single.last_system == multi.last_system
