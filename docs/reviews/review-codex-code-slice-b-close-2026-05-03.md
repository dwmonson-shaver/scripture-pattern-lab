---
type: codex-review
flavor: code
date: 2026-05-03
verdict: minor-fixes-recommended
base: dc90b8c (start of Slice B)
scope: src/ingestion/loader.py, src/ingestion/db.py, scripts/db/ingest_corpus.py, tests/unit/test_loader.py, tests/unit/test_corpus_parser.py, tests/integration/test_corpus_ingest.py, tests/fixtures/morphgnt/multi/
plugin: codex@openai-codex 1.0.4
codex_cli: 0.125.0
findings_summary: 0 P0, 0 P1, 0 P2, 2 P3, 1 info
---

# Codex Code Review — Slice B Close — 2026-05-03

Defensive second-pair-of-eyes pass before slice closure. Paired with the
prior Slice A reviews in `thoughts/review-codex-code-2026-05-02.md` and
`thoughts/review-codex-adversarial-design-2026-05-02.md`. Severity language
calibrated against those artifacts. Closed findings from prior reviews are
not re-raised.

## Command

```
Defensive code review of git diff dc90b8c..HEAD — seven concern categories
(correctness, security, resource hygiene, test fragility, contract violations,
project-convention violations, subprocess/env interactions).
```

## Verdict

**minor-fixes-recommended.** No production blockers. The correctness,
security, SQL-composition, and resource-hygiene categories are clean. Two
P3s exist: one is a test-ordering fragility that is already partially
mitigated by a comment but not enforced, and one is a gap in the `done`
event test that could let a regression in the post-transaction emission
order pass undetected. Neither is a ship-stopper; both are worth addressing
before the next slice adds complexity on top of this surface.

---

## Findings

### Category 1 — Correctness bugs

No findings. Boundary detection (`last_book != token.book`) fires correctly
on the first token (because `last_book` starts as `None`), and the docstring
matches that behavior. `_present_filenames_in_bb_order` raises correctly on
extras and on an empty mapped subset. `global_position` threading in
`_stream_files` matches `parse_corpus_directory`'s idiom exactly.

---

### Category 2 — Security

No findings. Subprocess invocations (`_run_ingest_script`) pass arguments as
a list, so no shell injection surface. `--corpus-dir` resolves through
`Path.iterdir()` rather than string interpolation into SQL. The
`text("TRUNCATE TABLE tokens RESTART IDENTITY")` and all other raw SQL calls
use static strings — no user-controlled data is interpolated into any
`text()` call. `_redact_database_url` uses `rsplit('@', 1)` as documented,
correctly handling embedded `@` in the password.

---

### Category 3 — Resource hygiene

No findings. `parse_corpus_file` is a `with path.open(...) as fh:` generator.
Python's generator protocol guarantees the `with` block's `__exit__` fires when
the generator is closed (including on early termination via `break` or GC),
so the file handle is not leaked. `engine.begin()` and `engine.connect()` are
used as context managers throughout; no raw connection is held open past its
block. `truncate_tokens` uses `engine.begin()` as a context manager — the
transaction commits or rolls back correctly on scope exit.

---

### Category 4 — Test fragility / coverage gaps

**[P3] `tests/integration/test_corpus_ingest.py:212` — `test_full_corpus_smoke`
ordering is document-only, not enforced**

`file:line` — `tests/integration/test_corpus_ingest.py:231` (comment) and
line 212 (test function start).

**What's wrong.** The docstring of `test_full_corpus_smoke` notes it is
"placed last in the file so the module-scope `loaded_engine` fixture's
219-row 3-John state is not wiped before the tests that depend on it."
This is true, and the test authors clearly knew the risk. However, pytest's
default execution order is file-declaration order, which enforces the
invariant only as long as no one reorders the file or runs with
`--randomly-seed` (via `pytest-randomly`) or a similar shuffle plugin. If
test order is shuffled, `test_full_corpus_smoke` can run first and truncate
the table that `test_script_fails_loud_when_tokens_nonempty_without_truncate`
(line 151) needs to be non-empty.

**Why it matters.** A flaky integration suite caused by test-order
sensitivity is a silent CI risk: it fails under shuffle but passes in
declaration order, making it hard to diagnose. The sentinel check in
`test_script_fails_loud_when_tokens_nonempty_without_truncate` explicitly
depends on `loaded_engine` (line 161), so that fixture provides a data
dependency for that test but `test_full_corpus_smoke` does not declare
`loaded_engine` at all — there is no pytest dependency edge to prevent it
from running first.

**Suggested fix.** Two options (either is fine):
1. Add `loaded_engine` as a parameter to `test_full_corpus_smoke` (even
   unused) so pytest's fixture dependency graph guarantees the 3-John rows
   exist before the smoke test wipes them. This is the lowest-friction fix.
