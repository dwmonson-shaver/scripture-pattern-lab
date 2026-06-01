---
type: code-review
flavor: codex-code
slice: M
checkpoint: slice-close
verdict: APPROVE
base_sha: b2f963a
head_sha: f81c089
date: 2026-06-01
scope: >
  Cumulative Slice M diff, git diff b2f963a..f81c089 (6 phase commits +
  fallback-review-closure commit). Stateless multi-turn conversational
  refinement on /query/nl: ConversationTurn schema + QueryNLRequest.prior_turns
  (M1), additive complete_turns() LLM seam + DEC-071 amendment (M2),
  translate() multi-message affordance (M3), orchestration/route/proxy
  threading (M4), exit-gate two-round test + canonical-09 §2 (M5),
  fallback-review finding closures: 2 P2 + info (f81c089).
reviewer: >
  Codex (codex-companion 1.0.4). This is the authoritative Codex pass that was
  owed since 2026-05-26 (the slice-close Codex run was blocked by
  ~/.codex/sessions permission-denied; a claude-fallback APPROVE WITH FOLLOW-UPS
  stood in, Bucket-M1). Permissions resolved; this pass replaces that stand-in
  as the slice's authoritative review.
findings_summary:
  P0: 0
  P1: 0
  P2: 0
  P3: 0
  info: 0
---

# Codex Review — Slice M Close (authoritative pass)

## Scope

Six phase commits plus the fallback-review closure commit land Slice M:

- `886f487` Phase 1: ConversationTurn + QueryNLRequest.prior_turns (schema-only)
- `6cee834` Phase 2: additive complete_turns LLM seam + DEC-071 amendment
- `48707e9` Phase 3: translate() multi-message affordance + prompt framing
- `129747f` Phase 4: thread prior_turns through orchestration + route + proxy
- `6c10a1e` Phase 5: exit-gate two-round refinement test + live_llm twin + canonical-09 §2
- `f81c089` Slice M: close fallback-review findings (2 P2 + info inline)

Cumulative diff: 20 files changed. All modified files are in
`src/app/schemas.py`, `src/app/orchestration.py`, `src/app/routes/nl.py`,
`src/nlp/llm_client.py`, `src/nlp/translator.py`, `src/nlp/prompts/`,
`web/server/api/sp/query/nl.post.ts`, associated test files, and governance/
canonical docs.

## Method

Read the full Slice M diff (`b2f963a..f81c089`), all modified source files at
HEAD, and the prior fallback review artifact. Verified each DEC checklist item
by direct code inspection (not by trusting the governance log). Ran the
architecture-boundary `rg` sweeps, read the schema validator in full, traced
the stateless echo-back path from route → orchestration → translate → seam, and
ran the focused Slice M unit test suite.

## DEC Checklist

### DEC-052 — Boundary: app schema ↔ nlp conversion at orchestration boundary — PASS

`ConversationTurn` objects from the request body are converted to `Message`
dicts at `src/app/orchestration.py:252` via
`[{"role": t.role, "content": t.content} for t in prior_turns]` before the
call to `translate()`. `src/nlp/translator.py` receives only `list[Message]`
(a TypedDict); it never imports or references `ConversationTurn`. Boundary is
clean.

### DEC-071 (amendment) — SYSTEM_PROMPT cached prefix on both seams — PASS

`SYSTEM_PROMPT` is a module-level constant built once at import time in
`src/nlp/prompts/system_prompt.py:92`. Both `complete()` (single-shot) and
`complete_turns()` (multi-turn) in `src/nlp/llm_client.py` receive it as the
`system=` argument; the same reference is passed in both cases from
`src/nlp/translator.py:150,153`. The `is`-identity assertion in
`tests/unit/test_translator.py:331-333` proves the same object reaches both
call sites. No cache-correctness regression.

### DEC-098 — Stateless echo-back; server holds no conversation state — PASS

No session store, no mutable module-level history, no in-memory conversation
accumulation anywhere in `src/app/`. `src/app/routes/nl.py:68` passes
`body.prior_turns` directly to `run_nl_query`; `run_nl_query` converts it and
passes to `translate()`. No state survives the request lifecycle. The client
re-sends the full turn list each request by contract; the server ignores
everything outside the current request. Fully stateless.

### DEC-100 — ConversationTurn validator (starts user / alternates / ends
assistant / 16000-char aggregate cap) — PASS

