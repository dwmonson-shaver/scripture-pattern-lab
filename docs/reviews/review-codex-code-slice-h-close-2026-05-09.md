---
type: code review
flavor: codex
slice: H — NL to DSL translator + first LLM dependency
checkpoint: slice-close
base_sha: da0b4c9
head_sha: 43a71e6
date: 2026-05-09
plugin_version: codex-cli 0.125.0
verdict: minor-fixes-recommended
findings_summary: 0 P0, 0 P1, 0 P2, 3 P3, 1 info
---

## Scope

Reviewed cumulative diff `git diff da0b4c9..43a71e6` with the requested calibration artifacts:

1. `docs/reviews/review-codex-code-slice-g-close-2026-05-09.md`
2. `docs/reviews/review-claude-code-slice-h-h1h2-checkpoint-2026-05-09.md`
3. `docs/reviews/review-codex-code-slice-h-h3h4-checkpoint-2026-05-09.md`
4. `thoughts/design-slice-h-nl-translator-2026-05-09.md`
5. `docs/canonical/09_backend-service-boundaries.md`

Focused unit verification run:

```bash
pytest tests/unit/test_llm_client.py tests/unit/test_translator.py tests/unit/test_app_orchestration.py tests/unit/test_app_schemas.py tests/unit/test_app_routes_nl.py tests/unit/test_app_main.py
```

Result: `93 passed in 0.76s`.

Focused lint run:

```bash
ruff check src/nlp/llm_client.py src/nlp/translator.py src/nlp/prompts/system_prompt.py src/nlp/explainer.py src/app/schemas.py src/app/orchestration.py src/app/dependencies.py src/app/main.py src/app/routes/nl.py tests/unit/test_llm_client.py tests/unit/test_translator.py tests/unit/test_app_orchestration.py tests/unit/test_app_schemas.py tests/unit/test_app_routes_nl.py tests/unit/test_app_main.py tests/integration/test_app_nl_route_live_llm.py
```

Result: `All checks passed!`.

Live-LLM integration was not run in this review environment: both `DATABASE_URL` and `ANTHROPIC_API_KEY` were unset.

## End-To-End Trace

`POST /api/v1/query/nl` enters `post_query_nl`, with `Engine`, `ConceptRegistry`, `LLMClient`, and `TranslationContext` supplied by the four dependency providers (`src/app/routes/nl.py:52`, `src/app/routes/nl.py:55`, `src/app/routes/nl.py:58`). The route calls `run_nl_query` (`src/app/routes/nl.py:62`), which calls `translate` first (`src/app/orchestration.py:123`) and then passes `translation_result.dsl` into the existing DSL pipeline (`src/app/orchestration.py:125`). `run_dsl_query` still performs parse, validate, retrieve with `contextualize=True`, and explain in that order (`src/app/orchestration.py:68`, `src/app/orchestration.py:70`, `src/app/orchestration.py:81`, `src/app/orchestration.py:89`). The NL response copies the executed DSL response fields and adds translator metadata (`src/app/orchestration.py:131`).

The compiled-DSL invariant holds in code: `QueryNLResponse.query` is the compiled DSL (`src/app/schemas.py:67`, `src/app/schemas.py:71`) and unit/integration tests assert `body["query"]` rather than `translation.dsl` (`tests/unit/test_app_routes_nl.py:146`, `tests/integration/test_app_nl_route_live_llm.py:111`).

## Regression Checks

Slice G lifespan cleanup still holds. The engine local is initialized before the startup `try` (`src/app/main.py:60`) and disposed in `finally` if constructed (`src/app/main.py:98`). H4's router imports and LLM startup branch did not move disposal outside the protected block.

`QueryNLResponse(QueryDSLResponse)` does not narrow DSL serialization. The subclass adds `translation` while inheriting the four DSL fields (`src/app/schemas.py:67`, `src/app/schemas.py:77`), and the NL route uses `response_model=QueryNLResponse` (`src/app/routes/nl.py:52`).

H-H1H2-001 is closed in final state. `AnthropicLLMClient.complete` wraps only connection, timeout, rate-limit, auth, permission, and 5xx server exceptions (`src/nlp/llm_client.py:71`) and deliberately lets 4xx request-bug classes propagate raw (`src/nlp/llm_client.py:80`); unit coverage asserts that raw propagation (`tests/unit/test_llm_client.py:166`).

H-H3H4-001 is closed by documentation and final code semantics. `src/app/main.py` now states the degradation contract is absence-only and construction failures are intentionally fail-fast (`src/app/main.py:9`). The code matches: missing env vars set app state to `None` (`src/app/main.py:69`, `src/app/main.py:90`), while builder exceptions are not caught.

