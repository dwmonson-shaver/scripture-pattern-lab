"""NL→DSL translator — single-shot LLM call returning a parsed TranslationResult.

Implements REQ:09.nl-to-dsl from canonical-09 §2. The translator is a thin layer
over an LLMClient: it builds the user message from the NL query plus context
summaries, calls .complete(), and parses the structured output.

Output extraction is regex-based against the documented format in
src/nlp/prompts/system_prompt.py. If the LLM doesn't follow the format
(no "DSL:" line), NLCompileError is raised — the route layer maps this to
422 nl_compile_error per DEC-070.
"""

from __future__ import annotations

import re

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


class TranslationResult(BaseModel):
    """Translator output. dsl is the load-bearing field; rest are metadata."""

    model_config = ConfigDict(frozen=True)
    dsl: str
    confidence: float = 1.0
    alternatives: list[str] = Field(default_factory=list)
    explanation: str = ""


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


def translate(
    nl_query: str,
    context: TranslationContext,
    llm_client: LLMClient,
) -> TranslationResult:
    """Compile a natural-language query into a TranslationResult.

    Single-shot LLM call per canonical-09 §2 MVP implementation. Raises
    LLMUnavailable (from llm_client.complete()) on API errors; raises
    NLCompileError if the LLM output cannot be parsed.
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


def _parse_output(*, nl_query: str, raw_output: str) -> TranslationResult:
    dsl_match = _DSL_LINE.search(raw_output)
    if dsl_match is None:
        raise NLCompileError(
            nl_query=nl_query,
            attempted_output=raw_output,
            reason="LLM output did not contain a 'DSL:' line",
        )
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

    return TranslationResult(
        dsl=dsl,
        confidence=confidence,
        alternatives=alternatives,
        explanation=explanation,
    )


def _extract_confidence(raw_output: str) -> float:
    match = _CONFIDENCE_LINE.search(raw_output)
    if match is None:
        return 1.0
    try:
        value = float(match.group(1))
    except ValueError:
        return 1.0
    if value < 0.0 or value > 1.0:
        return 1.0
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
