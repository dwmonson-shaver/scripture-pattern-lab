# Independent Reviews Log

Index of independent code and design reviews. Each entry links to the review
artifact in `docs/reviews/`.

Independent review is an explicit Quality Gate at slice-close (CLAUDE.md): a
slice is not declared closed until a Codex pass has run on the cumulative
slice diff, the artifact is committed to `docs/reviews/`, this log has a new
row, and any P0/P1/P2 findings have been addressed.

## Reviews

| Date | Review | Scope | Verdict | Findings | Closure |
|------|--------|-------|---------|----------|---------|
| 2026-05-02 | [Codex code (Slice A)](../reviews/review-codex-code-slice-a-2026-05-02.md) | Slice A — corpus ingestion 3-John end-to-end | needs-attention | 0 P0, 0 P1, 3 P2 | All closed pre-Slice-B as Bucket 1: `9f39f25` (tokenize wildcard `*`), `9aa900a` (parser polarity-on-parens), `6d6af2a` (validator composite recursion). DECs DEC-031, DEC-032, DEC-033. |
| 2026-05-02 | [Codex adversarial design (Slice A)](../reviews/review-codex-adversarial-design-slice-a-2026-05-02.md) | Slice A — corpus design + canonical-09 boundary, adversarial pass | needs-attention | 4 (2 high, 2 medium) | Design #4 (canonical-09 ingestion section) closed by `4da88f6` (REQ:09.ingestion added). Design #1+#2 (registry epistemics + validator extension) → **Bucket 2** — Trigger: at Slice C start (epistemic-discipline backlog items 3–5). Rationale: closing them requires canonical-08 REQ markers + a `/design` for registry epistemics + validator code changes — three coordinated artifacts that belong to Slice C's scope (concept registry seeding); doing them in Slice B would be a horizontal cross-cut. Slice B doesn't ship conceptual/polarity behavior, so Codex's no-ship verdict doesn't fire on Slice B. **[Triage 2026-05-03 — pre-Slice-C, by assistant]** Disposition: **scope in**. Slice C's `/research` and `/design` will fold in (a) `REQ:08.registry-epistemics` in `docs/canonical/08_mvp-corpus-scope.md` (backlog item 3); (b) `/design` discussion for registry epistemics — prior-grounded vs evidence-grounded match types, provenance/evidence schema, default-confidence semantics (backlog item 4); (c) capability-validator extension that flags polarity-marked concept queries against unverified registry entries as prior-grounded rather than supported (backlog item 5). **[Update 2026-05-03 — design phase, by assistant]** Slice C `/design` for registry epistemics landed at `thoughts/design-registry-epistemics-2026-05-03.md` (status: approved). 8 decisions + 6 open questions resolved. Path B selected: Slice C **expands** to a second design track for **result contextualization** (anti-confirmation-bias species 2 — observed pattern count vs alternative orderings vs null-distribution baseline), addressing a gap in canonical specs the user surfaced during design review (canonical specs commit to finding/ranking matches but not to contextualizing them against baselines). Bucket 2 closure now requires: both design artifacts + `REQ:08.registry-epistemics` + new contextualization REQ marker (id TBD) + validator/scoring code realizing both. Closing SHA pending Slice C close. **[Update 2026-05-08 — slice re-scope, by orchestrator]** Track 2 (result contextualization) design landed at `thoughts/design-result-contextualization-2026-05-03.md` (status: design-stable-implementation-deferred). OQs #1–#4 resolved in-walkthrough (middle-path default; retrieval-side code home; defer null-distribution; cap=24). OQs #5–#6 deferred-pending-interface. **Slice C re-scoped**: ships Track 1 (registry epistemics) implementation + `src/engine/executor.py` (was Bucket 3 — see disposition flip below) + thin CLI `scripts/query.py` so the user can run real queries against the seeded registry. Track 2 implementation moves to Slice D with sharpened trigger: *after CLI ships and the user has interacted with real result counts* — calibration-shape decisions (OQs #5, #6) require seeing actual `MatchCandidate` output, which doesn't exist until the executor + CLI land. Rationale: the user surfaced mid-walkthrough that they cannot meaningfully evaluate calibration shapes for results that don't yet exist; deferring Track 2 implementation is honest about the feedback-loop gap. Bucket 2 closure now requires: ✓ Track 1 design (approved 2026-05-03), ✓ Track 2 design (design-stable 2026-05-08), Track 1 code in Slice C, Track 2 code in Slice D. Closing SHA pending Slice D close (not Slice C close). Design #3 (book-id normalization: BB digits in `tokens.book` vs `book:rom` abbrev form in DSL examples) → **Bucket 3** — Trigger: before any pattern-engine work that consumes the DSL `book:` constraint. Rationale: Slices A–C don't execute DSL queries against `tokens.book`, so the mismatch isn't exercised yet; adding a normalization layer now would be premature without the actual call site to design against. **[Triage 2026-05-03 — pre-Slice-C, by assistant]** Disposition: **re-defer**. Trigger reaffirmed and sharpened: *before pattern-engine work in `src/engine/executor.py` that consumes the DSL `book:` constraint against `tokens.book`*. Rationale (specific to Slice C): Slice C is concept-registry seeding — it writes to `concepts` / `concept_lemmas` / `concept_inverse` tables and does not execute DSL queries against `tokens.book`, so the BB-digit ↔ abbreviation mismatch is not exercised yet. Adding a normalization layer now would be premature without the actual call site to design against. Original trigger remains specific and accurate; this is not a stale "eventually" re-deferral. **[Update 2026-05-08 — Slice C re-scope, by orchestrator]** Disposition flipped: **scope in** to Slice C. Rationale: Slice C re-scope (see Bucket 2 update above) pulls `src/engine/executor.py` into this slice as the prerequisite for the user-runnable CLI. The original trigger now fires. Bucket 3 closure requires the executor design to address book-id normalization between DSL `book:rom` form and `tokens.book` BB-digit form, plus the resolution code itself. Closing SHA pending Slice C close. |
| 2026-05-03 | [Codex code (Slice B close)](../reviews/review-codex-code-slice-b-close-2026-05-03.md) | Slice B — full ingestion CLI + observability + smoke test | minor-fixes-recommended | 0 P0, 0 P1, 0 P2, 2 P3, 1 info | Both P3s closed by `069a923` (fixture-edge ordering on `test_full_corpus_smoke`; `_FakeEngine.in_transaction` post-commit assertion in `test_callback_emits_done_with_final_count`). Info note acknowledged (subprocess env inheritance pattern is sound). |
| 2026-05-08 | [Codex code (Slice C Track 1 interim)](../reviews/review-codex-code-slice-c-track-1-2026-05-08.md) | Slice C Track 1 — registry epistemics, 6 phases (≈2,439 lines across 15 files); base SHA `fed3b98` | FAIL → clean after fix | 0 P0, 1 P1, 1 P2, 0 P3, 0 info | Both findings closed inline before executor work begins. **P1 — `seed_registry.py` non-empty gate could mutate a foreign registry whose row count happens to match the CSV**: closed by tightening the gate to a strict `existing > 0 → refuse` predicate matching `ingest_corpus.py`. The `test_seed_is_idempotent` test (which depended on the relaxed predicate) was renamed `test_seed_is_reproducible_via_truncate` and rewritten to drive idempotency through `--truncate + reseed`. **P2 — SQL schema did not enforce declared value domains for `origin`, `verification_state`, `polarity`, `evidence_count`, or `confidence`**: closed by adding DB-level CHECK constraints to `data/schemas/02_concept_registry.sql` (`origin IN (...)`, `verification_state IN (...)`, `polarity IN ('+','-','±')`, `evidence_count >= 0`, `confidence IS NULL OR confidence BETWEEN 0 AND 1`). Mirrored the same checks in `src/ontology/registry.py` Table definitions; added 5 new IntegrityError-raising tests in `tests/integration/test_apply_schemas.py`. Closing SHA recorded in this row's commit. |

