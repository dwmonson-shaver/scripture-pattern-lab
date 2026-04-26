# /close-step — Close out a step or phase, prepare for clean context switch

You are closing out a unit of work in the spec-driven harness — either a full
step from the corpus-ingestion / pattern-engine roadmap, or a phase within a
step (research → design → structure → implement). The goal is that after
`/clear` and a fresh session, the user can ask "what's next?" and pick up
without re-explanation.

## When To Run

**Automatically**, at the end of every step or phase. The assistant drives
this — do NOT wait for the user to ask. (See feedback memory:
"Drive step close-out automatically".)

Run it after the unit's work is committed and tests pass. Do not run it
mid-phase.

## Process

### Step 1: Confirm clean state
1. Run `git status`. If there are uncommitted changes belonging to this unit,
   stop and run `/commit` first.
2. Run the test suite for the affected modules. If tests fail, stop and fix.
3. Verify any new files referenced in the design / structure artifact actually
   exist.

### Step 2: Extract decisions (if any)
1. If decisions were made during this unit (technology choice, deviation from
   the structure outline, interpretation of an ambiguous spec), run `/review`.
2. `/review` handles approval and updates `docs/governance/decision-log.md`.
3. If the unit was purely mechanical (e.g., fetch script, gitignore tweak),
   note "no decisions" and skip the decision-log update.

### Step 3: Update spec coverage (if REQ markers were touched)
1. If new code implements or tests a `<!-- REQ:NN.slug -->` marker, run
   `/coverage` or update `docs/governance/spec-coverage.md` directly.
2. Skip if no REQ markers were involved.

### Step 4: Update project status memory
1. Read the user's `project_status.md` memory file.
2. Mark this step or phase as ✅ done with the commit SHA(s) and the date.
3. Write a clear handoff for the next unit:
   - The next step/phase number and title.
   - Any **carry-over context** the next session needs but that is NOT in the
     code or canonical docs (format gotchas, surprising findings, decisions
     deferred, alternative approaches considered and rejected).
   - The exact command to run next (e.g., "Run `/research` on the parser
     problem").

### Step 5: Announce close-out
Tell the user:
- What was closed out (step/phase + commit SHAs).
- What got saved (memory updates, decision-log entries, coverage updates).
- The recommended next move: `/clear`, then run `<next command>`.

Do not auto-run `/clear` — that is a context-destroying operation the user
should trigger themselves.

## Rules

- This command does NOT make code changes. It only updates governance,
  memory, and reports state.
- Do NOT skip the carry-over context in Step 4. The whole point is that
  `/clear` doesn't lose facts that aren't otherwise written down.
- Do NOT auto-run `/clear`. Recommend it, then stop.
- If `/review` finds decisions and the user has not yet approved them, the
  close-out is not complete — wait for approval before updating
  `project_status.md`.
- If the unit was a phase (not a full step), the memory update should
  reflect "phase X of step Y done" so the next session resumes at phase X+1.
