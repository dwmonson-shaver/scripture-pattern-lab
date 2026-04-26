# Scripture Pattern Lab — Project Instructions

## What This Is
An AI-assisted original-language hypothesis exploration platform for Judeo-Christian scripture. Symbolic retrieval is the core engine; AI is the assistant layer. See `docs/canonical/` for the full design specs.

## Non-Negotiable Rules
- Natural language compiles to DSL — never bypass it
- The system must say when it cannot do something yet
- Symbolic retrieval is the core engine; embeddings are supporting
- Results must distinguish match types (exact, conceptual, inverse, expanded, intertwined)
- No slop. Read and own every line of code generated.

## Quality Gates
- Every feature must have a design discussion artifact before implementation begins
- Every non-trivial change must have a structure outline before writing code
- Build vertically (mock → wire → test → next slice), never horizontally (all DB, then all services, then all API)
- Each implementation phase must be testable independently
- No code is complete until tests pass and the developer has read every line

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
- `src/nlp/` — NL-to-DSL translation and result explanation (AI layer)
- `src/ontology/` — Concept and domain registry access
- `src/retrieval/` — Multi-stage retrieval orchestration
- `src/scoring/` — Scoring and ranking logic
- `src/validation/` — Capability validator (deterministic, no AI)

## Workflow: Before Writing Code
For any feature or non-trivial change:

1. **Research** — Gather objective facts about the current codebase. Do not include the goal in the research prompt. Output: factual notes about relevant code paths, patterns, and types.

2. **Design Discussion** — Create a `design-*.md` artifact in the working directory (template: `prompts/dev/design-discussion-template.md`). ~200 lines max. Must include: current state, desired end state, patterns to follow, patterns to avoid, resolved decisions, open questions. Get human review before proceeding.

3. **Structure Outline** — Create a `structure-*.md` artifact (template: `prompts/dev/structure-outline-template.md`). Like a C header file: phases, new types/signatures, test checkpoints. Must be vertical (each phase is independently testable). Get human review before proceeding.

4. **Implement** — Follow the structure outline phase by phase. Commit after each phase. Run tests between phases. Stop and realign if something diverges from the design.

5. **Close out** — At the end of every step AND between phases, run `/close-step`. Do not skip. (See "Phase Discipline" below.)

### Phase Discipline (Context Hygiene)

Each of `/research`, `/design`, `/structure`, `/implement` is meant to run with
a clean context. The artifacts on disk (`design-*.md`, `structure-*.md`,
governance files, `project_status.md` memory) are the handoff between phases —
not chat history.

- Before a new phase: the assistant runs `/close-step` for the current phase, then recommends `/clear` and names the next command. The user triggers `/clear`.
- `/research` is goal-blind by rule. That only works if prior design conversation is not in context.
- Within one phase, keep context until the phase is done.
- The assistant drives this without being asked. The user should never have to re-explain the methodology.

### Resume Behavior

When the user opens a session and asks "what's next?":
1. Read `project_status.md` memory for the resume cue.
2. Verify it against current code state (memory can be stale).
3. Present the next step/phase + the exact command to run.

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

## Commit Conventions
- Commit after each implementation phase, not at the end
- Commit messages: imperative mood, explain why not what
- Never commit untested code to main

## What Not To Do
- Do not write horizontal plans (all DB → all services → all API)
- Do not put 85+ instructions in a single prompt
- Do not invent features not in the canonical docs without a design discussion
- Do not auto-approve concept registry entries — all mappings are human-reviewed
- Do not use RAG as the primary retrieval mechanism
