# MVP Corpus Scope

## Purpose
Decide and document the corpus, text edition, annotation requirements, and data sources for the MVP. The goal is to choose the narrowest scope that still demonstrates the full value of the pattern engine. [DEC-020]

## Decision: Greek New Testament (SBLGNT + MorphGNT)

### Why Greek NT
- Richest available open annotation data (morphology, lemmas, syntax)
- Manageable size (137,554 tokens across 27 books — pinned via the slice exit-gate test `tests/integration/test_corpus_ingest.py::test_full_corpus_smoke`; see DEC-047)
- Contains the flagship use case (faith > hope > love in 1 Corinthians 13:13)
- Pauline corpus alone provides dense ground for sequence hypothesis testing
- Community of scholars and students most likely to engage early
- Avoids the additional complexity of Hebrew cantillation, vowel pointing ambiguity, and ketiv/qere variants in the first iteration

### Why SBLGNT
- Open license (SBLGNT is freely available for non-commercial use under the SBLGNT EULA)
- Widely accepted critical text
- Paired with MorphGNT for full morphological parsing and lemmatization
- Active community maintaining the data (MorphGNT on GitHub)

### What's deferred
- Hebrew Bible / Old Testament (v0.2+)
- Septuagint / LXX (v0.3+)
- Cross-lingual alignment / MT-LXX-NT mediation (v0.4) [ASM-005]
- Aramaic portions of Daniel/Ezra (deferred with Hebrew)
- Textual variant apparatus (future feature, not MVP)

<!-- REQ:08.annotation-layers -->
## Required Annotation Layers

Each token in the corpus must carry the following annotations:

| Layer | Source | Example |
|-------|--------|---------|
| Surface form | SBLGNT text | πίστις |
| Lemma | MorphGNT | πίστις |
| Morphological parse | MorphGNT | N-NSF (noun, nominative, singular, feminine) |
| Part of speech | Derived from morph parse | NOUN |
| Book | Text structure | 07 |
| Chapter | Text structure | 13 |
| Verse | Text structure | 13 |
| Token position | Sequential index | 1-based within verse |

Book values are stored as 2-digit `BB` codes from MorphGNT's `BBCCVV` row prefix (e.g. `07` for 1 Corinthians, `25` for 3 John). See DEC-026.

<!-- REQ:08.apparatus-marks -->
### Editorial apparatus marks

SBLGNT preserves critical-apparatus marks (`⸀ ⸂ ⸃`) on tokens that carry editorial decisions about the underlying text. The ingestion pipeline retains these marks in `surface_form` (for citation fidelity) and removes them from `normalized_form` (the canonical match key). Queries that need to match real tokens should target `normalized_form` or `lemma`; matching against `surface_form` will silently miss any token carrying apparatus marks.

No `surface_form` index is created for this reason — indexing it would invite the silent-miss failure mode.

### Nice-to-have for MVP (if available without significant effort)
- Clause boundaries (from OpenText or similar)
- Sentence boundaries
- Discourse unit boundaries (pericope)

### Not required for MVP
- Semantic role labels
- Syntax trees
- Discourse structure annotations
- Textual variant data

## Data Source: MorphGNT

MorphGNT provides a row-per-token dataset with columns:

```
book/chapter/verse  part-of-speech  parse-code  text  word  normalized  lemma
```

This maps directly to our required annotation layers:
- `text` → surface form
- `lemma` → lemma
- `parse-code` → morphological parse (Robinson encoding)
- `part-of-speech` → POS (first field of parse code)
- `book/chapter/verse` → structural position

MorphGNT is available on GitHub under the MorphGNT project. The data is derived from the SBLGNT.

<!-- REQ:08.concept-registry -->
## Concept Registry — MVP Scope

The concept registry maps concepts to lemmas. For MVP, we need a small but meaningful initial set that covers the flagship use cases.

### Minimum viable concept set