## Severity language

Code reviews use P-numbers. Adversarial design reviews use high / medium / low.

| Severity | Meaning | Disposition |
|----------|---------|-------------|
| P0 | No-ship — blocks merge | Must close before the slice closes |
| P1 | Must-fix-before-merge | Must close before the slice closes |
| P2 | Must-fix-before-slice-close | Must close before the slice closes |
| P3 | Worth-doing-soon | Fix inline or schedule into a named bucket |
| info | Note for future authors | Acknowledged in the closure column |
| high (design) | Architectural risk; treat as P0/P1 | Close inline or land in a tracked bucket with a named trigger |
| medium (design) | Worth addressing | Treat as P3 — fix soon or bucket |
| low (design) | Note | Acknowledge |

## Process

- **When (slice-close pass)**: After the slice's last `/review`, before its `/close-step`. The Codex pass runs on the cumulative slice diff (`git diff <pre-slice-base>..HEAD`).
- **How**: User invokes `/codex:rescue` or the assistant spawns the `codex:codex-rescue` subagent with a self-contained brief naming scope, prior-review artifacts (so severity language calibrates), severity language, and the categories to focus on (correctness / security / resource hygiene / test fragility / contract / convention / subprocess-env).
- **Where the artifact lands**: `docs/reviews/review-codex-{code|adversarial-design}-{slice-id}-{YYYY-MM-DD}.md`. Include frontmatter with type, verdict, base SHA, scope, plugin/CLI versions, and findings summary.
- **Closure dispositions** (every finding gets exactly one):
  - **fixed** — fix-commit SHA recorded in this log.
  - **deferred to a tracked bucket** — bucket name + trigger condition + written rationale (why this slice is not the right home). The trigger MUST be specific enough that a future-you can recognize the matching slice without re-reading the original finding.
  - **rejected** — documented reason; rare.
  - "Filed and forgotten" is **not** a valid disposition.
