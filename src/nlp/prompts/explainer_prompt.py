"""Explainer LLM prompt assembly — system prompt + grounded user message.

Per Slice K (Bucket 7 closure): when ``src/nlp/explainer.py`` is invoked with
an injected ``LLMClient``, the per-candidate prose for ``match_type ==
"conceptual"`` is paraphrased by the LLM from grounded structured fields.

This module owns the prompt text. Two surfaces:

- ``EXPLAINER_SYSTEM_PROMPT`` — module constant. The "rephrase, do not add"
  contract that enforces DEC-081's no-fabrication clause structurally: the
  LLM is told to use ONLY values from the structured user message, to emit
  exactly one sentence under 200 characters, and to bail out via the literal
  token ``FALLBACK`` if it cannot.
- ``build_explainer_user_message(candidate, sequence_label) -> str`` — pure
  function that formats labeled-field lines from a ``MatchCandidate`` and
  the rendered sequence label. Every field passed to the LLM comes from a
  frozen Pydantic instance produced by the deterministic executor.

The system prompt is module-level (built once at import time) because it
never changes per request. The user message is per-call because it carries
the candidate's grounded fields.

Mirrors the pattern in ``src/nlp/prompts/system_prompt.py`` (Slice H's
translator prompt). Substring-tested in
``tests/unit/test_explainer_prompt.py``.
"""

from __future__ import annotations

from src.engine.models import MatchCandidate

EXPLAINER_SYSTEM_PROMPT: str = """\
You paraphrase a single Greek-corpus pattern-match candidate into one short
English sentence.

You are NOT performing exegesis. You are NOT supplying commentary. You are
NOT citing other passages. You translate the structured fields below into
one fluent sentence.

Strict rules:
1. Use ONLY the values from the structured fields below. Do not invent
   verse references, lemma counts, lemma identities, match-type labels,
   or any claim not present in the input.
2. Do not add interpretive, theological, exegetical, or historical
   commentary. No "this represents...", "this echoes...", "Pauline...", etc.
3. Output exactly one sentence. No headers. No Markdown. No bullets. No
   newlines. Under 200 characters.
4. The verse reference and the matched lemmas must appear in your sentence
   verbatim.
5. If you cannot produce a sentence that satisfies rules 1-4, emit the
   single token: FALLBACK
"""


def build_explainer_user_message(
    candidate: MatchCandidate,
    sequence_label: str,
) -> str:
    """Format the user message for a single conceptual-match candidate.

    The message is a labeled-fields block: every field the LLM may use is
    explicit and traceable to the candidate's frozen Pydantic state. This is
    the structural enforcement of DEC-081's no-fabrication clause — the LLM
    has nothing else to draw from.

    Step lines are emitted in alignment order so the LLM produces prose that
    matches the corpus token sequence.
    """
    lines: list[str] = [
        f"Verse reference: {candidate.reference}",
        f"Sequence pattern: {sequence_label}",
        f"Match type: {candidate.match_type}",
    ]
    for step in candidate.alignment:
        resolved = ", ".join(step.resolved_lemmas) if step.resolved_lemmas else ""
        lines.append(
            f'Step {step.step_index}: concept "{step.node_value}" matched '
            f"lemma {step.token.lemma}; registry resolves to [{resolved}]"
        )
    lines.append("")
    lines.append(
        "Paraphrase the match above into one short English sentence per the "
        "system rules."
    )
    return "\n".join(lines)
