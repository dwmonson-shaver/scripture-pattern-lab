---
type: code review
flavor: codex
slice: I — endpoint follow-up
checkpoint: slice-close
base_sha: 5ddbf40
head_sha: 95f9eab
date: 2026-05-09
plugin_version: codex-cli 0.125.0
verdict: clean
findings_summary: 0 P0, 0 P1, 0 P2, 0 P3, 0 info
---

# Slice I Close — Code Review

## Summary

Slice I ships cleanly. All three new route modules (capabilities, concepts, validate) are correctly wired through their DI providers, handlers, and orchestration helpers with no logic gaps, no unhandled edge cases, and no regressions to Slice G or H. I-MID-001 closure held: the four SQL-path tests added at 786ac6c remain intact and cover all required cases. DEC-079 (validate returns 200 on unsupported) is enforced at the route, in the integration test, and in the unit regression guard. No findings above info severity.

## I-MID-001 Closure Verification

**Held.** The four SQL-path tests introduced at commit 786ac6c to close the mid-slice finding are present and intact at `tests/unit/test_ontology_registry.py` lines 350–412. Coverage confirmed:

| Test | Lines | Case covered |
|---|---|---|
| `TestListAllConceptsSqlPath::test_empty_lemmas_omitted` | ~350–365 | Concepts with no lemma rows return with empty `lemmas: []`, not skipped |
| `TestListAllConceptsSqlPath::test_multilanguage_filter` | ~366–381 | `language=` param correctly filters rows before Python aggregation |
| `TestListAllConceptsSqlPath::test_language_no_matches_keeps_concept` | ~382–397 | A concept with lemmas only in other languages still appears in list (no cross-concept bleed) |
| `TestListAllConceptsSqlPath::test_multi_concept_aggregation` | ~398–412 | Multiple concepts aggregate independently; no row-mixing |

All four cases use a real SQLAlchemy in-memory session (not a mock) — the original I-MID-001 concern about mock-only coverage is resolved.

## Findings

No findings. The review examined all seven review focus areas and found no issues meeting P3 or above severity thresholds.

## Bucket 9 Trigger Assessment

**Current trigger language** (from design doc and code comments, not yet in `docs/governance/reviews-log.md`):

> *"registry grows past ~500 rows / UI response-size pain"*

**Assessment: needs sharpening.** The trigger is directionally correct — Python-side aggregation in `list_all_concepts()` becomes a performance risk at scale — but the current phrasing has two gaps:

1. **Not in `reviews-log.md` yet.** The bucket is referenced in design prose and inline comments but has no formal row in `docs/governance/reviews-log.md`. A future developer scanning the governance log to determine which buckets fire on a given slice would not find it.
2. **"~500 rows" is vague.** It is unclear whether this refers to total `concepts` table rows, total `concept_lemmas` rows, or concepts returned per query. For `list_all_concepts()` the bottleneck is Python-side grouping across `concept_lemmas` rows, so the better trigger is: *"when `concept_lemmas` table exceeds 500 rows OR when any `/concepts` response observed to exceed 50 KB in manual testing."*

**Recommended sharpening:**

```
Trigger: When concept_lemmas table grows past 500 rows (check with
`SELECT COUNT(*) FROM concept_lemmas;` at start of a corpus-ingestion
slice), OR when any manual /api/v1/concepts response body exceeds 50 KB.
Action: Scope pagination (page/page_size) into list_all_concepts() and
the GET /api/v1/concepts route, add X-Total-Count header.
```

Add this row to `docs/governance/reviews-log.md` during the Slice I close-out step.

## Cumulative Regression Check

**No regressions detected.** The following areas were inspected:

- **Router mounting (`src/app/main.py`):** Three new routers (`capabilities_router`, `concepts_router`, `validate_router`) are appended after the existing `query_router` and `dsl_router`. No path collisions exist: new paths are `/api/v1/capabilities`, `/api/v1/concepts`, and `/api/v1/query/validate`; existing paths are `/api/v1/query/dsl` and `/api/v1/query`. FastAPI route resolution is first-match, and none of the new paths are prefixes of or identical to the existing paths.
- **Middleware ordering:** No new middleware added; CORS and exception handlers defined in Slice G/H are untouched.
- **Schema namespace:** `ConceptsResponse`, `QueryValidateRequest`, `QueryValidateResponse`, `ConceptSummary` are additive. No existing Pydantic model was modified.
- **`src/app/orchestration.py`:** `run_validate_only()` is a new function; `run_query()` and `run_query_dsl()` signatures are unchanged.
- **`src/ontology/registry.py`:** `list_all_concepts()` and `ConceptSummary` are additive. `get_concept_by_name()` and other existing functions are unchanged.

## End-to-End Trace

### GET /api/v1/capabilities

Request arrives → FastAPI routes to `capabilities_router` → `get_capabilities()` handler in `src/app/routes/capabilities.py` → handler imports `CapabilityRegistry` from `src/validation/capabilities.py` and instantiates it (no DI injection; the registry is stateless and cheap) → constructs `CapabilitiesResponse(capabilities=registry)` per DEC-075 (registry reused as response model directly) → returns 200 with JSON. No database touch, no AI call. The unit test suite covers the happy path and verifies the response shape round-trips through Pydantic without data loss.

### GET /api/v1/concepts

Request arrives → FastAPI routes to `concepts_router` → `get_concepts()` handler in `src/app/routes/concepts.py` → handler receives `db: Session` via `Depends(get_db)` → calls `list_all_concepts(db, language=language)` in `src/ontology/registry.py` → function issues one SQL query joining `concepts` and `concept_lemmas`, groups by concept in Python, returns `list[ConceptSummary]` → handler wraps in `ConceptsResponse(concepts=...)` → returns 200. Optional `language` query parameter filters lemmas pre-aggregation. An empty registry returns `{"concepts": []}` (verified by unit test). The I-MID-001 SQL-path tests confirm edge-case correctness at the data layer.

### POST /api/v1/query/validate

Request arrives → FastAPI routes to `validate_router` → `validate_query()` handler in `src/app/routes/validate.py` → Pydantic parses body as `QueryValidateRequest{query: str}` (422 on malformed JSON, as expected) → handler calls `run_validate_only(query, db)` in `src/app/orchestration.py` → `run_validate_only` calls the NL→DSL validator and returns a `ValidationResult` with `status` one of `valid | invalid | unsupported` → handler wraps in `QueryValidateResponse{query, validation}` → **always returns 200**, even when `status == "unsupported"` (DEC-079). The unit test `test_validate_unsupported_returns_200` and the integration test `test_validate_unsupported_status` both assert `status_code == 200` for the unsupported branch. The schema test `TestValidateNoExecutionFields` asserts that `result` and `explanation` keys are absent from `QueryValidateResponse`, enforcing the contract that this endpoint does not execute the query.
