---
type: review
flavor: codex-code
date: 2026-05-25
slice: L (proximity-window broadening)
scope: cumulative slice diff e18c723..60a3239 (6 phase commits)
verdict: needs-attention → clean after closures
reviewer: Codex (codex-cli 0.125.0, gpt-5 default model)
---

# Codex Review — Slice L Close

## Scope

Six phase commits land Slice L:

- `c814d79` Phase 1: ScopeUnit discriminated union + `within:window(N)` parser + `~` gap
- `51d0c5d` Phase 2: cross-verse window execution + `~` activation
- `0ca1ee3` Phase 3: ProximityInfo envelope populated on window queries
- `2720675` Phase 4: capability surface + validator window rules
- `a8edce6` Phase 5: NL→DSL clarification path + proximity cookbook vocabulary
- `60a3239` Phase 6: explainer prose + canonical-doc edits + ExplainedResult.proximity

Cumulative diff: 25 files, +1649 / -191 (12 source files, 11 tests, 3 canonical docs, 1 cookbook).

## Codex Invocation

```
codex review --base e18c723
```

Codex CLI 0.125.0, logged-in via ChatGPT. Review duration ~6 minutes. Codex was the intended reviewer (Bucket 5's "re-run Codex once .codex permissions are fixed" trigger fired on this slice; permissions verified pre-review).

## Findings

| ID | Severity | Path | Summary | Closure SHA |
|----|----------|------|---------|-------------|
| L-CLOSE-001 | P1 | `src/validation/validator.py:381-386` | `WINDOW_EXCEEDS_MAX` error fell through `_reduce_plan()` and produced a `partial` plan that the executor would happily run — silently breaching the advertised window_max_tokens=50 ceiling. | `6453975` |
| L-CLOSE-002 | P2 | `src/engine/executor.py:543-548` | Windowed `~` used a forward-only window `[base.gp, base.gp + n]`, making `lemma:ἀγάπη ~ lemma:πίστις` order-dependent when πίστις preceded ἀγάπη. Fix: COOCCURRENCE uses symmetric `[base.gp - n, base.gp + n]`. | `6453975` |
| L-CLOSE-003 | P2 | `src/engine/executor.py:717-721` | `A ~ B ~ A` could satisfy by reusing the first A's token (identity check only compared against the immediate predecessor). Fix: chain extension rejects candidates whose `id` is already in the chain. | `6453975` |
| L-CLOSE-004 | P2 | `src/nlp/translator.py:77` | `TranslationNeedsClarification.suggested_windows = [20, 50, 100]` included 100, which exceeds the advertised `window_max_tokens=50` ceiling — the user's choice would produce a follow-up DSL the validator rejects with WINDOW_EXCEEDS_MAX. Fix: default to `[10, 20, 50]`. | `6453975` |
| L-CLOSE-005 | P2 | `src/engine/executor.py:616` | `span_tokens = gp_hi - gp_lo` where `gp_hi = chain[-1].gp` underreports the matched span for mixed ordered/unordered queries (e.g. `A > B ~ C` where C lands between A and B). Fix: compute from `max(chain.gp) - min(chain.gp)`. | `6453975` |

No P0 findings. No P3 / info findings.

## Verdict

**Needs-attention before fixes → clean after.** All P1+P2 findings closed inline at `6453975` with corresponding unit tests. Slice L is ready to close.

## Reviewer Notes

Codex spent the first half of the session exploring the executor and parser before producing the findings list; the findings themselves are factual and well-anchored (each one cites exact line numbers). The P1 has the highest user-visible impact: without it the engine silently runs queries beyond the advertised capability. The two unordered-semantics fixes (#2, #3) are real correctness gaps that would have produced confusing results for users running `~` queries.

The reviewer correctly did NOT flag the suggested_windows / window_max_tokens mismatch as P1 — it's a contract drift the next iteration's user-feedback would catch, but it doesn't corrupt corpus-grounded results. P2 is the right severity.

L-CLOSE-005 (span_tokens) is a presentation bug, not a corpus-grounding bug; user-facing prose would have under-reported the span but the underlying match was still correct. P2 is right.

## Bucket 5 Status

Codex was previously blocked on a `.codex` permission issue (Bucket 5, opened Slice E). This slice's pre-review check confirmed permissions are now fixed; Codex ran cleanly. **Bucket 5 closes here** — re-runs of Codex against this repo work without intervention. Reviews-log row updated accordingly.
