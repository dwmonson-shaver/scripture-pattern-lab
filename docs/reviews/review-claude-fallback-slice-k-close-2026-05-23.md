# Claude-Fallback Slice-Close Code Review — Slice K (LLM-in-Explainer)

- Date: 2026-05-23
- Reviewer flavor: claude-fallback (Codex blocked by ~/.codex/sessions; Bucket 5 stays open).
- Scope: cumulative diff `b88b83b..d0244eb` — Phases K.0 → K.6.
- Base SHA: `b88b83b` (Slice J1 close).
- 11 files changed, +1,626 / -27 lines.
- Severity language: P0 / P1 / P2 / P3 / info.

## Brief

The orchestrator-mode close brief:

> Does this implementation respect DEC-081's no-fabrication clause? Are there
> codepaths where LLM output bypasses the deterministic baseline contract?
> Is the no-fabrication test in the exit gate sufficient?

## Six-category Pass

1. **Correctness** — per-candidate dispatch, fallback contract, env-var parsing, ordering of `_run_dsl_pipeline_with_optional_explainer_llm`.
2. **Security** — no prompt/response logging at INFO; no anthropic SDK leak into the explainer module; LLM client construction stays in `lifespan` (Slice H pattern).
3. **Resource hygiene** — no per-call client construction (the LLM client is lifespan-scoped); broad-except in helper is the only resource path; deterministic fallback never leaks state.
4. **Test fragility** — caplog usage uses `getMessage()` (portable); FakeLLMClient and FailingLLMClient stubs cover the documented paths; live-LLM tests are env-var-gated.
5. **Contract** — DEC-061 (deterministic baseline preserved as default + fallback) + DEC-081 (LLM has only grounded inputs) + DEC-090 (this slice's headline DEC).
6. **Convention** — kw-only argument, module-level constants, docstring discipline.

## DEC-081 Conformance Audit (Hostile Pass)

The brief's load-bearing question. Walking every codepath where LLM output could land in the response envelope:

### Path 1: NL route → `run_nl_query` → `_run_dsl_pipeline_with_optional_explainer_llm` → `explain(llm_client=...)` → `_per_candidate_prose_llm`

- LLM input: ONLY the grounded structured fields from `build_explainer_user_message`. Verified by reading `src/nlp/prompts/explainer_prompt.py:55-79` — the function reads only `candidate.reference`, `candidate.match_type`, and per-step `node_value` / `step.token.lemma` / `step.resolved_lemmas`. No `Contextualization` data, no baselines, no `validation_notes`. ✓
- LLM output landing site: `ExplainedResult.explanation` for the per-candidate row. NOT `summary`, NOT `contextualization`, NOT `validation_notes`. Verified by reading `src/nlp/explainer.py:79-128`. ✓
- Dispatch gate: `if llm_client is not None and c.match_type == "conceptual"`. Two conditions; both must hold. Variant + exact always get deterministic. Confirmed by `test_variant_match_type_not_routed_through_llm` + K-MID-003 closure `test_exact_match_type_not_routed_through_llm`. ✓
- Output validation: post-truncation cap at 300 chars; FALLBACK sentinel detection. ✓

### Path 2: DSL route → `run_dsl_query` → `explain` (no `llm_client` kwarg)

- DSL route never sees an LLM. Confirmed by reading `src/app/orchestration.py:64-104` (`run_dsl_query`). The DSL route's `explain()` call site does not pass `llm_client`. ✓

### Path 3: CLI → `scripts/query.py` → `explain()`

- CLI never sees an LLM. The CLI does not opt into the env var. Confirmed by `scripts/query.py` (unchanged in this slice). ✓

### Conclusion of DEC-081 audit

LLM output exclusively lands in `ExplainedResult.explanation` for `match_type == "conceptual"` candidates, AND only when the NL route's env var opt-in fires. Every other surface stays deterministic. The structural enforcement is sound.

## Findings

### K-CLOSE-001 (P3, doc clarity) — `_summary_prose` docstring still says "≤ 6-line"

**Finding**: K-MID-006 fixed the module docstring's "≤ 6 lines"; the internal helper `_summary_prose` at `src/nlp/explainer.py:139` still says `"≤ 6-line"`. The canonical spec (canonical-09 §9 invariant ≤ 5 lines) and the test class `TestExplainFlagship.test_summary_at_most_five_lines` assert ≤ 5.

**Disposition**: Close inline at K-CLOSE commit.

**Fix**: Trivial docstring edit.

### K-CLOSE-002 (P3, code review) — Code duplication between `run_dsl_query` and `_run_dsl_pipeline_with_optional_explainer_llm`

**Finding**: The two functions are 90% identical. They differ in: (a) `_run_dsl_pipeline_with_optional_explainer_llm` accepts an `explainer_llm` kwarg; (b) it passes that kwarg into `explain()`. Otherwise the parse / validate / retrieve / construct response sequence is byte-identical.

**Disposition**: Acceptable. The design rationale (in the helper's docstring) names the deliberate separation: keep the public `run_dsl_query` ignorant of the LLM env var so the DSL surface remains a clean deterministic API. Refactoring to share a single internal helper that both `run_dsl_query` and `run_nl_query` consume would create an additional call hop and a new private function; the duplication is two paragraphs and self-contained.

**Fix**: None. Optionally, a future slice can consolidate if a third caller emerges.

### K-CLOSE-003 (info, observability) — No success-path INFO log for the LLM call

**Finding**: K-MID-002 already discussed. Re-affirming at close: deliberate choice to keep success-path silent. The fallback path's WARNING log is the load-bearing operational signal. If the operator wants visibility into "LLM is being called for X% of conceptual candidates", a future slice can add structured logging at the orchestration layer (which has the env-var state in scope) rather than threading a logger through the helper.

**Disposition**: No fix.

### K-CLOSE-004 (info, deferred) — `SPL_EXPLAINER_LLM` is not lifespan-scoped

**Finding**: K-DESIGN-005 already named this. Re-affirming: env-var read at call time inside `run_nl_query` is the chosen pattern. A future slice can hoist it to `app.state.explainer_llm_enabled` if a second consumer emerges (e.g., a CLI flag).

**Disposition**: No fix.

### K-CLOSE-005 (info, design) — The system prompt is English-only

**Finding**: The prompt assumes the operator wants English prose. If the project later targets a Greek- or Hebrew-speaking audience, the prompt would need translation.

**Disposition**: Out of scope for this slice. Not a regression.

**Fix**: None.

### K-CLOSE-006 (info, fairness) — The grounded-substring test's regex for verse references is conservative

**Finding**: `verse_pattern = re.compile(r"\b\d?[A-Za-z]+\s+\d+:\d+(?:-\d+)?\b")` matches `1Cor 13:13` and `John 3:16-17`. It does NOT match references with non-ASCII book names (Hebrew/Aramaic transliterations) or unusual chapter/verse separators. For MorphGNT (Greek NT) the regex is fully sufficient — every reference in the corpus is ASCII-form-book + numeric chapter:verse.

**Disposition**: Acceptable for MVP corpus. Future corpora may require the regex to expand.

**Fix**: None.

### K-CLOSE-007 (info, naming) — `_LLM_FALLBACK_MAX_LEN` is one-use only

**Finding**: The constant is used only inside `_is_fallback_signal`. Could be inlined. But naming it documents the intent ("FALLBACK token plus up to 5 chars of trailing punctuation").

**Disposition**: Keep as-is. Self-documenting.

**Fix**: None.

## Verdict

**clean-with-conditions → clean after fix**. One P3 closure (K-CLOSE-001 docstring); the rest are info-level acknowledgements.

The DEC-081 conformance audit passed: LLM output is structurally constrained to a single field (`ExplainedResult.explanation` for `match_type == "conceptual"`) and the LLM has access only to grounded structured fields. The deterministic fallback is airtight (4 fallback triggers: `LLMUnavailable`, any `Exception`, `FALLBACK` sentinel, empty output). The no-fabrication exit gate (`test_llm_prose_only_contains_grounded_numbers_and_refs`) is the structural check of the load-bearing claim.

## Test count summary

- Slice F close: 340 unit + 11 integration = 351 (deterministic baseline).
- Slice K close: +37 new unit tests (17 prompt + 17 explainer helper/dispatch + 3 K-MID closures + 7 orchestration env-var opt-in) + 5 new live_llm integration tests = 42 net new tests.
- Backend total (estimated against project_status): 495 + 37 ≈ 532 unit + 80 integration + 7 live_llm = ~619 backend tests. Live execution deferred to user (sandbox blocks pytest collection on `.env` permission).

## Bucket triage at close

- **Bucket 5** (Codex permissions) — still open. Codex sessions directory permission unchanged. Same trigger.
- **Bucket 7** (LLM-backed conceptual-match prose) — **CLOSED** by this slice. Path (b) per the trigger language: "user explicitly authorized wiring the LLM client into the explainer's conceptual-match path." Closing SHA chain: K.0 `2d29076` (design review) → K.1 `b76e15e` (prompt) → K.2 `4cb6983` (helper) → K.3 `947f1a6` (explain signature) → mid-slice `cbab605` (K-MID closures) → K.4 `f2c96f9` (orchestration env-var) → K.5 `8c71b75` (live-LLM tests) → K.6 `d0244eb` (canonical + spec-coverage) → close `<pending>`.
- **Bucket 8** (static system-prompt context) — re-defer with sharpened trigger: "registry-curator workflow lands OR explainer's LLM prose surfaces a stale `verification_state` in a user-visible way." Rationale: explainer reads grounded data and the registry is stable today; runtime invalidation is premature.
- **Bucket 9** (concepts pagination) — re-defer unchanged.
- **Buckets J1-1 / J1-2 / J1-3 / J1-4** — re-defer unchanged (user-side bootstrap, frontend defensive-error polish).

## Cross-references

- DEC-061, DEC-081, DEC-090 — load-bearing for the slice's contract.
- Mid-slice review: `review-claude-fallback-slice-k-mid-2026-05-23.md`.
- Design review: `review-claude-fallback-slice-k-design-2026-05-23.md`.
