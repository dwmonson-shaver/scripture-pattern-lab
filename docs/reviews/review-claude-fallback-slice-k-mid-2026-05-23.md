# Claude-Fallback Mid-Slice Code Review — Slice K (LLM-in-Explainer)

- Date: 2026-05-23
- Reviewer flavor: claude-fallback (Codex blocked by ~/.codex/sessions; Bucket 5 open).
- Scope: cumulative diff `b88b83b..947f1a6` — Phases K.0 (review only) + K.1 + K.2 + K.3.
- Base SHA: `b88b83b` (last commit before Slice K).
- Files changed: 5 (1 review artifact + 4 source/test).
  - `docs/reviews/review-claude-fallback-slice-k-design-2026-05-23.md` (NEW, +94)
  - `src/nlp/prompts/explainer_prompt.py` (NEW, +85)
  - `src/nlp/explainer.py` (+150 / -20)
  - `tests/unit/test_explainer.py` (+292)
  - `tests/unit/test_explainer_prompt.py` (NEW, +194)
- Severity language: P0 / P1 / P2 / P3 / info.

## Brief

Before K.4 lands the env-var opt-in in the orchestrator, the mid-slice review
inspects: (a) does the helper's broad except chain leak surprising
exceptions? (b) does the system prompt's wording stand up to inspection?
(c) is the explain() branch correctly localized? (d) is the test surface
sufficient for the load-bearing contracts?

## Categories Inspected

- **Correctness**: per-candidate dispatch, fallback contract, truncation edge.
- **Security**: no prompt/response logging at INFO; no anthropic SDK leak through explainer.py.
- **Resource hygiene**: no per-call client construction; client stays injected.
- **Test fragility**: caplog usage; FakeLLMClient and FailingLLMClient stubs cover the documented paths.
- **Contract**: DEC-061 (deterministic baseline preserved) + DEC-081 (no fabrication, structural enforcement).
- **Convention**: kw-only argument, module-level constants, docstring discipline.

## Findings

### K-MID-001 (P3, contract clarity) — `_per_candidate_prose_llm` recognizes `FALLBACK` only as exact token

**Finding**: The K.2 helper checks `cleaned == _LLM_FALLBACK_TOKEN`. If the
LLM emits `"FALLBACK"` followed by a period, newline, or whitespace mismatch
not caught by `.strip()` (e.g., `"FALLBACK."` or `"FALLBACK\n"`), the cleaner
will preserve characters and the comparison fails → the helper returns the
literal `"FALLBACK."` as the LLM's prose, which then enters the result
envelope.

**Severity**: P3. The cleaner strips whitespace, so `"FALLBACK\n"` becomes
`"FALLBACK"` — caught. The `"FALLBACK."` case is the realistic gap.

**Disposition**: Close inline. Use `cleaned.upper().startswith("FALLBACK")`
with a length guard (`len(cleaned) <= len("FALLBACK") + 5`) so that
"FALLBACK." matches but a sentence like "FALLBACK is what I should do here"
does NOT match (avoids false positives on real prose that happens to start
with the token).

**Fix**: edit `_per_candidate_prose_llm` and add a unit test.

### K-MID-002 (P3, log surface) — Successful LLM-call path emits no INFO log

**Finding**: The structure outline named "single INFO log per `explain()`
call recording the path taken". K.2 only logs on fallback (WARNING level).
The successful LLM-call path is silent.

**Severity**: P3. The fallback log is the load-bearing operational signal
("the LLM is broken"); the success log was nice-to-have for visibility.

**Disposition**: Acceptable trade-off — keep the success path silent. INFO
logs at every per-candidate LLM call could fill logs in production with no
operational value (operators care about failures, not successes). The
trade-off matches the translator's pattern in `src/nlp/translator.py:73-86`
which also does not log success.

**Fix**: None. Document the choice in the structure outline's K.4 notes
(orchestration-layer logging can carry an opt-in summary log if useful in
the future).

### K-MID-003 (P2, contract test) — No test exercises the `match_type == "exact"` path against an injected LLM client

**Finding**: `TestExplainWithLLMClient.test_variant_match_type_not_routed_through_llm`
covers variant. There is no symmetric test for `match_type == "exact"`.
Today the executor never produces "exact" against the seeded conceptual
flagship — only conceptual matches surface in the integration tests — so
this isn't field-exercised. But the helper's dispatch rule has three
match_type values; only two are unit-covered.