| Concept | Greek Lemma(s) | Polarity | Notes |
|---------|---------------|----------|-------|
| faith | πίστις, πιστεύω | + | Core use case |
| hope | ἐλπίς, ἐλπίζω | + | Core use case |
| love | ἀγάπη, ἀγαπάω | + | Core use case |
| unbelief | ἀπιστία, ἀπιστέω | - | Inverse of faith |
| doubt | διακρίνω, διστάζω | - | Inverse of faith (partial) |
| despair | ἐξαπορέω | - | Inverse of hope |
| hatred | μῖσος, μισέω | - | Inverse of love |
| righteousness | δικαιοσύνη, δίκαιος | + | Common Pauline concept |
| sin | ἁμαρτία, ἁμαρτάνω | - | Inverse of righteousness |
| grace | χάρις | + | Common Pauline concept |
| law | νόμος | neutral | Pauline theology keyword |
| salvation | σωτηρία, σῴζω | + | Core theological concept |
| death | θάνατος, ἀποθνῄσκω | - | Common contrast concept |
| life | ζωή, ζάω | + | Common contrast with death |
| spirit | πνεῦμα | + | Pauline theology keyword |
| flesh | σάρξ | - | Pauline contrast with spirit |
| truth | ἀλήθεια | + | Common concept |
| knowledge | γνῶσις, γινώσκω | + | Common concept |
| joy | χαρά, χαίρω | + | Common concept |
| peace | εἰρήνη | + | Common concept |

This gives ~20 concepts with ~30 lemma mappings, enough to test sequence, polarity, and inverse queries across the Pauline corpus.

### Registry growth strategy
- The initial set is manually curated (`origin='curated'`)
- AI-assisted expansion suggests new mappings; suggestions land with `origin='ai_suggested'` and `verification_state='unverified'`
- Each new mapping must be reviewed before it advances to `verification_state='human_confirmed'` (not auto-approved)
- The registry is versioned alongside the DSL
- The seed-time `Polarity` column above is informational; in the schema, polarity is a *claim* (a row in `polarity_claims`, see below) with provenance and evidence — not a column on `concepts`

<!-- REQ:08.registry-epistemics -->
## Registry Epistemics — Provenance, Evidence, and Grounding

DEC-024 makes the corpus-is-ground-truth principle a non-negotiable architectural rule: registry entries (concept seeds, lemma mappings, polarity claims, inverse claims) are **provisional priors** that must clear corpus evidence before the system treats them as confirmed. Query results that depend on unverified registry entries are **prior-grounded**, not evidence-grounded, and must be labeled as such.

This section is the structural commitment behind that decision. It encodes four invariants that the schema sketch below realizes:

1. **Provenance on every registry row.** Every row in `concepts`, `concept_lemmas`, `polarity_claims`, and `inverse_claims` carries `origin VARCHAR(20) NOT NULL DEFAULT 'curated'`. Allowed values: `'curated'` (human-entered seed), `'ai_suggested'` (AI-proposed, awaiting review), `'lexicon_imported'` (drawn from a third-party lexical source). Origin tracks where the assertion came from; absence of provenance is not allowed.

2. **`confidence` defaults to NULL, never 1.0.** A NULL confidence reads as "we have no probability estimate yet" — distinct from `0.0` ("we estimate zero"). Defaulting to `1.0` would silently convert a curator's unverified assertion into a maximum-confidence corpus fact, which is the failure mode DEC-024 exists to prevent.

3. **Polarity and inverse are evidence-bearing relational claims, not concept properties.** `polarity_claims` and `inverse_claims` are separate tables (not columns on `concepts`), each carrying `evidence_count INTEGER NOT NULL DEFAULT 0` and `verification_state VARCHAR(20) NOT NULL DEFAULT 'unverified'`. The verification state has three values: `'unverified'` (seeded but not corroborated by corpus observation), `'corpus_observed'` (the assertion has been observed in corpus evidence above some threshold), `'human_confirmed'` (a human reviewer has explicitly confirmed it). Seeded rows always start `'unverified'`.

4. **Query results carry a grounding axis.** `ValidationResult.grounding` (and, when the executor lands, `MatchCandidate.grounding`) takes one of `'evidence-grounded'`, `'prior-grounded'`, `'mixed'`, or `null`. The grounding axis is **orthogonal to match-mode** — it answers "is the resolution backed by corpus evidence" rather than "how do we resolve the node". The capability validator's rule 13 (`_rule_13_registry_grounding`) inspects backing registry rows for any concept node referenced with polarity or inverse and emits a `RULE13_PRIOR_GROUNDED` warning when any backing claim is `'unverified'`. The warning is **additive, not blocking**: status remains `supported`; only `grounding` flips to `'prior-grounded'`. Aligns with DEC-007 (results distinguish match types) and DEC-015 (AI explains rather than silently decides).

