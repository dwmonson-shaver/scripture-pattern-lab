"""Result explainer — prose synthesis from a RetrievalResult.

Per canonical-09 §9 (REQ:09.result-explainer): the explainer transforms a
``RetrievalResult`` into an ``ExplainedResultSet`` whose ``summary`` is the
slice-level prose (≤ 5 lines) and whose ``results`` carry per-candidate
explanations grounded in actual corpus counts.

Default (DEC-061): deterministic templating for ALL match types. f-strings
inside small helpers compose every line; every prose claim is derived from
fields on ``result``, ``plan``, or ``validation`` — never invented.

Optional LLM augmentation (Slice K, DEC-090, closes Bucket 7): when ``explain``
is called with an injected ``LLMClient``, per-candidate prose for
``match_type == "conceptual"`` is paraphrased by the LLM from grounded
structured fields. The LLM never replaces deterministic grounded fields:
``summary``, ``contextualization`` baselines, alt-ordering phrases, and
``validation_notes`` stay deterministic. The LLM has access only to the
fields ``build_explainer_user_message`` exposes (verse reference, sequence
label, match type, per-step lemma + node value + resolved lemmas) — the
structural enforcement of DEC-081's no-fabrication clause. Any LLM failure
(``LLMUnavailable``, unexpected ``Exception``, ``FALLBACK`` sentinel, empty
output) cleanly falls back to the deterministic helper.

Cap policy (Bucket 4 closure):
- resolved-lemma display capped at 5 items with "(+N more)" suffix
- sequence labels capped at 64 chars with ellipsis
- LLM-paraphrased prose post-truncated to 300 chars (defense-in-depth)

Substring-tested in ``tests/unit/test_explainer.py``;
``tests/integration/test_explainer_llm_prose_live.py`` covers the live-LLM
exit gate (DEC-081 conformance: grounded-substring check).
"""

from __future__ import annotations

import logging

from src.engine.models import (
    AlternativeOrderingCount,
    Contextualization,
    ExplainedResult,
    ExplainedResultSet,
    MatchCandidate,
    NodeBaseline,
    NodeRef,
    QueryPlan,
    RetrievalResult,
    SequenceExpr,
)
from src.nlp.llm_client import LLMClient, LLMUnavailable
from src.nlp.prompts.explainer_prompt import (
    EXPLAINER_SYSTEM_PROMPT,
    build_explainer_user_message,
)
from src.validation.validator import ValidationFinding, ValidationResult

logger = logging.getLogger(__name__)  # convention: above constants (K-MID-005)

_LEMMA_CAP = 5
_SEQUENCE_LABEL_MAX = 64
_VERSE_LIST_CAP = 3
_LLM_PROSE_MAX = 300
_LLM_FALLBACK_TOKEN = "FALLBACK"
# K-MID-001: bail on FALLBACK plus up to 5 trailing characters (punctuation,
# whitespace, newline), but not on a sentence that *contains* the word.
_LLM_FALLBACK_MAX_LEN = len(_LLM_FALLBACK_TOKEN) + 5


def explain(
    result: RetrievalResult,
    plan: QueryPlan,
    validation: ValidationResult,
    *,
    llm_client: LLMClient | None = None,
) -> ExplainedResultSet:
    """Build an ExplainedResultSet from a RetrievalResult, plan, and validation.

    Default: deterministic. Every prose claim is derived from fields on
    ``result``, ``plan``, or ``validation`` — never invented.

    Optional (Slice K — DEC-090): when ``llm_client`` is supplied, each
    candidate with ``match_type == "conceptual"`` has its ``explanation``
    field paraphrased by the LLM from grounded structured fields. The
    deterministic helper is the airtight fallback (any LLM failure returns
    the deterministic prose). Variant / exact candidates always get the
    deterministic helper. The summary, contextualization, baseline phrases,
    alt-ordering phrases, and validation notes are always deterministic —
    LLM augmentation touches only per-candidate ``explanation`` strings.

    Caller contract (DEC-024 corpus-is-ground-truth): when
    ``result.contextualization`` is supplied, its ``observed_count`` MUST be
    derived from the same retrieval pass that produced ``result.candidates``.
    The explainer reads ``ctx.observed_count`` for the alt-ordering
    comparative phrase and ``len(candidates)`` for the match-count line; if
    the caller passes inconsistent values the summary will internally
    contradict itself. The explainer does not re-execute retrieval to verify.
    """
    sequence_label = _sequence_label_for_plan(plan)
    summary = _summary_prose(
        sequence_label=sequence_label,
        candidates=result.candidates,
        ctx=result.contextualization,
    )
    explained_results: list[ExplainedResult] = []
    for c in result.candidates:
        if llm_client is not None and c.match_type == "conceptual":
            explanation = _per_candidate_prose_llm(c, sequence_label, llm_client)
        else:
            explanation = _per_candidate_prose(c, sequence_label)
        explained_results.append(
            ExplainedResult(
                reference=c.reference,
                text_display=_text_display_for_candidate(c),
                match_type=c.match_type,
                score=None,
                explanation=explanation,
            )
        )
    validation_notes = _format_validation_notes(validation)

    return ExplainedResultSet(
        query_shown=plan.source,
        nl_source=plan.metadata.nl_source,
        validation_notes=validation_notes,
        results=explained_results,
        contextualization=result.contextualization,
        summary=summary,
    )


