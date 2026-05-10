---
type: code review
flavor: codex
slice: H — NL→DSL translator + first LLM dependency
checkpoint: H3+H4 mid-slice
base_sha: 4448d59
head_sha: 0dda204
date: 2026-05-09
plugin_version: codex-cli 0.125.0
verdict: minor-fixes-recommended
findings_summary: 0 P0, 0 P1, 0 P2, 1 P3
---

# Slice H H3+H4 Code Review Checkpoint

Scope reviewed: `git diff 4448d59..0dda204`.

Note: `src/app/schemas.py`, `src/app/orchestration.py`, `tests/unit/test_app_orchestration.py`, and `tests/unit/test_app_schemas.py` have no changes in this diff, but were read for contract context.

## Findings

### H-H3H4-001

- **Severity**: P3
- **Category**: Lifespan independent-degradation semantics
- **File:line**: `src/app/main.py:54`, `src/app/main.py:69`
- **Description**: The advertised absence-based degradation works, but the two startup branches are still sequential inside one `try`. The `ANTHROPIC_API_KEY` block starts at line 69, after the `DATABASE_URL` branch has called `build_engine_from_env()` and `ConceptRegistry(engine)`. If the database branch raises before line 69, the LLM client and translation context branch is skipped entirely and app startup fails rather than degrading each resource independently. This is definitely true for construction failures; whether it is wrong depends on whether the Slice H contract means independent degradation only for missing env vars or for startup failures too.
- **Suggested fix**: If independent degradation is intended to cover construction failures, split DB and LLM startup into isolated guarded blocks (each with its own `try/except`). If construction failures should still fail process startup, document that distinction next to the lifespan docstring and add a test that asserts a DB construction failure prevents startup.

## Clean Category Checks

### HTTP error mapping completeness vs canonical-09 §1

Clean. `src/app/routes/nl.py:70`, `:83`, `:100`, `:110`, `:124`, `:134`, and `:148` cover `LLMUnavailable`, `NLCompileError`, `ParseError`, `ValidationUnsupported`, `UnsupportedPlanShape`, `ConceptNotMapped`, and `RegistryRequired`. No documented `run_nl_query()` exception falls through to the bare `except Exception` at `src/app/routes/nl.py:162`.

### Dependency-injection symmetry with Slice G

Clean. `get_llm_client()` and `get_translation_context()` both use the Slice G pattern: `getattr(..., None)`, `HTTPException(status_code=503)`, and `ErrorResponse(...).model_dump()` envelopes. Shape and error semantics match `get_engine` and `get_concept_registry`.

### Schema subclassing

Clean. `QueryNLResponse(QueryDSLResponse)` inherits `model_config = ConfigDict(frozen=True)` correctly. A read-only import probe confirmed `model_dump_json()` / `model_validate_json()` preserve the `translation` field. The route uses `response_model=QueryNLResponse`, so FastAPI does not narrow serialization to the parent model.

### Exception-chain correctness across orchestration boundary

Clean. `run_nl_query()` calls `translate()` before `run_dsl_query()`. The route's `except` chain catches translator-side exceptions (`LLMUnavailable`, `NLCompileError`) before downstream DSL exceptions. No superclass-ordering issue found.

### Lifespan independent-degradation semantics

One P3 finding above. Env-var absence degrades independently; construction-failure isolation does not.

### Security

Clean. `get_llm_client()` returns the client by reference server-side, but no route exposes or serializes it. `post_query_nl()` only passes it to orchestration. The H1 warning remains present in `src/nlp/llm_client.py:10-12`, and H4 adds no new `vars()` / logging leak path.

## Verdict Summary

**Overall verdict**: minor-fixes-recommended.

**P0/P1/P2 findings that must close before H5 starts**: none.

**Patterns worth watching in H5+**:
- Keep startup-degradation language precise: absence-only degradation is implemented; construction-failure isolation is not. If H5 adds more startup dependencies, decide the contract before the phase.
- Route handlers cover `ParseError` and `ValidationUnsupported`, but H4 route tests do not directly exercise those two branches (they enter via the DSL orchestration path). Worth adding direct tests before slice close.
- Do not add any debug endpoint or log path that serializes `vars(llm_client)` or `vars(llm_client._client)`.
