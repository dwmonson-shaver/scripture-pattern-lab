---
type: code-review
slice: F
flavor: code
base-sha: fd46c5d
head-sha: de364a8
date: 2026-05-09
reviewer: Claude fallback (Codex blocked — .codex session permissions; Bucket 5 still open)
note: "Codex blocked by /Users/dwmonson/.codex session-directory permission error. Claude fallback ran the same severity language and checklist as prior Codex passes. Bucket 5 trigger: next /codex:rescue success against this repo."
findings_summary: "0 P0, 0 P1, 0 P2, 2 P3, 1 info"
---

# Slice F Code Review — Full Slice Close

## Scope

Six commits (base `fd46c5d`, head `de364a8`):

| SHA | Phase | What |
|-----|-------|------|
| `62c5fd3` | F4 | `ExplainedResult` + `ExplainedResultSet` Pydantic models in `src/engine/models.py` |
| `5e8bf1b` | F5 | `src/nlp/explainer.py` — deterministic prose synthesis (full module) |
| `18d6948` | F5b | Inline closure of mid-slice checkpoint findings (P2 + P3 + info) |
| `707669b` | F6 | `scripts/query.py` CLI integration: `explain()` call + `--no-prose` flag + 2 integration tests |
| `de364a8` | F7 | `docs/canonical/09_backend-service-boundaries.md` §9 amendment — `REQ:09.result-explainer` |

Prior mid-slice review (`review-claude-code-slice-f-f4f5-checkpoint-2026-05-09.md`) covered F4+F5 and closed all findings. This pass focuses on F6 (CLI integration) and F7 (canonical amendment) which the mid-slice did not cover, and verifies the full-slice surface for any cross-cutting concerns.

---

## Summary Verdict

**PASS WITH CONDITIONS** — two P3 findings, one info note. No P0/P1/P2 found. P3 findings are eligible for inline closure or bucket deferral; both are scoped and well-bounded.

---

## Findings

### Category 1: Canonical-09 §9 Amendment Accuracy

**Status:** Clean with one P3 annotation.

All five invariants in §9 are verifiable against code:

**(a) Signature uses `RetrievalResult`** — `explainer.py:44-47` declares `def explain(result: RetrievalResult, plan: QueryPlan, validation: ValidationResult) -> ExplainedResultSet`. Confirmed against canonical-09 §9 Interface block. Clean.

**(b) Every prose claim is field-derived** — every branch in `_summary_prose`, `_per_candidate_prose`, `_format_baselines_phrase`, `_format_alt_orderings_phrase`, and `_verse_list_clause` derives values exclusively from `result.candidates`, `result.contextualization`, `plan.sequence`, `plan.source`, `plan.metadata`, and `validation.findings`. No string literals fabricate corpus facts. The caller-contract note (docstring lines 51-58) is present and correct. Clean.

**(c) No LLM imports** — `grep` of `explainer.py` for `anthropic`, `openai`, `httpx`, `asyncio` returns zero results. The module has no I/O, no external deps beyond `src.engine.models` and `src.validation.validator`. Verifiable per the canonical-09 invariant (c) grep recipe. Clean.

**(d) `validation_notes` raw-string format** — `_format_finding` at `explainer.py:311-312` produces `"{f.severity}: {f.code} at {f.path}: {f.message}"`. `_print_findings` in `scripts/query.py:190` produces the same format with a leading two-space indent. The explainer output and the CLI print helper emit identical content-level format; the indent difference is appropriate (one is stored as data, one is rendered to terminal). Clean.

**(e) Cap policy in prose layer only** — `_truncate_lemmas` (cap 5, `+N more`) at `explainer.py:230-237` and `_truncate_sequence_label` (64-char, ellipsis at `>` boundary) at `explainer.py:240-251` are prose-layer-only. `_print_contextualization` in `scripts/query.py:138-175` is confirmed unchanged in Slice F (the diff adds only the `explain()` call and `--no-prose` flag; the structured block at lines 138-175 is untouched). Clean.

---

