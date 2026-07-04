# Scripture Pattern Lab — Project Instructions

## What This Is
An AI-assisted original-language hypothesis exploration platform for Judeo-Christian scripture. Symbolic retrieval is the core engine; AI is the assistant layer. See `docs/canonical/` for the full design specs.

## Non-Negotiable Rules
- Natural language compiles to DSL — never bypass it
- The system must say when it cannot do something yet
- Symbolic retrieval is the core engine; embeddings are supporting
- Results must distinguish match types (exact, conceptual, inverse, expanded, intertwined)
- The corpus is ground truth; user hypotheses and registry entries are priors. The system's job is to test priors, not confirm them.
- No slop. Read and own every line of code generated.

## Why Rigor Exists Here (read this before applying process)
This is a personal study tool built to TEST a specific hypothesis — not to confirm
it. The owner's stated risk: accidentally building a machine that reinforces his own
biases. The evidence the tool produces must stand up to scrutiny by someone using
the same tool to try to DISPROVE the same claims. That is what the heavy process
protects. It does not need to protect theming, tooling, deploy scripts, or UI chrome.

## Rigor Tiers (adopted 2026-07-03; supersedes uniform application of the workflow below)

**Tier E — epistemic core: full methodology.** Applies to any change touching:
- `src/ontology` (registry, verification lifecycle, promotion paths)
- evidence computation in `src/retrieval`, and all of `src/scoring`
- match-type labeling, evidence grading, citation integrity, the honesty protocol,
  lens/absence reporting (DEC-081, DEC-102, DEC-135, DEC-136, DEC-138, DEC-141)
- anything that changes what the system presents as evidence or how claims advance

Full workflow applies: research → design (human review) → structure → implement →
independent review before close. Adversarial design review required when
promotion or evidence semantics change.

**Tier L — everything else: lightweight loop.** UI, theming, infra, deploy,
tooling, ingestion mechanics, docs:
- A short design note (a few paragraphs, inline in conversation or a small file)
  only when the change is genuinely novel — no template, no artifact ceremony
- Implement with tests; commit when green; developer reads every line (unchanged)
- No per-step `/close-step`; one wrap-up at natural stopping points
- Independent review optional — invoke it when a change is large or surprising,
  not by default

**Straddling changes** (e.g. UI that displays evidence): the epistemic part gets
Tier E treatment; the surrounding surface gets Tier L. When unsure which tier
applies, ask — the answer is usually obvious once stated.

## Quality Gates
Universal (both tiers):
- Build vertically (mock → wire → test → next slice), never horizontally (all DB, then all services, then all API)
- Each implementation phase must be testable independently
- No code is complete until tests pass and the developer has read every line

Tier E only:
- Design discussion artifact before implementation begins
- Structure outline before writing code
- Independent code review before declaring closure (typically Codex via `/codex:rescue`) — artifact in `docs/reviews/`, indexed and triaged in `docs/governance/reviews-log.md`. P0/P1/P2 findings (or design `high` findings) must close before the slice closes

## Coding Conventions
- Language: Python 3.12+
- Backend framework: FastAPI
- Type hints required on all function signatures
- Pydantic models for all data structures crossing boundaries (API schemas, AST nodes, config)
- Tests: pytest, one test file per module
- Database: PostgreSQL, SQLAlchemy for ORM, raw SQL for pattern engine queries
- Dependency management: uv
- Formatting: ruff

## Architecture Boundaries
- `src/app/` — FastAPI routes and request/response schemas only
- `src/engine/` — DSL parser and pattern engine (no HTTP, no AI)
- `src/ingestion/` — corpus loaders (file IO + DB bulk insert)
- `src/nlp/` — NL-to-DSL translation and result explanation (AI layer)
- `src/ontology/` — Concept and domain registry access
- `src/retrieval/` — Multi-stage retrieval orchestration
- `src/scoring/` — Scoring and ranking logic
- `src/validation/` — Capability validator (deterministic, no AI)

## Workflow: Before Writing Code (Tier E)
For Tier-E changes (see Rigor Tiers above). Tier-L work skips straight to
implement-with-tests, with at most a short inline design note first.

1. **Research** — Gather objective facts about the current codebase. Do not include the goal in the research prompt. Output: factual notes about relevant code paths, patterns, and types.

2. **Design Discussion** — Create a `design-*.md` artifact in the working directory (template: `prompts/dev/design-discussion-template.md`). ~200 lines max. Must include: current state, desired end state, patterns to follow, patterns to avoid, resolved decisions, open questions. Get human review before proceeding.

3. **Structure Outline** — Create a `structure-*.md` artifact (template: `prompts/dev/structure-outline-template.md`). Like a C header file: phases, new types/signatures, test checkpoints. Must be vertical (each phase is independently testable). Get human review before proceeding.

4. **Implement** — Follow the structure outline phase by phase. Commit after each phase. Run tests between phases. Stop and realign if something diverges from the design.

5. **Close out (per phase)** — At the end of every step AND between phases, run `/close-step`. Do not skip. (See "Phase Discipline" below.)

