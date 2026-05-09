---
type: code-review
verdict: minor-fixes-recommended
base_sha: 2b5e6dd
head_sha: 0d02c47
scope: Slice G phases G1-G4 checkpoint
reviewed_by: claude-sonnet-4-6 (manual + Codex-assisted)
date: 2026-05-09
findings_summary: "0 P0, 0 P1, 0 P2, 4 P3, 1 info — clean foundation; six unannotated inner functions + one unused import + one lifespan startup-exception leak pattern + one untested partial-validation path"
---

## Scope and Context

This is a mid-slice checkpoint review covering Slice G phases G1–G4 (commits 281afaf–0d02c47): HTTP wire schemas (`src/app/schemas.py`), pipeline orchestration helper `run_dsl_query()` (`src/app/orchestration.py`), FastAPI app factory + lifespan + DI providers (`src/app/main.py`, `src/app/dependencies.py`), and the `GET /api/v1/health` endpoint (`src/app/routes/health.py`). G5 (DSL route + exception mapping), G6 (live integration test), and G7 (canonical-09 amendment) are explicitly out of scope. All 33 unit tests pass in 0.41 s.

## Files Read

- `git diff 2b5e6dd..0d02c47` (809 lines added across 11 files)
- `thoughts/design-slice-g-fastapi-route-2026-05-09.md` (DEC-G1 through DEC-G14)
- `thoughts/structure-slice-g-fastapi-route-2026-05-09.md`
- `thoughts/research-slice-g-fastapi-route-2026-05-09.md`
- `scripts/query.py` (pipeline semantics reference)
- `src/app/orchestration.py`, `src/app/schemas.py`, `src/app/main.py`, `src/app/dependencies.py`, `src/app/routes/health.py`
- `tests/unit/test_app_orchestration.py`, `tests/unit/test_app_main.py`, `tests/unit/test_app_schemas.py`, `tests/unit/test_app_health.py`
- `src/ontology/registry.py` (ConceptRegistry.__init__ — verified no DB I/O)
- `src/ingestion/db.py` (get_engine — boundary check)
- `src/engine/models.py`, `src/validation/validator.py` (frozen/v2 confirmation)
- `docs/reviews/review-codex-code-slice-d-d3d4-checkpoint-2026-05-09.md` (format reference)
- `docs/reviews/review-codex-code-slice-c-close-2026-05-09.md` (severity calibration)

## Findings

| ID | Severity | File | Category | Title |
|----|----------|------|----------|-------|
| G-G1G4-001 | P3 | `tests/unit/test_app_main.py:91,110,123` | Convention | Three inner `_probe` route functions missing return type annotation |
| G-G1G4-002 | P3 | `tests/unit/test_app_orchestration.py:67,78,89` | Convention | Three inner `boom()` stubs missing return type annotation |
| G-G1G4-003 | P3 | `tests/unit/test_app_main.py:5` | Convention | `import os` is unused |
| G-G1G4-004 | P3 | `src/app/main.py:40–43` | DI-lifespan | Engine resource leak if startup raises after `app.state.engine` is set but before `yield` |
| G-G1G4-005 | P3 | `tests/unit/test_app_orchestration.py` | Test-fragility | No dedicated test for the `partial` validation-status path through `run_dsl_query()` |
| G-G1G4-006 | info | `tests/unit/test_app_health.py:14` | Test-fragility | `TestClient` not used as context manager in health fixture — lifespan not exercised |

---

### G-G1G4-001

**Severity:** P3
**Category:** Convention
**File:** `tests/unit/test_app_main.py:91,110,123`

**Finding:** CLAUDE.md requires type hints on all function signatures. Three inner route functions registered on the probe app in `TestDependencyProviders` are missing return type annotations:

```python
# line 91
def _probe(
    engine=Depends(get_engine),
    registry=Depends(get_concept_registry),
):   # <-- no return type
    ...

# line 110
def _probe(engine=Depends(get_engine)):  # <-- no return type

# line 123
def _probe(registry=Depends(get_concept_registry)):  # <-- no return type
```

These are test-local helpers, but they are registered as real FastAPI route handlers and the annotation gap is caught by `ast` inspection. The `Depends()` parameters also lack type hints, though FastAPI infers them.

**Remediation:** Add `-> dict[str, str]` (or `-> dict`) to each `_probe` definition. The `Depends()` parameters may also add explicit type annotations (`engine: Engine = Depends(get_engine)`) for consistency with the codebase's standard.

---

### G-G1G4-002

**Severity:** P3
**Category:** Convention
**File:** `tests/unit/test_app_orchestration.py:67,78,89`

**Finding:** The three `boom()` stubs in `TestPipelineExceptionsPropagate` are missing `-> None` return type annotations:

```python
# line 67
def boom(*args, **kwargs):   # <-- should be -> None
    raise UnsupportedPlanShape("boom", path="$.sequence.steps[0]")
```