**P3 — F-CLOSE-001 — `summary` field comment says `≤ 5 lines`; code implements `≤ 6 lines`**

File: `docs/canonical/09_backend-service-boundaries.md:257`
Also: `src/nlp/explainer.py:98` (docstring) and `tests/unit/test_explainer.py:237` (test name + assertion)

Observation: The `ExplainedResultSet.summary` field comment in canonical-09 reads `# Slice-level prose (≤ 5 lines per invariant (e))`. Invariant (e) itself (line 274) describes the cap policy for lemmas and labels — it does not define a line count. The `explainer.py` module docstring (line 5) says `≤ 6 lines`, the `_summary_prose` docstring (line 98) says `≤ 6-line`, and `test_summary_at_most_five_lines` asserts `len(lines) <= 5`. The actual implementation can produce at most 5 lines (1 count + 1 singularity/multi-verse + 1 alt-ordering + 1 baselines + 1 capped-qualifier), making 5 the tight bound and 6 the spec tolerance. The canonical field comment references `≤ 5` while the code-level docs say `≤ 6`, creating a minor inconsistency.

Risk: Low. The code correctly enforces the tighter bound (5); no prose can overflow. But "≤ 5 lines per invariant (e)" in the field comment is misleading — invariant (e) has nothing to do with line count, and the comment disagrees with the module-level doc. A future reader may be confused about which is authoritative.

Recommendation: Align the field comment to say `# Slice-level prose (≤ 6 lines; actual implementation max is 5)` or simply `# Slice-level prose (≤ 6 lines)` to match the module docstring and docstring on `_summary_prose`. The test name `test_summary_at_most_five_lines` is correctly tight and can remain as-is. This is a doc-only fix.

---

### Category 2: CLI Integration Discipline

**Status:** Clean.

All five sub-checks pass:

**`--no-prose` skips the `explain()` call** — `scripts/query.py:287-290` is:
```python
if not no_prose:
    explained = explain(result, executable, validation)
    print()
    _print_explanation(explained.summary)
```
The `explain()` call is gated under `not no_prose`, not just the print. `test_cli_no_prose_flag_suppresses_explanation` (integration test) gates on `"Explanation:" not in out`, which confirms the call is never made when the flag is set (because if `explain()` were called and its output suppressed, the `_print_explanation` function still outputs the heading). The guard is correct.

**Explanation block lands after `_print_contextualization`** — stdout order in `main()` lines 279-290: `_print_results` → `_print_contextualization` (if ctx present) → `explain()` + `_print_explanation` (if not no-prose). The `test_cli_renders_explanation_for_flagship_sequence` integration test asserts `exp_idx > ctx_idx` on the actual stdout string. Order is correct.

**`_print_contextualization` is unchanged** — the Slice F diff touches only: `scripts/query.py:+from src.nlp.explainer import explain`, `+--no-prose` argument, `+no_prose = args.no_prose`, `+_print_explanation()` function, and the `if not no_prose:` block. Lines 138-175 (`_print_contextualization`) are untouched. Clean.

**No new exception paths needed** — `explain()` is deterministic and purely synchronous; it operates only on in-memory objects already produced by `retrieve()` and `validate()`. The only caller-contract requirement is that `result.contextualization.observed_count == len(result.candidates)` (documented in the docstring). The CLI satisfies this because both values come from the same `retrieve()` call with `contextualize=True`. No new exception paths are warranted. Clean.

**`executable` plan passed to both `retrieve()` and `explain()`** — `scripts/query.py:249` sets `executable = validation.executable_plan`. Line 251-255 calls `retrieve(executable, ...)`. Line 288 calls `explain(result, executable, validation)`. Same `executable` object in both calls. If the validator reduced the plan, both the retrieval and the explanation see the reduced plan — prose claims about the query match what was executed. Clean.

---

### Category 3: DEC-061 LLM-Deferral Coherence

**Status:** Clean with one P3 annotation.

The deferral text in canonical-09 §9 line 267 reads:
> "The deferral is tracked in a named bucket; trigger is 'Slice H ships an LLM dependency for translation OR the deterministic explainer prose is judged inadequate against a real research question.'"