# -- Summary prose -----------------------------------------------------------


def _summary_prose(
    sequence_label: str,
    candidates: list[MatchCandidate],
    ctx: Contextualization | None,
) -> str:
    """Compose the ≤ 5-line slice-level prose summary."""
    label = _truncate_sequence_label(sequence_label)
    n = len(candidates)
    lines: list[str] = []

    # Line 1: observed count + verse-list clause
    if n == 0:
        lines.append(
            f'The pattern "{label}" does not appear in the scoped corpus '
            f"(0 matches)."
        )
    elif n == 1:
        lines.append(
            f'The pattern "{label}" appears 1 time in the corpus, '
            f"at {candidates[0].reference}."
        )
    else:
        verse_clause = _verse_list_clause(candidates)
        lines.append(
            f'The pattern "{label}" appears {n} times in the corpus, '
            f"{verse_clause}."
        )

    # Line 2: singularity / multi-verse note. Suppress when line 1 already
    # carries the same information: n=1 already names the only verse;
    # multi-verse with refs ≤ cap already enumerates them inline.
    refs = sorted({c.reference for c in candidates})
    if n > 1 and len(refs) == 1:
        lines.append("This is the only verse where the sequence fires.")
    elif n > 1 and len(refs) > _VERSE_LIST_CAP:
        lines.append(f"The pattern fires across {len(refs)} distinct verses.")

    # Line 3: alt-ordering comparative observation (if contextualization present)
    if ctx is not None and ctx.alternative_orderings:
        alt_clause = _format_alt_orderings_phrase(ctx.alternative_orderings, ctx.observed_count)
        if alt_clause:
            lines.append(alt_clause)

    # Line 4: baselines (if present)
    if ctx is not None and ctx.node_baselines:
        baseline_phrase = _format_baselines_phrase(ctx.node_baselines)
        lines.append(f"Baselines: {baseline_phrase}.")

    # Line 5: capped-permutations qualifier (only if it fired)
    if ctx is not None and ctx.alternative_orderings_capped:
        lines.append(
            "(Alternative-orderings list is capped — sequence has 5+ steps; "
            "showing a representative subset.)"
        )

    return "\n".join(lines)


# -- Per-candidate prose -----------------------------------------------------


def _per_candidate_prose(candidate: MatchCandidate, sequence_label: str) -> str:
    """Compose a one-paragraph explanation for a single MatchCandidate."""
    label = _truncate_sequence_label(sequence_label)
    if not candidate.alignment:
        return (
            f'Match for "{label}" at {candidate.reference} '
            f"(match type: {candidate.match_type})."
        )
    pieces: list[str] = []
    for step in candidate.alignment:
        if step.node_value and step.token.lemma != step.node_value:
            pieces.append(f"{step.token.lemma} (for {step.node_value})")
        else:
            pieces.append(step.token.lemma)
    aligned = ", ".join(pieces)
    return (
        f'At {candidate.reference}: {aligned}. '
        f"Match type: {candidate.match_type}."
    )


