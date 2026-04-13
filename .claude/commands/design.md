# /design — Design Discussion Artifact

You are creating a design discussion artifact for a feature. This is where the goal is first introduced. The purpose is to surface what you think, catch mistakes early, and align with the human before any code is written.

## Input

$ARGUMENTS

Expected format: `feature-name | goal (one sentence) | path/to/research/artifact`

If the research artifact path is not provided, check `thoughts/research-*.md` for the most recent one and confirm with the human.

## Process

1. Read the research artifact to ground the design in codebase facts.
2. Read relevant canonical docs from `docs/canonical/` (identified by the research).
3. Read the decision log at `docs/governance/decision-log.md` for relevant prior decisions.
4. Spawn the `spec-checker` sub-agent to identify which `<!-- REQ:... -->` markers this feature touches.
5. Use the template at `prompts/dev/design-discussion-template.md` as the output structure.
6. Write the design discussion artifact.

## Output

Write to `thoughts/design-{slug}-{date}.md` where:
- `{slug}` is a short kebab-case name for the feature
- `{date}` is today's date in YYYY-MM-DD format

Use this frontmatter:

```yaml
---
type: design-discussion
feature: feature-name
date: YYYY-MM-DD
status: draft
research_ref: thoughts/research-*.md
canonical_refs: []
requirement_ids: []
---
```

## Rules

- The design discussion must be UNDER 200 LINES.
- Reference specific files, functions, and types from the research artifact.
- Identify patterns to follow AND patterns to avoid from the existing codebase.
- List every design decision as a numbered row in the Key Design Decisions table.
- In the "Spec Requirements Touched" section, list each REQ marker this feature implements.
- Include open questions — things you don't know that need human input.
- STOP after writing the artifact. Do NOT proceed to structure or implementation.
- Tell the human: "Review this design discussion. Reply with approvals, changes, or questions before proceeding."
