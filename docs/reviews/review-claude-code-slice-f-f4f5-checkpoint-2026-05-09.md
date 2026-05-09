---
type: code-review
flavor: claude-fallback
slice_id: slice-f
checkpoint: F4+F5
date: 2026-05-09
verdict: minor-fixes-recommended
base_sha: fd46c5d
scope: src/engine/models.py + src/nlp/explainer.py + tests/unit/test_models.py + tests/unit/test_explainer.py (2 commits)
findings_summary: "0 P0, 0 P1, 1 P2, 4 P3, 3 info"
note: "Independent fallback review; Codex blocked by .codex permissions (Bucket 5 still open)."
---

# Slice F F4+F5 Checkpoint Review

**Reviewer:** Claude Code (fallback for Codex)
**Commits:** `62c5fd3` (F4: ExplainedResult + ExplainedResultSet models) + `5e8bf1b` (F5: explainer.py)
**Tests run:** 121 passed, 0 failed (39 pre-existing + 39 F4 model tests + 10 F4 ExplainedResult tests + 29 F5 explainer tests; the 10 ExplainedResult/Set model tests in test_models.py are counted in F4, full count 133 in test_models.py + 29 in test_explainer.py across all suites).

---

## Executive Summary

The checkpoint is mechanically sound. DEC-061 is clean — zero LLM/HTTP client dependencies confirmed by grep and manual inspection. Every prose claim in `_summary_prose`, `_per_candidate_prose`, and the phrase composers is traceable to a field on the input objects. The Pydantic model invariants (frozen, no validators, no serializers, correct Literal alignment) are exactly right. The cap/wrap helpers are correct at all boundaries tested.

Four findings follow. None are P0 or P1. One P2 concerns missing test coverage for paths that are in scope for this checkpoint (InverseExpr plan label, `nl_source` round-trip, `text_display` content). Three P3s flag prose redundancy and a prose-quality edge case. Three info notes flag design-contract choices that are acceptable as-is but worth recording.

---

## Category 1: Determinism + Grounding

**Result: clean.**

Every prose branch was traced manually and via Python interpreter:

- `_summary_prose` line 1: derives count from `len(candidates)` (not a hardcoded literal) and references from `candidates[i].reference`. Grounded.
- `_summary_prose` line 2 (singularity/multi-verse): computed from `{c.reference for c in candidates}`. Same source as line 1. No fabrication risk.
- `_format_alt_orderings_phrase`: uses `top.count` and `observed_count` passed in from `ctx.observed_count`. The comparison branches (tied, lower, higher, zero) are all grounded in those two fields. No invented comparisons.
- `_format_baselines_phrase`: uses `nb.node_value`, `nb.resolved_lemmas` (via `_truncate_lemmas`), and `nb.count`. All from the `NodeBaseline` object. Grounded.
- `_verse_list_clause`: derives ref list from `{c.reference for c in candidates}` and `_VERSE_LIST_CAP`. No fabrication.
- `_per_candidate_prose`: uses `candidate.reference`, `candidate.match_type`, and `step.token.lemma` / `step.node_value` from alignment. Grounded.
- `_format_validation_notes`: uses `f.severity`, `f.code`, `f.path`, `f.message` from `ValidationFinding`. Grounded.

No string that asserts a count without a field read. No placeholder injection risk found.

---

## Category 2: DEC-061 / No-LLM Invariant

**Result: clean.**

```
$ grep -i "anthropic\|openai\|langchain\|instructor\|httpx\|tiktoken" src/nlp/explainer.py
(no output)
```

No `await`, no `async`, no `os.environ`/`getenv`, no I/O. The module is purely synchronous and in-memory. Import list: `src.engine.models` and `src.validation.validator` only — no `src.retrieval.*` (DEC-025 boundary intact), no DB access.

---

## Category 3: Cap/Wrap Correctness

**Result: clean.**

`_truncate_lemmas`: tested at under-cap (3 items), at-cap (5 items), over-cap (7 items), empty list, and custom cap. Production code paths that would produce an unbounded lemma list (`_format_baselines_phrase`) correctly route through `_truncate_lemmas`. No unbounded f-string found in either `_summary_prose` or `_per_candidate_prose` that renders resolved lemmas directly.

`_truncate_sequence_label`: tested at under-max, at-max, over-max with separator alignment, over-max mid-token. Also verified extreme low `max_chars` (1, 2, 4) — correctly produces `"…"`, `"f…"`, `"fai…"` without panicking or violating the length contract.

