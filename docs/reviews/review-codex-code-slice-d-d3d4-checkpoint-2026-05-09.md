---
type: code
verdict: clean
base_sha: cbd27b5
head_sha: d48aaca
scope: Slice D D3+D4 checkpoint
reviewed_by: codex
date: 2026-05-09
findings_summary:
  P0: 0
  P1: 0
  P2: 0
  P3: 1
  info: 0
---

## Findings

| ID | Severity | File:Line | Category | Title |
|----|----------|-----------|----------|-------|
| D-D3D4-001 | P3 | `src/retrieval/contextualization.py:131` | B/G/F | Fallback permutations can exceed the stated 24-permutation ceiling for very long direct-call plans |

## D-D3D4-001

`compute_alternative_orderings()` switches all `N >= 5` plans to `_fallback_permutations(n)` and sets `capped=True` (`src/retrieval/contextualization.py:131-136`). The fallback helper returns identity, reverse, and every adjacent pairwise swap (`src/retrieval/contextualization.py:173-180`), which is `N + 1` permutations. That matches the subset shape requested for ordinary validated MVP traffic, and the current capability registry limits validated plans to 10 steps (`src/validation/registry.py:40`), so normal flows stay below 24 re-entries. However, the helper is exported through `compute_alternative_orderings()` without rechecking that validator limit, so a direct-call `QueryPlan` with 24+ steps would run more than the design's stated `min(N!, 24)` ceiling; tests cover N=5/6/7 shape but not the ceiling boundary.

## Clean Categories

- A: `compute_node_baselines()` validates shape, resolves concepts through the promoted executor helper, and applies the shared `build_scope_where()` clauses to every `COUNT(*)` statement (`src/retrieval/contextualization.py:75-92`).
- B: For supported MVP sequence lengths, full enumeration is used through 4! and the N>=5 fallback contains identity, reverse, and adjacent swaps with `capped=True` (`src/retrieval/contextualization.py:131-136`, `src/retrieval/contextualization.py:165-180`).
- C: Alternative ordering re-entry builds a new `SequenceExpr` and copied `QueryPlan` per permutation while preserving operator order (`src/retrieval/contextualization.py:140-147`).
- D: `RegistryRequired`, `ConceptNotMapped`, and `UnsupportedPlanShape` are not swallowed; contextualization delegates to executor helpers and lets those exceptions propagate (`src/retrieval/contextualization.py:75-87`, `src/retrieval/contextualization.py:127-147`).
- E: The promoted executor helpers preserve behavior and avoid an import cycle: contextualization imports from `src.engine.executor`, while the executor does not import retrieval (`src/engine/executor.py:85-96`, `src/engine/executor.py:207-362`).
- F: Unit and integration tests cover baseline resolution, shape rejection, scoped book counts, permutation counts through N=5, and observed-ordering count parity with `execute()` (`tests/unit/test_contextualization.py:77-468`, `tests/integration/test_contextualization.py:102-240`).
- G: The implemented cost for validated MVP plans is bounded by direct SQL baseline counts plus at most 24 full permutations for N<=4 and 11 fallback re-entries at the registry's current max length of 10.
- H: Contextualization lives in `src/retrieval/`, null distribution remains a schema slot only, and the D1/D2 review findings about canonical lifecycle, directory mapping, and non-negative schema constraints are addressed in the reviewed range.

## Verdict Rationale

Verdict: clean. The D3/D4 implementation is aligned with the requested checkpoint scope: baseline SQL carries scope filters into every count, concept resolution uses `ConceptRegistry` through the executor helper boundary, exceptions propagate cleanly, and alternative ordering re-enters the engine with fresh plan envelopes while preserving operator order. The only issue found is a low-severity ceiling edge for direct-call long plans beyond the current validator's supported length; it is worth tightening before slice close or adding a boundary test, but it does not block this per-batch checkpoint.

Verification run: `pytest tests/unit/test_contextualization.py tests/unit/test_models.py tests/unit/test_executor.py` passed, 122 tests.
