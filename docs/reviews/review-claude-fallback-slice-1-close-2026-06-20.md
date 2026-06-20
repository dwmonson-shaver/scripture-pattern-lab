# Independent Review — Slice 1 close (concept-identification reader)

- **Date:** 2026-06-20
- **Reviewer:** claude-fallback (Codex blocked by the recurring `~/.codex/sessions`
  permission class — same blocker as Bucket-M1/N1/NP1/O/P; `sudo chown -R $(whoami)
  /Users/dwmonson/.codex` still owed). Ran the same severity language + checklist
  as the Codex pass, per the established E/F/J1/K/M/N/O/P fallback precedent.
- **Scope:** full cumulative Slice 1 diff `247b8db..b823065` — English (KJV)
  translation ingest + chapter-read API + concept create/edit (authored
  color/polarity/opposite) + span-annotation (mark) CRUD + the Nuxt reader
  frontend.
- **Passes run:** one design advisory (DEC-146), one mid-slice code review
  (phases 1–3), one slice-close code review (full diff).

## Design advisory — DEC-146 (high-stakes)

**Verdict: SOUND + 3 mandatory guardrails (all implemented).** Storing the
human's authored color/polarity/opposite as plain `concepts` columns — OFF the
`verification_state`/`evidence_count` endorsement axis, NOT as
`polarity_claims`/`inverse_claims` rows — correctly honors DEC-024/081. The real
risk is a *silent dual source of truth* (`concepts.polarity` vs
`polarity_claims.polarity`), not evidence contamination. Guardrails folded in:
(a) the `authored_` column prefix; (b) the fixed stale `registry.py` "No polarity
column" comment + the DDL evidence-firewall note; (c) a guard test asserting
`create_concept(authored_polarity='+')` writes ZERO claim-table rows. Plain
columns beat an `origin='authored'` flag on claim rows (would smuggle authored
data onto the endorsement axis) and beat a separate table (premature).

## Mid-slice code review (phases 1–3)

**Verdict: clean at P0/P1.** Boundaries hold (`src/ontology` imports neither
retrieval/nlp/app; `reader.py` no app import); DEC-146 firewall intact; charter
intact (human concepts curated/unverified, never auto-promoted; translation
layer separate from corpus ground truth); SQL parameterized; idempotent schema
(the `02` ALTER + guarded `DO $$` constraint add).

- **P2 (fixed inline, `48e576e`)** — `reader.read_chapter` issued the Greek
  query even on the empty-chapter 404 path. Now checks English-empty before the
  Greek query.
- **P2 (accepted)** — `read.get_chapter`'s `version` query param is
  unconstrained; an unknown version yields a 404 `chapter_empty` rather than a
  distinct `version_not_found`. Honest; the version switcher only offers
  ingested codes. No bucket.
- **P3 (accepted tripwire)** — the DEC-146 firewall unit test asserts on
  compiled-SQL-string text; since the editor only touches `concepts_table` it
  can't fail. Documents intent; acceptable as a tripwire.

## Slice-close code review (full diff)

**Verdict: MINOR-FIXES → clean after fix.** No P0/P1. DEC-146 firewall verified
airtight in both the SQL and the SQLAlchemy mirror; no LLM SDK anywhere in
`web/` (grep clean — DEC-081); architecture boundaries hold; parameterization
fully via the SQLAlchemy expression API; all three schema files idempotent; the
`_UNSET`/`model_fields_set` PATCH path and the zod `.nullish()` proxies preserve
absent-vs-null partial-update semantics; `ON DELETE CASCADE` on `mark_concepts`
sound; the new 204-tolerant `sendToBackend` preserves the `BackendError`
contract and leaves `proxyToBackend`/`getFromBackend` intact.

- **S1-CLOSE-001 (P2 — DEC-143 contract break) → CLOSED INLINE.** char offsets
  are PER-VERSE (start into the first verse, end into the last), so a legitimate
  cross-verse selection may end earlier on its line than it began. The
  unconditional `char_end > char_start` check (Pydantic `MarkCreateRequest._check_span`
  + the `07_marks.sql` CHECK) wrongly 422'd / violated the CHECK for such marks,
  while the frontend zod correctly allowed it (`char_end > char_start ||
  verse_end > verse_start`). **Fixed:** both the Pydantic validator and the SQL
  CHECK are now conditional on single-verse (`char_end > char_start OR verse_end
  > verse_start`), matching the frontend.
- **S1-CLOSE-002 (P3) → CLOSED INLINE.** The existing cross-verse test used
  char 0→10 and never exercised the failing geometry. **Fixed:** added
  `test_cross_verse_lower_char_end_allowed` (verse 5→7, char 50→10, expects 201)
  + `test_single_verse_char_end_not_after_start_422`.
- **S1-CLOSE-003 (P3/info) → CLOSED INLINE.** The concept POST/PATCH proxies'
  zod `authored_color` allowed `max(32)` while the backend is `max(9)`.
  **Fixed:** tightened both proxies to `max(9)` so the proxy's fail-fast intent
  holds for this field.

## Findings ledger

| ID | Sev | Disposition |
|----|-----|-------------|
| DEC-146 advisory | — | SOUND; 3 guardrails implemented |
| mid P2 (Greek-on-404) | P2 | fixed inline `48e576e` |
| mid P2 (version 404 conflation) | P2 | accepted (no bucket) |
| mid P3 (firewall test tripwire) | P3 | accepted |
| S1-CLOSE-001 | P2 | fixed inline (this close) |
| S1-CLOSE-002 | P3 | fixed inline (this close) |
| S1-CLOSE-003 | P3/info | fixed inline (this close) |

No P0/P1 at any pass. No open P2 left. Slice 1 backend is unit-green (819) +
ruff-clean; integration tests collect cleanly (DATABASE_URL-gated). The frontend
is committed code-complete + UNVERIFIED (web DoD deferred, DEC-149/125); static
checks (no-LLM-SDK, no text-white-in-chrome) are clean.

## Bucket-P-Codex

Re-deferred — Codex still blocked by the `~/.codex/sessions` perms class. Trigger
unchanged: next session in which the perms are fixed and `/codex:rescue` is
reachable, run an authoritative Codex pass over Slice P **and Slice 1**
(`975aeb3..b823065`), with attention to DEC-146 (the authored-vs-evidence
firewall) and the per-verse mark-offset semantics.