Same issue applies to lines 78 and 89. These are passed to `monkeypatch.setattr` so they will never be called with a type-checked contract, but the convention requirement is unconditional in CLAUDE.md.

**Remediation:** Change to `def boom(*args: object, **kwargs: object) -> None:` on all three stubs.

---

### G-G1G4-003

**Severity:** P3
**Category:** Convention
**File:** `tests/unit/test_app_main.py:5`

**Finding:** `import os` on line 5 is not used anywhere in the file. Confirmed by grepping for `os.` — no hits. The `monkeypatch.delenv` / `monkeypatch.setenv` calls in the tests replace what might have been a direct `os.environ` approach.

**Remediation:** Remove `import os` from line 5.

---

### G-G1G4-004

**Severity:** P3
**Category:** DI-lifespan
**File:** `src/app/main.py:40–43`

**Finding:** The lifespan's `try/finally` block wraps only the `yield`, not the startup sequence. If `build_engine_from_env()` succeeds (line 41) and sets `app.state.engine` (line 42), but `ConceptRegistry(engine)` raises on line 43, the exception propagates out of the lifespan generator before the `try:` at line 52 is ever entered. The `finally` block at line 54 is therefore never reached, and `engine.dispose()` is never called.

```python
if url:
    engine = build_engine_from_env()   # line 41
    app.state.engine = engine          # line 42 — state set
    app.state.registry = ConceptRegistry(engine)   # line 43 — if this raises...
    ...
try:                      # line 52 — ...this is never entered
    yield
finally:
    engine = getattr(app.state, "engine", None)
    if engine is not None:
        engine.dispose()  # ...so this is never called
```

**Current risk is LOW** because `ConceptRegistry.__init__` (verified: `src/ontology/registry.py:249–251`) only assigns `self.engine = engine` — it performs no database I/O and cannot raise. However the pattern is fragile against future changes to `ConceptRegistry.__init__` or additional startup steps (e.g., registry pre-warming).

**Remediation (before slice close):** Wrap the startup sequence in its own try/except-or-finally, or restructure the startup block to enter the `try:` before building the engine:

```python
engine = None
try:
    url = os.environ.get("DATABASE_URL")
    if url:
        engine = build_engine_from_env()
        registry = ConceptRegistry(engine)
        app.state.engine = engine
        app.state.registry = registry
        logger.info("lifespan startup: engine + registry constructed")
    else:
        app.state.engine = None
        app.state.registry = None
        logger.warning("lifespan startup: DATABASE_URL unset; engine + registry left as None")
    yield
finally:
    if engine is not None:
        engine.dispose()
        logger.info("lifespan shutdown: engine disposed")
```

This also removes the dependency on `app.state` in the cleanup path, which is cleaner.

---

### G-G1G4-005

**Severity:** P3
**Category:** Test-fragility
**File:** `tests/unit/test_app_orchestration.py`

**Finding:** `run_dsl_query()` has two success branches: `supported` and `partial`. The happy-path tests only assert `resp.validation.status in ("supported", "partial")` (line 127) — there is no test that explicitly exercises a `partial` plan (a query where the validator reduces the plan but still produces an executable). The route handler in G5 will treat both branches identically (200 OK), but an explicit partial-path test would confirm that `validation.findings` carries the partial-reduction warnings into the response envelope.

**Remediation:** Add one test in `TestHappyPathWithMockedRetrieve` (or a new `TestPartialPath` class) that monkeypatches `validate` to return a `ValidationResult(status="partial", executable_plan=..., findings=[...partial warning...])` and asserts that `resp.validation.status == "partial"` and the findings list is non-empty in the response.

---

### G-G1G4-006

**Severity:** info
**Category:** Test-fragility
**File:** `tests/unit/test_app_health.py:14`

**Finding:** The `client` fixture creates `TestClient(create_app())` without using it as a context manager. In Starlette's `TestClient`, `lifespan` is triggered only on `__enter__` (i.e., when used as `with TestClient(app):`). Without the context manager, individual requests still work (the client spawns a fresh async portal per request), but the lifespan startup/shutdown sequence is not executed for the health tests.

For `GET /api/v1/health` this is intentional — the endpoint is designed to return 200 regardless of `app.state.engine`. The test named `test_health_does_not_require_database` validates exactly this. But the fixture comment could make this explicit to avoid confusion.

This is not a correctness bug — the tests are correctly verifying the health endpoint's liveness-only contract. It is flagged as `info` for clarity.

**Remediation (optional):** Add a comment to the fixture clarifying that lifespan is intentionally not triggered:

```python
@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Not used as context manager: lifespan is intentionally not triggered.
    # /health is liveness-only (DEC-G10) and must work before DB is available.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return TestClient(create_app())
```

Alternatively, the fixture may be upgraded to use `with TestClient(create_app()) as client:` and return the context-managed client via `yield client` — this exercises the lifespan (which sets state to None on unset DATABASE_URL) and keeps the same behavior. Either approach is acceptable; the current form is not broken.

---

## Clean Categories