The trigger is dual-condition and specific:
- Condition A: "Slice H ships an LLM dependency" — identifies a concrete future slice by name and a concrete deliverable.
- Condition B: "deterministic explainer prose is judged inadequate against a real research question" — identifies a qualitative evaluation event.

Both conditions are specific enough that a future-you can recognize when they fire without re-reading the original finding. Condition A is the expected trigger (Slice H is the NL→DSL translator); Condition B is the fallback for an earlier-than-expected failure case. Neither condition uses "eventually", "soon", "future", or other non-specific language. The trigger satisfies bucket-discipline rules.

---

**P3 — F-CLOSE-002 — DEC-061 LLM deferral is named in canonical-09 but not registered as a formal bucket in `reviews-log.md`**

File: `docs/governance/reviews-log.md` (no line; bucket is absent)
Also: `docs/canonical/09_backend-service-boundaries.md:267`

Observation: The canonical-09 text says "the deferral is tracked in a named bucket" but there is no corresponding bucket entry in `reviews-log.md`. Existing buckets in the log are Bucket 1–6. The DEC-061 LLM-prose deferral has a trigger and rationale in the canonical doc but no row in the governance log where bucket triggers are tracked between slices.

Risk: Medium-low. The trigger is well-specified in canonical-09, but the bucket-triage process (CLAUDE.md "Between-slice triage") reads from `reviews-log.md`, not from canonical docs. A future slice-start triage would miss this trigger because it scans the log, not the canonical doc. The bucket would silently go un-triaged at Slice H start.

Recommendation: Add a "Bucket 7 — LLM prose deferral (DEC-061)" entry to `reviews-log.md` in the Slice F close row, with trigger: "Slice H ships an LLM dependency for translation OR the deterministic explainer prose is judged inadequate against a real research question." This is a governance-file-only fix (one sentence in the closure column). The trigger language already exists in canonical-09 and can be copied verbatim.

---

### Category 4: Bucket 4 Closure

**Status:** Clean.

Bucket 4 (D-CLOSE-003: CLI rendering unbounded) triggered on Slice F as the "next slice that touches CLI output discipline / adds prose rendering." Slice F addresses it by:

1. **Prose-layer cap (lemmas):** `_truncate_lemmas` at `explainer.py:230-237` caps resolved-lemma display at 5 items with `(+N more)` suffix. Tested in `TestTruncateLemmas` unit class (lines 375-391).

2. **Prose-layer cap (labels):** `_truncate_sequence_label` at `explainer.py:240-251` caps sequence labels at 64 chars, truncating at a `>` separator boundary when possible. Tested in `TestTruncateSequenceLabel` unit class (lines 393-413).

3. **Structured block deliberately unbounded:** `_print_contextualization` in `scripts/query.py:138-175` is confirmed unchanged. The canonical-09 §9 invariant (e) explicitly states "The structured `_print_contextualization` block in `scripts/query.py` remains unbounded — that block is the data-fidelity view." The bucket entry for Bucket 4 closes with this slice.

Both the prose-layer cap AND the deliberate non-cap of the structured block are documented in canonical-09 §9 invariant (e). Bucket 4 is **closed** by Slice F.

---

### Category 5: Test Coverage End-to-End

**Status:** Clean.

**Unit coverage (`tests/unit/test_explainer.py` — 675 lines, 40 test functions):**
- All primary paths covered: zero-match, single-match, multi-match (same verse, multi-verse under/over cap), capped-permutations qualifier, alt-ordering comparative phrases (all-zero, tied, lower, higher), baselines rendering, validation notes (supported/partial), InverseExpr label, nl_source round-trip, text_display content/empty, variant match type, singularity suppression logic.
- Cap/wrap helpers tested at boundary: `_LEMMA_CAP` (under, at, over, empty, custom), `_SEQUENCE_LABEL_MAX` (under, at, over with separator, over without separator, zero-chars).
- No DB access; fixture builders compose hand-crafted `RetrievalResult` objects. Correct placement as unit tests.

