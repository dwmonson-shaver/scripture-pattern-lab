# /orchestrate-slice — Drive a Slice End-to-End in Orchestrator Mode

You are running a full slice (research → design → structure → implement → close)
end-to-end without per-phase user gating. The user trusts the methodology and
wants momentum. Your quality gate is at slice close, not before. Codex
(`codex:codex-rescue`) is the second pair of eyes on high-stakes decisions and
on the cumulative slice diff at close.

## When To Run

Invoke `/orchestrate-slice` when the user signals any of:

- "Run this slice end-to-end"
- "Use the orchestrator"
- "Drive it through" / "expedited" / "streamlined"
- "Same way as Slice C / Slice D"
- "Get it done. Check with me after."

This pattern was validated through Slice C (2026-05-04) and Slice D
(2026-05-09). Default to it when the user authorizes a slice without
qualification.

## What Orchestrator Mode IS

- The **main thread** acts as orchestrator. Sub-agents are dispatched per
  phase: `codebase-researcher` for `/research`, `codex:codex-rescue` for
  high-stakes decisions and Codex review checkpoints, `spec-checker` at slice
  close.
- Every phase boundary is closed automatically (`/close-step`). The user does
  not have to ask.
- Decisions are made autonomously when low-stakes/high-confidence, or with a
  Codex advisory pass when high-stakes/low-confidence. **All decisions are
  surfaced to the user at slice close**, in context against working code.

## What Orchestrator Mode IS NOT

- It is not "decide everything yourself with no oversight" — Codex is on
  high-stakes calls.
- It is not "skip the methodology" — every command (`/research`, `/design`,
  `/structure`, `/implement`, `/commit`, `/review`, `/coverage`,
  `/close-step`) still runs. The user just doesn't gate on each one.
- It is not "skip canonical-doc updates" — REQ markers, decision log entries,
  and spec-coverage updates land at slice close.

---

## Phase Sequence (the spine)

For each slice, in order:

1. **Slice-start bucket triage** — before `/research`, scan
   `docs/governance/reviews-log.md` for buckets whose trigger matches this
   slice. Each matching bucket gets one of: *scope in*, *re-defer with new
   trigger + new rationale*, or *reject with reason*. No silent deferrals.
   Record the dispositions in the slice's eventual `/review` artifact.
2. **`/research`** — goal-blind fact gathering. Spawn `codebase-researcher`
   sub-agents (parallel where possible, partitioned by surface area). Assemble
   into `thoughts/research-{slug}-{date}.md`. **Do not include the slice goal
   in the sub-agent prompt** — that's the goal-blind contract.
3. **`/design`** — produce `thoughts/design-{slug}-{date}.md` (~200 lines):
   current state, desired end state, patterns to follow/avoid, resolved
   decisions, open questions. **In orchestrator mode, the design artifact is
   not gated on user review** — it is part of the slice's reviewable state at
   close.
4. **`/structure`** — vertical phase outline (each phase independently
   testable). Same close-out norm: not gated on user review.
5. **`/implement`** — execute phase by phase. `/commit` after each phase.
   Tests must pass between phases.
6. **Mid-slice Codex checkpoint(s)** — at meaningful midpoints (typically
   after a coherent pair of phases, e.g., D1+D2, D3+D4), spawn
   `codex:codex-rescue` for a code review on the cumulative diff. Save the
   artifact to `docs/reviews/review-codex-{flavor}-{slice-id}-{checkpoint}-{date}.md`.
   Address P0/P1/P2 findings inline before continuing.
7. **Slice-close Codex review** — full cumulative slice diff.
   `docs/reviews/review-codex-{flavor}-{slice-id}-close-{date}.md`. P0/P1/P2
   (or design `high`) findings must close before the slice closes. P3 / info
   findings either land inline or join a named bucket.
8. **`/review` + `/coverage`** — extract decisions, update
   `docs/governance/decision-log.md`, update `docs/governance/spec-coverage.md`,
   add the row to `docs/governance/reviews-log.md`.
9. **`/close-step`** — final close-out: update `project_status.md` memory,
   note next-slice options (do not pre-decide), surface the slice-end summary.
10. **Check in with the user** — slice closed. Surface the full close-out
    summary; await authorization for the next slice.

---

## Decision Rule (mid-slice, autonomous)

For every decision that would otherwise become a DEC entry:

### Low-stakes + high-confidence → decide autonomously, record DEC inline

Examples:
- Choosing a column type, file location, or test fixture style where one
  answer is clearly better.
- Picking among two implementation patterns where one already appears in
  the codebase and the other doesn't.
- Naming a private helper function.

### High-stakes OR low-confidence → spawn `codex:codex-rescue` first

Examples:
- "Touches DEC-024 (corpus is ground truth) directly."
- "New architecture boundary in CLAUDE.md."
- "Contradicts or amends an existing DEC."
- "Picks among options where canonical specs and codebase patterns don't
  clearly constrain the answer."
- "Requires inserting a new section into a canonical doc with a new REQ
  marker."

When invoking Codex, brief it on:
- The decision being made.
- The options considered.
- The constraints (DECs, canonical specs, code patterns).
- The specific question (e.g., "is option A better than option B for reason X?").

