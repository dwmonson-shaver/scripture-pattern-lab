---
type: code_review
verdict: FAIL
base_sha: fed3b98
head_sha: 15a6bb132ab1514c53b2f402821d8eddec2f0324
scope: Slice C close review; executor + CLI additions from 0eef8f5 onward, with cross-track DEC-024/DEC-025 integrity checks across fed3b98..HEAD
date: 2026-05-09
findings_summary: 1 P0, 1 P1, 3 P2, 1 P3, 0 info
---

## Findings

### C-CLOSE-001

- severity: P0
- location: `src/engine/executor.py:216-230`
- title: Negated NodeRefs are accepted and executed as positive matches
- description: `_validate_plan_shape()` only checks that a step is a `NodeRef` and that its type is `LEMMA` or `CONCEPT`; it never rejects `NodeRef.negated=True`. Resolution then ignores all node modifiers and returns the positive lemma/concept expansion (`src/engine/executor.py:271-288`). Because the validator has no negation rule in the diff, a parsed negated node can reach `execute()` and silently return the opposite of the requested semantics.
- recommendation: Treat `step.negated` as unsupported in `_validate_plan_shape()` and raise `UnsupportedPlanShape` with the step path until exclusion semantics are implemented. Add a unit test for a negated lemma/concept plan.

### C-CLOSE-002

- severity: P2
- location: `src/engine/executor.py:216-244`
- title: Executor shape gate is incomplete for unsupported NodeRef modifiers and malformed operator counts
- description: The second-wall gate does not reject `NodeRef.morph_filters` even though the executor resolution path ignores them (`src/engine/executor.py:271-288`), and it also never verifies `len(sequence.operators) == len(sequence.steps) - 1`. Too few operators fall through to `sequence.operators[step_index - 1]` at runtime (`src/engine/executor.py:122-124`), while extra operators are silently ignored by the execution loop.
- recommendation: In `_validate_plan_shape()`, reject non-empty `morph_filters` and malformed operator counts with `UnsupportedPlanShape`. Keep this defensive even though the validator catches morph filters, because `execute()` is documented as the second wall.

### C-CLOSE-003

- severity: P2
- location: `src/engine/executor.py:111-114; src/engine/executor.py:331-348`
- title: Corpus and language scope filters are applied only to the first step
- description: `execute()` applies the assembled scope WHERE clauses only to the step-0 query. Subsequent step queries constrain book/chapter/verse/lemma, but not `scope.corpus` or `scope.language`. With more than one corpus or language sharing the same structural verse keys, later tokens can be pulled from outside the requested scope while still forming a candidate.
- recommendation: Carry the resolved corpus/language filters into `_match_step_in_verse()` and apply them to every step query, or pass the full base scope clauses into that helper.

### C-CLOSE-004

- severity: P1
- location: `src/engine/executor.py:114-139`
- title: Sequence execution has unbounded per-candidate SELECT fan-out
- description: The step-0 query materializes all first-step rows, then each later step issues one SELECT for every surviving chain. A common first lemma can produce thousands of chains and therefore thousands of serial SELECTs for a two- or three-step query. The connection is reused (`src/engine/executor.py:90-139`), so this is not a connection leak, but it is still a real query-amplification hot path under broad or adversarial input.
- recommendation: Batch later-step matching by verse/window, use a set-based SQL plan/self-join for MVP sequence searches, or add an explicit candidate/query cap with a user-facing unsupported/too-broad error.

### C-CLOSE-005

- severity: P2
- location: `src/engine/executor.py:48`
- title: `src/engine` imports `src.ingestion`, breaching DEC-025
- description: DEC-025 and canonical-09 state that query-side packages, including `src/engine/`, must not import `src/ingestion/`. The new executor imports `tokens_table` directly from `src.ingestion.db`, adding exactly that dependency in post-Track-1 code.
- recommendation: Move the read-only `tokens_table` mirror to a neutral persistence/schema module that both ingestion and engine can import, or create a query-side read interface outside `src.ingestion`.

### C-CLOSE-006

- severity: P3
- location: `scripts/query.py:147-183; src/engine/executor.py:285-288`
- title: CLI registry-empty exit path is effectively unreachable for empty concept mappings
- description: `scripts/query.py` documents exit code 3 for a concept node with no lemma mapping and catches `RegistryRequired`, but `main()` always constructs and passes a `ConceptRegistry`. The executor only raises `RegistryRequired` when the registry object is `None`; if the registry exists but returns `[]` for a concept, execution returns zero matches instead of exit 3.
- recommendation: Decide whether unknown/unseeded concepts should be a user error. If yes, raise a dedicated exception when a concept step resolves to an empty lemma list and map it to exit 3. If no, remove the dead exit-code contract from the CLI.

## Summary

Verdict: FAIL. Slice C is close, but it is not slice-ready until the negated-node correctness bug and DEC-025 boundary breach are fixed; the scope leakage and fan-out issues should be addressed before treating executor behavior as stable beyond the narrow happy path.

Slice-readiness: not ready to close.
