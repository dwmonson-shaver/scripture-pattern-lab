---
type: code-review
flavor: claude-fallback
slice_id: slice-e
date: 2026-05-09
verdict: needs-attention
base_sha: 4e57cf0
scope: docs/agent/* + .claude/commands/orchestrate-slice.md (5 commits)
findings_summary: "0 P0, 3 P1, 3 P2, 3 P3, 3 info"
note: "Independent fallback review; Codex blocked by .codex permissions."
---

# Independent Review — Slice E Close

**Scope:** `git diff 4e57cf0..HEAD`
**Files:** `docs/agent/dsl-cookbook.md`, `docs/agent/prompt-template.md`, `.claude/commands/orchestrate-slice.md`
**Purpose:** Verify cookbook accuracy against live code before agents consume it. A cookbook that misrepresents what the code does teaches agents to fail.

---

## Summary of Findings

| ID | Severity | Area |
|----|----------|------|
| E-CLOSE-001 | P1 | `UnsupportedPlanShape` stderr format (cookbook misquotes exact string) |
| E-CLOSE-002 | P1 | `Status: unsupported` stderr recognition (cookbook misquotes prefix) |
| E-CLOSE-003 | P1 | Polarity marked `❌ parses, validator rejects` — MVP registry has `polarity_support=True`, so validator does NOT reject polarity; executor does |
| E-CLOSE-004 | P2 | `concept not mapped` stderr quote does not match actual message |
| E-CLOSE-005 | P2 | `RegistryRequired` stderr quote does not match actual message |
| E-CLOSE-006 | P2 | Zero-match output format: cookbook shows `(showing first 0):` with blank block; code prints `Found 0 matches.` with no candidate block |
| E-CLOSE-007 | P3 | Cookbook quick-reference says polarity "parses, validator rejects" — same root as E-CLOSE-003; consistency fix needed once P1 is resolved |
| E-CLOSE-008 | P3 | Worked Example 1: two duplicate alignment blocks shown for the same verse/chain — may confuse agents about why duplicates appear |
| E-CLOSE-009 | P3 | `>>` operator: cookbook marks it `❌ parses, raises UnsupportedPlanShape` but MVP capability registry includes `adjacency` in `operators` list, meaning validator passes it and executor raises the shape error — the categorization is accurate but the failure path description is subtly wrong |
| E-CLOSE-010 | info | `Match type:` header line only printed when candidates exist — not printed for 0-match results; cookbook's field table doesn't call this out |
| E-CLOSE-011 | info | Orchestrate-slice skill lists DEC-051 as precedent for rubber-stamp rescope; DEC-051 is correct but the skill could note that the same DEC number was assigned to Track 2 deferral — minor clarity gap, not a correctness error |
| E-CLOSE-012 | info | Prompt template cites DEC-003, DEC-006, DEC-024 — all confirmed present in `docs/governance/decision-log.md`. No accuracy issue. |

---

## Detailed Findings

---

### E-CLOSE-001 — P1 — Cookbook misquotes `UnsupportedPlanShape` stderr format

**File:** `docs/agent/dsl-cookbook.md:433–436`

**What the cookbook says:**
```
UnsupportedPlanShape: <message>
  path: <jsonpath>
```

**What the code actually prints** (`scripts/query.py:255`):
```python
print(f"executor rejected plan: {exc} (path={exc.path})", file=sys.stderr)
```

This produces a single line like:
```
executor rejected plan: <message> (path=<jsonpath>)
```

There is no `UnsupportedPlanShape:` prefix and no `path:` on a separate line. The recognition signature in the cookbook is wrong. An agent reading for `UnsupportedPlanShape:` in stderr will not find it and may be confused about what it received.

**Suggested fix:** Replace the cookbook recognition block (lines 433–436) with:
```
executor rejected plan: <message> (path=<jsonpath>)
```
Single line, no multi-line format.

---

### E-CLOSE-002 — P1 — `Status: unsupported` failure mode misquotes the stderr prefix

**File:** `docs/agent/dsl-cookbook.md:372–378`

**What the cookbook says (recognition block):**
```
validator returned unsupported — cannot execute
  error: <CODE> at <path>: <message>
```

**What the code actually prints** (`scripts/query.py:216–221`):
```python
_print_findings(
    f"validator rejected plan: status={validation.status}",
    validation.findings,
    sys.stderr,
)
```

Which via `_print_findings` (line 180–184) produces:
```
validator rejected plan: status=unsupported
  error: <CODE> at <path>: <message>
```

The prefix is `validator rejected plan: status=unsupported`, not `validator returned unsupported — cannot execute`. An agent pattern-matching for `validator returned unsupported` in stderr will miss it.

**Suggested fix:** Update the recognition block to:
```
validator rejected plan: status=unsupported
  error: <CODE> at <path>: <message>
```

---

### E-CLOSE-003 — P1 — Polarity marked as "validator rejects" but MVP registry has `polarity_support=True`

**File:** `docs/agent/dsl-cookbook.md:86` (quick-reference table) and related failure-mode catalog

**What the cookbook says:**
```
| `+`, `-`, `±` (polarity prefix) | polarity marker on a node | ❌ parses, validator rejects |
```
and in the coming-soon section (line 484): `+`, `-`, `±` polarity prefixes listed as "not yet executable."

**What the code actually does:**
`src/validation/registry.py:42`:
```python
polarity_support=True,
```

With `polarity_support=True`, `_rule_5_polarity` in `validator.py` returns no findings. Polarity passes the validator. The executor's `validate_plan_shape` does NOT check polarity on NodeRefs — it only checks `step.negated` and `step.morph_filters`. So polarity-prefixed nodes currently pass both the validator AND the executor's shape check.

This means polarity does not raise `UnsupportedPlanShape`. Whether polarity-annotated nodes produce any meaningful filtering is a separate question (the rule 13 grounding path uses `node.polarity` in `is_prior_grounded`), but the claim that the validator rejects polarity is factually wrong for MVP v0.1.

The cookbook both (a) misdirects agents expecting a rejection and (b) incorrectly lists polarity in the "coming soon — raises `UnsupportedPlanShape`" section.

**Suggested fix:**
- Update the quick-reference table to reflect actual behavior. If polarity is in fact a no-op at the execution level (doesn't change what lemmas match), document it as `parses, passes validator, but has no effect on result matching in MVP` rather than `validator rejects`.
- Remove polarity from the "Coming Soon" list or annotate it accurately.
- If the intent was to disable polarity and it was accidentally left enabled, that's a code bug to fix separately; the cookbook should reflect whichever truth is intended.

---

### E-CLOSE-004 — P2 — `concept not mapped` stderr quote does not match actual message

**File:** `docs/agent/dsl-cookbook.md:410–412`

**What the cookbook says (recognition block):**
```
concept not mapped: '<concept-name>' has no lemma rows in the registry
```

**What the code actually prints** (`scripts/query.py:248–252`):
```python
print(
    f"concept not mapped: {exc.concept_name!r} is not present in the "
    "concept registry (no lemma rows). Add it via "
    "scripts/db/seed_registry.py or correct the query.",
    file=sys.stderr,
)
```

The actual stderr text is:
```
concept not mapped: '<concept-name>' is not present in the concept registry (no lemma rows). Add it via scripts/db/seed_registry.py or correct the query.
```

The phrase `has no lemma rows in the registry` does not appear in the code. An agent using substring search on that exact phrase to recognize this error will fail.

**Suggested fix:** Replace the recognition quote with:
```
concept not mapped: '<concept-name>' is not present in the concept registry (no lemma rows). Add it via scripts/db/seed_registry.py or correct the query.
```

---

### E-CLOSE-005 — P2 — `RegistryRequired` stderr quote does not match actual message

**File:** `docs/agent/dsl-cookbook.md:424–426`

**What the cookbook says (recognition block):**
```
RegistryRequired: concept registry is required to resolve concept node '<name>' but none was supplied
```

**What the code actually prints** (`scripts/query.py:241–245`):
```python
print(
    f"registry not seeded: concept {exc.concept_name!r} has no "
    "lemma mapping. Run scripts/db/seed_registry.py first.",
    file=sys.stderr,
)
```

The actual stderr text is:
```
registry not seeded: concept '<name>' has no lemma mapping. Run scripts/db/seed_registry.py first.
```

The `RegistryRequired:` prefix is the Python exception class name and does NOT appear in the printed output. The CLI catches the exception and prints its own message, not `str(exc)`. An agent looking for `RegistryRequired:` in stderr will not find it.

**Suggested fix:** Replace the recognition block with:
```
registry not seeded: concept '<name>' has no lemma mapping. Run scripts/db/seed_registry.py first.
```

---

### E-CLOSE-006 — P2 — Zero-match output format is wrong

**File:** `docs/agent/dsl-cookbook.md:447–454`

**What the cookbook says:**
```
Found 0 matches (showing first 0):

Contextualization (REQ:09.contextualization):
  Observed count: 0
  ...
```

**What the code actually prints** (`scripts/query.py:121–123`):
```python
if total == 0:
    print("Found 0 matches.")
    return
```

When there are zero matches, `_print_results` prints `Found 0 matches.` (with a period) and immediately returns — no `(showing first 0):` suffix, no blank line, no candidate block. The contextualization block is printed separately by the caller (line 264–266), so it does appear, but the match-count line format is wrong.

An agent reading for `(showing first 0):` to detect a zero-match result will fail to pattern-match the correct output. This is directly relevant to the guidance "This is NOT an error."

**Suggested fix:** Update the recognition block to:
```
Found 0 matches.

Contextualization (REQ:09.contextualization):
  Observed count: 0
  ...
```

---

### E-CLOSE-007 — P3 — Quick-reference table polarity row inconsistent with E-CLOSE-003

**File:** `docs/agent/dsl-cookbook.md:86`

Same root cause as E-CLOSE-003. Once E-CLOSE-003 is resolved, this table row must be updated for consistency. Filed separately because the table and the failure-mode catalog are different locations an agent may read.

---

### E-CLOSE-008 — P3 — Worked Example 1 shows two duplicate alignment blocks without explaining why

**File:** `docs/agent/dsl-cookbook.md:188–212`

The worked example shows:
```
  [1] 1Cor 13:13
        πίστις   (faith)  @ position 2
        ἐλπίς    (hope)   @ position 3
        ἀγάπη    (love)   @ position 4
  [2] 1Cor 13:13
        πίστις   (faith)  @ position 2
        ἐλπίς    (hope)   @ position 3
        ἀγάπη    (love)   @ position 4
```

Both candidates are the same verse with identical positions. The accompanying text (line 215) does say "2 chain alignments at that verse" but an agent unfamiliar with the executor's chain-enumeration behavior may not understand why there are two distinct candidates with identical data and conclude the output is a bug or a duplicate.

The executor can produce multiple `MatchCandidate` objects for the same verse when the same lemmas appear at the same positions via different alignment paths. The example is accurate but the explanation is slightly thin for a guide meant to be self-contained. The fact that the alternative ordering `faith > love > hope` also returns 2 means there are likely different token-pair paths, but the annotation doesn't make this explicit.

**Suggested fix (minor):** Add a sentence under the worked example noting why two candidates can share the same verse+positions (multiple chain paths through the executor's in-memory join), so agents don't treat it as a rendering bug.

---

### E-CLOSE-009 — P3 — `>>` adjacency operator failure path description needs precision

**File:** `docs/agent/dsl-cookbook.md:84`

**What the cookbook says:**
```
| `>>` | strict adjacency | ❌ parses, raises `UnsupportedPlanShape` |
```

**What actually happens:** The MVP capability registry (`src/validation/registry.py:38`) includes `adjacency` in `operators`, meaning the validator (rule 3) does NOT flag `>>` as unsupported. The executor, however, checks for `OperatorType.PRECEDENCE` only (line 282–285 of `executor.py`), so `>>` raises `UnsupportedPlanShape` there.

The statement "raises `UnsupportedPlanShape`" is correct. But the categorization "parses, raises `UnsupportedPlanShape`" skips the validator pass-through step. A more precise description would be: "parses, passes validator, executor raises `UnsupportedPlanShape`." This matters because the exit code is still 2 and the error message is `executor rejected plan:` (per E-CLOSE-001 corrected form), but the agent needs to understand it wasn't rejected at the validator stage.

**Suggested fix:** Update the row to `❌ parses, passes validator, executor raises UnsupportedPlanShape` for accuracy. Same applies to `~` cooccurrence (also listed as a supported operator in the capability registry but rejected by the executor).

---

### E-CLOSE-010 — info — `Match type:` line is conditional but presented as always-present

**File:** `docs/agent/dsl-cookbook.md:306–309` (field-by-field table)

The "Header lines" table shows `Match type:` as a standard field. The code (`scripts/query.py:116–117`) only prints this line when there are candidates:
```python
if candidates:
    print(f"Match type: {candidates[0].match_type}")
```

For a zero-match result, the output has no `Match type:` line. An agent reading a zero-match response and expecting to parse a `Match type:` field will find nothing and may erroneously conclude the format is wrong.

**Suggested fix:** Add a note to the field table: `Match type:` line is only present when at least one match was found; absent for zero-match results.

---

### E-CLOSE-011 — info — Orchestrate-slice skill: DEC-051 reference is accurate

**File:** `.claude/commands/orchestrate-slice.md:163`

The skill references `DEC-051` as the precedent for the rubber-stamp rescope pattern. Verified against `docs/governance/decision-log.md`: DEC-051 does record the Track 2 deferral with the stated rationale. The skill description matches the memory file `feedback_rubber_stamp_signal.md`. No accuracy issue; noted for completeness.

---

### E-CLOSE-012 — info — Prompt template DEC citations verified correct

**File:** `docs/agent/prompt-template.md:45–50`

DEC-003 (DSL bypass forbidden), DEC-006 (capability validation explicit), DEC-024 (corpus is ground truth) all confirmed present in `docs/governance/decision-log.md` with matching descriptions. The prompt template's constraint list faithfully represents these decisions. No inaccuracies found.

---

## Orchestrate-Slice Skill Accuracy Assessment

`.claude/commands/orchestrate-slice.md` was cross-checked against:
- CLAUDE.md § Workflow, § Phase Discipline, § Slice Boundaries
- Memory files: `feedback_dec_autonomy.md`, `feedback_close_out.md`, `feedback_bucket_triage.md`, `feedback_resume_summary.md`, `feedback_rubber_stamp_signal.md`

**Result: Accurate.** All five memory files are faithfully consolidated. The phase sequence (§ "Phase Sequence"), decision rule (§ "Decision Rule"), context-hygiene rules (§ "Phase Discipline"), rescope signal (§ "Rescope Signal"), and both checklists (slice-start, slice-close) match the canonical source. The skill correctly names the orchestrator pattern as validated through Slice C and Slice D. The note about collapsing phase-boundary `/clear` for doc-shape slices like Slice E is an appropriate and accurate adaptation of the CLAUDE.md rule.

---

## Worked Examples Accuracy Assessment

- **Example 1 format:** The `Query:`, `Status:`, `Grounding:`, `Match type:`, `Found N matches (showing first M):` header sequence matches `_print_results` in `scripts/query.py`. The candidate block indentation (`  [N]`, `        LEMMA  (CONCEPT)  @ position POS`) matches `_format_candidate`. The contextualization block matches `_print_contextualization`. Baselines (483/84/259) and 2-match count are from project_status.md and accepted as ground truth for this review. The `(faith)`, `(hope)`, `(love)` annotations are correct for `CONCEPT` nodes per the `if step.node_type == NodeType.CONCEPT` branch.

- **Example 2 format:** The `Match type: exact` and `Grounding: n/a` are correctly predicted for an all-`lemma:` query. The absence of `(CONCEPT_ANNOTATION)` for LEMMA steps is correct. The scoped baselines note is accurate. Numbers are declared constructed.

- **Example 3 format:** Shape is correct. The gap semantics explanation (lines 294–296) is accurate against the executor's per-pair gap enforcement.

---

## Concept Registry Table Accuracy

All 20 concepts in the cookbook table match `data/seeds/registry/concepts.csv` and `data/seeds/registry/concept_lemmas.csv` exactly. Greek lemmas for each concept verified row-by-row. No errors.

---

## Prioritized Fix List

| Priority | ID | Change |
|----------|----|--------|
| P1 | E-CLOSE-003 | Correct polarity: MVP registry has `polarity_support=True`; validator does not reject polarity |
| P1 | E-CLOSE-002 | Fix `Status: unsupported` stderr recognition quote to `validator rejected plan: status=unsupported` |
| P1 | E-CLOSE-001 | Fix `UnsupportedPlanShape` stderr recognition to single-line `executor rejected plan: <msg> (path=<jsonpath>)` |
| P2 | E-CLOSE-006 | Fix zero-match format to `Found 0 matches.` (period, no `(showing first 0):` suffix) |
| P2 | E-CLOSE-005 | Fix `RegistryRequired` recognition to `registry not seeded: concept '<name>' has no lemma mapping...` |
| P2 | E-CLOSE-004 | Fix `concept not mapped` recognition to include full actual message text |
| P3 | E-CLOSE-007 | Consistency fix in quick-reference table after E-CLOSE-003 is resolved |
| P3 | E-CLOSE-009 | Clarify `>>` and `~` failure path: passes validator, executor rejects |
| P3 | E-CLOSE-008 | Add sentence explaining duplicate candidates from same verse |
