---
type: code-review
flavor: codex-code
slice: O
slice_label: Tier-2 conceptual groupings (slice 1) + DEC-118 backport
diff_range: 29e1aab..b4fe084
date: 2026-06-02
artifact_filename_date: 2026-06-01
reviewer: Codex-code
verdict: FAIL
findings_summary:
  P0: 1
  P1: 0
  P2: 1
  P3: 0
  info: 0
---

# Codex Review - Slice O Close + DEC-118 Backport

Cumulative diff reviewed: `git diff 29e1aab..b4fe084`. I read the full diff by file, the current post-diff source files, the referenced tests, and the two requested prior review artifacts. `git log 29e1aab..b4fe084` shows 9 commits in the range; the task text calls it 8 commits.

## Summary

**FAIL** because the requested pointer-merge invariant is violated: `write_grouping` can overwrite a member document's existing full anchor blob with a pointer blob when a concept is already an anchor of one grouping and then becomes a non-anchor member of another. I also found a Tier-2 guard gap: the DEC-081 validator names the invariant when invoked, but `write_grouping` dumps the incoming `Tier2Grouping` directly, so an explicit `model_construct` bypass is not revalidated at the writer boundary. DEC-118's Tier-1 backport is structurally sound for the auto-create path, DEC-024 corpus boundaries are clean, the API surface is additive, the frontend renders all three Tier-2 shapes, and `check:no-llm-sdk` passed. I did not run the test suite per the action-safety instruction.

## DEC-115 Three-Layer Guard Assessment (Tier-2)

Layer A: **PASS with a bypass caveat.** `write_grouping(grouping, engine)` has no `verification_state` parameter (`src/ontology/concept_grouping.py:153`). The docstring states the invariant (`src/ontology/concept_grouping.py:156`), and the emitted grouping blob comes from the caller-supplied `Tier2Grouping` instance (`src/ontology/concept_grouping.py:183`) before the anchor row update (`src/ontology/concept_grouping.py:202`). The signature is not bypassable through a direct `verification_state` argument, but O-CODEX-002 shows the writer still trusts a validation-bypassed model object.

Layer B-i: **PASS.** `Tier2Grouping.verification_state` is `Literal["unverified"]` (`src/ontology/concept_grouping.py:85`). `origin` is also narrowed for Tier-2 to `Literal["curated", "ai_suggested"]` (`src/ontology/concept_grouping.py:84`).

Layer B-ii: **PASS when invoked; writer-boundary gap filed.** `_guard_dec_081` is present (`src/ontology/concept_grouping.py:88`) and raises an error string naming `DEC-081` when `verification_state` is not `unverified` (`src/ontology/concept_grouping.py:95`). The validator also enforces anchor-in-members and distinct members (`src/ontology/concept_grouping.py:102`, `src/ontology/concept_grouping.py:110`). However, `write_grouping` does not revalidate the incoming model before `model_dump`, so an object built with Pydantic's explicit validation bypass can skip B-ii at write time (O-CODEX-002).

## DEC-118 Three-Layer Guard Assessment (Tier-1)

Layer A: **PASS.** `auto_create_cited_concept(resolution, engine, *, description=None)` has no `verification_state` or `origin` parameter (`src/ontology/concept_writer.py:118`). The writer uses `LEXICON_ORIGIN` and `LEXICON_VSTATE` constants (`src/ontology/concept_writer.py:58`) for both concept and lemma inserts (`src/ontology/concept_writer.py:166`, `src/ontology/concept_writer.py:183`).

Layer B-i: **PASS.** `ConceptCreationOutcome.origin` is `Literal["lexicon_imported"]` and `verification_state` is `Literal["unverified"]` (`src/ontology/concept_writer.py:79`).

Layer B-ii: **PASS.** `_guard_dec_081` is present (`src/ontology/concept_writer.py:82`) and both bad-state branches raise errors that name `DEC-081` (`src/ontology/concept_writer.py:89`, `src/ontology/concept_writer.py:96`).

Scope distinction: **PASS.** DEC-118 narrows only the writer outcome model. The broader read-side aliases in `src/ontology/registry.py` remain `Origin = Literal["curated", "ai_suggested", "lexicon_imported"]` and `VerificationState = Literal["unverified", "corpus_observed", "human_confirmed"]` (`src/ontology/registry.py:36`), which is correct for reading existing curated or confirmed rows.

## DEC-024 Corpus-Is-Ground-Truth Check

