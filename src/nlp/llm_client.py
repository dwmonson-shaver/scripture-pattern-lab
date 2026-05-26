"""LLM client seam — single .complete() method per provider.

Implements the project's first external-service abstraction. The base class is
concrete (not typing.Protocol — see DEC-067) so unit tests can stub it via the
project's existing monkeypatch.setattr("module.NAME", stub) idiom.

For MVP, the sole concrete child is AnthropicLLMClient. Adding another provider
means adding a new subclass; no architectural change required.

Security note: api_key is stored on the inner anthropic.Anthropic client. Do
NOT log `vars(self._client)` or include the client in tracebacks via __repr__
overrides — the SDK exposes the api_key publicly on the instance.
"""

from __future__ import annotations

import os
from typing import Literal, TypedDict

import anthropic


class Message(TypedDict):
    """One element of the Anthropic messages array. Internal to the LLM seam.

    Used by complete_turns() to carry a caller-assembled multi-message
    conversation (user/assistant/user/...) verbatim. The app layer converts its
    schema-level ConversationTurn into this nlp-layer type at the boundary so
    src/nlp never imports from src/app (CLAUDE.md boundary discipline).
    """

    role: Literal["user", "assistant"]
    content: str


# Anthropic error families that map to a 503 LLMUnavailable: availability +
# auth + server-side faults. Excluded ON PURPOSE: BadRequestError, NotFoundError,
# UnprocessableEntityError, ConflictError — these are translator-side request
# bugs (we wrote a bad request to the API), not availability issues; they
# propagate raw so the route handler returns 500 (DEC-070; H-H1H2-001). Shared
# by complete() and complete_turns() so both seams classify identically.
_UNAVAILABLE_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.AuthenticationError,
    anthropic.PermissionDeniedError,
    anthropic.InternalServerError,
)


class LLMUnavailable(Exception):  # noqa: N818
    """Raised when the LLM API is unreachable, unauthenticated, or rate-limited.

    Wraps any anthropic.APIError subclass that the route layer should treat as
    a 503 (per DEC-070, canonical-09 §1 status table extension).
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class LLMClient:
    """Concrete base for LLM completion calls.

    Subclasses override the completion methods with provider-specific logic.

    Two seams (DEC-071 amended by proposed DEC-098):
      - complete() — the single-shot default and the cache-friendly base case.
        Translation is single-shot per DEC-071 unless the caller opts in to
        multi-turn refinement. A single-element user messages array.
      - complete_turns() — the ADDITIVE multi-message affordance for caller-
        driven, stateless refinement. The caller passes the full conversation
        as `turns`; the server holds no conversation state between requests
        (proposed DEC-098). The system prompt stays the static cached prefix
        (DEC-071 unchanged) on BOTH seams — only the per-request `messages`
        array grows when prior turns are present, so the cache prefix is
        identical across the two paths.
    """

    def complete(self, system_prompt: str, user_message: str) -> str:
        raise NotImplementedError

    def complete_turns(self, system_prompt: str, turns: list[Message]) -> str:
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
        except _UNAVAILABLE_ERRORS as exc:
            # See _UNAVAILABLE_ERRORS for the 503-vs-500 classification rationale
            # (DEC-070; H-H1H2-001).
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc

        return self._extract_text(response)

    def complete_turns(self, system_prompt: str, turns: list[Message]) -> str:
        """Multi-message seam. messages = `turns` verbatim; `system` stays the
        static cached prefix (DEC-071 unchanged, proposed DEC-098).

        Same exception wrapping as complete() — the shared _UNAVAILABLE_ERRORS
        families wrap as LLMUnavailable; everything else (4xx request bugs)
        propagates raw. The `system=` argument is byte-identical to the
        single-shot path for the same system_prompt, preserving the cache prefix.
        """
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=turns,
            )
        except _UNAVAILABLE_ERRORS as exc:
            # See _UNAVAILABLE_ERRORS for the 503-vs-500 classification rationale
            # (DEC-070; H-H1H2-001).
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc

        return self._extract_text(response)

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
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
