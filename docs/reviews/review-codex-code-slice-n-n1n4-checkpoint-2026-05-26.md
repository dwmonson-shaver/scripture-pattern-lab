---
type: code-review
flavor: claude-fallback
slice: N
checkpoint: N1-N4 mid-slice
verdict: minor-fixes-recommended (no P0/P1/P2)
base_sha: a549160
head_sha: afca1d4
scope: >
  Deterministic Tier-1 concept auto-generation core, git diff a549160..afca1d4
  (19 files, +1820): lexicon schema + parsers + Core mirrors (N1), bulk loader
  + ingest CLI (N2), English->lemma resolver (N3), auto-create-cited-concept
  writer + dedup (N4).
reviewer_note: >
  Codex was the intended reviewer but is BLOCKED by the recurring
  ~/.codex/sessions permission-denied issue (the same .codex ownership problem
  that produced historic Bucket 5 and Bucket-M1's owed pass — distinct from
  quota). `codex-companion task` errors with "Codex cannot access session files
  ... Operation not permitted"; the user-side fix is
  `sudo chown -R $(whoami) /Users/dwmonson/.codex` from their own terminal,
  which the orchestrator cannot run. Per the established fallback protocol
  (Slices E/F/J1/K/M), this pass runs as `claude-fallback` flavor with the same
  six focus categories and the same P-number severity language; the slice owes
  an authoritative Codex pass tracked as Bucket-N1.
findings_summary: "0 P0, 0 P1, 0 P2, 2 P3, 1 info"
---

# Slice N mid-slice review (N1-N4): deterministic Tier-1 core

## Method

Reviewed `git diff a549160..afca1d4` against six categories: correctness, the
non-negotiable epistemic invariants (DEC-024 / DEC-102), SQL correctness +
injection, resource hygiene, architecture boundaries (DEC-025), and test
fragility. Verified statements compile against the Postgres dialect and that
boundary greps are clean.

## Epistemic-invariant verification (the heart of the slice) — PASS

- `auto_create_cited_concept` writes `origin='lexicon_imported'`,
  `verification_state='unverified'` on every fresh create; the module-level
  constants `LEXICON_ORIGIN`/`LEXICON_VSTATE` are the only values written, and
  `test_concept_writer.py::TestEpistemicConstants` locks them to
  `!= 'human_confirmed'` and `!= 'corpus_observed'`. No code path sets
  `verification_state` to anything else. **PASS.**
- `confidence=None` is written explicitly for lemma rows (never 1.0), honoring
  DEC-024. **PASS.**
- No LLM import anywhere in the N1-N4 surface (`src/ingestion/lexicon/`,
  `src/ontology/lexicon_resolver.py`, `src/ontology/concept_writer.py`). The
  concept + resolver path is 100% deterministic. **PASS.**
- Integration test `test_corpus_is_ground_truth_invariant` asserts
  `DISTINCT verification_state == {'unverified'}` across the concept + its
  lemma rows (mirrors the Slice C exit gate). **PASS.**

## Architecture boundaries (DEC-025) — PASS

- `grep` confirms zero `src.app` imports under `src/ontology/` and
  `src/ingestion/lexicon/`.
- `src/ingestion/lexicon/` imports no query-side packages.
- `concept_writer` imports the `concepts_table` / `concept_lemmas_table` Core
  mirrors (ingestion-shaped mutation), NOT the read-only `ConceptRegistry`
  reader — matches the seed-script discipline. **PASS.**

## SQL correctness + injection — PASS

- All statements are SQLAlchemy Core `select` / `pg_insert`; user input flows
  through bound parameters (`ilike(f"%{term}%")` binds the pattern; `in_(...)`
  binds the list). No string interpolation into SQL text. The `text()` helpers
  in `concept_verification_states` and the CLI use named bind params.
- ON CONFLICT index_elements match the declared UNIQUE constraints exactly:
  `lemma_strongs (morphgnt_lemma, strongs)`; `strongs_glosses (strongs, source,
  gloss)`; `concepts (name)`; `concept_lemmas (lemma, language, concept_id)`.
  Verified the multi-row `pg_insert(table).values(list).on_conflict_do_nothing`
  form compiles to a single parameterized INSERT. **PASS.**

## Resource hygiene — PASS

- Loader runs the whole ingest in one `engine.begin()`; the resolver opens one
  short-lived `engine.connect()` and does at most three bounded queries (no
  per-candidate fan-out — the corpus-presence filter is a single grouped
  `IN (...)` count). Verse-ref helper caps at 12. **PASS.**

## Findings

### N3-FB-001 — P3 (correctness/recall) — gloss ILIKE over-broadens
`_strongs_for_term` matches `gloss ILIKE '%term%'`, so "love" matches
"beloved", "faith" matches "faithfulness", etc. This is acceptable-by-design
for Tier-1 recall (the design wants "the Greek lemmas usually translated as
it"), and the corpus-presence filter + dedup downstream bound the blast radius,
but it can pull in semantically adjacent Strong's. **Disposition: documented as
a known broadening; defer refinement (word-boundary match) to the Tier-2 slice
where graded membership is the explicit subject.** The resolver docstring
already notes the ILIKE recall tradeoff; no inline fix needed at MVP.

### N4-FB-002 — P3 (dedup scope) — exact-name dedup only
`find_existing_concept_id` dedups on exact `concepts.name`. A term differing
only in case/whitespace would create a near-duplicate concept. **Disposition:
acceptable for MVP** — the concept name is the normalized English term and the
orchestration layer (N5) controls the name it passes; richer alias/overlap
dedup is explicitly Tier-2 scope (DEC-102). Re-evaluate when Tier-2 grouping
lands.

### N2-FB-003 — info — empty-dataset emits a dataset_boundary event
`_load_one` emits a `dataset_boundary` event before iterating, so an empty
dataset stream still emits one boundary. Harmless and symmetric with the corpus
loader's always-emit-first-boundary semantics (DEC-036). No fix.

## Verdict

`minor-fixes-recommended` — no P0/P1/P2. The two P3s are design-acceptable at
MVP and dispositioned to the Tier-2 slice; the info note needs no action. The
epistemic core is sound. Cleared to continue to N5 (wire-in + dead-end killer).
An authoritative Codex re-run is owed (Bucket-N1).
