---
type: production-smoke
slice: N
date: 2026-05-30
deployed_sha: b352fb6
db_endpoint: ep-divine-glitter-akevxuwx (Neon us-west-2 pooler)
backend_host: scripture-pattern-lab-api.onrender.com (GCP us-west1)
verdict: APPROVE WITH FOLLOW-UPS
findings: 2 P3 (Bucket-N2, Bucket-N3), 1 info (Workflow-1)
---

# Slice N — Production Smoke (2026-05-30)

First end-to-end verification of Slice N against real Neon + real Anthropic, four days after slice-close (Bucket-N1 owed Codex pass also outstanding).

## What was exercised

A single live NL query against the deployed Render service, bearer-authenticated, with corpus + registry + lexicon all loaded on Neon:

- **Input:** `POST /api/v1/query/nl` with `{"nl_query":"what is humility?"}`
- **Path traversed:** NL translation (Anthropic) → DSL `concept:humility within:verse corpus:nt` → registry lookup → `concept_not_mapped` short-circuit intercepted by Slice N's dead-end killer → English-→-lemma resolver (TBESG/jtauber/Dodson on Neon) → `auto_created_concept_writer` persists `humility` with `origin='lexicon_imported'` / `verification_state='unverified'` → bounded re-run → engine returns 7 conceptual matches → response carries the `auto_created_concept` summary + `document_available=true`.
- **Wall-clock:** 32.5s (includes cold-start + LLM round-trip; subsequent NL calls expected sub-3s)
- **HTTP status:** 200

## Verified (PASS)

- **The dead-end is dead.** The exact `concept:humility` query that would previously have 422'd with `concept_not_mapped` now succeeds with auto-creation.
- **Tier-1 epistemic line held end-to-end** (not just structurally): the response's `auto_created_concept` object reads *"Machine/lexicon-sourced and unverified — a starting prior you can correct, not a confirmed claim"* — exactly DEC-104/DEC-105's contract, surfaced to the caller.
- **Persisted two-part Conceptual Document exists** (`document_available: true` in the response envelope, retrievable at `GET /api/v1/concepts/humility/document` — see follow-up A below).
- **Conceptual matches are real, lemma-resolved, citation-grade.** Seven hits across Acts, Eph, Php, Col (×3), 1Pe, all on `ταπεινοφροσύνη`. The engine's `match_type='conceptual'` and `resolved_lemmas` are populated.
- **The `auto_created_concept` envelope is a single short note**, not a duplicate of the full document (DEC-106 / not-silent inline + linkable long article).

## Findings

### Bucket-N2 NEW — LLM upstream-4xx maps to generic 500 (P3)

When Anthropic returns a 4xx with a real business-meaning message (in this case credit-exhausted: `BadRequestError: 400 — Your credit balance is too low`), `src/app/routes/nl.py` lets the exception propagate up to FastAPI's generic catch-all. The user-facing response becomes:

```json
{"detail":{"error":"internal_error","message":"an unexpected error occurred","details":null}}
```

— a flat HTTP 500 with no diagnostic value. The runbook (`docs/runbooks/render-deploy.md` § Troubleshooting) explicitly documents the shape we *should* return: `503 llm_unavailable`. The existing 503 path catches transport-level unavailability (auth missing, network); the 4xx-with-business-meaning path is uncaught.

- **Severity:** P3 (cosmetic until the UX cares about meaningful upstream errors; no functional or epistemic impact).
- **Trigger:** "Next slice that touches `src/nlp/llm_client.py` or `src/app/routes/nl.py`, OR the first curator/UX slice that surfaces backend errors to end users."
- **Rationale to defer:** Self-contained micro-fix (one `try/except anthropic.BadRequestError`, one envelope mapping, one unit test). Doesn't belong wedged into the Cloudflare-Worker-redeploy follow-up.

### Bucket-N3 NEW — Tier-1 gloss recall is narrower than the design anticipated (P3)

`humility` resolved to **1 lemma** (`ταπεινοφροσύνη`, the abstract noun) where the design discussion (thoughts/design-concept-layers-2026-05-26.md) anticipated **3–5** (`ταπεινός`, `ταπεινόω`, `πραΰτης`, `πραΰς`). Cause: TBESG glosses the noun directly as "humility" but the adjective/verb forms gloss as "humble"/"humble oneself" — the resolver's exact-token match against the English term doesn't cross those gloss boundaries.

The mid-slice review already flagged the converse problem (N3-FB-001: ILIKE `%term%` over-broadens, e.g. "love" → "beloved") and called it design-acceptable Tier-1 recall, deferred to Tier-2. This finding is the **same recall-precision tradeoff observed in real data with a concrete case**, which is useful evidence for the Tier-2 design.

- **Severity:** P3 (design-acceptable per Tier-1 charter — Tier-1 is a sourced prior, not a comprehensive grouping; the broader cluster is what Tier-2 exists to build).
- **Trigger:** "Tier-2 curator slice (where weighted phrase-capable groupings can pull in `ταπεινός`/`πραΰτης` as conceptual neighbors of `ταπεινοφροσύνη`), OR a Tier-1 tuning slice if user complaints concentrate on missing-coverage."
- **Rationale to defer:** Tier-2 is the design's stated home for this kind of grouping; pre-fixing in Tier-1 risks compromising the "near-lexical, low-stakes prior" disposition.

### Workflow-1 NEW (info) — Worker auto-deploy is silently dormant

`web/.github/workflows/deploy.yml` is in the wrong location for GitHub Actions to pick it up (must be `.github/workflows/` at repo root, not `web/.github/workflows/`). The Cloudflare Worker has therefore **never been auto-deployed by CI** — every Worker deploy to date has been manual `wrangler deploy`, and the J1-4 fix is still un-deployed to the live Worker.

- **Severity:** info (no functional impact; manual deploys work).
- **Trigger:** "Next frontend slice OR when manual `wrangler deploy` friction becomes painful." Likely small fix: move the file to root and add `defaults.run.working-directory: web` to the job, OR add a separate root-level wrapper workflow.
- **Rationale to defer:** Out of scope for a Slice-N smoke; orthogonal to backend correctness.

## Carry-over for next session

- `web/types/backend.ts` regen still owed (now that the backend is deployed with Slice L/M/N schemas, `npm run gen:types` will pick up `ProximityInfo`, `ConversationTurn`, `prior_turns`, `AutoCreatedConceptNote`, `ConceptDocument`).
- The Worker (frontend) is still pre-J1-4-fix: user-visible errors in the browser still read "no message / code unknown" because the Worker hasn't been redeployed. Will resolve when the manual `wrangler deploy` cycle is run.
- Bucket-M1 + Bucket-N1 (authoritative Codex passes) remain owed and gated on the `~/.codex/sessions` permission fix the user runs in their own terminal.