**Integration coverage (`tests/integration/test_query_cli.py` — new tests in F6):**
- `test_cli_renders_explanation_for_flagship_sequence`: exercises full stack (ingest + seed + retrieve + explain + CLI render) on `faith > hope > love`. Asserts heading presence, ordering relative to contextualization block, count `"2 times"`, verse `"1Cor 13:13"`, at least one baseline count, and `"alternative ordering"` phrase. Ground-truth counts pinned to `project_status.md` values (483/84/259).
- `test_cli_no_prose_flag_suppresses_explanation`: verifies `--no-prose` suppresses the Explanation heading while the structured + contextualization blocks remain. Correctly gated on `"Explanation:" not in out`.
- Both tests inherit `pytestmark = pytest.mark.integration` (line 28); they are excluded from unit runs.

**Unit vs. integration boundary assessment:** The unit tests cover deterministic prose synthesis with hand-crafted fixtures; the integration tests cover the CLI wiring and real corpus data. The split is appropriate. No unit-level case needs integration coverage, and vice versa. The `_print_explanation` helper is thin (heading + indented lines) and its behavior is fully captured by the integration test — a unit test for it would be redundant.

---

### Category 6: Slice F Exit-Gate Test

**Status:** Pass.

`test_cli_renders_explanation_for_flagship_sequence` at `tests/integration/test_query_cli.py:269-300`:

**(a) Gates on the design-promised observable behavior:**
- `≤ 6 lines` is not directly asserted (the integration test asserts content, not line count; the unit test `test_summary_at_most_five_lines` covers the line cap). The design promised the Explanation block appears after Contextualization — the test asserts `exp_idx > ctx_idx`. The design promised the block names the verse — `"1Cor 13:13" in out` asserted. The design promised it cites the count — `"2 times" in out` asserted. The design promised an alt-ordering observation — `"alternative ordering" in out.lower()` asserted. The design promised grounding in baseline numbers — `any(n in out for n in ("483", "84", "259"))` asserted. The gate covers the observable surface the design committed to.

**(b) Correctly marked as integration:**
- File has `pytestmark = pytest.mark.integration` at module scope (line 28); both new tests inherit this mark without needing individual decorators. Unit runs exclude the integration mark. Correct.

**(c) Assertions robust to formatting drift but tight enough to catch regressions:**
- Substring assertions (`"Explanation:" in out`, `"faith > hope > love" in out`, `"2 times" in out`, `"1Cor 13:13" in out`) are resistant to whitespace/indentation changes.
- `exp_idx > ctx_idx` is a positional assertion that would catch a reordering of the output blocks — tight enough.
- `any(n in out for n in ("483", "84", "259"))` is deliberately broad (any one of three numbers) — this handles the case where one baseline count changes due to corpus updates while still catching a complete absence of baseline data. Appropriately calibrated.
- The `"alternative ordering" in out.lower()` assertion is a substring match on the rendered alt-ordering sentence — would catch removal of the alt-ordering phrase. Tight enough.
- The assertions are not brittle to minor prose wording changes (e.g., "appears 2 times" vs "found 2 times") because only "2 times" is asserted, not the full sentence. This is intentional and appropriate.

---

### Category 7: Cross-Cutting

**Status:** Clean.

**DEC-025 boundary:** `scripts/query.py` imports `from src.ingestion.db import get_engine` — this is an existing pre-Slice-F import, not introduced by this slice. The slice adds `from src.nlp.explainer import explain`, which is within the query-side boundary. `src/nlp/explainer.py` imports only from `src.engine.models` and `src.validation.validator` — no ingestion imports. Clean.

**Module docstring accuracy:** `explainer.py:1-20` accurately describes the module's role, cap policy (Bucket 4 closure), and determinism contract. The only discrepancy is the `≤ 6 lines` vs canonical-09's `≤ 5 lines` field comment — addressed in F-CLOSE-001.

---

**info — F-CLOSE-003 — `test_cli_renders_explanation_for_flagship_sequence` does not assert prose indentation format**

