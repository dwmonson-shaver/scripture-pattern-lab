# Design: Slice 1 — Concept Identification UI

> Slice 1 of the concepts/connections/evidence umbrella (DEC-127..143).
> Scope: concept IDENTIFICATION only. Connections, axes, patterns, evidence
> dossiers, citations/OKF, AI discovery, the lens, and the explainer's
> for/against are OUT (Slices 2–5). Research: `thoughts/research-slice-1-concept-identification-2026-06-20.md`.

## Goal
Ship a runnable scripture-marking workbench: read a chapter (English + aligned
Greek interlinear), select a phrase, mark it as a concept, and create/manage a
concept library — primarily on iPad. Backend tested; frontend code-complete
from the prototype with interim types.

## Current state (what we build on)
- Greek-only corpus in `tokens` (book BB / chapter / verse / position), reachable
  only via the DSL pipeline. No English text, no chapter-read, no span model,
  no concept-write API. `concepts` has name/description/origin/verification_state
  only — no color/polarity/opposite columns.
- One engine factory (`get_engine`), `engine.begin()`+`pg_insert` write pattern,
  `ErrorResponse` envelope, `Depends(get_engine)` DI, bearer middleware.
- Nuxt 3 + Vuetify (dark blue theme, semantic tokens, SBL Greek font),
  Nitro proxy, `types/{backend,api}.ts` seam, `check-no-llm-sdk` guard. A
  clickable prototype is the EXACT interaction + visual-grammar spec.

## Desired end state
1. **English translation layer** — `translations` + `translation_verses` tables
   (06_), KJV ingested (WEB optional), verse-aligned by corpus_id/book(BB)/
   chapter/verse. Ingest script mirrors `ingest_corpus.py`.
2. **Chapter-read API** — `GET /api/v1/read/{corpus}/{book}/{chapter}?version=kjv`
   returns ordered verses: `{ref, english_text, greek_tokens:[{position,surface,
   lemma,normalized,morph,pos}]}`. English from `translation_verses`; Greek from
   `tokens` via `tokens_bcvp_idx`. Plus `GET /api/v1/read/versions` (ingested
   translations) for the version switcher.
3. **Span-annotation (mark) model** — `marks` table (07_): id, corpus_id, book,
   chapter, verse_start, verse_end, char_start, char_end, version_code, actor,
   created_at, updated_at; `mark_concepts` join (mark_id, concept_id) for 1..n
   concept refs. CRUD: `POST /api/v1/marks`, `GET /api/v1/marks?corpus=&book=&chapter=&version=`,
   `PATCH /api/v1/marks/{id}` (span + concept reassignment), `DELETE /api/v1/marks/{id}`.
   Cross-verse spans allowed (DEC-129/143).
4. **Concept create/edit** — `POST /api/v1/concepts` + `PATCH /api/v1/concepts/{name}`.
   Human-created = `origin='curated'`, `verification_state='unverified'`. Adds
   authored UI metadata: `color`, `polarity`, `opposite_name`.
5. **Frontend** — the reader (chapter view, version switcher, interlinear
   toggle with tap-chip→highlight), select→popup→right-panel marking, concept
   library + create/edit (color picker + polarity + opposite), mark
   reassignment, draggable word-snapping handles, iPad slide-over + large tap
   targets. Prototype interaction grammar exactly; project Vuetify theme.

## Resolved decisions (new DECs to log)
- **DEC-144 — English translation as its own two-table layer.** A `translations`
  registry (code, name, license, is_public_domain) + `translation_verses`
  (translation_id, corpus_id, book BB, chapter, verse, text). Aligned to the
  corpus by (corpus_id, book, chapter, verse). KJV mandatory (public domain);
  WEB optional. *Rationale:* mirrors the corpus ingest discipline; keeps English
  separable from the Greek ground truth; supports the version switcher and
  later OT/Hebrew without reshaping. Low-stakes/high-confidence.
- **DEC-145 — Marks are a first-class span table with char offsets into a named
  version, plus a concept join.** char_start/char_end are offsets into the
  *English text of the named version* (the surface the human selects on);
  verse_start/verse_end carry the cross-verse range (DEC-143). Greek alignment
  is derived per-read, not stored on the mark (Slice 1 surfaces sampled Greek;
  full BSB word-alignment is later). *Rationale:* the human marks rendered
  English; storing offsets-into-version is the honest anchor. A mark with no
  concept is a "plain highlight" (cids=[]), matching the prototype.