`src/app/schemas.py:123-162` implements a `@model_validator(mode="after")` on
`QueryNLRequest` that:
- Rejects lists that do not start with a `"user"` turn (line 141)
- Rejects lists that do not end with an `"assistant"` turn (line 144)
- Rejects consecutive same-role turns with a clear error message (line 150)
- Rejects payloads whose total content exceeds `_MAX_PRIOR_TURNS_CONTENT_CHARS`
  (16000) with a descriptive message (line 161)

All four rules are enforced at the request boundary before any LLM call.
Validator tests in `tests/unit/test_app_schemas.py` cover all four branches.

## Architecture Boundaries — PASS

- `rg "from src\.app|import src\.app" src/nlp/` → zero Python imports (two
  docstring-prose mentions only).
- `rg "from src\.nlp|import src\.nlp" src/ontology/` → zero results.
- LLM client is consumed only through the seam interface (`LLMClientProtocol`
  in `src/nlp/llm_client.py`); no direct `anthropic` SDK call sites outside
  that module.

## Prior Fallback Closure Verification

The 2026-05-26 fallback review (APPROVE WITH FOLLOW-UPS) surfaced 2 P2 and
5 P3/info findings. The closure commit `f81c089` addressed both P2s inline.
Verified by direct code inspection:

- **M-CLOSE-001 (P2)** — `_build_turns` role relabeling + alternation not
  enforced. **Verified closed.** `src/app/schemas.py` `@model_validator` now
  enforces that `prior_turns[0].role == "user"`, roles alternate strictly, and
  the list ends on `"assistant"`. A schema-valid request with out-of-order
  roles now returns 422 before reaching `_build_turns`. The silent-relabeling
  behavior can no longer be triggered by a well-formed but out-of-order payload.

- **M-CLOSE-002 (P2)** — No aggregate character cap; worst-case 42 KB to
  billed API. **Verified closed.** `_MAX_PRIOR_TURNS_CONTENT_CHARS = 16000`
  aggregate cap added at `src/app/schemas.py:109,156-162`. Total content across
  all `prior_turns` entries is summed and rejected with 422 if over the limit.

- **M-CLOSE-003 (P3)** — Proxy zod schema `prior_turns` diverged from backend
  nullability (`.optional()` vs `= []`). **Verified closed.**
  `src/app/orchestration.py` also added `prior_turns: list[ConversationTurn] | None = None`
  guard to handle absence gracefully; the orchestration boundary treats None
  and `[]` identically. (The proxy nullability note was addressed via the
  orchestration guard rather than changing the zod schema — an equivalent
  disposition.)

- **M-CLOSE-004 / 005 / 006 / 007 (P3 / info)** — Previously dispositioned:
  M-CLOSE-004 (framing positional note) accepted with comment, M-CLOSE-005
  (still-clarification round untested) accepted as info/out-of-scope,
  M-CLOSE-006 (prompt injection documented by design) accepted with
  DEC-024 rationale, M-CLOSE-007 (dual-type drift) accepted with test cover.
  None required inline fixes; all were explicitly accepted or bucketed at
  slice-close.

## Test Coverage

- **Unit tests:** 147 unit tests pass across all relevant modules
  (test_app_schemas.py, test_app_nl_refinement.py, test_translator.py,
  test_llm_client.py, test_app_routes_nl.py, test_app_orchestration.py).
  Multi-turn path tested: validator branches (all 4 rules), orchestration
  conversion, translate() multi-turn dispatch, llm_client.complete_turns(),
  route threading.
- **Live LLM integration twin:**
  `tests/integration/test_app_nl_refinement_live_llm.py::test_two_round_refinement_reaches_executed_result`
  covers the real two-round contract (API-key-gated; collects cleanly).
- **ruff:** clean on all modified files.
- No coverage gaps found for the features in scope.

## Findings by Severity

### P0

None.

### P1

None.

### P2

None.

### P3

None.

### Info

None.

## Verdict

**APPROVE.** No findings of any severity. All DEC checklist items pass.
Architecture boundaries are clean. Both P2s from the prior fallback review are
verified closed in code (not just in the governance log). The stateless
echo-back invariant holds end-to-end. Test coverage is solid across the full
multi-turn path. **Slice M is ratified.**

## Bucket-M1 Status

Bucket-M1 ("owed authoritative Codex slice-close pass for Slice M, trigger:
~/.codex perms resolved") fires on this pass. **Bucket-M1 closes here.**
Reviews-log row should be updated to record this artifact and the APPROVE
verdict.
