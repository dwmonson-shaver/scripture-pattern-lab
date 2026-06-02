---
type: code-review
flavor: codex-code
slice: NP1
checkpoint: slice-close
verdict: REQUIRES-CHANGES
base_sha: a921bea
head_sha: 29e1aab
date: 2026-06-01
reviewer: Codex
findings_summary:
  P0: 0
  P1: 0
  P2: 1
  P3: 2
  info: 0
---

# Codex Review — Slice NP1 Close

## Header

| Field | Value |
|---|---|
| Slice | NP1 — frontend rendering of Slice N outputs, Workflow-1 CI relocation, lint cleanup, `web/types/backend.ts` regen, `wrangler.toml` account pin |
| Diff range | `a921bea..29e1aab` |
| Date | 2026-06-01 |
| Reviewer | Codex |
| Verdict | **REQUIRES-CHANGES** |

## Executive Summary

Reviewed the full requested diff (`git diff a921bea..29e1aab`, 36 files / 3545 diff lines) against the NP1 checklist and prior review artifact shape. Most DEC gates pass: the frontend does not import LLM SDKs, the auto-create note is visible above results, the conceptual document preserves the §1-before-§2 epistemic split, the root CI workflow is present, and the exact `29e1aab` archive passes lint, typecheck, unit tests, build, and the no-LLM-SDK bundle check. Findings: **0 P0, 0 P1, 1 P2, 2 P3, 0 Info**. The P2 is a route-encoding correctness bug for concept names containing `/`, so this pass is **REQUIRES-CHANGES**.

## Findings Table

| ID | Severity | File:Line | Description | Recommendation |
|---|---:|---|---|---|
| NP1-CODE-001 | P2 | `web/server/api/sp/concepts/[name]/document.get.ts:16` | The proxy reads the route param without decode options, then re-encodes it at `:35-36`. H3 leaves encoded slashes as `%2F`, so a concept name containing `/` is forwarded upstream as `%252F`, despite the route comment claiming slash characters survive. | Use `getRouterParam(event, 'name', { decode: true })` before `encodeURIComponent`, and add a regression test for a concept name like `foo/bar`. If slash names are intentionally unsupported, remove the slash-survival claim and block them explicitly. |
| NP1-CODE-002 | P3 | `web/components/EducationalArticleSection.vue:19` | The §2 component hard-codes Vuetify's `purple` palette at `:19` and `:27`; the test locks that literal at `web/tests/components/EducationalArticleSection.test.ts:63-68`. This violates the checklist's "no hardcoded colors" portion, even though no hex/rgb/Tailwind/`text-white` usage was found. | Use a semantic theme token such as `secondary`, or introduce a named theme color for LLM commentary and assert the semantic treatment instead of the literal palette name. |
| NP1-CODE-003 | P3 | `web/tsconfig.json:14` | `git diff --check a921bea..29e1aab` fails with `web/tsconfig.json:14: new blank line at EOF.` | Remove the trailing blank line so the diff passes `git diff --check`. |

## Findings Detail

### NP1-CODE-001 — P2 — Encoded slash concept names double-encode before reaching the backend

`web/server/api/sp/concepts/[name]/document.get.ts:16` reads `rawName` with `getRouterParam(event, 'name')`. The same handler documents that "spaces, Greek, and `/` characters in concept names survive the round trip" at `web/server/api/sp/concepts/[name]/document.get.ts:32-34`, then calls `encodeURIComponent(rawName)` and forwards `/api/v1/concepts/${encoded}/document` at `web/server/api/sp/concepts/[name]/document.get.ts:35-36`.

The spaces case is covered by `web/tests/server/concept-document.get.test.ts:90-105`, but slash is not. A local H3 reproduction with the installed package returned `raw: "foo%2Fbar"` and `decoded: "foo/bar"` for `/api/sp/concepts/foo%2Fbar/document`; therefore NP1's current handler forwards `foo%252Fbar` for a real slash-bearing name. That breaks the route for any persisted concept whose name contains `/`, and it contradicts the explicit slash-survival comment in the diff.

### NP1-CODE-002 — P3 — §2 visual treatment uses a hardcoded palette name

The new §2 renderer uses `color="purple"` on the card at `web/components/EducationalArticleSection.vue:19` and on the badge at `web/components/EducationalArticleSection.vue:27`. The test also asserts the literal palette at `web/tests/components/EducationalArticleSection.test.ts:63-68`.

The broader source sweep found no hex/rgb/hsl colors, no Tailwind markers, and no `text-white` in the new NP1 UI files. The remaining issue is specifically the hardcoded non-semantic Vuetify palette literal. The epistemic split should remain visually distinct, but it should be expressed through the theme contract rather than a raw palette name.

### NP1-CODE-003 — P3 — Diff whitespace check fails

`git diff --check a921bea..29e1aab` reports `web/tsconfig.json:14: new blank line at EOF.` The file content at `web/tsconfig.json:1-13` is otherwise a small JSON exclude list; line 14 is only the extra trailing blank line.

## Checklist Results