**PASS.** `src/ontology/concept_grouping.py` imports only ontology registry state at module import (`src/ontology/concept_grouping.py:39`) and imports `concept_documents_table` lazily inside writer/reader functions (`src/ontology/concept_grouping.py:172`, `src/ontology/concept_grouping.py:245`, `src/ontology/concept_grouping.py:268`). `rg` found no imports from `src.nlp`, `src.ingestion`, or `src.app` in `concept_grouping.py`. `rg` also found no `tokens`, `concept_lemmas`, `update(concepts_table)`, or `update(concept_lemmas_table)` references there; the only updates target `concept_documents.part2_grouping` (`src/ontology/concept_grouping.py:203`, `src/ontology/concept_grouping.py:229`).

## DEC-113 Anchor Model

**PASS with the blocking pointer-merge exception below.** The model has one `anchor_name` per grouping (`src/ontology/concept_grouping.py:81`), and the validator requires that anchor to appear in `members` (`src/ontology/concept_grouping.py:102`). The writer stores the full grouping blob on the anchor document (`src/ontology/concept_grouping.py:202`) and writes `GroupingPointer` blobs for non-anchor members (`src/ontology/concept_grouping.py:213`). The exception is O-CODEX-001: a concept that is already an anchor can lose that full blob when later written as a member.

## DEC-114 Persistence

**PASS.** Persistence uses the existing `concept_documents.part2_grouping` JSONB column (`src/ontology/concept_document.py:71`). `ConceptDocument` exposes typed `part2_grouping` and `part2_grouping_pointer` fields (`src/ontology/concept_document.py:139`). `_decode_part2` auto-discriminates by key presence: `members` for a full grouping and `grouping_anchors` for a pointer (`src/ontology/concept_document.py:251`, `src/ontology/concept_document.py:276`). I found no new relational `concept_groupings` table in the diff or current source.

## Pointer-Merge Invariant

**FAIL.** The writer does not preserve an existing anchor blob when writing a pointer. In the non-anchor loop, the code reads the existing `part2_grouping` blob (`src/ontology/concept_grouping.py:214`) but only preserves it when it already has `grouping_anchors` (`src/ontology/concept_grouping.py:221`). If the existing blob is a full `Tier2Grouping` with `members`, `existing_anchors` stays empty and the writer overwrites the same `part2_grouping` column with a `GroupingPointer` (`src/ontology/concept_grouping.py:227`, `src/ontology/concept_grouping.py:231`). That violates the requested invariant that pointer writes must not clobber an existing anchor blob.

## API Surface

**PASS.** The existing `GET /api/v1/concepts/{name}/document` route remains the route surface and returns `response_model=ConceptDocument` (`src/app/routes/concepts.py:34`). The route handler still just reads `get_document` and returns the model, with the same 404 path when absent (`src/app/routes/concepts.py:49`). Tests cover anchor, member, and Tier-1-only response shapes (`tests/unit/test_app_routes_concept_document.py:111`, `tests/unit/test_app_routes_concept_document.py:132`, `tests/unit/test_app_routes_concept_document.py:146`). This is additive over the prior document route.

## Frontend

**PASS.** `ConceptDocumentView.vue` passes `document.part2_grouping` and `document.part2_grouping_pointer` into `Tier2GroupingSection` (`web/components/ConceptDocumentView.vue:70`). `Tier2GroupingSection.vue` renders anchor (`web/components/Tier2GroupingSection.vue:33`), pointer (`web/components/Tier2GroupingSection.vue:92`), and placeholder (`web/components/Tier2GroupingSection.vue:133`) shapes. The TypeScript API aliases expose `Tier2Grouping`, `GroupingMember`, and `GroupingPointer` (`web/types/api.ts:32`), and `web/types/backend.ts` includes the new schemas and nullable fields (`web/types/backend.ts:302`, `web/types/backend.ts:331`).

## DEC-116 Worked-Example Seed

**PASS from code inspection; live recall is unverifiable from diff alone.** The seed defines the humility/meekness/lowliness cluster with confidences (`scripts/db/seed_humility_grouping.py:68`), resolves and auto-creates concepts through the Tier-1 path (`scripts/db/seed_humility_grouping.py:89`, `scripts/db/seed_humility_grouping.py:98`), persists deterministic documents (`scripts/db/seed_humility_grouping.py:110`), builds a `Tier2Grouping` (`scripts/db/seed_humility_grouping.py:164`), and writes it through `write_grouping` (`scripts/db/seed_humility_grouping.py:186`). The integration test asserts seed persistence and idempotency (`tests/integration/test_seed_humility_grouping.py:48`, `tests/integration/test_seed_humility_grouping.py:69`).

## DEC-117 Bucket-NP1-2 Scope-In