2. Mark the test with `@pytest.mark.last` (via `pytest-ordering`) or add a
   module-level `pytest_collection_modifyitems` hook that pins it to the
   end. Only worth doing if the suite is otherwise order-sensitive for other
   reasons.

Option 1 is consistent with how `test_script_fails_loud_when_tokens_nonempty_without_truncate`
already uses `loaded_engine` as an ordering dependency (line 161).

---

### Category 5 — Contract violations

**[P3] `tests/unit/test_loader.py:147` — `done` event test does not verify
post-transaction emission**

`file:line` — `tests/unit/test_loader.py:147`.

**What's wrong.** DEC-036 specifies the `done` event is emitted "post-commit
done" — i.e., after `engine.begin()`'s context manager exits (the
transaction commits), not inside it. The loader code at `loader.py:96–99`
correctly places the `done` callback call outside the `with engine.begin()`
block. However, `test_callback_emits_done_with_final_count` only asserts
`events[-1] == ProgressEvent(kind="done", book=None, tokens_loaded=5)`. It
does not verify that the `done` event arrives after the connection context
closes. If someone accidentally moves the `done` callback inside the
`with engine.begin()` block, the test still passes because the fake engine's
`begin()` context manager exits immediately (no real commit). The test cannot
distinguish pre-commit from post-commit emission.

**Why it matters.** The DEC contract exists to give callers a reliable
signal that the data is durable before they act on the count. A regression
that moves `done` inside the transaction would not be caught by the unit
test, and only integration tests would expose it.

**Suggested fix.** Extend `_FakeEngine.begin()` to record whether the
connection context has already exited when callbacks fire. Example pattern:

```python
class _FakeEngine:
    def __init__(self) -> None:
        self.connection = _FakeConnection()
        self._in_transaction = False

    @contextmanager
    def begin(self) -> Iterator[_FakeConnection]:
        self._in_transaction = True
        try:
            yield self.connection
        finally:
            self._in_transaction = False
```

Then in `test_callback_emits_done_with_final_count`, wrap the callback to
capture `fake_engine._in_transaction` at the moment `done` fires and assert
it is `False`.

---

### Category 6 — Project-convention violations

No findings. All public function signatures in the three production files
carry full type hints. `ProgressEvent` is a frozen Pydantic model at the
module boundary (satisfying "Pydantic at boundaries"). `loader.py` contains
no `logging` calls — observability is pushed to the caller via the callback.
Raw SQL uses `text()` throughout. `ProgressCallback` is a `Callable` type
alias, not a bare annotation — acceptable given `ProgressEvent` is itself a
Pydantic model.

---

### Category 7 — Subprocess / env interactions

**[info] `test_script_truncate_requires_env_confirm` uses `monkeypatch.delenv`
on the parent process; child process env inheritance is implicit**

`file:line` — `tests/integration/test_corpus_ingest.py:178`.

**What this is.** `monkeypatch.delenv("SPL_INGEST_CONFIRM_TRUNCATE", raising=False)`
removes the variable from the parent process env before calling
`_run_ingest_script`. Because `_run_ingest_script` calls `subprocess.run`
without an explicit `env=` argument, it inherits the parent process env,
which after `monkeypatch.delenv` will have `SPL_INGEST_CONFIRM_TRUNCATE`
absent. `monkeypatch` restores the env after the test. This is correct
behavior and monkeypatch is re-entrant-safe.

**Why it is info, not a finding.** The pattern is sound. No state leaks
between tests because monkeypatch is function-scoped. The `test_full_corpus_smoke`
uses `monkeypatch.setenv`, which also scopes the env mutation to that test
and restores it after. There is no interaction between these two tests that
could cause a flake: the env mutations are isolated by monkeypatch's teardown,
and the subprocess inherits a clean snapshot of the (already-patched) parent
env in each test.

**Note for future tests.** If any future test runs `_run_ingest_script` and
also needs to guarantee `SPL_INGEST_CONFIRM_TRUNCATE` is absent (not merely
unset by default), it should explicitly call `monkeypatch.delenv(...)` rather
than relying on ambient env state. The current tests do this correctly.

---

## Summary

| Severity | Count |
|----------|-------|
| P0       | 0     |
| P1       | 0     |
| P2       | 0     |
| P3       | 2     |
| info     | 1     |

**P3-1** — `tests/integration/test_corpus_ingest.py:212` — `test_full_corpus_smoke`
ordering enforced only by declaration order, not by a pytest dependency edge.
Fix: add `loaded_engine` as an unused parameter to create a hard ordering dependency.

**P3-2** — `tests/unit/test_loader.py:147` — `done` event test cannot detect a
regression where the callback is moved inside the transaction context. Fix:
extend `_FakeEngine` to record whether the connection context has exited at
callback time and assert it is `False` when `done` fires.

Both are low-risk for the current slice; neither affects production behavior.