**Correctness — run_dsl_query() vs scripts/query.py:** Pipeline step ordering matches exactly: `parse()` → `validate()` → guard on `unsupported/None` → `retrieve(executable, executable.scope, engine, contextualize=True, registry=registry)` → `explain(result, executable, validation)`. The `partial` branch proceeds identically to `scripts/query.py` (line 244: same guard structure). Exception types propagate unchanged — `ParseError`, `UnsupportedPlanShape`, `ConceptNotMapped`, `RegistryRequired` all let through without wrapping. `ValidationUnsupported` is correctly defined with `# noqa: N818` and carries the full `ValidationResult` payload for G5's HTTP mapping.

**DI lifespan — DATABASE_URL-unset path:** When `DATABASE_URL` is unset, `app.state.engine` and `app.state.registry` are both set to `None` before `yield`, and the `finally` block's `getattr(app.state, "engine", None)` safely returns `None` (no dispose called). The DI providers raise `HTTP 503` via `HTTPException` with a structured `ErrorResponse` payload. This is confirmed by `test_provider_returns_503_when_state_unset_and_no_override`. The database-URL-set path is tested with a monkeypatched engine (`fake_engine.dispose.assert_called_once()` passes).

**Pydantic model contracts:** `QueryDSLRequest`, `QueryDSLResponse`, and `ErrorResponse` all use `model_config = ConfigDict(frozen=True)`. The upstream models they compose (`ValidationResult`, `RetrievalResult`, `ExplainedResultSet`) are all `frozen=True` in `src/engine/models.py` and `src/validation/validator.py`. Round-trip tests pass for all three new schemas. The frozen-immutability tests correctly trigger `ValidationError` (Pydantic v2 raises `ValidationError`, not `AttributeError`, on frozen assignment — the tests assert the right exception type).

**Architecture boundaries:** `src/app/main.py:24` imports `src.ingestion.db.get_engine` (aliased as `build_engine_from_env`) — this is the DEC-025 carve-out, explicitly documented in the design. No other `src/app/` file imports from `src.ingestion`. `src/app/orchestration.py` imports only from `src.engine`, `src.retrieval`, `src.nlp`, `src.ontology`, and `src.validation` — all permitted layers. `src/app/dependencies.py` imports from `src.app.schemas` and `src.ontology.registry` — correct. No circular imports detected.

**OQ #6 / DEC-G8 — null emission:** Verified at runtime: `ErrorResponse(error='x', message='y').model_dump()` emits `{'error': 'x', 'message': 'y', 'details': None}`. `QueryDSLResponse.model_dump()` emits `validation.grounding: None`, `result.contextualization: None`, `explanation.nl_source: None`. No `exclude_none=True` anywhere in the diff. DEC-G8 is correctly implemented throughout.

**Test correctness:** The three `TestPipelineExceptionsPropagate` tests use `monkeypatch.setattr("src.app.orchestration.retrieve", boom)` — the module-path target is correct (the `retrieve` name in the orchestration module's namespace, not the original module). Exception identity is verified via `exc_info.value.path` and `.concept_name` attribute checks — these would fail if the wrong exception type or a wrapped version were raised.

## Verdict Rationale

**Verdict: minor-fixes-recommended.** The G1–G4 foundation is structurally sound. Pipeline semantics match the CLI reference, DI and lifespan behave correctly for both the URL-set and URL-unset paths, all three new Pydantic schemas are frozen and v2-compatible, architecture boundaries are respected, and DEC-G8's null-emission policy is correct throughout. All 33 unit tests pass.

The four P3 findings are genuine gaps (convention violations, one latent resource-management pattern, one test coverage gap) but none are correctness bugs that would block G5 from shipping. The info finding is purely a style note with no behavioral impact.

**Severity histogram:**
- P0: 0
- P1: 0
- P2: 0
- P3: 4 (G-G1G4-001, G-G1G4-002, G-G1G4-003, G-G1G4-004)
- info: 1 (G-G1G4-006)

## Next Steps

**What must close before G5 ships:**
- None of the P3 findings are blocking. G5 can proceed.
- However, G-G1G4-001 through G-G1G4-003 (type annotations + unused import) are fast fixes — ruff/mypy will flag them on any future lint pass, so closing them inline before G5 is recommended to keep the test suite clean.

**What can wait for slice close:**
- G-G1G4-004 (lifespan startup leak pattern) — current risk is effectively zero given `ConceptRegistry.__init__`'s no-op body, but worth fixing before slice-close to establish a clean pattern for future startup steps.
- G-G1G4-005 (no partial-path test) — add one test in G5 or at slice-close alongside the full exception-mapping tests.
- G-G1G4-006 (health fixture lifespan note) — info only; can be closed inline or ignored if the DEC-G10 intent is already clear from the test name.

Verification run: `pytest tests/unit/test_app_schemas.py tests/unit/test_app_orchestration.py tests/unit/test_app_main.py tests/unit/test_app_health.py` — 33 passed in 0.41 s.
