# /review — Decision Extraction and Spec Feedback

You are reviewing the decisions made during recent implementation work. This command extracts decisions, checks for spec divergence, and updates governance files.

## When To Run

After `/commit`, or periodically after completing all phases of a feature. Skippable for purely mechanical changes (formatting, typo fixes).

## Process

### Step 1: Gather Context
1. Read the recent git diff(s) since the last `/review` (or the last few commits if unclear).
2. Review the current conversation context for decisions that were made.

### Step 2: Extract Decisions
A decision is any choice between alternatives that shaped the code. Look for:
- Technology or library choices
- Data structure choices (e.g., Pydantic vs dataclass)
- Algorithm or approach selections
- Deviations from the structure outline
- Tradeoffs that were made (performance vs simplicity, etc.)
- Interpretations of ambiguous spec requirements

For each decision, format:
```
DECISION: [short title]
  Question: [what question did this resolve?]
  Choice: [what was chosen]
  Rationale: [why]
  Confidence: High | Medium | Low
  Spec refs: [REQ:NN.slug if applicable]
  Files: [which files were affected]
```

### Step 3: Present for Review
Present ALL extracted decisions to the human. For each one, ask: approve, reject, or edit.
- If none found, report "No decisions identified — this was a mechanical change."

### Step 4: Check Spec Divergence
Spawn the `spec-checker` sub-agent to compare recent code changes against canonical docs.
- If divergences found, surface them: "REQ:05.order-operator says X, your code does Y."
- The human decides whether to update the spec (a SEPARATE act) or change the code.
- Do NOT update canonical docs directly. Flag them for the human.

### Step 5: Update Governance Files
For approved decisions:
1. Read `docs/governance/decision-log.md` to find the current highest DEC-NNN number.
2. Append new entries continuing the numbering, using this format:
   ```markdown
   ## DEC-NNN — [short title]
   - Status: Accepted
   - Question: [what question did this resolve?]
   - Decision: [what was chosen]
   - Rationale: [why]
   - Confidence: High | Medium | Low
   - Made-by: human-approved
   - Commit: [short SHA]
   - Files: [affected files]
   - Spec refs: [REQ:NN.slug]
   ```
3. Update `docs/governance/spec-coverage.md` if any REQ markers are now implemented or tested.
4. Commit the governance file updates separately with message: "Update decision log and spec coverage"

## Rules

- Do NOT auto-approve decisions. Every decision must be presented to the human.
- Do NOT modify canonical docs in `docs/canonical/`. Only flag divergences.
- Governance file updates are their own commit, separate from code commits.
- If the human rejects a decision, note it but do not attempt to modify code. The human handles that.
- Keep the decision log format consistent with existing DEC-001 through DEC-020 entries.
