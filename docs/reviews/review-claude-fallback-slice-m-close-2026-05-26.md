---
type: code-review
flavor: claude-fallback
slice: M
base_sha: b2f963a
head_sha: 6c10a1e
date: 2026-05-26
scope: >
  Cumulative diff of Slice M (conversational query refinement),
  `git diff b2f963a..HEAD`, phase commits 886f487..6c10a1e. Stateless
  caller-driven multi-turn refinement: ConversationTurn schema + prior_turns
  on QueryNLRequest, additive complete_turns() LLM seam, translate()
  multi-message affordance, orchestration/route/proxy threading,
  canonical-09 + DEC-071 amendment.
verdict: APPROVE WITH FOLLOW-UPS
findings_summary:
  P0: 0
  P1: 0
  P2: 2
  P3: 2
  info: 3
---

# Slice M close — independent review (Claude fallback flavor)

Codex was quota-blocked; this fallback pass runs the project's standard
severity language and the same focus checklist. I read every changed file in
full (not just hunks), plus the design + structure artifacts for grounding,
and ran the boundary grep.

## Verdict

**APPROVE WITH FOLLOW-UPS.** The slice is well-built and matches its resolved
design decisions closely. The stateless echo-back is correct, the single-shot
path is genuinely preserved (`if not prior_turns` short-circuits to
`complete()` with the identical message construction), the system-prompt cache
prefix is provably identical across both seams (asserted by an `is`-identity
test), and the `src/nlp` → `src/app` boundary holds. Test coverage is strong
and the exit-gate test proves the real two-round contract rather than
over-stubbing it.

No P0 or P1. Two P2 findings concern client-controllable inputs that can reach
the Anthropic API in a shape that produces a 500 (a bad-request bug surfaced as
an internal error) — neither is a security or data-loss issue, but both are
"caller can trigger a 500 with a well-formed-per-schema request," which the
project's own error-mapping discipline (DEC-070: 4xx request bugs are 500, but
the request shouldn't be malformable from a schema-valid body) argues should be
caught before the API call. They are must-fix-before-slice-close.

## Boundary check (requested explicitly)

`grep -rn "from src.app\|import src.app" src/nlp/` → **only two hits, both in
docstring prose** (`llm_client.py:29`, `translator.py:139`), no actual imports.
**The src/nlp → src/app boundary holds.** The app layer converts
`ConversationTurn` → `Message` dict in `orchestration.run_nl_query`
(orchestration.py:182-186) before calling `translate()`; the nlp layer only
ever sees the local `Message` TypedDict.

---

## Findings

### M-CLOSE-001 — P2 — `_build_turns` silently relabels `prior_turns[0]` to role="user" and never enforces Anthropic's first-message-must-be-user / alternation contract

**File:** `src/nlp/translator.py:175-179` (and the schema that permits it,
`src/app/schemas.py:85`)

**Problem.** `ConversationTurn.role` is `Literal["user", "assistant"]` with no
positional constraint, and `QueryNLRequest.prior_turns` accepts any list of up
to 20 such turns in any order. `_build_turns` assumes `prior_turns[0]` is the
original user query and *forces* it to `{"role": "user", ...}` regardless of
the actual role:

```python
first: Message = {
    "role": "user",
    "content": _build_user_message(prior_turns[0]["content"], context),
}
return [first, *prior_turns[1:], {"role": "user", "content": nl_query}]
```

Two distinct defects fall out of this:

1. **Silent role relabeling.** If a client sends `prior_turns[0]` with
   role="assistant", its content is silently relabeled as a user turn and
   wrapped in the registry-summary framing. The docstring states the caller
   contract ("`prior_turns[0]` is the original user query (role 'user')") but
   nothing enforces it — a schema-valid request violates the unenforced
   contract and gets quietly reinterpreted.

2. **No alternation guarantee → client-triggerable 500.** The Anthropic
   Messages API requires roles to strictly alternate after the first user
   message. `prior_turns[1:]` is spliced in verbatim. A schema-valid body like
   `prior_turns=[{user}, {user}]` (or `[{assistant}, {assistant}]`) produces a
   `messages` array with two consecutive same-role turns. Anthropic rejects
   that with `BadRequestError` (400), which by design (DEC-070, H-H1H2-001)
   propagates raw and the route returns **500 internal_error**. So a caller can
   provoke a 500 with a request that passed every validation layer.

**Suggested fix.** Add a deterministic, AI-free guard at the boundary — either
in `ConversationTurn`/`QueryNLRequest` validation or in `_build_turns` — that
either (a) rejects malformed conversations with a 422 (e.g.
`nl_compile_error`-style or a new `invalid_conversation` code) when
`prior_turns[0].role != "user"` or roles don't alternate, or (b) at minimum
validates `prior_turns[0].role == "user"` and stops silently relabeling. Given
the project's "the system must say when it cannot do something" charter, an
explicit 422 is the more honest choice than letting a malformed conversation
become a surprise 500. A model-level Pydantic `@model_validator` on
`QueryNLRequest` keeps this AI-free and inside the existing schema seam.