- **Buckets**: Findings deferred to a later slice are tracked as named buckets ("Bucket 1", "Bucket 2", etc.). The closure column here carries the trigger + rationale; in-flight buckets are also summarized in `project_status.md`'s Carry-over memory; closed buckets dissolve into the SHA in the closure column.
- **Adversarial design reviews** are a separate flavor: run them when an architectural decision lands or before a major slice begins. Findings that close inline get a DEC; findings deferred join a bucket with a stated trigger and rationale, same as code findings.

## Between-slice triage

When a new slice begins, the assistant MUST do a pre-slice triage pass **before invoking `/research`**. This is the mirror of the slice-close review and the mechanism that prevents bucketed findings from drifting indefinitely.

1. **Scan**: read this file's table for any bucket whose **trigger** condition fires on the new slice (e.g. "Slice C blockers", "pre-pattern-engine", "when REQ:NN.X is scheduled"). Cross-reference `project_status.md` Carry-over for active triggers.
2. **Disposition**: every matching bucket gets one of three explicit choices:
   - **Scope in** — fold the items into this slice's `/research` and `/design`. Note in the design discussion which findings are now in scope. Update the bucket's closure column with `scoped into <slice-id>; see <design artifact>` and (later, after slice close) the closing SHA.
   - **Re-defer** — update the bucket entry with a new trigger and a written rationale (why this slice is still not the right home). Stale "eventually" deferrals are not allowed; re-deferral requires a new specific trigger.
   - **Reject** — document why the original finding no longer applies (rare; finding may have been overtaken by other work).
3. **Surface**: any matching bucket the assistant cannot dispositionalize (because the user hasn't decided yet) is reported to the user **before** `/research` runs, not after.
4. **Trigger quality**: a trigger should answer "what slice or pre-slice condition closes this?" Specific examples:
   - ✅ "Before any pattern-engine work that consumes the DSL `book:` constraint"
   - ✅ "When epistemic-discipline backlog items 3–5 are scheduled"
   - ✅ "When canonical-08 REQ:08.registry-epistemics is added"
   - ❌ "Eventually" / "When we get to it" / "Future" — these are not triggers.

This protocol is what makes "deliberately scoped or re-deferred with rationale" a process rule, not a hope.

## Cross-references

- Quality Gate definition: `CLAUDE.md` § Quality Gates and § Workflow step 6 (slice close).
- Decision log (DECs that close findings): `docs/governance/decision-log.md`.
- Spec coverage (REQ markers ↔ code/test): `docs/governance/spec-coverage.md`.
- Bucket-tracking memory (in-flight buckets only): user's `project_status.md` memory file.
