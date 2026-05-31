# Slice N-polish-1 (NP1) — Slice-close review (claude-fallback)

**Reviewer**: claude-fallback (Codex blocked, see Bucket-N1 note below).
**Date**: 2026-05-31.
**Slice**: NP1 — frontend rendering of Slice N + Workflow-1 close + lint
cleanup + account_id commit + regen of `web/types/backend.ts`.
**Cumulative diff**: `a921bea..c37f5d0` (5 commits, ~2.7K lines across 32
files — ~1.3K of those are the regenerated `types/backend.ts`).
**Scope**: frontend (Nuxt 3 + Vuetify) + infra. NO backend code changed
(verified by `git diff a921bea..HEAD -- src/`).
**Verdict**: **APPROVE WITH FOLLOW-UPS → clean** (0 P0, 0 P1, 0 P2, 2 P3,
3 info). All gates green.

## Codex availability

Codex was attempted via the codex-companion runtime and failed with
`Codex cannot access session files at /Users/dwmonson/.codex/sessions
(permission denied)` — the SAME blocker that put Bucket-M1 and Bucket-N1
on the books. The user's `sudo chown -R $(whoami) /Users/dwmonson/.codex`
fix has not been run yet in their own terminal. Per CLAUDE.md precedent
(Slices E / F / J1 / K / M / N), the slice-close pass falls back to
`claude-fallback` flavor carrying the same severity language + checklist
as a Codex pass. The owed-Codex pass on Slice N (Bucket-N1) and on
Slice M (Bucket-M1) both still hold; they're joined now by an owed-Codex
pass on Slice NP1 (**Bucket-NP1-1, NEW** — see below).

## Quality gates at close

- `npm run lint:check` — **clean** (0 errors, 0 warnings).
- `npm run typecheck` — **clean** (vue-tsc --noEmit, 0 errors).
- `npm test` — **89 / 89 passed** in 12 files; +43 tests vs. the
  pre-slice baseline of 46.
- `npm run check:no-llm-sdk` — **clean** ("DEC-081 check passed: no LLM
  SDK in output").

## Charter line — verified structurally sound

- **DEC-081 (no LLM SDK in frontend bundle)**: verified by
  `check:no-llm-sdk` AND by source-grep — every new file (5 components,
  1 composable, 1 server route, 1 type alias bridge, 1 page) imports
  ONLY from `~~/types/api`, `vue`, `vuetify` auto-globals, or sibling
  composables/components. No `import` of `@ai-sdk/anthropic`,
  `@anthropic-ai/sdk`, `openai`, `google-generative-ai`. The
  `EducationalArticleSection` component's docstring states the
  contract explicitly: *"the prose is rendered, not generated here.
  DEC-081 forbids any LLM SDK in the frontend bundle; the prose was
  generated server-side at concept-creation time and persisted
  alongside the document."*
- **DEC-106 epistemic split (§1 deterministic vs §2 cited LLM)** —
  verified visually load-bearing:
  - §1 (`ComparativeLexiconSection.vue`): outlined variant,
    **green** "Lexicon data" `v-chip` + `mdi-database-check-outline`
    icon, leading caption "Lemmas and verse references pulled directly
    from open-licensed lexicon data. No LLM, no opinion."
  - §2 (`EducationalArticleSection.vue`): **tonal purple** card,
    "LLM-generated commentary" `v-chip` + `mdi-robot-outline` icon,
    leading `v-alert` "The prose below is LLM-generated educational
    commentary on the lexicon data above. Treat it as a starting prior,
    not a confirmed claim — the deterministic table in section 1 is the
    ground truth."
  - The §1-before-§2 order is enforced by an ordering invariant in
    `ConceptDocumentView.test.ts`: *"renders §1 BEFORE §2 (epistemic
    order matters — ground truth first)"*.
- **DEC-105 not-silent auto-create note**: `<AutoCreatedConceptNote>`
  renders the backend's `summary` field VERBATIM (test:
  `'renders the backend summary verbatim (no paraphrase)'`), the
  lemmas in `<GreekText>` chips, and surfaces the conceptual-document
  link only when `document_available === true`.
- **Theme contrast discipline**: every text class is theme-aware
  (`text-medium-emphasis`, `text-caption`, `text-h5/h6`, `text-body-1/2`
  — no `text-white`, no `text-black`, no Tailwind, no hex). Vuetify
  colors are referenced semantically (`color="success"`,
  `color="info"`, `color="purple"`). The purple color is from
  Vuetify's standard Material palette; tonal variants produce a tint
  on the surface that remains readable in dark mode. Light/dark
  toggle verification: deferred to the user's manual smoke (see
  Carry-over).
