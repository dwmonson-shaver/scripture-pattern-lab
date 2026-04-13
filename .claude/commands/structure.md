# /structure — Vertical Phase Outline

You are creating a structure outline for an approved design discussion. This is the "C header file" — it defines WHAT will exist (types, signatures, phases) without writing the full implementation.

## Input

$ARGUMENTS

Expected: path to an approved design discussion artifact (e.g., `thoughts/design-ast-types-2026-04-13.md`).

If not provided, check `thoughts/design-*.md` for the most recent one with `status: approved` and confirm with the human.

## Process

1. Read the approved design discussion artifact.
2. Read the research artifact it references.
3. Use the template at `prompts/dev/structure-outline-template.md` as the output structure.
4. Break the implementation into vertical phases — each phase is independently testable.
5. For each phase, include: files touched, what happens, test checkpoint.
6. Include Pydantic type stubs and function signatures (no implementation bodies).

## Output

Write to `thoughts/structure-{slug}-{date}.md` using the same slug as the design.

Use this frontmatter:

```yaml
---
type: structure-outline
feature: feature-name
date: YYYY-MM-DD
status: draft
design_ref: thoughts/design-*.md
phases: []
---
```

## Rules

- Each phase MUST be independently testable. Build vertically, not horizontally.
- VERTICAL means: mock data or stub -> wire it up -> test it -> move on.
- HORIZONTAL means: all DB -> all services -> all API. DO NOT DO THIS.
- If any phase touches more than 3 files, it is probably too broad. Consider splitting.
- Include type stubs (Pydantic model shapes) and function signatures with one-line docstrings.
- No implementation bodies. This is a header file.
- List dependencies between phases — which must complete before others can start.
- List what is explicitly OUT OF SCOPE to prevent drift.
- STOP after writing the artifact. Do NOT proceed to implementation.
- Tell the human: "Review this structure outline. Reply with approvals or changes before implementation begins."
