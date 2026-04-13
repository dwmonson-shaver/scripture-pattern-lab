# /coverage — Three-Dimensional Spec Coverage Audit

You are auditing which spec requirements have implementations, tests, both, or neither.

## Input

$ARGUMENTS

Optional: a doc number to filter (e.g., `05` to audit only doc 05). If omitted, audit all 9 canonical docs.

## Process

1. Find all `<!-- REQ:NN.slug -->` markers across `docs/canonical/*.md` using Grep.
2. For each requirement marker, spawn the `spec-checker` sub-agent to determine:
   - Does corresponding code exist in `src/`? (implemented | partial | missing)
   - Do corresponding tests exist in `tests/`? (tested | partial | untested)
3. Read `docs/governance/decision-log.md` to find which decisions map to which requirements.
4. Update `docs/governance/spec-coverage.md` with the full coverage matrix.
5. Report a summary: total requirements, implemented count, tested count, gaps.

## Output

Update `docs/governance/spec-coverage.md` with:

```markdown
# Spec Coverage Tracker

Last updated: YYYY-MM-DD

## Summary
- Requirements identified: N
- Implemented: N (N%)
- Tested: N (N%)
- Both: N (N%)
- Neither: N (N%)

## Coverage Matrix

| Req ID | Description | Code | Test | Decision |
|--------|-------------|------|------|----------|
| REQ:05.query-plan | QueryPlan top-level AST | src/engine/models.py | tests/unit/test_models.py | DEC-021 |
| REQ:06.rule-1 | Version compatibility check | — | — | — |
```

Then report the gaps:
- **Specced but not coded**: list of REQ markers with no implementation
- **Coded but not tested**: list of REQ markers with code but no tests
- **Specced but not tested**: list of REQ markers with no tests at all

## Rules

- Only count requirements that have `<!-- REQ:... -->` markers in canonical docs.
- If no REQ markers exist, report this and suggest running Phase 0 (embedding markers).
- Do NOT invent requirement IDs — only use markers found in the docs.
- Commit the updated spec-coverage.md with message: "Update spec coverage report"