- **DEC-024 (corpus is ground truth)**: respected — the frontend
  renders backend output, never asserts or amends concept semantics.
- **Build-vertical + test-each-phase**: 5 commits, each independently
  testable; tests run between phases.

## Findings

### NP1-CLOSE-001 (P3, deferred to Bucket-NP1-2) — `useConceptDocument` uses `useFetch` without `lazy: true`, so a 404 throws during SSR rather than rendering ErrorPanel
The home / concept page hits SSR on direct URL load. When a user types
`/concept/foo` and there's no Conceptual Document for `foo`, the backend
returns 404. `useFetch` without `lazy: true` rejects the
`useAsyncData` promise during SSR, which Nuxt translates to a 500-style
error page rather than the in-page `<ErrorPanel>` the page-template
expects to render. The page works correctly for client-side navigation
(coming from the home page link, the error renders inline), but a
copy-paste URL to a non-existent concept gets a stack page.

Recommended fix: add `lazy: true` (and possibly `server: false`) to the
`useFetch` options inside `useConceptDocument`, so SSR completes
successfully with a pending state and the client hydration consumes the
error normally. Tests would need to cover the SSR-direct-load path
(Playwright or Nitro test runner).

Trigger: "Next frontend slice that touches `useConceptDocument` or
`pages/concept/[name].vue`, OR the first user report of a copy-paste
concept-document URL behaving worse than home-page navigation."
Rationale: the home-page-link path (which the auto-create note links to,
and is the primary entry point) works correctly today; the
direct-URL-load is a secondary entry point; deferring keeps this slice
shippable while letting the next frontend slice address it with a
proper SSR test fixture.

