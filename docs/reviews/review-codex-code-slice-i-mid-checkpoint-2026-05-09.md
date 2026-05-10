---
type: code review
flavor: codex
slice: I — endpoint follow-up (capabilities, concepts, query/validate)
checkpoint: I1+I2+I3 mid-slice
base_sha: 5ddbf40
head_sha: 88556be
date: 2026-05-09
plugin_version: codex-cli 0.125.0
verdict: minor-fixes-recommended
findings_summary: 0 P0, 0 P1, 1 P2, 0 P3, 0 info
---

## Summary

The Slice I mid-checkpoint implementation is functionally aligned with DEC-075 through DEC-080. `/query/validate` preserves the key DEC-079 contract: parse errors map to 422, while validator verdicts, including `unsupported`, are returned as HTTP 200. The new response models serialize and round-trip cleanly with Pydantic v2, and the new routes are mounted through the app factory. The main concern is test coverage rather than shipped behavior: `ConceptRegistry.list_all_concepts()` implements the right LEFT JOIN + Python aggregation semantics, but the edge cases called out by the design are not tested against an actual table-backed registry.

## Findings

### I-MID-001: list_all_concepts SQL edge cases are not covered by load-bearing tests
- Severity: P2
- Category: test-quality
- File: tests/unit/test_ontology_registry.py:305
- Description: The only direct `list_all_concepts()` test asserts `ConceptRegistry.empty().list_all_concepts() == []`, so the new SQL path in `src/ontology/registry.py:363` through `src/ontology/registry.py:407` is not exercised. Static review shows the implementation should include concepts with no lemmas, include concepts whose lemmas are only in other languages with `lemmas=[]`, and filter multi-language lemma rows in Python at `src/ontology/registry.py:395`. However, a future regression that changes the LEFT JOIN to an INNER JOIN, pushes the language filter into a WHERE clause, or drops concepts after language filtering would not be caught by the current unit suite. This is exactly the forward-compat edge surface called out for Slice I.
- Suggested fix: Add table-backed tests for `list_all_concepts()` using a small in-memory SQLite engine or existing DB test fixture. Cover at least: concept with no lemma rows, concept with GRC and HEB lemma rows, and a language filter with no matching lemma rows that still returns all concepts with empty lemma lists.

## Positive Observations

- `/query/validate` has only one explicit 422 branch, and it is scoped to `ParseError` at `src/app/routes/validate.py:47`. The handler returns `QueryValidateResponse` immediately after `run_validate_only()` at `src/app/routes/validate.py:44`, so unsupported verdicts are not translated into HTTP errors.
- `run_validate_only()` composes only parse + validate and returns `ValidationResult` directly at `src/app/orchestration.py:154`, with no `ValidationUnsupported` branch and no retrieve/explain calls.
- `TestValidateUnsupportedReturnsTwoHundredNotFourTwentyTwo` is load-bearing: it monkeypatches `src.app.routes.validate.run_validate_only` to return `status="unsupported"` at `tests/unit/test_app_routes_validate.py:107`, then asserts HTTP 200 at `tests/unit/test_app_routes_validate.py:114`. A future route-level status check that raised 422 for unsupported would fail this test.
- The empty-registry concepts path is covered at the HTTP layer: dependency override returns an empty registry at `tests/unit/test_app_routes_concepts.py:110`, and the route is asserted to return `{"concepts": []}` with 200 at `tests/unit/test_app_routes_concepts.py:115`.
- `QueryValidateResponse` deliberately does not inherit `QueryDSLResponse`; its MRO is `QueryValidateResponse -> BaseModel -> object`, and the code defines only `query` and `validation` at `src/app/schemas.py:105`. The route test asserts the response omits `result` and `explanation` at `tests/unit/test_app_routes_validate.py:161`.
- Import direction is acceptable: `src/app/schemas.py:15` imports the Pydantic `ConceptSummary` value object from `src/ontology/registry.py`, while `src/ontology/registry.py` imports no app-layer modules, so no circular dependency is introduced.

## Pre-I4 Gate

I-MID-001 should close before I4 starts if I4 depends on `/concepts` as a stable client contract. Otherwise, the implementation may proceed, but the SQL aggregation edge tests should be added before Slice I close.
