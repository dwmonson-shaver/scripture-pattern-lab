---
type: code-review
verdict: minor-fixes-recommended
base_sha: 2b5e6dd
head_sha: 0c85848
scope: Slice G cumulative diff G1 through G7
reviewed_at: 2026-05-09
findings_summary: P0:0 P1:0 P2:0 P3:1 info:0
---

## Summary

Verdict: `minor-fixes-recommended`.

Finding counts: P0: 0, P1: 0, P2: 0, P3: 1, info: 0. No closure-blocking findings were found.

Quality assessment: Slice G cleanly exposes the existing CLI query pipeline over `POST /api/v1/query/dsl`. `run_dsl_query()` mirrors `scripts/query.py::main` in the important behavioral order: parse, validate with `CapabilityRegistry.mvp()`, reject unsupported validation results, retrieve the executable plan with `contextualize=True`, then explain (`src/app/orchestration.py:66-93`; `scripts/query.py:216-290`). The route maps the project exception set to the canonical status table (`src/app/routes/query.py:50-122`; `docs/canonical/09_backend-service-boundaries.md:101-119`), and the 500 path returns a generic client message while logging server-side (`src/app/routes/query.py:112-121`). Lifespan cleanup now captures the engine in a local variable before startup work and disposes it from `finally` (`src/app/main.py:44-63`). Integration coverage verifies the live HTTP envelope and documented invariants, including contextualization, null emission, and flagship counts (`tests/integration/test_app_dsl_route.py:92-166`). The only remaining issue is a ruff-visible unused import in a test file.

## Mid-slice checkpoint re-verification

The G1-G4 checkpoint reported 4 P3 findings plus 1 info finding. All are closed in `e08fca5` and remain closed at `0c85848`:

- G-G1G4-001 closed: the three probe route functions now have return annotations and typed dependency parameters (`tests/unit/test_app_main.py:89-96`, `tests/unit/test_app_main.py:108-110`, `tests/unit/test_app_main.py:121-125`).
- G-G1G4-002 closed: the three `boom()` stubs now type `*args`, `**kwargs`, and `-> None` (`tests/unit/test_app_orchestration.py:68-69`, `tests/unit/test_app_orchestration.py:79-80`, `tests/unit/test_app_orchestration.py:90-91`).
- G-G1G4-003 closed: the prior unused `os` import is absent from the current import block (`tests/unit/test_app_main.py:3-14`).
- G-G1G4-004 closed: `lifespan()` now enters the `try/finally` before building startup resources, stores the engine in a local, and disposes it in `finally` (`src/app/main.py:44-63`).
- G-G1G4-006 info closed: the health fixture now documents why it intentionally avoids the TestClient context manager and therefore skips lifespan (`tests/unit/test_app_health.py:11-20`).

## Findings

### G-CLOSE-001

- severity: P3
- category: Convention / ruff cleanliness
- file: `tests/unit/test_app_routes.py:22`
- observation: `ValidationUnsupported` is imported but never used in the route test module. Local `ruff check src/app tests/unit/test_app_schemas.py tests/unit/test_app_orchestration.py tests/unit/test_app_main.py tests/unit/test_app_health.py tests/unit/test_app_routes.py tests/integration/test_app_dsl_route.py` reports `F401` for this line.
- impact: This does not affect runtime behavior or test intent, but it means the new Slice G test surface is not ruff-clean under the repo's configured `F` rules (`pyproject.toml:33-34`).
- remediation: Remove `ValidationUnsupported` from the import list at `tests/unit/test_app_routes.py:22`.

## Notes

Correctness: `run_dsl_query()` uses the same executable plan for retrieval and explanation, passes `executable.scope`, and leaves pipeline exceptions unwrapped for the route handler (`src/app/orchestration.py:74-93`). The route covers `ParseError`, `ValidationUnsupported`, `UnsupportedPlanShape`, `ConceptNotMapped`, `RegistryRequired`, and uncaught exceptions (`src/app/routes/query.py:50-122`).

Security: the 500 response uses `error="internal_error"` and `message="an unexpected error occurred"` with no details payload (`src/app/routes/query.py:112-121`). The test asserts that a raised `RuntimeError("connection refused")` does not leak that text to the client (`tests/unit/test_app_routes.py:188-202`).

Resource hygiene: engine construction is process-scoped, state-backed, and disposed on shutdown (`src/app/main.py:44-63`). Query-side DB access remains context-managed through the existing retrieval/executor paths; the integration fixture also passes the copied environment, including `DATABASE_URL`, into both ingest and seed subprocesses (`tests/integration/test_app_dsl_route.py:40-64`).

Spec contract: the canonical-09 section 1 amendment matches the implemented response envelope, null policy, status table, dependency-injection model, and sync handler rationale (`docs/canonical/09_backend-service-boundaries.md:73-135`). Per the review instructions, missing DEC-G entries in the decision log are not faulted here; those belong to `/review`.

Architecture boundaries: `src/app/` imports only app-local modules plus engine, retrieval, NLP, ontology, validation, and the DEC-025 carve-out import of `src.ingestion.db.get_engine` in `src/app/main.py:25`. No reverse imports from engine/retrieval/NLP/ontology/validation into `src.app` were found.

Bucket 5 closure note: this is the first real Codex close pass after the Slice E and Slice F close reviews shipped as Claude-fallback reviews. Bucket 5 can be treated as closed by this Slice G review artifact.

DEC-Gn needing decision-log entries: DEC-G1 through DEC-G14 are documented in `thoughts/design-slice-g-fastapi-route-2026-05-09.md` and should be copied into the formal decision log during the Slice G `/review` step, not blocked here.

Carry-forward for next slice: consider adding API-level assertions that `validation.executable_plan` is intentionally part of the public JSON contract if the verbatim `ValidationResult` envelope remains the chosen shape. This is not a finding because canonical-09 currently says the response composes existing project models verbatim (`docs/canonical/09_backend-service-boundaries.md:73-83`).

**Verdict: minor-fixes-recommended. Slice G can close with no P0/P1/P2 blockers; remove the unused test import before or shortly after closure to restore ruff cleanliness.**