6. **Slice close (independent review)** — At the end of a complete slice (multiple phases together), run an independent code review (typically Codex via `/codex:rescue` or by spawning the `codex:codex-rescue` subagent) on the cumulative slice diff. Save the artifact to `docs/reviews/review-codex-{flavor}-{slice-id}-{YYYY-MM-DD}.md`, add a row to `docs/governance/reviews-log.md` recording verdict + findings + closure SHAs, and ensure P0/P1/P2 (or design `high`) findings have closed. P3 / info findings either land inline or join a named bucket tracked in `project_status.md`. See `docs/governance/reviews-log.md` for the full process and severity language.

### Phase Discipline (Context Hygiene — Tier E)

Each of `/research`, `/design`, `/structure`, `/implement` is meant to run with
a clean context. The artifacts on disk (`design-*.md`, `structure-*.md`,
governance files, `project_status.md` memory) are the handoff between phases —
not chat history.

- Before a new phase: the assistant runs `/close-step` for the current phase, then recommends `/clear` and names the next command. The user triggers `/clear`.
- `/research` is goal-blind by rule. That only works if prior design conversation is not in context.
- Within one phase, keep context until the phase is done.
- The assistant drives this without being asked. The user should never have to re-explain the methodology.

### Slice Boundaries (Bucket Triage — Tier E findings only)

Independent reviews surface findings; some get fixed inline, others get
deferred to **named buckets** with a stated trigger condition (see
`docs/governance/reviews-log.md`). Buckets are reserved for Tier-E findings;
Tier-L follow-ups go to `ROADMAP_NEXT_STEPS.md` or get fixed inline — no triage
ceremony. To prevent buckets from drifting indefinitely,
both ends of a slice get an explicit triage step:

- **At slice close** (Workflow step 6): every finding from the slice's review pass gets one of three dispositions — *fixed* (with SHA), *deferred to a tracked bucket* (with trigger AND written rationale), or *rejected* (with reason). "Filed and forgotten" is not allowed.
- **At slice start** (before invoking `/research` for the new slice): the assistant scans `reviews-log.md` for buckets whose trigger fires on this slice. Each matching bucket is dispositionalized: *scoped in* (folded into this slice's `/research` and `/design`, with the bucket's closure column updated), *re-deferred* (with a new specific trigger AND new rationale — stale "eventually" deferrals are not allowed), or *rejected* (the original finding no longer applies). Triggers must be specific enough that a future-you can recognize the matching slice without re-reading the original finding.
- The assistant drives this without being asked. The user should not have to remember which bucket fires when.

This is the mechanism that turns "we wrote it down" into "we're going to do it or explicitly decide not to."

### Resume Behavior

When the user opens a session and asks "what's next?":
1. Read `project_status.md` memory for the resume cue.
2. Verify it against current code state (memory can be stale).
3. Present the **full close-out summary**, not just the next command:
   - **Last completed:** step/phase title + the relevant commit SHAs.
   - **What got saved:** decision-log entries, spec-coverage updates, canonical-doc edits, memory files written during the previous session's close-out.
   - **Next step/phase:** title + the exact command to run.
   - **Carry-over context:** non-obvious items from `project_status.md`'s Carry-over section (numbering conflicts, environment gaps, ordering recommendations).
   - **Cross-cutting recommendations:** anything from outside this phase that should land first or alongside (e.g., epistemic-discipline backlog items).

### Command Quick Reference

| Command | Purpose |
|---------|---------|
| `/research` | Gather objective codebase facts (no goal in prompt) |
| `/design` | Create ~200-line design discussion (human review required) |
| `/structure` | Create vertical phase outline (human review required) |
| `/implement` | Execute one phase, run tests |
| `/commit` | Stage and commit changes |
| `/review` | Extract decisions, check spec divergence, update governance |
| `/coverage` | Audit spec-to-code-to-test coverage against REQ markers |
| `/close-step` | Close out a step/phase: confirm clean state, update memory, prep for `/clear` |

## Governance Hygiene
- DEC numbers are reserved for decisions that **constrain future work**.
  Realizations, observations, and routine implementation choices do not get DECs.
- The decision log, spec-coverage, and reviews-log are maintained for Tier-E work.
  Tier-L work is recorded by its commits and CHANGELOG entries.

## Commit Conventions
- Commit after each implementation phase, not at the end
- Commit messages: imperative mood, explain why not what
- Never commit untested code to main

## What Not To Do
- Do not write horizontal plans (all DB → all services → all API)
- Do not put 85+ instructions in a single prompt
- Do not invent features not in the canonical docs without a design discussion
- Do not auto-approve **conceptual** claims — Tier-2 conceptual groupings/equivalences (claims that different expressions "hang together", incl. cross-lemma and phrase-level mappings) are hypotheses the corpus must test and a human must validate (DEC-081, DEC-102). Tier-1 translation-history mappings (a single English word ↔ the Greek lemmas usually translated as it) MAY be auto-generated from authoritative open lexicon data, but only as machine/lexicon-sourced (`origin='lexicon_imported'`), `verification_state='unverified'`, corrigible, and NEVER auto-promoted to `human_confirmed`. See DEC-102 for the tier distinction.
- Do not use RAG as the primary retrieval mechanism
