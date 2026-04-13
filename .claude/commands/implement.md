# /implement — Execute One Phase

You are implementing a single phase from an approved structure outline. You will write code and tests for ONE phase, run the tests, and stop.

## Input

$ARGUMENTS

Expected: `path/to/structure-outline.md | phase number`

Example: `thoughts/structure-ast-types-2026-04-13.md | 1`

## Process

1. Read the structure outline to get the phase definition.
2. Read the design discussion it references (for patterns to follow/avoid).
3. Read the implementation checklist at `prompts/dev/implementation-checklist.md`.
4. Implement the phase: write the code, write the tests.
5. Run `uv run pytest tests/ -v` for this phase's tests.
6. Report results.

## On Success

- Report what was implemented and what tests pass.
- Remind the human to run `/commit` followed by `/review`.
- State what the next phase is (from the structure outline).
- Do NOT start the next phase.

## On Failure

- Report the test failures with full output.
- STOP. Do NOT retry. Do NOT attempt to fix automatically.
- The human decides the next step.

## Rules

- Implement ONE phase. Do NOT proceed to the next phase.
- Follow the type signatures and function signatures from the structure outline exactly.
- Type hints on ALL function signatures.
- Pydantic models for all data crossing boundaries (API schemas, AST nodes, config).
- Follow patterns identified in the design discussion.
- Avoid anti-patterns identified in the design discussion.
- If something diverges from the structure outline, STOP and tell the human.
- Read every line of code you generate. No slop.
