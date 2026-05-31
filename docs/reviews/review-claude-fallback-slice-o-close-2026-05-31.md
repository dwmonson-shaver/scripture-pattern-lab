---
type: independent-code-review
flavor: claude-fallback
slice: O
slice_label: Tier-2 concept-groupings (Slice 1)
date: 2026-05-31
base_sha: 29e1aab
head_sha: 3981b72
diff_scope: cumulative slice diff (6 commits, 26 files changed, ~1,815 insertions / ~81 deletions)
reviewer_note: Codex was the intended reviewer; both the Skill-tool name (`codex:codex-rescue`) and the Agent-tool delegation path are unavailable in this background-orchestrator sub-agent context. This is the same blocker class as Bucket-M1 / Bucket-N1 / Bucket-NP1-1 (~/.codex/sessions permission-denied), now extended by a sub-agent harness limitation as well. Per the established precedent across Slices E/F/J1/K/M/N/NP1, this slice-close pass runs as `claude-fallback` with the same six-category checklist; an authoritative Codex pass remains owed.
---

# Slice O Close — Claude-fallback Independent Code Review

Cumulative slice diff `git diff 29e1aab..3981b72`.

## Verdict

**APPROVE WITH FOLLOW-UPS** — 0 P0, 0 P1, 0 P2, 2 P3 (1 closed inline, 1 deferred to new bucket), 1 info.

The two-layer DEC-081 / DEC-115 runtime guard is structurally sound. The application boundary is clean (no code path through `src/ontology/concept_grouping.py` can write `human_confirmed`). The JSONB persistence on the existing `concept_documents.part2_grouping` column avoids a schema migration cleanly. DEC-024 / DEC-025 / DEC-052 / DEC-090 boundaries all preserved.

## Categories reviewed (six-category checklist)

### 1. DEC-081 / DEC-115 enforcement — any path to write `human_confirmed`?

CLEAN at the application boundary.

- `write_grouping(grouping, engine)` signature accepts no `verification_state` parameter (Layer A; introspected by `TestLayerAStructuralGuard`).
- Only value written: module constant `GROUPING_VSTATE: Literal['unverified']`.
- `Tier2Grouping.verification_state: Literal['unverified']` (Layer B-i, Pydantic-enforced).
- `_guard_dec_081` model_validator names DEC-081 in error (Layer B-ii audit).
- `GroupingPointer` has no `verification_state` field — pointer writes cannot carry it.

DB-level mitigation NOT in place (raw SQL UPDATE on JSONB bypasses guards). Explicitly deferred in DEC-115 with rationale; not a finding.

### 2. JSONB shape-drift in auto-discriminator

**O-CLOSE-001 (P3, robustness) — discriminator-priority edge case.** `_decode_part2`, `read_grouping_for_anchor`, and `read_grouping_pointer` all auto-discriminate on key presence (`"members"` vs `"grouping_anchors"`). If a future malformed blob carried BOTH keys, `_decode_part2` would return a `Tier2Grouping` while `read_grouping_pointer` would return a `GroupingPointer` for the same row. No current writer produces both keys, so the path is unreachable today.

**Disposition: ACCEPTED inline as documented schema-discipline.** Closed by extending the docstring on `_decode_part2` (`src/ontology/concept_document.py`) with the discriminator-priority rule. See closure commit below.

Parse-failure degradation (R2 from design doc): both readers return `None` on `model_validate` exception. Sound.

### 3. Idempotency / pointer-merge logic

**O-CLOSE-002 (P3, edge case) → Bucket-O1 NEW (deferred).** In `write_grouping`, the pointer-merge logic on a non-anchor member concept reads the existing `part2_grouping` JSONB and merges anchor names into the pointer list. If the member concept's existing blob is a `Tier2Grouping` (i.e. the member is itself an anchor of a DIFFERENT grouping), the merge silently clobbers the prior anchor blob with a pointer blob. Concretely: write grouping A anchored on humility; then write grouping B anchored on patience with humility as a member; humility's group-A anchor blob is overwritten with `{grouping_anchors: ['patience']}`.

Mitigation today: the seed CLI only writes one grouping; the existing test fixtures use disjoint concepts; the path is not exercised.

**Disposition: DEFER → Bucket-O1.** The fix shape is well-scoped — either raise on the clobber (one-role-per-concept invariant; simplest) OR change the persistence model to allow a concept to carry BOTH an anchor blob and a pointer list (storage shape extension). The right answer depends on whether the curator workflow needs multi-role concepts. Trigger: "next Tier-2 slice OR first time a concept legitimately needs to be both anchor of one grouping and member of another."