API key handling is clean in project code. The key is read from env (`src/nlp/llm_client.py:101`) and passed to `anthropic.Anthropic(api_key=api_key)` (`src/nlp/llm_client.py:59`). It is not stored directly on the project wrapper, serialized in response schemas, or logged by project log statements. The module-level security note warns against logging the inner SDK client because the SDK exposes the key (`src/nlp/llm_client.py:10`).

## Findings

### H-CLOSE-001

Severity: P3

Category: Canonical contract drift / translator context

File: `src/app/main.py:79`

Description: The shipped `TranslationContext` is not actually built from the live capability registry or concept registry. The lifespan constructs it from two static prose strings (`src/app/main.py:79` through `src/app/main.py:87`). That conflicts with the translator docstring saying the context is "Built once at FastAPI startup from the live capability registry and concept registry" (`src/nlp/translator.py:26`) and canonical-09 saying "The LLM receives the current capability registry + concept registry as context" (`docs/canonical/09_backend-service-boundaries.md:190`). This is not breaking the current tests, but it overstates what the runtime sends to the LLM and weakens OQ-H1 evidence.

Suggested fix: Either build real summaries from `CapabilityRegistry.mvp()` and the startup `ConceptRegistry`, or amend `TranslationContext`/canonical text to say the MVP sends static high-level summaries while the cookbook carries the executable DSL surface.

### H-CLOSE-002

Severity: P3

Category: Security / cost control / input validation

File: `src/app/schemas.py:64`

Description: `QueryNLRequest.nl_query` has only `min_length=1` and no upper bound. The value is interpolated directly into the LLM user message (`src/nlp/translator.py:82`) and sent to Anthropic (`src/nlp/llm_client.py:65`). A very long request can consume unexpectedly large tokens/cost or hit provider request-size errors before project code has a chance to return a controlled validation error. The default pytest suite has no very-long-input test for this path; the live LLM suite is excluded by default (`pyproject.toml:44`).

Suggested fix: Add a `max_length` to `QueryNLRequest.nl_query` sized for the product, such as 2k-4k characters for MVP, and add route/schema tests asserting over-limit input is rejected before `run_nl_query` or `LLMClient.complete` is reached.

### H-CLOSE-003

Severity: P3

Category: Epistemic honesty / silent uncertainty

File: `src/nlp/translator.py:119`

Description: Missing, malformed, or out-of-range `Confidence:` values default to `1.0` (`src/nlp/translator.py:121`, `src/nlp/translator.py:125`, `src/nlp/translator.py:127`). The tests lock in that behavior (`tests/unit/test_translator.py:122`, `tests/unit/test_translator.py:127`, `tests/unit/test_translator.py:132`). This can surface maximum confidence when the LLM did not provide a parseable confidence value, which cuts against DEC-072's "surface; caller decides" posture because the surfaced value no longer distinguishes an LLM self-assessment from a parser fallback. The live ambiguity test checks one vague query, but it is gated and was not runnable here (`tests/integration/test_app_nl_route_live_llm.py:158`).

Suggested fix: Use an uncertainty-preserving default (`0.0` or `None`) or add a metadata field such as `confidence_source: "llm" | "default"`. If max-confidence fallback is intentional, canonical-09 should explicitly call out the epistemic tradeoff rather than describing the field only as self-assessed fidelity.

### H-CLOSE-004

Severity: info

Category: Documentation / response-envelope wording

File: `src/app/routes/nl.py:8`

Description: The route docstring says the 200 response has `translation.dsl` set to the compiled DSL (`src/app/routes/nl.py:8`). The shipped schema intentionally has no `translation.dsl`; `query` carries the compiled DSL and `translation` carries confidence, alternatives, and explanation (`src/app/schemas.py:67`, `src/app/schemas.py:77`). Tests and canonical-09 use the correct shape (`tests/integration/test_app_nl_route_live_llm.py:111`, `docs/canonical/09_backend-service-boundaries.md:252`), so this is a stale local docstring rather than a wire-contract bug.

Suggested fix: Change the docstring to "QueryNLResponse with `query` set to the compiled DSL string and `translation` metadata populated."

## Clean Checks

No P0/P1/P2 issues found.

The line-anchored parser is strict about missing/empty `DSL:` and propagates LLM availability failures unchanged (`src/nlp/translator.py:91`, `src/nlp/translator.py:100`, `src/nlp/translator.py:77`). Existing tests cover happy path, empty/missing DSL, optional metadata defaults, asterisk bullets, and LLMUnavailable propagation (`tests/unit/test_translator.py:75`, `tests/unit/test_translator.py:108`, `tests/unit/test_translator.py:147`, `tests/unit/test_translator.py:155`). Multi-line/unicode NL inputs are not inherently broken by the code path because they are plain Python strings threaded through Pydantic and f-strings, but they are not directly tested.