`_per_candidate_prose` routes `sequence_label` through `_truncate_sequence_label` at the top of the function. `_summary_prose` does the same. Both call sites use `label = _truncate_sequence_label(sequence_label)` before any f-string interpolation. Cap policy is consistently applied.

---

## Category 4: Pydantic Model Invariants

**Result: clean.**

`ExplainedResult` and `ExplainedResultSet`: both use `ConfigDict(frozen=True)` only — no validators, no serializers — consistent with every other model in `src/engine/models.py`. Verified:

- `score: float | None = None` — correct.
- `nl_source: str | None = None` — correct.
- `validation_notes: list[str]` with no default — field is required at construction, which is consistent with the intent (callers must always pass notes, even if empty).
- `summary: str` required — confirmed by `test_summary_required`.
- `contextualization: Contextualization | None = None` — correct.
- `match_type` Literal alignment: both `ExplainedResult.match_type` and `MatchCandidate.match_type` are `Literal["exact", "variant", "conceptual"]` — confirmed identical by runtime introspection. Values pass through without conversion.

Note: `MatchMode` (the plan-level mode) includes `"hybrid"` as a fourth option, but the per-match `match_type` does not — this asymmetry is intentional and correct (`hybrid` is a retrieval strategy, not a per-match classification).

---

## Category 5: Edge Case Audit

All five cases were traced via the Python interpreter.

| Case | Prose produced | Issues |
|------|---------------|--------|
| `candidates=[], ctx=None` | `The pattern "X" does not appear in the scoped corpus (0 matches).` | Clean. |
| `candidates=[], ctx=Contextualization(observed_count=0, empty lists)` | Same single line. | Clean. |
| 1 candidate at 1 verse | Match count line + **singularity note** appended. | See F-F4F5-003. |
| 5 candidates at 1 verse | Count line (`all at X`) + singularity note. | See F-F4F5-003. |
| 5 candidates across 5 verses | Count line (`across 5 verses including...`) + multi-verse note. | See F-F4F5-004. |
| `alternative_orderings_capped=True` | Capped qualifier appended as final line. | Clean. |
| `validation.status == "partial"` | Findings formatted as `"severity: code at path: message"`. | Clean. |

Special case traced: `candidates=[], ctx` where a non-observed alt ordering fires more than observed (5 vs. 0). Prose correctly states `"fires more often (5 vs. 0)"` — grounded from `ctx.observed_count`. This is a valid and useful warning even in the zero-match case (the reverse ordering fires in corpus). Not a bug.

---

## Category 6: Test Coverage Gaps

Four paths in scope for this checkpoint have no test assertions in `tests/unit/test_explainer.py`.

See findings F-F4F5-001 (P2) and F-F4F5-005, F-F4F5-006, F-F4F5-007 (P3).

---

## Category 7: Module-Import Discipline

**Result: clean.**

Import block (lines 23–37):

```python
from src.engine.models import (
    AlternativeOrderingCount, Contextualization, ExplainedResult,
    ExplainedResultSet, MatchCandidate, NodeBaseline, NodeRef,
    QueryPlan, RetrievalResult, SequenceExpr,
)
from src.validation.validator import ValidationFinding, ValidationResult
```

No `src.retrieval.*`, no `src.app.*`, no `src.db.*`, no `sqlalchemy`, no stdlib I/O. Architecture boundary (DEC-025) intact.

---

## Findings

### F-F4F5-001 — P2 — Missing tests: InverseExpr plan label, nl_source round-trip, text_display field

**File:** `tests/unit/test_explainer.py`
**Severity:** P2 — must-fix-before-slice-close

**What's wrong:**

Three paths in `explain()` / `_sequence_label_for_plan()` have no coverage in the explainer test file:

1. **InverseExpr plan label** — `_sequence_label_for_plan` has an `isinstance(sequence, SequenceExpr)` branch and a fallback `InverseExpr` branch that produces `"inverse(a > b > c)"`. The fallback branch is untested in `test_explainer.py`. The InverseExpr path is exercised in `test_models.py` model construction but never through `explain()` → `_sequence_label_for_plan`.

2. **`nl_source` round-trip** — `explain()` reads `plan.metadata.nl_source` and writes it to `ExplainedResultSet.nl_source`. No assertion in `test_explainer.py` verifies this field is populated on the output (the field is tested in `test_models.py` for construction, not for the wiring through `explain()`).

3. **`text_display` field content** — `ExplainedResult.text_display` is populated by `_text_display_for_candidate()`. No test in `test_explainer.py` asserts on `er.text_display` for a candidate with a populated alignment, nor for the empty-alignment case (which produces `""`).