Idempotent re-write of the same grouping is correct: `test_idempotent_rewrite_same_payload` confirms no double-append on the pointer list (the `if grouping.anchor_name not in existing_anchors` guard).

### 4. Frontend type-extension correctness

Hand-edited `web/types/backend.ts` matches the Python model surface:
- `Tier2Grouping`: anchor_name ✓ members[] ✓ rationale ✓ origin?: "curated"|"ai_suggested" ✓ verification_state?: "unverified" ✓ created_at ✓
- `GroupingMember`: concept_name ✓ confidence ✓ note?: string|null ✓
- `GroupingPointer`: grouping_anchors[] ✓
- `ConceptDocument` extended with both new nullable fields ✓

Over-the-wire epistemic invariant is preserved (`verification_state` typed as `Literal['unverified']` in TS too).

**O-CLOSE-003 (info) — backend.ts regen owed at next backend redeploy.** Hand-edited shape will be reconciled when `openapi-typescript` runs against the live `/openapi.json`. Carry-over to slice-close summary.

`check:no-llm-sdk` clean — no LLM SDK enters the bundle.

### 5. DEC-024 corpus-is-ground-truth boundary

INTACT.

- `concept_grouping.py` imports only from `src.ontology.registry` (eager) and `src.ontology.concept_document` (lazy, inside functions). No imports from `src.nlp` (no LLM), `src.ingestion` (no ingestion path), or `src.app` (no HTTP layer).
- `seed_humility_grouping.py` imports the engine factory via `src.ingestion.db.get_engine` (the established CLI escape-hatch per DEC-029, matching `seed_registry.py` / `ingest_lexicon.py`). No LLM.
- The writer never touches `tokens` (corpus untouched).
- The writer never mutates `concepts.verification_state` or `concept_lemmas.verification_state` — only `concept_documents.part2_grouping`. Tier-1 ground truth preserved.

### 6. Other discipline gates

- **DEC-025 src.engine ⊥ src.ingestion:** preserved (no new cross-imports).
- **DEC-052 src.app / src.nlp boundary:** preserved (ontology stays self-contained).
- **DEC-090 LLM opt-in pattern:** no new LLM dep; not invoked.
- **Frontend DEC-081 line:** `check:no-llm-sdk` clean.
- **Test discipline:** 713 unit (+28 vs 685 at slice start), 121 integration collected (DATABASE_URL-gated, +4), 102 frontend tests (+13). Ruff clean across src/ tests/ scripts/. Lint + typecheck clean on web/.
- **Phase commit hygiene:** 6 phases, 6 commits, each with imperative-mood subject + Co-Authored-By trailer; each phase tested before commit.

## Findings table

| ID | Severity | Category | One-line | Disposition |
|----|----------|----------|----------|-------------|
| O-CLOSE-001 | P3 | shape-drift | Auto-discriminator priority on `_decode_part2` if both JSONB keys ever co-exist | **Closed inline** — docstring discipline added |
| O-CLOSE-002 | P3 | idempotency | Pointer-merge clobbers an anchor blob if member is also anchor of another grouping | **Deferred → Bucket-O1** with trigger |
| O-CLOSE-003 | info | type-drift | Hand-edited backend.ts pending regen at next backend redeploy | Carry-over to slice-close summary |

## Slice exit gate

`tests/integration/test_tier2_grouping.py::test_humility_grouping_persists_and_renders` — DATABASE_URL-gated; covers write → GET /api/v1/concepts/{anchor}/document → GET /api/v1/concepts/{member}/document round trip; verifies `verification_state='unverified'` over the wire. Plus `test_dec_081_guard_rejects_human_confirmed_at_construction` for the Layer B-i invariant.

**Collects cleanly; live execution requires the user's DATABASE_URL** (deferred per the same pattern as Slice N / NP1).

## Carry-over

- `web/types/backend.ts` regen owed at next backend redeploy (now also includes Tier2Grouping / GroupingMember / GroupingPointer on top of the already-pending ProximityInfo / ConversationTurn / AutoCreatedConceptNote / ConceptDocument shapes).
- Authoritative Codex pass owed on Slice O alongside the pre-existing M1 / N1 / NP1-1 — see new Bucket-O-Codex below.
- Live verification of the worked-example seed deferred until user runs `python scripts/db/seed_humility_grouping.py` against Neon (after backend redeploy that picks up the schema-Python-mirror-aligned `ConceptDocument` model).
