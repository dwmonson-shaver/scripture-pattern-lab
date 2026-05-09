"""Result explainer — deterministic prose synthesis from a RetrievalResult.

Per canonical-09 §9 (REQ:09.result-explainer): the explainer transforms a
``RetrievalResult`` into an ``ExplainedResultSet`` whose ``summary`` is the
slice-level prose (≤ 6 lines) and whose ``results`` carry per-candidate
explanations grounded in actual corpus counts.

MVP shape (DEC-061): deterministic templating for ALL match types. The
canonical "LLM explanation for conceptual matches" sentence is deferred
to a named bucket — adding an LLM dependency for prose generation alone
is overkill and the user has not yet seen a deterministic baseline to
compare against.

Cap policy (Bucket 4 closure):
- resolved-lemma display capped at 5 items with "(+N more)" suffix
- sequence labels capped at 64 chars with ellipsis

The module is purely deterministic — no I/O, no LLM client, no external
template engine. f-strings inside small helpers compose every line.
Substring-tested in ``tests/unit/test_explainer.py``.
"""

from __future__ import annotations

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
from src.validation.validator import ValidationFinding, ValidationResult

_LEMMA_CAP = 5
_SEQUENCE_LABEL_MAX = 64
_VERSE_LIST_CAP = 3


def explain(
    result: RetrievalResult,
    plan: QueryPlan,
    validation: ValidationResult,
) -> ExplainedResultSet:
    """Build an ExplainedResultSet from a RetrievalResult, plan, and validation.

    Deterministic. Every prose claim is derived from fields on ``result``,
    ``plan``, or ``validation`` — never invented.
    """
    sequence_label = _sequence_label_for_plan(plan)
    summary = _summary_prose(
        sequence_label=sequence_label,
        candidates=result.candidates,
        ctx=result.contextualization,
    )
    explained_results = [
        ExplainedResult(
            reference=c.reference,
            text_display=_text_display_for_candidate(c),
            match_type=c.match_type,
            score=None,
            explanation=_per_candidate_prose(c, sequence_label),
        )
        for c in result.candidates
    ]
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
    """Compose the ≤ 6-line slice-level prose summary."""
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

    # Line 2: singularity / multi-verse note
    refs = sorted({c.reference for c in candidates})
    if n > 0 and len(refs) == 1:
        lines.append(
            f"This is the only verse where the sequence fires."
        )
    elif n > 1 and len(refs) > 1:
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
            f"All alternative orderings of these nodes return 0 matches in "
            f"the same scope — the observed direction is the only one that "
            f"fires."
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
    """64-char cap with ellipsis. Whole-string truncation; preserves operator semantics by ellipsizing on a token boundary when possible."""
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
