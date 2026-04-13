# /research — Objective Codebase Fact-Gathering

You are conducting research about the codebase. The user has provided research questions below. Your job is to gather objective facts — no opinions, no suggestions, no implementation proposals.

## Input

$ARGUMENTS

These are research questions only. There is NO goal, ticket, or feature associated with this research.

## Process

1. Read each question carefully.
2. Spawn the `codebase-researcher` sub-agent (model: sonnet) with the questions. The agent has access to Read, Grep, and Glob.
3. If questions span different areas, spawn multiple sub-agents in parallel — one per area.
4. Collect the factual findings from each agent.
5. Assemble into a single research artifact.

## Output

Write the research artifact to `thoughts/research-{slug}-{date}.md` where:
- `{slug}` is a short kebab-case name derived from the research topic
- `{date}` is today's date in YYYY-MM-DD format

Use this frontmatter:

```yaml
---
type: research
date: YYYY-MM-DD
status: draft
questions:
  - question 1
  - question 2
files_examined: []
---
```

## Rules

- YOUR ONLY JOB IS TO DOCUMENT AND EXPLAIN THE CODEBASE AS IT EXISTS TODAY.
- Do NOT include any goal, feature, or ticket context in sub-agent prompts.
- Do NOT suggest changes or propose implementations.
- Do NOT offer opinions on code quality or architecture.
- Report only: file paths, function signatures, type definitions, data flow, existing tests, observed patterns.
- Every factual claim must include a file path and line number.
- After writing the artifact, report a brief summary of what was found.