**Suggested fix:** Add a `TestExplainEdgePaths` class (or extend existing classes) with:

```python
def test_inverse_expr_plan_label_in_summary() -> None:
    plan = QueryPlan(
        version="0.1",
        source="inverse(faith > hope)",
        sequence=InverseExpr(
            inner=SequenceExpr(
                steps=[_node("faith"), _node("hope")],
                operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
            )
        ),
        scope=ScopeConstraint(),
        mode="conceptual",
        metadata=QueryMetadata(),
    )
    result = RetrievalResult(candidates=[], stages_used=["symbolic"])
    ers = explain(result, plan, _supported_validation())
    assert "inverse(faith > hope)" in ers.summary

def test_nl_source_round_trips_from_plan_metadata() -> None:
    plan = _plan_for_concepts("faith", "hope")
    plan = plan.model_copy(update={"metadata": QueryMetadata(nl_source="Does faith come before hope?")})
    result = RetrievalResult(candidates=[], stages_used=["symbolic"])
    ers = explain(result, plan, _supported_validation())
    assert ers.nl_source == "Does faith come before hope?"

def test_text_display_populated_from_alignment() -> None:
    result = RetrievalResult(
        candidates=[_candidate([("πίστις", "faith"), ("ἐλπίς", "hope")])],
        stages_used=["symbolic"],
    )
    ers = explain(result, _plan_for_concepts("faith", "hope"), _supported_validation())
    assert ers.results[0].text_display == "πίστις, ἐλπίς"

def test_text_display_empty_when_no_alignment() -> None:
    t = _token("πίστις")
    c = MatchCandidate(tokens=[t], reference="1Cor 13:13", match_type="exact", alignment=[])
    result = RetrievalResult(candidates=[c], stages_used=["symbolic"])
    ers = explain(result, _plan_for_concepts("faith"), _supported_validation())
    assert ers.results[0].text_display == ""
```

Note: `QueryPlan` is frozen so `model_copy(update=...)` is the correct mutation pattern.

---

### F-F4F5-002 — P3 — Redundant singularity note for n=1 candidate

**File:** `src/nlp/explainer.py`, lines 96–121 (`_summary_prose`)
**Severity:** P3 — worth-doing-soon

**What's wrong:**

When `n == 1`, line 1 already states the specific verse (`"at 1Cor 13:13"`). Line 2's singularity check (`n > 0 and len(refs) == 1`) then unconditionally appends `"This is the only verse where the sequence fires."` This is always trivially true for a single match and adds no information.

Observed output:
```
The pattern "faith" appears 1 time in the corpus, at 1Cor 13:13.
This is the only verse where the sequence fires.
```

The second sentence repeats what the first sentence already implies.

**Suggested fix:** Guard line 2 with `n > 1`:

```python
# Line 2: singularity / multi-verse note
refs = sorted({c.reference for c in candidates})
if n > 1 and len(refs) == 1:          # was: if n > 0 and len(refs) == 1
    lines.append("This is the only verse where the sequence fires.")
elif n > 1 and len(refs) > 1:
    lines.append(f"The pattern fires across {len(refs)} distinct verses.")
```

---

### F-F4F5-003 — P3 — Redundant verse count in multi-verse note (< cap case)

**File:** `src/nlp/explainer.py`, lines 107–120 (`_summary_prose`)
**Severity:** P3 — worth-doing-soon

**What's wrong:**

For `n > 1` and `len(refs) <= _VERSE_LIST_CAP` (e.g. 2 refs), `_verse_list_clause` returns `"across 2 verses (Rom 1:1, Rom 1:2)"`. Line 1 thus reads `"appears 2 times in the corpus, across 2 verses (Rom 1:1, Rom 1:2)."`. Line 2 then appends `"The pattern fires across 2 distinct verses."` — repeating the verse count already stated in line 1.

Observed output:
```
The pattern "faith" appears 2 times in the corpus, across 2 verses (Rom 1:1, Rom 1:2).
The pattern fires across 2 distinct verses.
```

**Suggested fix:** Suppress line 2 when `len(refs) <= _VERSE_LIST_CAP` (the verse list is already enumerated inline):

```python
elif n > 1 and len(refs) > 1:
    if len(refs) > _VERSE_LIST_CAP:  # verse list was truncated; reiterate count
        lines.append(f"The pattern fires across {len(refs)} distinct verses.")
    # else: refs already listed in full in line 1; no need to restate count
```