---

### M-CLOSE-002 — P2 — Token/DoS bound is per-turn × count only; no aggregate cap, and the worst case is ~42 KB of attacker-chosen text per request straight into the metered LLM

**File:** `src/app/schemas.py:86,98`; `web/server/api/sp/query/nl.post.ts:14-23`

**Problem.** The bounds are `content max_length=2000` per turn, `prior_turns
max_length=20`, plus `nl_query max_length=2000`. The realized worst case sent to
Anthropic is `20 × 2000 + 2000 = 42,000` characters of caller-controlled text,
every request, with **no aggregate byte/char cap and no rate limit at this
layer**. The design (design doc line 76, "note but do not over-engineer") and
the slice framing both call `max_length=20` a *resource guard, not a semantic
cap* — but a resource guard that still admits 42 KB/request to a metered
provider on a $0 hosting tier is a weak guard. Because the refinement is
stateless echo-back, nothing stops a caller from resubmitting maximal payloads
in a tight loop; each one is a full multi-message LLM call billed in tokens.

This is below P1 because: it requires a deliberately abusive caller (the system
is single-user/solo today per the separation note), there's no correctness or
secret-leak impact, and the per-field bounds do prevent the truly unbounded
case. But "42 KB of arbitrary prose per request to a billed API with no
aggregate cap" is a real cost-exposure footgun that should be dispositioned
before slice close — either tightened or explicitly bucketed with a trigger
(e.g. "revisit when the route is exposed beyond single-user").

**Suggested fix.** Either (a) add a `@model_validator` on `QueryNLRequest` that
caps the *total* characters across `nl_query` + all `prior_turns[].content`
(e.g. 8–10 KB, comfortably above any honest refinement conversation), or (b)
explicitly defer to a named bucket in `reviews-log.md` with the trigger "before
the NL route is reachable by more than the solo operator" and a written
rationale. "Filed and forgotten" is not allowed per the slice-close triage
rule, so this must get one of those two dispositions, not silence.

---

### M-CLOSE-003 — P3 — Proxy zod schema diverges from backend nullability: backend default is `[]` (always a list), proxy makes it `.optional()` (may be `undefined`)

**File:** `web/server/api/sp/query/nl.post.ts:15-23` vs `src/app/schemas.py:98`

**Problem.** Backend: `prior_turns: list[ConversationTurn] = Field(default_factory=list, max_length=20)` — omitting the field yields `[]`. Proxy:
`prior_turns: z.array(...).max(20).optional()` — omitting yields `undefined`,
and the proxy forwards `body` verbatim, so the backend receives a body with no
`prior_turns` key (fine, backend defaults it) OR `prior_turns: undefined` which
serializes away. Functionally equivalent today, but the two contracts don't
match: the proxy test even asserts `parsed.prior_turns` is `undefined`
(nl.post.test.ts:19), codifying the divergence. Bounds (role enum, content
1..2000, list max 20) *do* mirror correctly — only nullability drifts.

**Suggested fix.** Either `.default([])` on the zod schema to mirror the backend
exactly, or add a one-line comment in the proxy noting the intentional
optional-vs-default divergence and that both serialize to "backend applies its
default." Low stakes; fix inline or note.

---

### M-CLOSE-004 — P3 — `_build_turns` registry-summary framing only ever lands on `prior_turns[0]`; a forged/reordered first turn loses the framing silently

**File:** `src/nlp/translator.py:175-179`

**Problem.** Closely related to M-CLOSE-001 but worth its own note even if 001 is
fixed by a first-turn-role check rather than a full rebuild: the registry
summaries (capability + concept) are attached *only* to `turns[0]`. This is
correct for the happy path (it mirrors single-shot exactly, and the test at
test_translator.py:283-285 proves it), but it means the framing is positional,
not semantic. If a future caller or UI ever sends a conversation that doesn't
start with the original NL as turn 0 (e.g. a system-style preamble, or a
truncated history that dropped turn 0), the model loses the registry context
entirely with no signal. Today's two-round flow never does this, so it's P3.

**Suggested fix.** Once M-CLOSE-001's first-turn contract is enforced, this is
largely moot. If you keep the positional approach, add an assertion/comment that
turn 0 is contractually the original NL and that the framing is positional by
design, so a future author doesn't assume the summaries ride every user turn.

---

### M-CLOSE-005 — info — Two-round-still-clarification (round 2 re-clarifies) is untested

**File:** tests cover ambiguous→clarification→answered→executed
(test_app_nl_refinement.py, test_translator.py:292) but not
ambiguous→clarification→still-ambiguous-answer→clarification-again.

