# Claude-Fallback Design Review — Slice K (LLM-in-Explainer)

- Date: 2026-05-23
- Reviewer flavor: claude-fallback (orchestrator self-review)
- Scope: `thoughts/design-explainer-llm-prose-2026-05-23.md`
- Codex blocked: `~/.codex/sessions` permission denied (Bucket 5 remains open). User-side fix: `sudo chown -R $(whoami) /Users/dwmonson/.codex`.
- Severity language: design (high / medium / low).

## Brief

The orchestrator asked four hostile questions of the design:

1. Does the system prompt's wording leave room for fabrication?
2. Is the fallback to deterministic prose airtight against silent LLM-output corruption?
3. Does the architecture preserve `explain()`'s testability and the explainer's `src/nlp/` boundary?
4. Is the no-fabrication test in the exit gate sufficient?

## Findings

### K-DESIGN-001 (medium) — System prompt wording is not yet drafted; design defers it to Phase K.1

**Finding**: The design names the system prompt's REQUIRED clauses (role, forbid-invention, output format, structured-input format) but does not exhibit the actual prompt text. DEC-081 conformance cannot be evaluated against an unwritten string.

**Disposition**: Acceptable for the design phase under orchestrator mode — the prompt **is** the load-bearing artifact and should be drafted in Phase K.1 alongside its first unit test. The structure outline (Phase K.1) must include the prompt text verbatim. Mid-slice Codex/Claude-fallback review after K.3 must inspect the prompt body, not just the design intent.

**Fix**: Phase K.1 commits the prompt module with the full constant; mid-slice review reads it before K.4 ships. Recorded as a check-this-at-K.1 carry, not a design blocker.

### K-DESIGN-002 (medium) — Broad `except Exception` swallows programmer errors silently

**Finding**: Decision #4 says "any `Exception` → fall back to deterministic + WARNING log". This makes the LLM path resilient but also masks **caller bugs** (e.g., `_per_candidate_prose_llm` is buggy and raises `AttributeError` on every conceptual candidate). Without monitoring, the explainer would silently emit deterministic prose forever and no one would know the LLM path is broken.

**Disposition**: Acknowledge the trade-off explicitly. Two mitigations:
- The WARNING log must include the exception type and the candidate reference. Operators auditing logs see a stream of "LLM fell back for 1Cor 13:13 (AttributeError)" — that is the signal a deployed system is broken.
- Add a unit test that asserts the WARNING is emitted (the test exercises both the LLM-success path and the fallback path; the fallback test asserts the log line).
- Use Python's `logger.warning(..., exc_info=True)` so the traceback is captured. (`exc_info=True` is the WARNING-with-traceback pattern; the default is no traceback.)

**Fix**: Tighten decision #4 wording in the design's resolved decisions to specify: (a) exception type included in log; (b) `exc_info=True` for stack capture; (c) one unit test of the fallback path asserts the log fires. These are mechanical additions; recorded for Phase K.2 implementation.

### K-DESIGN-003 (high) — No-fabrication exit-gate test is necessary-but-not-sufficient

**Finding**: Decision #9 says "every number AND verse reference appearing in the LLM prose is a substring of the structured input". This catches **fabricated numbers and refs**, but NOT:
- Fabricated theological assertions ("This represents Pauline triadic theology…")
- Reframed match-type claims ("This is a partial/probable match" when the input says "conceptual")
- Made-up lemma claims ("πίστις is the Greek word for trust" — accurate-but-unprompted)
- Cross-references invented from biblical knowledge that don't appear as digits/refs ("see Hebrews 11" — gets caught; but "this echoes earlier Pauline writings" — does NOT)