Exception mapping is complete for the shipped `run_nl_query` surface. `LLMUnavailable`, `NLCompileError`, `ParseError`, `ValidationUnsupported`, `UnsupportedPlanShape`, `ConceptNotMapped`, and `RegistryRequired` all have explicit branches before the generic 500 handler (`src/app/routes/nl.py:70`, `src/app/routes/nl.py:83`, `src/app/routes/nl.py:100`, `src/app/routes/nl.py:110`, `src/app/routes/nl.py:124`, `src/app/routes/nl.py:134`, `src/app/routes/nl.py:148`).

The compiled DSL is exposed in the load-bearing `query` field. This is true in schema docs (`src/app/schemas.py:71`), orchestration assembly (`src/app/orchestration.py:131`), route unit tests (`tests/unit/test_app_routes_nl.py:146`), and the live-LLM exit gate (`tests/integration/test_app_nl_route_live_llm.py:111`).

## OQ Dispositions

OQ-H1: Static cookbook embedding is provisionally accepted for MVP, but the evidence is incomplete in this review. Code embeds `docs/agent/dsl-cookbook.md` into `SYSTEM_PROMPT` at import time (`src/nlp/prompts/system_prompt.py:62`) and passes context summaries in the user message (`src/nlp/translator.py:82`). The live-LLM exit gate exists (`tests/integration/test_app_nl_route_live_llm.py:93`) but could not be run here because `DATABASE_URL` and `ANTHROPIC_API_KEY` were unset. H-CLOSE-001 records the remaining overclaim about "current" live registry context.

OQ-H2: Resolved to free-form text with line-anchored extraction. The prompt mandates `DSL:`, `Confidence:`, `Alternatives:`, and `Explanation:` lines (`src/nlp/prompts/system_prompt.py:25`), and the parser extracts with regex helpers (`src/nlp/translator.py:55`). Unit coverage exercises the extractor shape (`tests/unit/test_translator.py:75`).

OQ-H3: Re-defer LLM-backed explainer prose. The Slice H code introduces `LLMClient` only for translation (`src/app/orchestration.py:123`), while `src/nlp/explainer.py` remains deterministic and imports no LLM seam (`src/nlp/explainer.py:25`). The re-defer rationale in the Slice H design is specific: after Slice H ships and the user has run at least one NL query, revisit only if deterministic prose is judged inadequate or the user explicitly authorizes LLM-in-explainer wiring (`thoughts/design-slice-h-nl-translator-2026-05-09.md:102`). That is a defensible scope boundary; do not scope Bucket 7 into Slice H close.

OQ-H4: Resolved as required metadata fields on the response. `TranslationMetadata` requires `confidence`, `alternatives`, and `explanation` (`src/app/schemas.py:30`), and `TranslationResult` supplies defaults (`src/nlp/translator.py:40`). H-CLOSE-003 remains because the chosen `confidence=1.0` fallback is overconfident when the LLM omits or malforms the field.

OQ-H5: Bucket 6 is not fully closed by evidence available in this review environment. The Slice H live-LLM test is the right closure mechanism for the NL/cookbook path (`tests/integration/test_app_nl_route_live_llm.py:93`), but it requires both `DATABASE_URL` and `ANTHROPIC_API_KEY` (`tests/integration/test_app_nl_route_live_llm.py:82`) and was not run here. Treat Bucket 6 as close-ready once that test is run and recorded, or explicitly narrow the bucket closure to the already-proven Slice G DSL HTTP path.

## Bucket Triage

Bucket 6: Partially remains. The codebase now has a live-LLM, live-DB exit gate that exercises an NL query through cookbook-backed translation and the real corpus (`tests/integration/test_app_nl_route_live_llm.py:93`), but the review environment did not satisfy the env-var preconditions (`tests/integration/test_app_nl_route_live_llm.py:82`). Close Bucket 6 only after recording a successful `pytest -m "live_llm" tests/integration/test_app_nl_route_live_llm.py` run, or amend the bucket text to say Slice G's DSL route was sufficient and why the original fresh-agent/cookbook live-corpus trigger no longer applies.

Bucket 7: Re-defer. The original trigger ("Slice H ships an LLM dependency") fired, but the Slice H design sharpened it to require at least one real NL-query user evaluation or explicit authorization before wiring the explainer to an LLM (`thoughts/design-slice-h-nl-translator-2026-05-09.md:102`). The current implementation keeps `src/nlp/explainer.py` deterministic (`src/nlp/explainer.py:18`), which preserves the DEC-061 baseline. Do not scope it into Slice H close.
