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
| 2026-05-02 | [Codex adversarial design (Slice A)](../reviews/review-codex-adversarial-design-slice-a-2026-05-02.md) | Slice A — corpus design + canonical-09 boundary, adversarial pass | needs-attention | 4 (2 high, 2 medium) | Design #4 (canonical-09 ingestion section) closed by `4da88f6` (REQ:09.ingestion added). Design #1+#2 (registry epistemics + validator extension) mapped to **Bucket 2** — Slice C blockers, gated by epistemic-discipline backlog items 3–5. Design #3 (book-id normalization) mapped to **Bucket 3** — pre-pattern-engine, queued. |
| 2026-05-03 | [Codex code (Slice B close)](../reviews/review-codex-code-slice-b-close-2026-05-03.md) | Slice B — full ingestion CLI + observability + smoke test | minor-fixes-recommended | 0 P0, 0 P1, 0 P2, 2 P3, 1 info | Both P3s closed by `069a923` (fixture-edge ordering on `test_full_corpus_smoke`; `_FakeEngine.in_transaction` post-commit assertion in `test_callback_emits_done_with_final_count`). Info note acknowledged (subprocess env inheritance pattern is sound). |

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

- **When**: At slice-close — after the slice's last `/review`, before its `/close-step`. The Codex pass runs on the cumulative slice diff (`git diff <pre-slice-base>..HEAD`).
- **How**: User invokes `/codex:rescue` or the assistant spawns the `codex:codex-rescue` subagent with a self-contained brief naming scope, prior-review artifacts (so severity language calibrates), severity language, and the categories to focus on (correctness / security / resource hygiene / test fragility / contract / convention / subprocess-env).
- **Where the artifact lands**: `docs/reviews/review-codex-{code|adversarial-design}-{slice-id}-{YYYY-MM-DD}.md`. Include frontmatter with type, verdict, base SHA, scope, plugin/CLI versions, and findings summary.
- **Closure**: Each P0/P1/P2 finding closes with either a fix commit (SHA recorded in this log) or a documented "rejected — reason" disposition (rare). P3 fixes either land inline (SHA) or join a named bucket. Info findings are acknowledged in the closure column.
- **Buckets**: Findings that defer to a later slice are tracked as named buckets ("Bucket 1", "Bucket 2", etc.). Buckets in flight are summarized in `project_status.md`'s "Carry-over" memory; closed buckets dissolve into the closure column here.
- **Adversarial design reviews** are a separate flavor: run them when an architectural decision lands or before a major slice begins. Findings that close inline get a DEC; findings deferred to later slices join a bucket gated by a stated trigger.

## Cross-references

- Quality Gate definition: `CLAUDE.md` § Quality Gates and § Workflow step 6 (slice close).
- Decision log (DECs that close findings): `docs/governance/decision-log.md`.
- Spec coverage (REQ markers ↔ code/test): `docs/governance/spec-coverage.md`.
- Bucket-tracking memory (in-flight buckets only): user's `project_status.md` memory file.