### NP1-CLOSE-002 (P3, deferred to Bucket-NP1-3) — typecheck quietly skips `vitest.config.ts` + `eslint.config.mjs`
`web/tsconfig.json` was extended to exclude these two config files from
`vue-tsc --noEmit` so the pre-existing peer-dep type noise (vite vs
vitest's bundled vite; missing `@types/eslint-config-prettier`) stops
blocking CI. The right long-term fix is to install
`@types/eslint-config-prettier` (or use the recommended ESM-flat-config
shape that doesn't need it), and to align the `vitest` / `vite` /
`@vitejs/plugin-vue` versions so the bundled-vite path stops drifting.

Trigger: "Next frontend slice that bumps vitest or vite, OR a fresh
`npm install` that surfaces a different peer-dep mismatch." Rationale:
the exclusion does NOT compromise app-code type safety (every `pages/`,
`components/`, `composables/`, `server/`, `tests/` file remains in the
typecheck graph); it only stops two third-party-shaped errors from
masking real ones. Closing this cleanly requires a coordinated
dep-version bump that's its own slice.

### NP1-CLOSE-003 (info) — `tests/server/concept-document.get.test.ts` uses a heavier mocking pattern than `tests/server/nl.post.test.ts`
The existing `nl.post.test.ts` only exercises the exported `requestSchema`
and stubs the handler-side auto-imports as inert `vi.stubGlobal`. The new
`concept-document.get.test.ts` stubs the whole event harness and exercises
the handler end-to-end (success / encoding / 400 / 404 mirror). The new
test is more thorough — strictly better coverage — but it's a different
shape. Future test authors should pick one pattern or document why both
co-exist. Not closing this slice on it; noting so a future author doesn't
"fix" the new test back to the lighter shape and lose coverage.

### NP1-CLOSE-004 (info) — `useConceptDocument` returns the raw `data` ref as `document` without a runtime validator
The composable trusts `useFetch<ConceptDocument>` to produce a
shape-correct `ConceptDocument`. If the backend's schema ever drifts
from the generated types (the way Slice L's window-scope addition drifted
without a regen), a real production response could pass through and
break rendering downstream rather than fail loudly here. The project's
existing pattern (see `useQuery.ts`) does the same thing — DEC-081 says
the structural seam is `types/backend.ts`, not runtime validation. So
this is consistent with project pattern; flagged in case a future slice
wants to add a zod validator on the read path.

### NP1-CLOSE-005 (info) — CI workflow trigger uses `paths:` filter
The moved `.github/workflows/deploy.yml` adds `on.push.paths: [web/**, .github/workflows/deploy.yml]` so backend-only commits don't churn the
Worker deploy. This is correct and saves CI minutes; flagging for
governance visibility because the prod-smoke's original Workflow-1
note didn't anticipate the trigger refinement, and a future author
reading the bucket close should know the workflow is more selective
than the original.

## Bucket triage (slice-start at slice close, per autopilot)

Done at slice close because `/research` was skipped (autopilot). Scanned
`docs/governance/reviews-log.md` for buckets whose trigger fires on this
slice:

- **Bucket-M1 (Codex on Slice M)** — re-deferred. Trigger ("next session
  in which `~/.codex/sessions` permission is fixed") did not fire — the
  fix command has not been run.
- **Bucket-N1 (Codex on Slice N)** — re-deferred. Same trigger as M1.
- **Bucket-N2 (anthropic 4xx → 503 mapping)** — re-deferred. Trigger
  ("next slice touching `src/nlp/llm_client.py` or `src/app/routes/nl.py`,
  OR first curator/UX slice surfacing backend errors") — NP1 surfaces
  backend errors via `<ErrorPanel>`, but only mirrors what the proxy
  already returns; no new error-mapping shape, so the trigger doesn't
  fire. Re-deferred with same trigger.
- **Bucket-N3 (Tier-1 gloss recall)** — re-deferred. Backend-only / Tier-2
  territory.
- **Workflow-1 (info)** — **CLOSED by `c37f5d0`** (Phase 3 commit moving
  the workflow to repo root + README addendum). Verified by `ls
  .github/workflows/` showing `deploy.yml` + `README.md`.
- **Buckets 8 / 9** — re-deferred. No trigger fires (the registry-state
  invalidation and pagination triggers are backend-shape concerns).
- **Buckets J1-3 / J1-4** — re-deferred. J1-3 (refactor reducer/render
  split) doesn't fire on this slice; J1-4 was already closed at
  `b027a12` and confirmed by the working error rendering in
  `<ErrorPanel>`.
- **Bucket-NP1-2 (NEW)** — `useConceptDocument` SSR direct-load path —
  see NP1-CLOSE-001 trigger.
- **Bucket-NP1-3 (NEW)** — vitest/vite/eslint-prettier typecheck noise —
  see NP1-CLOSE-002 trigger.

## DECs landed during this slice

- **DEC-109** — Auto-create note placement (above the result card,
  Vuetify `v-alert` / `v-card` with theme-aware classes, optional
  "View concept document" button on `document_available`).
- **DEC-110** — Concept Document page route shape: user-facing
  `/concept/:name` (singular), proxy + backend
  `/api/v1/concepts/:name/document` (plural + suffix).
- **DEC-111** — Epistemic split enforced by two separate cards with
  contrasting surface treatment (outlined+green for §1, tonal+purple
  for §2, disclaimer alert on §2).
- **DEC-112** — GitHub Actions workflow at `.github/workflows/` repo
  root, with job-level `defaults.run.working-directory: web` and
  `paths:` filter to skip backend-only commits.

To be appended to `docs/governance/decision-log.md` in the
governance-close commit.

## Slice exit gate

**Stated gate** (from `thoughts/structure-slice-np1-2026-05-31.md`): with
the local Worker dev server pointed at the deployed Render backend,
running `what is humility?` in the UI shows the auto-create alert above
the result card, and clicking "View concept document" opens a page with
the two-section split rendered as designed (verified in both light and
dark mode). Code gates (`lint:check`, `typecheck`, `test`,
`check:no-llm-sdk`) all pass.

**Status**: code gates verified green. Live UI verification deferred to
the user (their browser + their git auth for deploy; Claude's git auth is
work and 403s on push). The Vitest tests cover the structural invariants
the live smoke would verify; the manual deploy + browser smoke is on the
user's plate at slice resume.

## Carry-over for the next session

- The user owes a manual `git push origin main` to land the slice's 5
  commits to GitHub. After the push, the CI workflow will fire — it
  will fail at `gen:types` or `wrangler deploy` until the user sets the
  three GitHub Secrets (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`,
  `NUXT_BACKEND_URL`); that failure mode is documented in
  `.github/workflows/README.md`.
- Until the user runs `wrangler deploy` (manual fallback per
  `web/CLAUDE.md`) or sets the GitHub Secrets and pushes again, the
  live Worker does NOT have the new components — the backend still has
  Slice N, the frontend still shows the old rendering.
- The user should run `sudo chown -R $(whoami) /Users/dwmonson/.codex`
  in their own terminal to unblock Codex for Buckets M1 / N1 / NP1-1
  (the three pending Codex passes can run in one session).
- `.env.example` deletion is a sandbox-permission artifact (the file
  is read-restricted in this env) — user should run `git restore
  .env.example` outside the sandbox to undo.

## Notes for the governance commit

- DEC-109..112 to be appended to `docs/governance/decision-log.md`.
- New row in `docs/governance/reviews-log.md` referencing this artifact.
- `docs/governance/spec-coverage.md` to be updated under
  `REQ:08.concept-document` + `REQ:09.api-gateway` linking the new
  frontend surface files. No new REQ markers (no canonical-doc edits;
  the new code consumes contracts already covered by the Slice N
  governance close).