**PASS.** `useConceptDocument` now passes `lazy: true` to `useFetch` (`web/composables/useConceptDocument.ts:33`, `web/composables/useConceptDocument.ts:37`). This matches the Bucket-NP1-2 direct-URL SSR error-handling fix described in the code comment (`web/composables/useConceptDocument.ts:28`).

## Architectural Imports Check

**PASS.** `src/ontology/concept_grouping.py` does not import `src.nlp`, `src.ingestion`, or `src.app` by direct `rg` check. `npm run check:no-llm-sdk` passed in `web/` against the present `.output` bundle, and the script checks forbidden Anthropic/Gemini SDK strings plus OpenAI import/require patterns (`web/scripts/check-no-llm-sdk.mjs:23`, `web/scripts/check-no-llm-sdk.mjs:30`). The relevant package script is present at `web/package.json:25`.

## Test Coverage

**PASS for guard coverage; FAIL for the pointer-merge invariant.** Tier-2 Layer A is covered by signature introspection (`tests/integration/test_concept_grouping_writer.py:95`). Tier-2 Layer B-i and B-ii are covered in model tests (`tests/unit/test_concept_grouping_models.py:147`, `tests/unit/test_concept_grouping_models.py:172`). DEC-118 Layer A/B-i/B-ii are covered in `tests/unit/test_concept_writer.py:88`, `tests/unit/test_concept_writer.py:106`, and `tests/unit/test_concept_writer.py:152`; the current backport block contains ten test functions, including the requested eight-plus coverage. Worked-example persistence has integration coverage (`tests/integration/test_seed_humility_grouping.py:48`), and the HTTP exit gate covers anchor and member document reads (`tests/integration/test_tier2_grouping.py:78`). The missing test is the blocking case: a concept that already has a full anchor `part2_grouping` blob later being processed as a non-anchor member. The existing pointer idempotency test only covers rewriting the same grouping with a pointer list (`tests/integration/test_concept_grouping_writer.py:128`).

## Findings Table

| ID | Severity | File:Line | Description | Recommended action |
|----|----------|-----------|-------------|--------------------|
| O-CODEX-001 | P0 | `src/ontology/concept_grouping.py:221` | `write_grouping` ignores an existing full `Tier2Grouping` blob on a non-anchor member row, then overwrites `concept_documents.part2_grouping` with a `GroupingPointer` at `src/ontology/concept_grouping.py:231`. A valid sequence like "write grouping A anchored on humility, then write grouping B anchored on patience with humility as a member" destroys humility's grouping-A anchor blob. This is data loss against the requested pointer-merge invariant. | Before closing the slice, make pointer writes detect `existing` blobs containing `members`. Either raise a clear error until one-role-per-concept is the accepted invariant, or extend the storage shape so a row can preserve its anchor blob and also carry member pointers. Add a regression test where an existing anchor becomes a member of another grouping and prove the original anchor blob is not clobbered. |
| O-CODEX-002 | P2 | `src/ontology/concept_grouping.py:183` | The Tier-2 writer calls `grouping.model_dump(mode="json")` directly on the caller-supplied object and never revalidates or directly checks `grouping.verification_state` before persisting. Normal construction is protected by `Literal["unverified"]` at `src/ontology/concept_grouping.py:85`, and `_guard_dec_081` names the invariant when it runs at `src/ontology/concept_grouping.py:95`; but the tests themselves document that `Tier2Grouping.model_construct(...)` skips validators (`tests/unit/test_concept_grouping_models.py:179`). A future caller using that explicit bypass could pass `verification_state="human_confirmed"` into `write_grouping` and have it serialized. | Add a writer-boundary assertion or revalidation before `model_dump`, e.g. reject unless `grouping.verification_state == GROUPING_VSTATE` and/or round-trip through `Tier2Grouping.model_validate(grouping.model_dump())`. Add a focused regression that passes a `model_construct` bad grouping to `write_grouping` and expects a DEC-081-named failure. |

## Advisory (Not A Finding)

The three-layer pattern is structurally sound only if the writer boundary revalidates or directly asserts the incoming model's guarded fields. Layer A prevents a normal caller-supplied state argument, Layer B-i is the load-bearing Pydantic constraint, and Layer B-ii gives an explicit DEC-081 audit trail when validation is invoked. Without writer-boundary revalidation, B-ii is mostly diagnostic rather than protective for explicit `model_construct` bypasses.

## Footer

Finding counts: P0 = 1, P1 = 0, P2 = 1, P3 = 0, Info = 0.

Overall verdict: **FAIL**. Slice O should not close while `write_grouping` can clobber an existing anchor grouping blob during pointer writes, and the Tier-2 writer should revalidate or assert DEC-081 at the writer boundary before relying on the model validator.
