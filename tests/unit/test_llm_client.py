"""Unit tests for src.nlp.llm_client.

The Anthropic SDK is mocked via unittest.mock; no API tokens are consumed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import anthropic
import pytest

from src.nlp.llm_client import (
    AnthropicLLMClient,
    LLMClient,
    LLMUnavailable,
    build_anthropic_client_from_env,
)


def _fake_message(text: str) -> MagicMock:
    """Build a stand-in for an anthropic Message response."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response = MagicMock()
    response.content = [text_block]
    return response


class TestLLMClientBase:
    def test_base_complete_raises_not_implemented(self) -> None:
        client = LLMClient()
        with pytest.raises(NotImplementedError):
            client.complete("system", "user")

    def test_anthropic_subclasses_base(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic"):
            client = AnthropicLLMClient(api_key="test-key")
        assert isinstance(client, LLMClient)


class TestAnthropicConstruction:
    def test_empty_api_key_raises_runtime_error(self) -> None:
        with pytest.raises(RuntimeError, match="requires an api_key"):
            AnthropicLLMClient(api_key="")

    def test_construction_with_key_succeeds(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            client = AnthropicLLMClient(api_key="sk-test", model="claude-haiku-4-5")
            anth_cls.assert_called_once_with(api_key="sk-test")
            assert client._model == "claude-haiku-4-5"
            assert client._max_tokens == 1024

    def test_max_tokens_override(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic"):
            client = AnthropicLLMClient(api_key="sk-test", max_tokens=512)
            assert client._max_tokens == 512


class TestAnthropicCompleteHappyPath:
    def test_returns_concatenated_text_blocks(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            inner = MagicMock()
            inner.messages.create.return_value = _fake_message("DSL: faith > hope > love")
            anth_cls.return_value = inner
            client = AnthropicLLMClient(api_key="sk-test")
            result = client.complete("system text", "user text")
        assert result == "DSL: faith > hope > love"
        inner.messages.create.assert_called_once_with(
            model="claude-opus-4-7",
            max_tokens=1024,
            system="system text",
            messages=[{"role": "user", "content": "user text"}],
        )

    def test_filters_non_text_blocks(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            inner = MagicMock()
            text_block = MagicMock()
            text_block.type = "text"
            text_block.text = "real text"
            tool_block = MagicMock()
            tool_block.type = "tool_use"
            response = MagicMock()
            response.content = [tool_block, text_block]
            inner.messages.create.return_value = response
            anth_cls.return_value = inner
            client = AnthropicLLMClient(api_key="sk-test")
            assert client.complete("s", "u") == "real text"


class TestAnthropicErrorWrapping:
    @pytest.mark.parametrize(
        "exc_factory",
        [
            lambda: anthropic.APIConnectionError(request=MagicMock()),
            lambda: anthropic.APITimeoutError(request=MagicMock()),
        ],
    )
    def test_network_errors_wrap_as_llm_unavailable(self, exc_factory) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            inner = MagicMock()
            inner.messages.create.side_effect = exc_factory()
            anth_cls.return_value = inner
            client = AnthropicLLMClient(api_key="sk-test")
            with pytest.raises(LLMUnavailable):
                client.complete("s", "u")

    def test_rate_limit_wraps_as_llm_unavailable(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            inner = MagicMock()
            response = MagicMock()
            response.status_code = 429
            response.headers = {}
            inner.messages.create.side_effect = anthropic.RateLimitError(
                message="rate limited", response=response, body=None
            )
            anth_cls.return_value = inner
            client = AnthropicLLMClient(api_key="sk-test")
            with pytest.raises(LLMUnavailable, match="RateLimitError"):
                client.complete("s", "u")

    def test_authentication_error_wraps_as_llm_unavailable(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            inner = MagicMock()
            response = MagicMock()
            response.status_code = 401
            response.headers = {}
            inner.messages.create.side_effect = anthropic.AuthenticationError(
                message="bad key", response=response, body=None
            )
            anth_cls.return_value = inner
            client = AnthropicLLMClient(api_key="sk-test")
            with pytest.raises(LLMUnavailable, match="AuthenticationError"):
                client.complete("s", "u")

    def test_internal_server_error_wraps_as_llm_unavailable(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            inner = MagicMock()
            response = MagicMock()
            response.status_code = 500
            response.headers = {}
            inner.messages.create.side_effect = anthropic.InternalServerError(
                message="upstream 500", response=response, body=None
            )
            anth_cls.return_value = inner
            client = AnthropicLLMClient(api_key="sk-test")
            with pytest.raises(LLMUnavailable, match="InternalServerError"):
                client.complete("s", "u")

    def test_permission_denied_wraps_as_llm_unavailable(self) -> None:
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            inner = MagicMock()
            response = MagicMock()
            response.status_code = 403
            response.headers = {}
            inner.messages.create.side_effect = anthropic.PermissionDeniedError(
                message="forbidden", response=response, body=None
            )
            anth_cls.return_value = inner
            client = AnthropicLLMClient(api_key="sk-test")
            with pytest.raises(LLMUnavailable, match="PermissionDeniedError"):
                client.complete("s", "u")

    @pytest.mark.parametrize(
        ("exc_class", "name"),
        [
            (anthropic.BadRequestError, "BadRequestError"),
            (anthropic.NotFoundError, "NotFoundError"),
            (anthropic.UnprocessableEntityError, "UnprocessableEntityError"),
            (anthropic.ConflictError, "ConflictError"),
        ],
    )
    def test_4xx_request_bugs_propagate_raw_not_as_llm_unavailable(
        self, exc_class, name: str
    ) -> None:
        # Per H-H1H2-001 (P2 finding) + DEC-070: 4xx errors are
        # translator-side request bugs, not availability issues. They
        # must propagate raw so the route returns 500 internal_error
        # (not 503 llm_unavailable).
        with patch("src.nlp.llm_client.anthropic.Anthropic") as anth_cls:
            inner = MagicMock()
            response = MagicMock()
            response.status_code = 400
            response.headers = {}
            inner.messages.create.side_effect = exc_class(
                message=f"{name} fault", response=response, body=None
            )
            anth_cls.return_value = inner
            client = AnthropicLLMClient(api_key="sk-test")
            with pytest.raises(exc_class):
                client.complete("s", "u")


class TestBuildFromEnv:
    def test_unset_env_raises_runtime_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is required"):
            build_anthropic_client_from_env()

    def test_set_env_constructs_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch("src.nlp.llm_client.anthropic.Anthropic"):
            client = build_anthropic_client_from_env(model="claude-sonnet-4-6")
        assert isinstance(client, AnthropicLLMClient)
        assert client._model == "claude-sonnet-4-6"