def _per_candidate_prose_llm(
    candidate: MatchCandidate,
    sequence_label: str,
    llm_client: LLMClient,
) -> str:
    """LLM-backed paraphrase of grounded fields for a conceptual candidate.

    Calls ``llm_client.complete(EXPLAINER_SYSTEM_PROMPT, user_message)`` where
    ``user_message`` is the labeled-fields block produced by
    ``build_explainer_user_message``. The LLM has no inputs other than the
    grounded fields — that is the structural enforcement of DEC-081's
    no-fabrication clause.

    Fallback contract (DEC-061 — deterministic path is the source of truth):
    on ``LLMUnavailable`` OR any other ``Exception``, returns the deterministic
    ``_per_candidate_prose(...)`` output. A WARNING log is emitted with
    ``exc_info=True`` so operators can audit silent fallbacks. The LLM's
    explicit ``FALLBACK`` sentinel response also triggers deterministic
    fallback (the LLM signaled it could not satisfy the prompt's rules).

    Output is post-truncated to ``_LLM_PROSE_MAX`` characters as
    defense-in-depth against a misbehaving LLM ignoring the prompt's
    length constraint.
    """
    deterministic_prose = _per_candidate_prose(candidate, sequence_label)
    try:
        user_message = build_explainer_user_message(candidate, sequence_label)
        raw_output = llm_client.complete(EXPLAINER_SYSTEM_PROMPT, user_message)
    except LLMUnavailable as exc:
        logger.warning(
            "explainer LLM unavailable for %s; falling back to deterministic prose: %s",
            candidate.reference,
            exc.reason,
        )
        return deterministic_prose
    except Exception:  # noqa: BLE001 — broad catch is the airtight fallback.
        # DEC-061 mandates the deterministic baseline never breaks. Any
        # unexpected exception (programmer error in the helper, LLM SDK
        # surprise, etc.) falls back to deterministic prose with full
        # traceback in the log so the operator sees the bug.
        logger.warning(
            "explainer LLM raised unexpectedly for %s; falling back to "
            "deterministic prose",
            candidate.reference,
            exc_info=True,
        )
        return deterministic_prose

    cleaned = raw_output.strip()
    if not cleaned or _is_fallback_signal(cleaned):
        logger.warning(
            "explainer LLM emitted FALLBACK or empty output for %s; "
            "falling back to deterministic prose",
            candidate.reference,
        )
        return deterministic_prose

    return _truncate_llm_prose(cleaned)


def _is_fallback_signal(text: str) -> bool:
    """Recognize the LLM's FALLBACK bail-out sentinel.

    The system prompt instructs the LLM to emit the literal token ``FALLBACK``
    when it cannot satisfy the rules. In practice, LLMs sometimes pad the
    bail-out with trailing punctuation, whitespace, or newlines (e.g.,
    ``"FALLBACK."``, ``"FALLBACK\n"``). We accept the token plus up to
    ``_LLM_FALLBACK_MAX_LEN - len(_LLM_FALLBACK_TOKEN)`` trailing characters
    so that bail-outs are recognized, but a real paraphrase that *contains*
    the word "fallback" is NOT misclassified.
    """
    if len(text) > _LLM_FALLBACK_MAX_LEN:
        return False
    return text.upper().startswith(_LLM_FALLBACK_TOKEN)


def _truncate_llm_prose(text: str, max_chars: int = _LLM_PROSE_MAX) -> str:
    """Cap LLM-emitted prose at ``max_chars`` with ellipsis when truncated.

    Defense-in-depth: the system prompt requests ≤200 chars, but LLMs do not
    always honor length constraints. Post-truncation guarantees the result
    envelope stays bounded.
    """
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1].rstrip()}…"


# -- Phrase composers --------------------------------------------------------


def _format_baselines_phrase(baselines: list[NodeBaseline]) -> str:
    """Render baselines as 'faith (πίστις, πιστεύω) at 483, hope (...) at 84'."""
    parts: list[str] = []
    for nb in baselines:
        lemmas_display = _truncate_lemmas(nb.resolved_lemmas)
        if lemmas_display and nb.node_value != lemmas_display:
            parts.append(f"{nb.node_value} ({lemmas_display}) at {nb.count}")
        else:
            parts.append(f"{nb.node_value} at {nb.count}")
    return ", ".join(parts)