**Severity**: P2. The dispatch logic is a single expression
`c.match_type == "conceptual"`, so the exact case is logically equivalent
to the variant case. Symmetric test coverage is still the right discipline.

**Disposition**: Close inline. Add a test
`test_exact_match_type_not_routed_through_llm` that mirrors the variant
test against `match_type="exact"`.

**Fix**: append the test to TestExplainWithLLMClient.

### K-MID-004 (P3, test fragility) — `test_llm_paraphrases_conceptual_candidates` could over-promise

**Finding**: The test asserts `for r in ers_llm.results: assert r.explanation == canned`. Both
candidates in the fixture happen to be identical (same lemmas, same ref),
so the LLM helper gets two identical inputs and emits the same canned
response twice. This passes the byte-equality test but the test doesn't
verify the LLM was called for *each* candidate independently.

**Severity**: P3. A separate test
`test_llm_client_called_once_per_conceptual_candidate` already asserts
`len(client.calls) == 2` — the per-candidate dispatch is locked. So the
contract is fully covered when both tests are read together.

**Disposition**: Acceptable. Tests are complementary.

**Fix**: None.

### K-MID-005 (P3, convention) — `logger = logging.getLogger(__name__)` placement

**Finding**: The new `logger` is declared after the `_VERSE_LIST_CAP`
constants block. Convention in the codebase (see `src/app/main.py:55`,
`src/app/orchestration.py` if it had a logger, `src/app/routes/query.py:35`)
is `logger = logging.getLogger(__name__)` immediately after the imports
block. The current placement (after constants) is unconventional.

**Severity**: P3. Cosmetic.

**Disposition**: Close inline — move the `logger` declaration to
immediately follow the imports, before the constants block.

**Fix**: trivial reorder in `src/nlp/explainer.py`.

### K-MID-006 (P3, contract clarity) — Module docstring's "≤ 5 lines" should be "≤ 5 lines (formally ≤ 6 per spec)"

**Finding**: The K.3 docstring rewrite kept the implicit "≤ 6 lines"
language from the original; the canonical spec for the summary is "≤ 5 lines
(see MVP implementation note)" per `docs/canonical/09_…:416`. Old language
in the explainer module said "≤ 6 lines" which was tightened to 5 in the
canonical spec amendment landed at Slice F close.

**Severity**: P3. Cosmetic; the module's actual cap is 5 lines (the test
class `TestExplainFlagship.test_summary_at_most_five_lines` asserts it).

**Disposition**: Close inline; tighten the docstring's "≤ 6 lines" phrase to
"≤ 5 lines".

**Fix**: small docstring edit.

### K-MID-007 (info) — `_LLM_FALLBACK_TOKEN` not exported

**Finding**: The constant is module-private. A future authoring a separate
prompt module won't see it via star-import. Acceptable for now; the token
is tied to the prompt module's wording, so co-locating it with the prompt
would be cleaner.

**Severity**: info.

**Disposition**: Acknowledge. Future slice can co-locate if a second LLM
prompt module emerges.

**Fix**: None.

### K-MID-008 (info) — Test stubs `_FakeLLMClient` / `_FailingLLMClient` duplicate the pattern from test_translator.py

**Finding**: `tests/unit/test_translator.py:24` has a `FakeLLMClient`
(unprefixed) class with similar shape. Slight duplication; could be
hoisted to a shared `tests/unit/_stubs.py` or `conftest.py`.

**Severity**: info.

**Disposition**: Acknowledge; do NOT factor out now. The duplication is
cheap (15 lines per file); a shared module would create coupling between
test files for marginal cleanliness gain.

**Fix**: None.

## Verdict

**minor-fixes-recommended → clean after fix**. Two P2/P3 fixes
must land before K.4: K-MID-001 (FALLBACK token recognition) and K-MID-003
(symmetric exact-match-type test). The other findings are cosmetic /
informational.

## Closure plan

- K-MID-001: tighten `_per_candidate_prose_llm` FALLBACK detection + add 2 tests.
- K-MID-003: add `test_exact_match_type_not_routed_through_llm`.
- K-MID-005: relocate `logger` declaration above constants.
- K-MID-006: docstring "≤ 6 lines" → "≤ 5 lines".
- K-MID-007 + K-MID-008: acknowledged, no fix.

All fixes land in a single mid-slice closure commit before K.4 begins.

## Cross-references

- DEC-081 (no fabrication) — load-bearing for K-MID-001, K-MID-003.
- DEC-061 (deterministic baseline) — load-bearing for K-MID-003.
- Bucket 5 (Codex permissions) — still open; same trigger.