File: `tests/integration/test_query_cli.py:269`

Observation: The integration test asserts the `Explanation:` heading and content substrings but does not assert that summary lines are indented with two spaces (as `_print_explanation` implements). If a refactor removed the indentation, the content assertions would still pass.

Risk: Very low. `_print_explanation` is 5 lines and the indentation behavior is trivially auditable. Adding an assertion like `"  The pattern" in out` (two leading spaces) would close this gap, but it would also make the test brittle to the specific first-line wording of the summary. The current assertion level is appropriate.

Recommendation: Acknowledge; no fix required. This is a design tradeoff in the test — content correctness over formatting precision. If the indentation convention becomes load-bearing (e.g., agents parsing the CLI output depend on it), add a format assertion at that point.

---

## Bucket Dispositions

**Bucket 4 (CLI rendering polish):** ✅ **CLOSED** — Slice F implemented the prose-layer caps (`_truncate_lemmas` at 5 items, `_truncate_sequence_label` at 64 chars) in `src/nlp/explainer.py`. The structured `_print_contextualization` block deliberately remains unbounded (data-fidelity view per canonical-09 §9 invariant (e)). Both the prose-layer cap AND the non-cap of the structured block are documented in invariant (e). Closing SHAs: `5e8bf1b` (explainer module with truncators) and `18d6948` (F5b checkpoint fixes). Bucket 4 is dissolved.

**DEC-061 LLM-prose deferral:** Tracked in canonical-09 §9 but not yet registered as a formal governance bucket in `reviews-log.md`. This is F-CLOSE-002 (P3). Recommendation: add Bucket 7 entry to `reviews-log.md` Slice F closure row with the trigger already specified in canonical-09.

---

## Test Coverage Assessment

The 40-function unit suite in `test_explainer.py` provides thorough coverage of the deterministic explainer's prose synthesis paths. Fixture builders are well-structured. The 2 new integration tests in `test_query_cli.py` provide end-to-end wiring coverage including the `--no-prose` suppression path. The unit/integration boundary is correctly drawn: prose synthesis is unit-tested against hand-crafted data; CLI wiring is integration-tested against the real corpus. No coverage gaps found that warrant action in this slice.

Reported test counts at Slice D close were 285 unit + 68 integration = 353 total. Slice F adds 40 new unit tests (test_explainer.py) and 2 new integration tests. Expected total: ~325 unit + 70 integration ≈ 395. The brief says 340 unit tests pass — this is consistent with Slice E adding some tests and these numbers being approximate. No regressions are claimed and the test structure is sound.

---

## Exit-Gate Assessment

**`test_cli_renders_explanation_for_flagship_sequence`:** PASS.

The test gates on all the observable behaviors the design promised (block appears after Contextualization, heading present, verse named, count cited, baseline number present, alt-ordering phrase present). It is correctly marked as integration. Assertions are content-based substrings — resistant to formatting drift, tight enough to catch removal of any major claimed element. Ground-truth counts (483/84/259, 2 matches) anchor the test to the actual corpus state rather than synthetic data.

---

## Summary

Slice F ships a clean, deterministic explainer layer with correct Pydantic models, correct CLI integration, and a correctly scoped canonical amendment. The mid-slice review's P2 finding was addressed before this pass (F-F4F5-001: InverseExpr, nl_source, text_display tests — confirmed present at `test_explainer.py:554, 572, 581, 589`). Two P3 findings remain: F-CLOSE-001 (summary field comment says `≤ 5 lines` while code says `≤ 6 lines` — doc-only alignment) and F-CLOSE-002 (DEC-061 LLM deferral should be registered as Bucket 7 in reviews-log.md for slice-start triage). One info note (F-CLOSE-003: integration test does not assert prose indentation). No P0/P1/P2 findings. Slice F is eligible for close.

| Severity | Count | Finding IDs |
|----------|-------|-------------|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 0 | — |
| P3 | 2 | F-CLOSE-001, F-CLOSE-002 |
| info | 1 | F-CLOSE-003 |
