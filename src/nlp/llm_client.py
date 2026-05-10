"""LLM client seam — single .complete() method per provider.

Implements the project's first external-service abstraction. The base class is
concrete (not typing.Protocol — see DEC-067) so unit tests can stub it via the
project's existing monkeypatch.setattr("module.NAME", stub) idiom.

For MVP, the sole concrete child is AnthropicLLMClient. Adding another provider
means adding a new subclass; no architectural change required.
"""

from __future__ import annotations

import os

import anthropic


class LLMUnavailable(Exception):
    """Raised when the LLM API is unreachable, unauthenticated, or rate-limited.

    Wraps any anthropic.APIError subclass that the route layer should treat as
    a 503 (per DEC-070, canonical-09 §1 status table extension).
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class LLMClient:
    """Concrete base for LLM completion calls.

    Subclasses override .complete() with provider-specific logic. The seam
    is a single method by design — translation is single-shot per DEC-071.
    """

    def complete(self, system_prompt: str, user_message: str) -> str:
        raise NotImplementedError


class AnthropicLLMClient(LLMClient):
    """Anthropic Claude implementation. Reads ANTHROPIC_API_KEY at construction."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-7",
        max_tokens: int = 1024,
    ) -> None:
        if not api_key:
            raise RuntimeError(
                "AnthropicLLMClient requires an api_key; "
                "set ANTHROPIC_API_KEY or use build_anthropic_client_from_env()."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system_prompt: str, user_message: str) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except (
            anthropic.APIConnectionError,
            anthropic.APITimeoutError,
            anthropic.RateLimitError,
            anthropic.AuthenticationError,
        ) as exc:
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc
        except anthropic.APIError as exc:
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc

        parts = [block.text for block in response.content if block.type == "text"]
        return "".join(parts)


def build_anthropic_client_from_env(
    model: str = "claude-opus-4-7",
    max_tokens: int = 1024,
) -> AnthropicLLMClient:
    """Construct AnthropicLLMClient reading ANTHROPIC_API_KEY from environment.

    Raises RuntimeError if the env var is unset (mirrors src/ingestion/db.py
    pattern for DATABASE_URL).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is required (export it or set it in .env); "
            "the NL→DSL translator has no fallback."
        )
    return AnthropicLLMClient(api_key=api_key, model=model, max_tokens=max_tokens)