def _format_alt_orderings_phrase(
    orderings: list[AlternativeOrderingCount],
    observed_count: int,
) -> str:
    """Compose a one-sentence comparative note about alternative orderings.

    Strategy: find the highest-count non-observed ordering. Compare to the
    observed count. Three cases: tied with observed, lower than observed,
    all zero.
    """
    non_observed = [o for o in orderings if not o.is_observed]
    if not non_observed:
        return ""
    top = max(non_observed, key=lambda o: o.count)
    label = _truncate_sequence_label(top.sequence_label)

    if top.count == 0:
        return (
            "All alternative orderings of these nodes return 0 matches in "
            "the same scope — the observed direction is the only one that "
            "fires."
        )
    if top.count == observed_count:
        return (
            f'The alternative ordering "{label}" also fires {top.count} '
            f"time{'s' if top.count != 1 else ''} in the same scope — likely "
            f"adjacency rather than directional dependence."
        )
    if top.count < observed_count:
        return (
            f'The closest alternative ordering "{label}" fires '
            f"{top.count} time{'s' if top.count != 1 else ''} — "
            f"the observed direction is more frequent."
        )
    # top.count > observed_count
    return (
        f'The alternative ordering "{label}" fires more often '
        f"({top.count} vs. {observed_count}) — the observed direction is "
        f"NOT the dominant arrangement of these nodes."
    )


def _verse_list_clause(candidates: list[MatchCandidate]) -> str:
    """Render '<all> at 1Cor 13:13' or 'across N verses including X, Y, Z'."""
    refs = sorted({c.reference for c in candidates})
    if len(refs) == 1:
        return f"all at {refs[0]}"
    if len(refs) <= _VERSE_LIST_CAP:
        return f"across {len(refs)} verses ({', '.join(refs)})"
    head = ", ".join(refs[:_VERSE_LIST_CAP])
    return f"across {len(refs)} verses (including {head}, …)"


# -- Truncation helpers (Bucket 4 closure) ----------------------------------


def _truncate_lemmas(lemmas: list[str], cap: int = _LEMMA_CAP) -> str:
    """Cap-and-suffix policy: 'a, b, c, d, e' or 'a, b, c, d, e (+N more)'."""
    if not lemmas:
        return ""
    if len(lemmas) <= cap:
        return ", ".join(lemmas)
    head = ", ".join(lemmas[:cap])
    extra = len(lemmas) - cap
    return f"{head} (+{extra} more)"


def _truncate_sequence_label(label: str, max_chars: int = _SEQUENCE_LABEL_MAX) -> str:
    """64-char cap with ellipsis; ellipsizes on a token boundary when possible."""
    if len(label) <= max_chars:
        return label
    # Try to truncate at a ' > ' boundary so we don't cut mid-token.
    truncated = label[: max_chars - 1]
    last_sep = truncated.rfind(" > ")
    if last_sep != -1 and last_sep >= max_chars // 2:
        return f"{truncated[:last_sep]}…"
    return f"{truncated.rstrip()}…"


# -- Wiring helpers ----------------------------------------------------------


def _sequence_label_for_plan(plan: QueryPlan) -> str:
    """Render the plan's sequence as 'a > b > c'.

    For an InverseExpr top-level, render 'inverse(a > b > c)'. For SequenceExpr,
    join NodeRef values with ' > '. Non-NodeRef step types are rendered by
    their str() — should not normally occur on an executed plan since
    validate_plan_shape enforces NodeRef-only steps.
    """
    sequence = plan.sequence
    if isinstance(sequence, SequenceExpr):
        return _format_sequence(sequence)
    # InverseExpr
    return f"inverse({_format_sequence(sequence.inner)})"


def _format_sequence(seq: SequenceExpr) -> str:
    parts: list[str] = []
    for step in seq.steps:
        if isinstance(step, NodeRef):
            parts.append(step.value)
        else:
            parts.append(str(step))
    return " > ".join(parts)


def _text_display_for_candidate(candidate: MatchCandidate) -> str:
    """Show the matched lemmas in their corpus order, comma-separated."""
    if not candidate.alignment:
        return ""
    return ", ".join(step.token.lemma for step in candidate.alignment)


def _format_validation_notes(validation: ValidationResult) -> list[str]:
    """Raw validator finding strings; empty when status=supported with no findings."""
    if not validation.findings:
        return []
    return [_format_finding(f) for f in validation.findings]


def _format_finding(f: ValidationFinding) -> str:
    return f"{f.severity}: {f.code} at {f.path}: {f.message}"