---

### F-F4F5-004 — P3 — Missing test for `variant` match_type in per-candidate prose

**File:** `tests/unit/test_explainer.py`
**Severity:** P3 — worth-doing-soon

**What's wrong:**

`_per_candidate_prose` interpolates `candidate.match_type` into the output string (`"Match type: variant."`). The test suite exercises `"exact"` and `"conceptual"` (via the flagship fixture and model tests) but never exercises `"variant"` through the explainer. Since `match_type` is a pass-through from `MatchCandidate`, there's no real risk of a fabrication bug here — but the path is unexercised and a typo in the branch (if one were added) would go undetected.

**Suggested fix:** Add one test in `TestExplainFlagship` or a new `TestMatchTypeVariant` that builds a candidate with `match_type="variant"` and asserts `"variant"` appears in the result's `explanation`.

---

### F-F4F5-005 — info — `ctx.observed_count` vs `len(candidates)` divergence not detected

**File:** `src/nlp/explainer.py`, `explain()` function
**Severity:** info

**What's wrong:**

`_summary_prose` uses `n = len(candidates)` for the match-count prose in line 1 (`"appears N times"`), but uses `ctx.observed_count` when passing to `_format_alt_orderings_phrase` for the comparative note in line 3. These are two different sources for what should be the same number. If the caller supplies a `Contextualization` where `observed_count` differs from `len(candidates)` (e.g., a stale or incorrectly constructed ctx), the summary will internally contradict itself: `"appears 0 times... fires more often (5 vs. 3)"`.

This is a caller-contract responsibility, not a bug in the explainer. The corpus-is-ground-truth charter (DEC-024) requires that `observed_count` in `Contextualization` be derived from the same retrieval pass that produced `candidates`. The explainer has no way to enforce this without re-executing the retrieval.

**Recommendation:** Add a docstring note to `explain()` stating the caller contract explicitly, so future integration points know to propagate the same retrieval count into both fields. No code change required.

---

### F-F4F5-006 — info — `_summary_prose` maximum line count is 5 but spec says 6

**File:** `src/nlp/explainer.py`, `_summary_prose`; `tests/unit/test_explainer.py`, `test_summary_at_most_six_lines`
**Severity:** info

**What's wrong:**

The canonical spec says `<= 6 lines`. The test asserts `<= 6`. The actual maximum achievable by the current implementation is 5 lines (1 match-count + 1 singularity/multi-verse + 1 alt-ordering + 1 baseline + 1 capped qualifier). The test is passing and the spec is met, but the test tolerance is 1 line looser than the implementation's actual cap. If a sixth line were accidentally introduced, the test would still pass.

**Recommendation:** Either tighten the test to `<= 5` to match the current implementation, or leave it at `<= 6` as a forward buffer if a sixth line category is anticipated. This is a spec-tolerance call, not a correctness issue.

---

### F-F4F5-007 — info — `_format_baselines_phrase` with empty `resolved_lemmas` silently drops the lemma list

**File:** `src/nlp/explainer.py`, `_format_baselines_phrase` (lines 170–179)
**Severity:** info

**What's wrong:**

When `nb.resolved_lemmas == []`, `_truncate_lemmas([])` returns `""`, which is falsy. The condition `if lemmas_display and ...` falls to the else branch, producing `"faith at 0"` (no lemma list rendered). This is correct behavior — there are no lemmas to display. However, a concept node with zero resolved lemmas is a pathological state (the executor would have raised `ConceptNotMapped` before any result was produced). The "silent drop" won't be misleading in practice, but it is untested.

**Recommendation:** No code change required. This path will never be reached on a successfully executed plan. Noted for completeness.

---

## Verdict Summary

| Severity | Count | IDs |
|----------|-------|-----|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 1 | F-F4F5-001 |
| P3 | 4 | F-F4F5-002, F-F4F5-003, F-F4F5-004, + (see note) |
| info | 3 | F-F4F5-005, F-F4F5-006, F-F4F5-007 |

> Note: P3 count above is 3 numbered findings (002, 003, 004) since 005/006/007 are info. Total P3 = 3.

**Verdict: `minor-fixes-recommended`**

The checkpoint is shippable. P2 finding (F-F4F5-001) must close before slice-close: three test additions covering InverseExpr plan label, `nl_source` round-trip, and `text_display` content. P3 findings are prose-quality improvements that do not affect grounding correctness. DEC-061 is fully honored; the corpus-is-ground-truth charter (DEC-024) is operationalized correctly — no fabricated claims found.