Save the Codex output path in the DEC's `Sources:` line so the user can audit
at slice close.

### All decisions get reviewed with the user at slice close

Not before. Pre-review of every DEC turns autonomous orchestration into
rubber-stamping (the failure mode the user named on 2026-05-08).

---

## Phase Discipline (Context Hygiene)

- Each phase (`/research`, `/design`, `/structure`, `/implement`) must run
  with a **clean context**. The artifacts on disk plus `project_status.md`
  memory are the handoff between phases — not chat history.
- Drive `/close-step` automatically at every phase boundary. Recommend
  `/clear` and name the next command. The user triggers `/clear`.
- `/research` is goal-blind by rule. That only works if prior design
  conversation is not in context.
- Within one phase, keep context until the phase is done.

In orchestrator mode, you may collapse phase-boundary `/clear` if the slice
is small (cookbook-shape, doc-shape, single-file changes) and the user has
not signaled context-hygiene concern. For multi-file code slices like C and
D, do not collapse — the full clean-context cycle is part of the validated
pattern.

---

## Rescope Signal — STOP if user names rubber-stamping

If the user says any version of:
- "I'm just rubber-stamping these questions."
- "I don't have meaningful input here."
- "These OQs feel premature."

Treat it as a **structural signal that the current slice is asking for
judgment about things that don't yet exist concretely**. Stop pushing through
abstract decisions. Propose a slice rescope that delivers a runnable
observable surface the user can react to.

Do not respond with "let me decide for you autonomously" or "let me delegate
to an agent" — both push the same problem down a level.

DEC-051 is the precedent: Slice C's Track 2 (result contextualization) was
rescoped out when the user rubber-stamped calibration OQs against an empty
executor; Track 2 deferred to Slice D with sharpened trigger "after CLI ships
and the user has interacted with real result counts."

---

## Slice-Close Checklist (Workflow Step 6)

Before declaring the slice closed:

- [ ] All P0/P1/P2 (or design `high`) findings from the slice's Codex review
      are closed with commit SHAs in `reviews-log.md`.
- [ ] P3 / info findings either fixed inline OR added to a named bucket with
      *trigger* + *written rationale*.
- [ ] Every open bucket from prior slices has been triaged at slice start
      (the rule fires on the slice's character, not a checklist item).
- [ ] DECs landed during the slice are listed in
      `docs/governance/decision-log.md` with sources.
- [ ] REQ markers touched are reflected in
      `docs/governance/spec-coverage.md`.
- [ ] Slice exit gate test (the observable, runnable end-to-end criterion
      named in the structure outline) is green.
- [ ] `project_status.md` memory updated with: closing SHA chain, what
      landed, DECs landed, Codex review trail, buckets state, OQs still
      deferred, next-slice options (without pre-deciding).
- [ ] **User check-in.** Surface the full close-out summary; do not
      authorize the next slice without explicit user direction.

---

## Slice-Start Checklist (before `/research`)

- [ ] Slice ID assigned (next letter in sequence — A, B, C, D, ...).
- [ ] Slice target end-state stated in one paragraph.
- [ ] Slice exit gate proposed (observable, runnable; refine in `/structure`).
- [ ] Bucket-triage scan complete; matching buckets dispositioned.
- [ ] User has authorized this slice (do not auto-start a slice without
      authorization, even in orchestrator mode).

---

## What To Tell The User

At slice start:
- Slice ID + one-paragraph target.
- Bucket triage results (which buckets fire, which dispositions).
- Proposed slice exit gate.
- "Starting Phase 1: `/research`."

At each phase boundary:
- One-line update: phase complete, artifact path, next phase command.
- Recommend `/clear` if the next phase needs goal-blind context.

At slice close:
- Closing SHA chain.
- DECs landed (numbers + one-line each).
- Codex review trail (paths + verdicts).
- Buckets state (any new, any closed).
- Slice exit gate verification.
- Next-slice options (surfaced but not pre-decided).
- "Awaiting your direction on the next slice."

---

## Memory Touchpoints

This skill consolidates the playbook from these memory entries (still
authoritative on edge cases):

- `feedback_dec_autonomy.md` — autonomous DECs + Codex on high-stakes.
- `feedback_close_out.md` — drive `/close-step` automatically.
- `feedback_bucket_triage.md` — slice-boundary bucket triage.
- `feedback_resume_summary.md` — close-out summary format.
- `feedback_rubber_stamp_signal.md` — rescope rather than push through.

Update `project_status.md` at every slice close per the resume-summary format.

---

## Rules

- The orchestrator does NOT skip canonical-doc updates, REQ markers, or
  decision logging. It moves through them autonomously.
- The orchestrator does NOT auto-run `/clear` — recommend it, then stop.
- The orchestrator does NOT pre-decide the next slice. After close, surface
  options and check in.
- The orchestrator DOES drive close-out automatically at every phase and
  slice boundary.
- The orchestrator DOES pause and rescope if the user names rubber-stamping.
- The orchestrator DOES spawn `codex:codex-rescue` for high-stakes decisions
  without asking permission first — that is the second-pair-of-eyes contract.