| Item | Result | Evidence |
|---|---|---|
| 1. DEC-081 LLM SDK charter | PASS | Import-specific `git grep` over `29e1aab -- web` for `@ai-sdk/anthropic`, `@anthropic-ai/sdk`, `openai`, and `google-generative-ai` returned zero import/require matches. `web/scripts/check-no-llm-sdk.mjs:23-33` enforces the bundle guard, and `npm run check:no-llm-sdk` passed after building the exact `29e1aab` archive. §2 renders `section.prose` from props at `web/components/EducationalArticleSection.vue:14,55-59`; it does not generate prose client-side. |
| 2. DEC-106 epistemic split | PASS | §1 renders first via `<ComparativeLexiconSection>` at `web/components/ConceptDocumentView.vue:46-48`; §2 follows via `<EducationalArticleSection>` at `web/components/ConceptDocumentView.vue:49-53`. §1 uses an outlined card and success chip at `web/components/ComparativeLexiconSection.vue:17-31`; §2 uses a tonal card, LLM badge, and disclaimer at `web/components/EducationalArticleSection.vue:18-53`. The §1-only degrade renders an info alert when `part1_educational` is absent at `web/components/ConceptDocumentView.vue:54-65`. |
| 3. DEC-105 not-silent summary | PASS | `AutoCreatedConceptNote` interpolates `{{ note.summary }}` directly at `web/components/AutoCreatedConceptNote.vue:53-55`. The verbatim contract is tested at `web/tests/components/AutoCreatedConceptNote.test.ts:20-23`. |
| 4. DEC-109 auto-create note placement | PASS | The home page renders `<AutoCreatedConceptNote>` before `<ResultEnvelope>` at `web/pages/index.vue:44-46`, so the note is above the result card. |
| 5. DEC-110 route shapes | PASS | User-facing links use singular `/concept/${encodeURIComponent(...)}` at `web/components/AutoCreatedConceptNote.vue:23-25`, backed by `web/pages/concept/[name].vue`. The Nuxt proxy route is plural in `web/server/api/sp/concepts/[name]/document.get.ts`, and the backend URL it calls is plural `/api/v1/concepts/${encoded}/document` at `web/server/api/sp/concepts/[name]/document.get.ts:35-36`. Slash encoding inside that route is the P2 above, but the singular/plural route shape itself is correct. |
| 6. DEC-111 two-card visual split | PASS | The deterministic §1 card is a separate outlined card at `web/components/ComparativeLexiconSection.vue:17-31`; the LLM §2 card is a separate tonal card with its own badge/disclaimer at `web/components/EducationalArticleSection.vue:18-53`. Ordering is locked by `web/components/ConceptDocumentView.vue:46-53` and tested at `web/tests/components/ConceptDocumentView.test.ts:108-120`. |
| 7. DEC-112 CI workflow | PASS | The workflow is rooted at `.github/workflows/deploy.yml:1`; no `web/.github` workflow remains in the reviewed tree. The `paths:` filter scopes pushes to `web/**` and the workflow file at `.github/workflows/deploy.yml:10-16`. Job-level `working-directory: web` is set at `.github/workflows/deploy.yml:30-32`. Required GitHub secrets are documented at `.github/workflows/README.md:12-22`. |
| 8. Workflow-1 closure correctness | PASS | Diff summary shows `web/.github/workflows/deploy.yml` renamed to `.github/workflows/deploy.yml` in commit `c37f5d0`; `git ls-tree -r --name-only 29e1aab` lists only `.github/workflows/README.md` and `.github/workflows/deploy.yml` for workflows. The workflow runs lint, typecheck, tests, type generation, build, bundle check, and deploy at `.github/workflows/deploy.yml:55-81`; the local archive passed lint/typecheck/tests/build/bundle check. |
| 9. Test coverage for new Vue/Nuxt components | PASS | New component tests cover `AutoCreatedConceptNote` at `web/tests/components/AutoCreatedConceptNote.test.ts:14-69`, `ComparativeLexiconSection` at `web/tests/components/ComparativeLexiconSection.test.ts:25-75`, `EducationalArticleSection` at `web/tests/components/EducationalArticleSection.test.ts:14-70`, and `ConceptDocumentView` at `web/tests/components/ConceptDocumentView.test.ts:46-121`. `Tier2GroupingPlaceholder` is covered through the parent render assertion at `web/tests/components/ConceptDocumentView.test.ts:100-105`. |
| 10. Type-safety / backend type regen | PASS | `web/types/api.ts:27-30` exposes aliases for `AutoCreatedConceptNote`, `ConceptDocument`, `ComparativeLexiconSection`, and `EducationalArticleSection`. Generated `AutoCreatedConceptNote` includes `summary` and `document_available` at `web/types/backend.ts:204-213`; `ConceptDocument` includes `part1_comparative`, nullable `part1_educational`, and `part2_grouping_placeholder` at `web/types/backend.ts:290-300`; `EducationalArticleSection` includes prose/citations/model fields at `web/types/backend.ts:384-396`; `QueryNLResponse` includes `auto_created_concept` at `web/types/backend.ts:766-775`; the backend document endpoint is generated at `web/types/backend.ts:107-123` and `web/types/backend.ts:1141-1159`. |
| 11. Theme/contrast | FAIL | No hex/rgb/hsl, Tailwind, or `text-white` usage was found in the new NP1 UI files. However, `web/components/EducationalArticleSection.vue:19` and `web/components/EducationalArticleSection.vue:27` hard-code `color="purple"`, and the test locks that palette at `web/tests/components/EducationalArticleSection.test.ts:63-68`; see NP1-CODE-002. |
| 12. P0/P1/P2 Vue/Nuxt correctness bugs | FAIL | No P0 or P1 issues found. One P2 correctness bug was found in the concept-document proxy route: `web/server/api/sp/concepts/[name]/document.get.ts:16,35-36` double-encodes slash-bearing concept names; see NP1-CODE-001. |

## Verdict

**REQUIRES-CHANGES.** The slice is close on the main NP1 contracts and the exact `29e1aab` archive passes the web gates after Nuxt prepare: `npm run lint:check`, `npm run typecheck`, `npm test` (89/89), `npm run build`, and `npm run check:no-llm-sdk`. However, the proxy route still mishandles concept names containing `/`, which is a P2 correctness bug in a route whose own comment promises slash-safe round trips. Fix that route and regression test first; the two P3s are straightforward cleanup items.