- **DEC-146 — Concept authored UI metadata (`color`, `polarity`, `opposite_name`)
  are plain columns on `concepts`, NOT entries in the evidence-bearing
  `polarity_claims`/`inverse_claims` tables.** *(HIGH-STAKES — Codex checkpoint.)*
  The claim tables carry `verification_state`/`evidence_count` — they are
  *hypotheses the corpus tests*. A user picking a swatch or typing an opposite
  while reading is *authored display metadata*, not a corpus-tested claim, and
  must not enter the endorsement axis (DEC-024/081 confirmation-bias guard —
  exact trap the Slice P review caught). So: add nullable, **`authored_`-prefixed**
  columns to `concepts`: `authored_color VARCHAR(9)` (hex),
  `authored_polarity VARCHAR(2) CHECK IN ('+','-','±')` nullable,
  `authored_opposite_name VARCHAR(64)` nullable (soft ref, no FK — opposite may
  be unminted). `polarity_claims`/`inverse_claims` remain the future
  evidence-grounded layer (Slice 2 connections will relate the two).
  **Codex-fallback advisory (2026-06-20): SOUND + 3 mandatory guardrails** —
  (a) the `authored_` prefix is the single highest-leverage fix (bare `polarity`
  is what a future dev mis-reads as the claim); (b) update the stale
  `src/ontology/registry.py` "No polarity column — claims live in
  polarity_claims" comment + add a REQ note on the DDL: "Authored display
  metadata. NEVER read as evidence; NEVER copy into polarity_claims/
  inverse_claims without a corpus-evidence pass + human promotion (DEC-119/146)";
  (c) a guard test asserting `create_concept(authored_polarity='+')` writes
  ZERO rows to `polarity_claims`/`inverse_claims`. The real risk is a *silent
  dual source of truth*, not evidence contamination; the prefix + the test lock
  the boundary. Plain columns beat an `origin='authored'` flag on claim rows
  (which would smuggle authored data onto the endorsement axis — the exact
  anti-pattern) and beat a separate table (premature). *Rationale:* keeps the
  prototype's per-concept polarity/opposite as cheap authored fields while
  preserving the charter's claim-vs-evidence separation.
- **DEC-147 — Concept-write code lives in a new `src/ontology/concept_editor.py`,
  not the read-only `ConceptRegistry`.** Functions `create_concept(...)` /
  `update_concept(...)` take `Engine`, use `engine.begin()`+`pg_insert`/`update`,
  return the row. Mirrors `concept_writer.py`/`concept_grouping.py`. Keeps the
  reader read-only.
- **DEC-148 — Reader read path lives in `src/retrieval/reader.py`** (multi-stage
  read orchestration is retrieval's job; it joins corpus tokens + translation
  verses). App route calls it with the injected `Engine`. Keeps `src/app`
  routes-only and `src/ontology` claim-free. *(Alternative: a new `src/reading/`
  package — rejected; retrieval is the existing home for corpus reads.)*
- **DEC-149 — Frontend committed code-complete with interim hand-written types
  in `types/api.ts`, web DoD deferred** (DEC-125 precedent — `gen:types` needs a
  deployed backend). Commit message flags the frontend unverified.
- **DEC-150 — Prototype palette maps onto the project Vuetify dark theme.** The
  prototype's warm-parchment look is NOT adopted; its *interaction grammar* is.
  Concept highlight tint = the user-chosen concept color (the one place a raw
  color is legitimately rendered, as content not chrome); all chrome uses
  semantic tokens. *Rationale:* charter says project design system wins; concept
  color is user data, not theme.

## Patterns to follow
- Ingest: `corpus_parser`/`loader` shape (frozen Pydantic row, batched
  `engine.begin()` insert, progress callback, two-factor `--truncate`).
- Writes: `engine.begin()`+`pg_insert(...).on_conflict_do_nothing`/`.returning`.
- Routes: `Depends(get_engine)`, `ErrorResponse` envelope, one exception→row.
- Schema: next files `06_translations.sql`, `07_marks.sql`; idempotent
  `CREATE IF NOT EXISTS`; CHECK constraints mirrored in SQLAlchemy Table.
- Web: components read `~~/types/api`; `GreekText` for Greek; semantic tokens;
  `mountWithVuetify` tests; proxy via `server/utils/backend.ts`.

## Patterns to avoid
- Authored UI metadata leaking onto the `verification_state`/`evidence_count`
  endorsement axis (DEC-024/081).
- Concept-write logic in the registry reader (keep it read-only).
- Adopting the parchment palette into chrome (project theme wins).
- Storing derived Greek alignment on the mark (recompute on read).
- Building connections/axes/patterns/evidence — out of slice.

## Open questions (resolved autonomously per autopilot; surfaced at close)
1. Char offsets vs token offsets for the mark anchor? → **char offsets into the
   named English version** (DEC-145) — matches the prototype's DOM selection and
   the human's actual surface; token offsets would force a Greek anchor the
   English reader never sees.
2. WEB ingest in Slice 1? → KJV mandatory; WEB ingested *if* a clean
   public-domain source is fetchable from GitHub, else KJV-only + the version
   switcher still renders (graceful "not loaded" like the prototype).
3. Mark actor identity (no auth users yet)? → `actor='local'` default constant
   for Slice 1 (single-user); the column exists for later multi-user.

## Slice exit gate (refined in /structure)
Backend: full unit suite green; an integration test that (apply 06+07 schema →
ingest a KJV chapter → `create_concept` → `create_mark` over a cross-verse span
→ `list_marks` by chapter returns it with its concept → read chapter returns
English+Greek) collects cleanly (DATABASE_URL-gated). Frontend: lint/typecheck/
vitest green locally is the user's last-mile; committed code-complete.

## Spec requirements touched (new markers)
- `REQ:08.english-translation` (NEW, canonical-08) — verse-aligned English layer.
- `REQ:08.span-annotations` (NEW, canonical-08) — mark = span→concept(s).
- `REQ:08.concept-authoring` (NEW, canonical-08) — color/polarity/opposite + create/edit.
- `REQ:09.reader-api` (NEW, canonical-09) — chapter-read + versions routes.
- `REQ:09.marks-api` (NEW, canonical-09) — mark CRUD routes.
- `REQ:09.concept-write-api` (NEW, canonical-09) — concept create/edit routes.

## References
- Vision: `design-concepts-connections-evidence.md`; DEC-127..143, DEC-024/081/102/125.
- Prototype: `scratchpad/marker-prototype.html` (interaction + visual grammar).
