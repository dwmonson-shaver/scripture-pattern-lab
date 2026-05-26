"""NL→DSL translator — single-shot LLM call returning a parsed TranslationResult.

Implements REQ:09.nl-to-dsl from canonical-09 §2. The translator is a thin layer
over an LLMClient: it builds the user message from the NL query plus context
summaries, calls .complete(), and parses the structured output.

Output extraction is regex-based against the documented format in
src/nlp/prompts/system_prompt.py. The LLM may emit one of two response
shapes (Slice L Decision #6):

- "DSL:" line + Confidence + Alternatives + Explanation → ``TranslationSuccess``
- "Clarification:" line (no DSL:) → ``TranslationNeedsClarification`` for the
  cross-verse proximity scope-window question; route handler surfaces the
  question back to the user and the query does NOT execute.

If the LLM emits neither, ``NLCompileError`` is raised — the route layer maps
this to 422 nl_compile_error per DEC-070.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from src.nlp.llm_client import LLMClient
from src.nlp.prompts.system_prompt import SYSTEM_PROMPT


class TranslationContext(BaseModel):
    """Inputs threaded into the translator user message.

    Built once at FastAPI startup from the live capability registry and concept
    registry. Static for the process lifetime.
    """

    model_config = ConfigDict(frozen=True)
    capability_registry_summary: str
    concept_registry_summary: str


class TranslationSuccess(BaseModel):
    """Translator output for a successful NL→DSL compilation.

    ``dsl`` is the load-bearing field; rest are metadata. ``confidence``
    default is 0.0 — when the LLM doesn't volunteer a ``Confidence:`` line,
    treat as zero-confidence rather than max (H-CLOSE-003). Honest signal
    per DEC-024 (corpus-is-ground-truth): don't claim certainty the LLM
    didn't claim. Confidence is informational per DEC-072 — never gates
    execution — so the value's calibration is a transparency claim, not a
    control claim.
    """

    model_config = ConfigDict(frozen=True)
    kind: Literal["success"] = "success"
    dsl: str
    confidence: float = 0.0
    alternatives: list[str] = Field(default_factory=list)
    explanation: str = ""


class TranslationNeedsClarification(BaseModel):
    """Translator output when the NL is silent about proximity scope and the
    LLM emits a ``Clarification:`` line instead of ``DSL:`` (Slice L
    Decision #6).

    The route handler surfaces ``question`` to the user along with
    ``suggested_windows`` so they can pick a window N and resubmit. No
    query executes. ``nl_source`` echoes the original NL so the frontend
    can render context.

    Codex P2: ``suggested_windows`` defaults to ``[10, 20, 50]`` —
    every value must lie at or below ``CapabilityRegistry.window_max_tokens``
    so the user's choice always produces a runnable DSL. The original design
    used ``[20, 50, 100]``; ``100 > window_max_tokens=50`` would have the
    follow-up query rejected by the validator's WINDOW_EXCEEDS_MAX rule.
    """

    model_config = ConfigDict(frozen=True)
    kind: Literal["needs_clarification"] = "needs_clarification"
    question: str
    suggested_windows: list[int] = Field(default_factory=lambda: [10, 20, 50])
    nl_source: str


TranslationResult = Annotated[
    Union[TranslationSuccess, TranslationNeedsClarification],
    Field(discriminator="kind"),
]


# Legacy alias — many callers import ``TranslationResult`` expecting the
# success-shape directly. Keep the alias so the existing surface stays
# compatible; new code should branch on ``isinstance(result,
# TranslationSuccess | TranslationNeedsClarification)``.


class NLCompileError(Exception):
    """Raised when LLM output cannot be extracted as a DSL string."""

    def __init__(self, nl_query: str, attempted_output: str | None, reason: str) -> None:
        self.nl_query = nl_query
        self.attempted_output = attempted_output
        self.reason = reason
        super().__init__(reason)


_DSL_LINE = re.compile(r"^DSL:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
_CONFIDENCE_LINE = re.compile(r"^Confidence:[ \t]*([0-9.]+)[ \t]*$", re.MULTILINE)
_ALT_BULLET = re.compile(r"^[\-\*][ \t]*(.+?)[ \t]*$", re.MULTILINE)
_ALT_SECTION = re.compile(
    r"^Alternatives:[ \t]*\n((?:[\-\*][ \t]*.+\n?)*)",
    re.MULTILINE,
)
_EXPLANATION_LINE = re.compile(r"^Explanation:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
_CLARIFICATION_LINE = re.compile(r"^Clarification:[ \t]*(.+?)[ \t]*$", re.MULTILINE)


def translate(
    nl_query: str,
    context: TranslationContext,
    llm_client: LLMClient,
) -> TranslationSuccess | TranslationNeedsClarification:
    """Compile a natural-language query into a translator result.

    Single-shot LLM call per canonical-09 §2 MVP implementation. Raises
    LLMUnavailable (from llm_client.complete()) on API errors; raises
    NLCompileError if the LLM output cannot be parsed as either a DSL or
    a clarification.

    Slice L Decision #6: when the NL implies cross-verse proximity but is
    silent on the window size, the translator returns a
    :class:`TranslationNeedsClarification` instead of guessing a default.
    """
    user_message = _build_user_message(nl_query, context)
    raw_output = llm_client.complete(SYSTEM_PROMPT, user_message)
    return _parse_output(nl_query=nl_query, raw_output=raw_output)


def _build_user_message(nl_query: str, context: TranslationContext) -> str:
    return (
        f"Research question: {nl_query}\n\n"
        f"Capability registry summary:\n{context.capability_registry_summary}\n\n"
        f"Concept registry summary:\n{context.concept_registry_summary}\n\n"
        f"Translate the question above into DSL using the format specified in "
        f"the system prompt."
    )


def _parse_output(
    *, nl_query: str, raw_output: str
) -> TranslationSuccess | TranslationNeedsClarification:
    # Slice L: ``Clarification:`` takes precedence ONLY when no ``DSL:`` line
    # is present. If the LLM emitted both, we honor the DSL (Decision #6 set
    # the contract that DSL and Clarification are mutually exclusive; the
    # explicit DSL still represents a successful compile).
    dsl_match = _DSL_LINE.search(raw_output)
    if dsl_match is not None:
        dsl = dsl_match.group(1).strip()
        if not dsl:
            raise NLCompileError(
                nl_query=nl_query,
                attempted_output=raw_output,
                reason="LLM emitted an empty DSL string",
            )
        confidence = _extract_confidence(raw_output)
        alternatives = _extract_alternatives(raw_output)
        explanation = _extract_explanation(raw_output)
        return TranslationSuccess(
            dsl=dsl,
            confidence=confidence,
            alternatives=alternatives,
            explanation=explanation,
        )

    clarification_match = _CLARIFICATION_LINE.search(raw_output)
    if clarification_match is not None:
        question = clarification_match.group(1).strip()
        if question:
            return TranslationNeedsClarification(
                question=question,
                nl_source=nl_query,
            )

    raise NLCompileError(
        nl_query=nl_query,
        attempted_output=raw_output,
        reason="LLM output did not contain a 'DSL:' or 'Clarification:' line",
    )


def _extract_confidence(raw_output: str) -> float:
    """Parse the LLM's `Confidence:` line.

    Returns 0.0 (not 1.0) when the line is missing, malformed, or out of
    range — treating "I don't know what the LLM thinks" as zero confidence
    rather than max confidence (H-CLOSE-003 / DEC-024 corpus-is-ground-truth
    charter).
    """
    match = _CONFIDENCE_LINE.search(raw_output)
    if match is None:
        return 0.0
    try:
        value = float(match.group(1))
    except ValueError:
        return 0.0
    if value < 0.0 or value > 1.0:
        return 0.0
    return value


def _extract_alternatives(raw_output: str) -> list[str]:
    section = _ALT_SECTION.search(raw_output)
    if section is None:
        return []
    bullets = _ALT_BULLET.findall(section.group(1))
    return [b.strip() for b in bullets if b.strip()]


def _extract_explanation(raw_output: str) -> str:
    match = _EXPLANATION_LINE.search(raw_output)
    if match is None:
        return ""
    return match.group(1).strip()