The seed-script discipline that realizes this commitment: every row inserted at seed time lands `origin='curated'`, `verification_state='unverified'`, `confidence=NULL`. Nothing in the seed flips to `'corpus_observed'` or `'human_confirmed'` — those transitions are downstream slice work.

**Tier-1 lexicon-imported concepts (DEC-102/DEC-104).** A query for a term with no registry mapping now triggers deterministic Tier-1 auto-generation: the term is resolved against the self-hosted lexicon (below) to the MorphGNT lemmas usually translated as it AND present in the corpus, and a concept is written with `origin='lexicon_imported'`, `verification_state='unverified'`, `confidence=NULL`. This is a sourced prior (a single English word ↔ its usual Greek lemmas — "almost citing a dictionary"), NOT a conceptual claim, and is **never** auto-promoted to `'corpus_observed'` or `'human_confirmed'`. No LLM touches this write path. Tier-2 conceptual groupings (different underlying Greek that "hangs together") remain a human-validated later-slice concern (DEC-081, scoped to Tier 2).

<!-- REQ:08.lexicon-sourcing -->
## Lexicon Sourcing — Self-Hosted Open Datasets (Tier-1)

Tier-1 auto-generation rests on a self-hosted, permissively-licensed lexicon stack (DEC-103), ingested once into Postgres like the corpus (no runtime API dependency, <10 MB). Three datasets, each vendored under `data/raw/lexicon/` (provenance + licenses in that directory's README):

1. **`jtauber/greek-lemma-mappings`** (CC BY-SA 4.0) — the MorphGNT-lemma ↔ Strong's bridge. Its lemma keys byte-match the SBLGNT corpus lemmas by construction (same author), so it reconciles Strong's to the exact lemma forms in `tokens`. Loaded into `lemma_strongs (morphgnt_lemma, strongs)`.
2. **STEPBible TBESG** (CC BY 4.0) — the Strong's ↔ English-gloss reverse-lookup source (Abbott-Smith based). Loaded into `strongs_glosses (strongs, lemma, gloss, source='tbesg')`.
3. **Dodson Greek Lexicon** (Public Domain) — gloss fallback. Loaded into `strongs_glosses (..., source='dodson')`.

The reverse-lookup pipeline (deterministic, NO LLM): `English term → strongs_glosses.gloss ILIKE '%term%' → Strong's set → lemma_strongs bridge → MorphGNT lemma forms → INNER JOIN tokens (corpus-presence filter) → resolved lemmas + their corpus verse citations`. A lemma absent from the loaded corpus is dropped (it cannot be queried); a term that maps to no corpus-present lemma resolves as *unresolved* and the query returns the honest `concept_not_mapped` 422 (DEC-006). Schema: `data/schemas/03_lexicon.sql`; ingest CLI: `scripts/db/ingest_lexicon.py` (wholesale, two-factor `--truncate` + `SPL_LEXICON_CONFIRM_TRUNCATE=1` gate, exit codes 0/1/2/3 — mirrors the corpus/seed ingests). The lexicon is the *cited authority*; the corpus is the *grounding*; an LLM is at most an assembler/explainer (below), never the source of truth.

<!-- REQ:08.concept-document -->
## Conceptual Document — Persisted Two-Part Article

Every Tier-1 auto-creation yields a SHORT inline summary in the query interaction AND a persisted, linkable long article; BOTH the concept and the article persist (stored on first creation, retrieved later — **never regenerated per query**). The article is a first-class per-concept entity (`concept_documents` table, `data/schemas/04_concept_documents.sql`) with two parts:

- **Part 1 = the Tier-1 article (now)**, two clearly-labeled sections:
  - **§1 Pure comparative lexicon analysis** — DETERMINISTIC, NO LLM: which Greek lemmas, which Strong's, the usual English renderings, the corpus verse references. A factual comparison drawn straight from the ingested datasets + corpus. No opinion, no assertion.
  - **§2 LLM-generated educational analysis** — explicitly labeled as generated. Beginner-friendly prose where the LLM is strictly an EXPLAINER/ASSEMBLER of the §1 evidence it is handed; it cites its sources and is stored WITH those citations. It NEVER feeds back into the concept's lemma set or verification state. Opt-in (`SPL_CONCEPT_ARTICLE_LLM`), NL path only; on LLM unavailable/FALLBACK/empty it degrades to §1-only (the concept + §1 never depend on it).
- **Part 2 = the Tier-2 grouping artifact** — formerly a placeholder; SHIPPED in Slice O (see `REQ:08.tier-2-groupings` below). The `part2_grouping` JSONB column on `concept_documents` carries either a full Tier-2 `Tier2Grouping` (when the concept is the grouping anchor) or a `GroupingPointer` (when the concept is a non-anchor member), discriminated by the JSONB shape. NULL when the concept is not yet part of any grouping.

The epistemic line is structural: the **concept** (lemma set, origin, verification state, cited corpus verses) is regenerable-proof ground truth (DEC-024); the **article §2** is regenerable commentary layered on top (DEC-081, DEC-106); the **Tier-2 grouping** is a hypothesis the corpus + a human must validate (DEC-081, DEC-115). The persisted document is retrieved via `GET /api/v1/concepts/{name}/document` (404 if not yet generated).

<!-- REQ:08.tier-2-groupings -->
## Tier-2 Conceptual Groupings (Slice O)

A **Tier-2 grouping** is a claim that 2+ existing concepts "hang together" conceptually — distinct from Tier-1 lexicon translation mappings (DEC-102) and from the binary asymmetric `polarity_claims` / `inverse_claims` tables. Tier-2 is the curator territory where DEC-081 actually bites: every grouping is a HYPOTHESIS the corpus + a human must validate.

**Persistence (Slice O — DEC-114).** Groupings persist as JSONB on the existing `concept_documents.part2_grouping` column. Two shapes share that slot:
- The grouping **anchor** concept's document carries the full `Tier2Grouping` blob: `{ anchor_name, members: [{concept_name, confidence ∈ [0,1], note?}], rationale, origin ∈ {curated, ai_suggested}, verification_state, created_at }`.
- Every non-anchor **member** concept's document carries a `GroupingPointer { grouping_anchors: [str] }` back to the anchor(s). A concept may belong to multiple groupings; the pointer's anchor list grows additively.

**Runtime DEC-081 enforcement (Slice O — DEC-115).** Two-layer guard:
- **Layer A (structural):** `src/ontology/concept_grouping.py::write_grouping(...)` accepts NO `verification_state` parameter. The only value ever written is the module constant `GROUPING_VSTATE: Literal['unverified']`. This is the same pattern `auto_create_cited_concept` uses for Tier-1 — new caller paths cannot bypass.
- **Layer B (model-level):** `Tier2Grouping.verification_state` is typed `Literal['unverified']` (Pydantic rejects any other value at construction) AND a `model_validator` re-asserts the invariant with a DEC-081-named error message, catching documented bypasses like `model_construct` when their output round-trips through `model_validate`. Layer B-i is load-bearing; B-ii names DEC-081 for audit/debug.

**What's NOT in scope for Slice O (bucketed for future Tier-2 slices):** phrase-valued members (DSL fragments as members); LLM evidence-assembly / white-paper-style commentary; match-type expansion (`expanded` / `grouping`). The corpus-evidence finder and the promotion-to-`human_confirmed` write path — listed here originally as future work — SHIPPED in **Slice P** (see below).

**Worked example.** `scripts/db/seed_humility_grouping.py` (DEC-116) seeds the humility/meekness/lowliness cluster — the concrete bridge for Bucket-N3 (Tier-1 narrow recall: TBESG glosses verb/adjective forms as "humble"/"humble oneself" rather than the noun, so the Tier-1 path produced only `ταπεινοφροσύνη` for "humility"; the Tier-2 grouping bridges that recall gap by surfacing the wider conceptual neighborhood).

<!-- REQ:08.grouping-evidence -->
<!-- REQ:08.curator-promotion -->
## Tier-2 Corpus Evidence + Curator Promotion (Slice P)

Slice P adds the two halves that make a Tier-2 grouping *testable and curatable* — the curator territory DEC-081 was written for.

**Corpus-evidence finder (deterministic).** For a grouping, `src/retrieval/grouping_evidence.py::compute_grouping_evidence` measures whether the members' lemmas actually co-occur in the corpus, by compiling each unordered member pair to DSL (`lemma:A ~ lemma:B within:window(N) corpus:nt`) and running the Slice-L cooccurrence/window engine. It reports per pair: resolved lemmas, `match_count`, sample verse refs, `window_n`, whether the registry already declares the pair an inverse, and a descriptive `cooccurrence_threshold_met` flag. It performs no LLM calls and **advances no state**. Co-occurrence is *evidence to weigh, not confirmation* — antonyms co-occur constantly; a member with no corpus lemma surfaces as zero-evidence (the Bucket-N3 recall gap made visible).

**Curator promotion (human-gated).** A grouping's **`curator_state`** advances `unverified → corpus_observed → human_confirmed`, forward-only and single-step, via `src/ontology/concept_grouping.py::promote_grouping` (exposed at `POST /api/v1/concepts/{name}/grouping/promote`). Each advance is a HUMAN action recorded append-only in the `grouping_promotions` audit log with an actor, a rationale, and a frozen snapshot of the evidence reviewed (DEC-124, the authoritative source of `curator_state`). `corpus_observed` = a human reviewed the corpus evidence and judged it relevant; `human_confirmed` = a human endorsed the grouping as conceptually sound. **The corpus never advances state on its own (DEC-120)** — the deterministic evidence informs the human; it does not confirm the hypothesis. Critically, `curator_state` is a SEPARATE fact from the grouping blob's `verification_state`, which stays `Literal['unverified']` forever (DEC-119) — the auto-create/auto-group DEC-081 guard is untouched, and a new anti-regression test enforces that the promotion path cannot weaken it (DEC-126). This is the human-gated write path the Slice-O runtime guard existed to prevent being added *by accident*; Slice P adds it *deliberately and safely*.

<!-- REQ:08.english-translation -->
## English Translation Layer (Slice 1)

The corpus (`tokens`) is Greek-only; the human reads and marks in English. Slice 1 adds a verse-aligned English translation layer SEPARATE from the corpus ground truth (English is a reading surface, not the symbolic-retrieval substrate; DEC-128/144).

- `translations` — registry of ingested versions: `code` (UNIQUE), `name`, `license`, `is_public_domain`.
- `translation_verses` — `(translation_id, corpus_id, book BB, chapter, verse, text)` with a UNIQUE natural key, aligned to `tokens` by `(corpus_id, book, chapter, verse)`.

KJV is the mandatory public-domain default; other public-domain versions (WEB/ASV/YLT) may ingest under their own `code`. Schema `data/schemas/06_translations.sql`; parse/load in `src/ingestion/translations/` (KJV-shape per-book JSON → BB codes; batched `engine.begin()` + ON CONFLICT DO NOTHING; idempotent re-run); CLI `scripts/db/ingest_translation.py` (two-factor `--truncate` + `SPL_TRANSLATION_CONFIRM_TRUNCATE=1`, exit 0/1/2/3); fetch helper `scripts/ingest/fetch_kjv.sh` (aruljohn/Bible-kjv, vendored under gitignored `data/raw/translations/`).

The chapter-read path (`src/retrieval/reader.py::read_chapter`, DEC-148) joins `translation_verses` to `tokens` and surfaces, per verse, the English text plus the ordered Greek tokens beneath it (the interlinear). `list_versions` backs the version switcher. Greek↔English per-word alignment (BSB) is a later slice; Slice 1 surfaces the verse's Greek tokens as a whole.

<!-- REQ:08.span-annotations -->
## Span Annotations (Marks) (Slice 1)

A **mark** is a span annotation tying a selected phrase to 0..n concepts (DEC-129/143/145). It is distinct from the per-token corpus annotation of `REQ:08.annotation-layers` above — a mark is a HUMAN-authored selection over the *rendered English text*, not a corpus token property.

- `marks` — `(corpus_id, book BB, chapter, verse_start, verse_end, char_start, char_end, version_code, actor, created_at, updated_at)` with `CHECK(verse_end >= verse_start)` and `CHECK(char_end > char_start)`. `char_start`/`char_end` are offsets into the English text of the NAMED version (the surface the human selects on); the verse range carries the cross-verse extent (DEC-143 — single-verse marking was a prototype simplification only).
- `mark_concepts` — `(mark_id, concept_id)` join, `ON DELETE CASCADE`. A mark with no rows here is a "plain highlight."

Greek alignment is derived at read time, never stored on the mark (DEC-145). Logic in `src/ontology/marks.py` (concepts referenced by NAME at the API boundary, resolved to id; `UnknownConcept` is all-or-nothing in one transaction; update replaces the concept set wholesale). Schema `data/schemas/07_marks.sql`.

<!-- REQ:08.concept-authoring -->
## Concept Authoring — color / polarity / opposite (Slice 1)

Human-authored concepts gain user-editable DISPLAY metadata while reading (DEC-130): `authored_color`, `authored_polarity` (`+`/`-`/`±`), `authored_opposite_name` — plain NULLable columns on `concepts`.

**These authored fields are deliberately OFF the endorsement axis (DEC-146).** They carry no `verification_state`/`evidence_count`. They are display priors a human typed, NOT corpus-tested claims, and must NEVER be read as evidence or copied into the evidence-bearing `polarity_claims`/`inverse_claims` without a corpus-evidence pass + a human promotion (DEC-119/146). The `authored_` prefix, the DDL firewall comment, and a guard test (authored polarity writes ZERO claim rows) enforce the separation. The evidence-grounded polarity/inverse layer remains `polarity_claims`/`inverse_claims`; Slice 2 connections will relate the two.

Human concepts are `origin='curated'`, `verification_state='unverified'`, never auto-promoted (DEC-081/102). Write code: `src/ontology/concept_editor.py` (`create_concept`/`update_concept`, DEC-147) — separate from the read-only `ConceptRegistry`.

<!-- REQ:08.ingestion-pipeline -->
## Ingestion Pipeline — MVP

### Steps
1. Download MorphGNT data (one file per book; rows are single-ASCII-space delimited, 7 columns each)
2. Parse each row into a structured token record
3. Assign sequential token IDs (global and per-verse)
4. Load into Postgres with appropriate indexes
5. Seed the concept registry from the table above
6. Build lemma-to-concept index

### Production entrypoint

Step 4 (load) is realized by `scripts/db/ingest_corpus.py` — the production CLI. See DEC-039. The whole 27-book load runs inside a single `engine.begin()` transaction (DEC-044) so the `tokens` table is never observed in a partial-load state.

**Re-run idempotency.** The script never auto-resets the `tokens` table. To re-run an ingestion, pass `--truncate` AND set `SPL_INGEST_CONFIRM_TRUNCATE=1` (two-factor destructive-op gate). Without both, the script refuses if `tokens` is non-empty (exit code 2). The truncate primitive is `src/ingestion/db.py::truncate_tokens` (DEC-038): a short-lived transaction running `TRUNCATE TABLE tokens RESTART IDENTITY`. The primitive does not gate on its own — the caller (the script's `main()`) owns the gate.

**Filename-drift guard.** The default-path guard (`_assert_27_files_present`) asserts every one of the 27 mapped MorphGNT filenames is present in `data/raw/morphgnt-sblgnt/`; extras like the upstream-vendored `README.md` are tolerated (DEC-048). The relaxed `--corpus-dir` path (used by tests against the 2-book `tests/fixtures/morphgnt/multi/`) still rejects extras (DEC-041).

**Exit-code taxonomy** (DEC-040):

| Code | Meaning |
|------|---------|
| 0 | Success — `inserted N tokens` printed to stderr |
| 1 | Uncaught exception — traceback printed to stderr |
| 2 | User error — refused destructive op (`--truncate` without env confirm, or non-empty table without `--truncate`) |
| 3 | Corpus-dir filename drift — a mapped MorphGNT book is missing |

<!-- REQ:08.token-schema -->
### Database Schema (sketch)

```sql
-- Core token table
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    book VARCHAR(10) NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    position INTEGER NOT NULL,        -- 1-based position within verse
    global_position INTEGER NOT NULL, -- 1-based position within corpus
    surface_form TEXT NOT NULL,       -- raw token, apparatus marks preserved
    normalized_form TEXT NOT NULL,    -- canonical match key, apparatus marks removed
    lemma TEXT NOT NULL,
    morph_code VARCHAR(20) NOT NULL,
    pos VARCHAR(10) NOT NULL,
    language VARCHAR(5) DEFAULT 'grc',
    corpus_id VARCHAR(10) DEFAULT 'nt' -- forward-compat for non-NT corpora
);

<!-- REQ:08.concept-table -->
-- Concept registry. Polarity is NOT a column here — it's a claim with
-- provenance and evidence (see polarity_claims). See REQ:08.registry-epistemics.
CREATE TABLE concepts (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL UNIQUE,
    description         TEXT,
    origin              VARCHAR(20) NOT NULL DEFAULT 'curated',
    verification_state  VARCHAR(20) NOT NULL DEFAULT 'unverified'
);

<!-- REQ:08.concept-lemma-table -->
-- Concept-to-lemma mappings. confidence defaults to NULL (no estimate),
-- never 1.0 — see REQ:08.registry-epistemics.
CREATE TABLE concept_lemmas (
    id                  SERIAL PRIMARY KEY,
    concept_id          INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    lemma               TEXT NOT NULL,
    language            VARCHAR(5) NOT NULL DEFAULT 'grc',
    confidence          FLOAT DEFAULT NULL,
    origin              VARCHAR(20) NOT NULL DEFAULT 'curated',
    verification_state  VARCHAR(20) NOT NULL DEFAULT 'unverified',
    UNIQUE (lemma, language, concept_id)
);

<!-- REQ:08.polarity-claims-table -->
-- A claim that a concept has a particular polarity. One row per (concept, pole).
-- Each claim carries provenance and evidence — it is not a property of the concept.
CREATE TABLE polarity_claims (
    id                  SERIAL PRIMARY KEY,
    concept_id          INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    polarity            VARCHAR(2) NOT NULL,  -- '+', '-', '±'
    origin              VARCHAR(20) NOT NULL DEFAULT 'curated',
    evidence_count      INTEGER NOT NULL DEFAULT 0,
    verification_state  VARCHAR(20) NOT NULL DEFAULT 'unverified',
    confidence          FLOAT DEFAULT NULL,
    UNIQUE (concept_id, polarity)
);

<!-- REQ:08.inverse-claims-table -->
-- A claim that concept A is the inverse of concept B (asymmetric pair).
-- Each claim carries provenance and evidence.
CREATE TABLE inverse_claims (
    id                  SERIAL PRIMARY KEY,
    concept_id          INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    inverse_concept_id  INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    origin              VARCHAR(20) NOT NULL DEFAULT 'curated',
    evidence_count      INTEGER NOT NULL DEFAULT 0,
    verification_state  VARCHAR(20) NOT NULL DEFAULT 'unverified',
    confidence          FLOAT DEFAULT NULL,
    UNIQUE (concept_id, inverse_concept_id),
    CHECK (concept_id <> inverse_concept_id)
);
```

### Key indexes
- `tokens(book, chapter, verse, position)` — verse-scoped sequence search
- `tokens(lemma)` — lemma lookup
- `tokens(global_position)` — cross-verse sequence search
- `concept_lemmas(lemma, language)` — reverse lookup from lemma to concepts
- `polarity_claims(concept_id)` — fetch claims for a given concept
- `inverse_claims(concept_id)` — fetch inverse pairs for a given concept

## Scope Boundaries

### In scope for MVP
- Greek New Testament (SBLGNT/MorphGNT)
- Token, lemma, and morphology annotations
- Verse-level structural boundaries
- Manually curated concept registry (~20 concepts)
- Lemma-to-concept and concept-to-inverse mappings

### Explicitly out of scope for MVP
- Hebrew Bible, LXX, or any non-Greek corpus
- Clause, sentence, or discourse boundaries (unless trivially available)
- Syntax tree data
- Textual variant apparatus
- Automated concept discovery or mapping
- Embedding/vector representations of tokens or passages
- Cross-lingual alignment

## Open Questions
1. Should we include clause boundaries from OpenText if the data is readily parseable?
2. What is the licensing situation for OpenText annotations layered on SBLGNT?
3. Should the concept registry live in the database or as a versioned config file?
4. Should we use SBLGNT book abbreviations or SIL/OSIS standard codes?

## Confidence and Volatility
- Confidence: High
- Volatility: Low (this is a scoping decision, unlikely to change once made)

## References
- Decisions: DEC-020, DEC-024 (registry epistemics), DEC-026 (BB book codes), DEC-038–DEC-048 (ingestion entrypoint)
- Assumptions: ASM-003, ASM-005
- Prior docs: 04_node-ontology.md, 06_capability-validator.md