The slice framing explicitly notes "the server never decides to stop
clarifying — the caller quits by not resubmitting," which implies a second
clarification round is a supported state. There is no test that a multi-turn
request (`prior_turns` present) can itself *return* a `TranslationNeedsClarification`
and that the route surfaces it as a 200 clarification (not a 500/422). The code
path supports it (`_parse_output` is shared and returns the clarification
variant regardless of seam), but it's unproven. Worth one deterministic test:
`complete_turns()` returns a `Clarification:` block → assert 200 with
`clarification` set. Not blocking; the shared `_parse_output` makes the behavior
very likely correct.

---

### M-CLOSE-006 — info — Prompt-injection via forged assistant turn is accepted-by-design but undocumented in code

**File:** `src/nlp/translator.py` (the `prior_turns` path)

A client can forge an assistant turn ("you said use window 50") and steer the
re-translation. The design doc (line 76) explicitly accepts this for a
single-user system and leans on DEC-024 (corpus is ground truth) — the
translator re-evaluates from the cookbook regardless. That's a defensible call.
I'm noting it only because the *code* carries no comment about it; if this route
is ever exposed multi-user, the acceptance rationale lives only in the design
artifact. A one-line comment at the `complete_turns` call site pointing at the
DEC-024 acceptance would keep the rationale with the code. No action required
this slice.

---

### M-CLOSE-007 — info — `Message` TypedDict and `ConversationTurn` are duplicated shapes by necessity; conversion is unguarded against future field drift

**File:** `src/nlp/llm_client.py:23-33`, `src/app/schemas.py:79-86`,
`src/app/orchestration.py:182-186`

The boundary conversion `{"role": t.role, "content": t.content}` is hand-rolled
and correct today. Because `Message` (nlp) and `ConversationTurn` (app) are
deliberately separate types (to preserve the boundary), there's no compile-time
link between them — if `ConversationTurn` ever gains a field that `Message`
needs, the conversion silently drops it. This is the correct tradeoff for the
boundary discipline; just flagging that the two types must be kept in sync by
hand. The conversion is well-tested (test_app_orchestration.py:717-755). No
action.

---

## What I checked and found clean

- **Single-shot byte-identical preservation** — `if not prior_turns` routes to
  the unchanged `complete()` with the unchanged `_build_user_message`. None of
  the single-shot construction was touched. Proven by
  test_translator.py:248-258 and test_app_orchestration.py:668-715.
- **Cache-prefix claim (system prompt identical across seams)** — `SYSTEM_PROMPT`
  is passed by reference to both seams; `complete_turns` puts it in `system=`
  exactly like `complete`. Proven by `is`-identity assertion
  (test_translator.py:331-333, test_llm_client.py:322).
- **Exception classification shared across seams** — `_UNAVAILABLE_ERRORS`
  tuple is shared; both seams wrap the same families as `LLMUnavailable` and let
  4xx propagate raw. Refactor is clean and tested on both seams.
- **`_build_turns` indexing safety for the empty case** — `prior_turns[0]` is
  only reached inside the `else` of `if not prior_turns`, so it is never indexed
  on an empty/None list. No IndexError. (The *role* of `[0]` is the M-CLOSE-001
  concern, not the index.)
- **Frozen Pydantic / type hints / house style** — `ConversationTurn` is
  `frozen=True`, all new signatures are typed, the `Message` TypedDict is the
  right tool for the LLM-array element. Consistent with the codebase.
- **Route threading** — `body.prior_turns` flows route → orchestration →
  translate cleanly; all existing error mappings unchanged.
- **Proxy passthrough** — the validated `body` (including `prior_turns`) is
  forwarded to the backend; the proxy no longer strips the field. Bounds mirror
  backend (modulo the nullability nit in M-CLOSE-003).
- **Canonical-09 §2 vs code** — the prose amendment accurately describes the
  implemented behavior (stateless echo-back, same route, additive seam, cache
  prefix, boundary crossing). No spec/code drift found.
- **DEC-071 amendment** — correctly scoped as "single-shot stays default,
  multi-turn is opt-in," does not rewrite the original decision.

## Disposition guidance for the orchestrator

- **M-CLOSE-001 (P2)** and **M-CLOSE-002 (P2)** must be dispositioned before
  slice close: fixed (with SHA), or deferred to a named bucket with a specific
  trigger + written rationale. 001 is a small deterministic validator; 002 is a
  small aggregate-cap validator or an explicit trigger-bound bucket.
- **M-CLOSE-003 / 004 (P3)** — fix inline (both are tiny) or bucket.
- **M-CLOSE-005/006/007 (info)** — author's discretion; 005 is the most
  worthwhile (one cheap test for a supported state).