**Disposition**: The check IS necessary; the gap is that LLM **commentary**, not LLM **citations**, is the more likely DEC-081 violation mode. The mitigation is structural, not test-based:
- The system prompt MUST forbid "interpretive commentary" explicitly (already named in design's prompt-shape clause).
- The system prompt MUST cap output at one sentence under N chars — interpretive commentary tends to come in additional sentences; a one-sentence-only constraint is a forcing function for paraphrase-only mode.
- The exit-gate test should also assert: (a) output is a single sentence; (b) output contains the matched verse reference; (c) every digit substring in the output is a digit substring of the structured input; (d) every "X X:Y"-shape reference token in the output is a substring of the structured input.
- Add a stretch test: assert the lemma `step.token.lemma` value appears in the prose (a positive grounding check — the LLM cannot drop the lemma and still be paraphrasing).

**Fix**: Strengthen the exit-gate test specification in the design's "Risks and Concerns" section and in the structure outline's Phase K.5 test list. Recorded as a structure-outline P1-ish: must land in Phase K.5 verbatim, not be left implicit.

### K-DESIGN-004 (medium) — Env-var opt-in semantics need to be specific

**Finding**: Decision #6 says `SPL_EXPLAINER_LLM` env var; `run_nl_query()` checks at call time. Not specified: what truthy values activate it, what happens when ANTHROPIC_API_KEY is unset but SPL_EXPLAINER_LLM=1, default value when unset.

**Disposition**: Use the existing pattern from `src/app/main.py:137-142`: empty-string-as-disabled with a WARNING log. Specifically:
- Unset OR empty OR "0" OR "false" (case-insensitive) → deterministic path.
- "1" OR "true" (case-insensitive) → LLM path.
- Other values → log WARNING and treat as disabled (avoid silent typos enabling LLM).
- If `SPL_EXPLAINER_LLM=1` but `llm_client` arg is `None` (env var on, lifespan didn't construct client) → deterministic path with a single WARNING ("explainer LLM opted in but client not configured; falling back").

**Fix**: Add a section to the design's "Resolved Decisions" or to the structure outline's Phase K.4 file-touches list. Recorded for Phase K.4.

### K-DESIGN-005 (low) — `src/app/orchestration.py::run_nl_query()` env-var read is a cross-layer concern

**Finding**: Reading `os.environ.get("SPL_EXPLAINER_LLM")` inside `run_nl_query()` mixes config with orchestration. Slice G/H read env vars in `lifespan` and stash on `app.state`; reading at call time inside orchestration is a small architectural deviation.

**Disposition**: Acceptable for this slice — the env var is a single opt-in flag, not a multi-value config; lifespan-scoping it would require adding `app.state.explainer_llm_enabled`, a new dependency provider, and a new test for the unset/set lifespan branches. Marginal cleanliness gain for material complexity. Use call-time read with a single test of both branches.

**Fix**: Document this trade-off in the structure outline's Phase K.4 notes. No design change required.

### K-DESIGN-006 (low) — `_truncate_llm_prose` cap should not be a magic number

**Finding**: Decision #3 names `max_chars=300`. The translator's character limits are not exposed as module-level constants; the explainer uses module-level constants (`_LEMMA_CAP=5`, `_SEQUENCE_LABEL_MAX=64`).

**Disposition**: Follow the existing pattern. Add a module-level `_LLM_PROSE_MAX = 300` constant in `explainer.py`. Acknowledge tightness: the system prompt requests ≤200; the post-cap allows 50% overage as a safety margin without truncating cleanly-formed paraphrases.

**Fix**: Add to structure outline's Phase K.2 module-constants list. Mechanical.

## Verdict

**clean-with-conditions**. No design-`high` findings that block the slice. K-DESIGN-003 is `high` because it changes the structure outline's exit-gate test specification — that change must land verbatim in Phase K.5, not "soon" or "eventually". The other findings are mechanical refinements that fold into Phase K.1–K.5.

Six findings; six dispositions; all addressed via mechanical fixes during implementation (K.1–K.5) with the structure outline carrying the specification.

## Cross-references

- DEC-081 (no fabrication) — load-bearing for K-DESIGN-001 and K-DESIGN-003.
- DEC-061 (deterministic baseline) — load-bearing for K-DESIGN-002.
- DEC-070 (LLM error mapping) — referenced for K-DESIGN-002's fallback semantics.
- Bucket 5 (Codex permissions) — remains open; same trigger.
