# MVP Corpus Scope

## Purpose
Decide and document the corpus, text edition, annotation requirements, and data sources for the MVP. The goal is to choose the narrowest scope that still demonstrates the full value of the pattern engine. [DEC-020]

## Decision: Greek New Testament (SBLGNT + MorphGNT)

### Why Greek NT
- Richest available open annotation data (morphology, lemmas, syntax)
- Manageable size (~138,000 tokens across 27 books)
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

## Required Annotation Layers

Each token in the corpus must carry the following annotations:

| Layer | Source | Example |
|-------|--------|---------|
| Surface form | SBLGNT text | πίστις |
| Lemma | MorphGNT | πίστις |
| Morphological parse | MorphGNT | N-NSF (noun, nominative, singular, feminine) |
| Part of speech | Derived from morph parse | NOUN |
| Book | Text structure | 1cor |
| Chapter | Text structure | 13 |
| Verse | Text structure | 13 |
| Token position | Sequential index | 1-based within verse |

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
- The initial set is manually curated
- AI-assisted expansion will suggest new mappings as users explore queries that reference unmapped concepts
- Each new mapping must be reviewed before it enters the registry (not auto-approved)
- The registry is versioned alongside the DSL

## Ingestion Pipeline — MVP

### Steps
1. Download MorphGNT data (TSV per book)
2. Parse each row into a structured token record
3. Assign sequential token IDs (global and per-verse)
4. Load into Postgres with appropriate indexes
5. Seed the concept registry from the table above
6. Build lemma-to-concept index

### Database Schema (sketch)

```sql
-- Core token table
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    book VARCHAR(10) NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    position INTEGER NOT NULL,       -- 1-based position within verse
    global_position INTEGER NOT NULL, -- 1-based position within corpus
    surface_form TEXT NOT NULL,
    lemma TEXT NOT NULL,
    morph_code VARCHAR(20) NOT NULL,
    pos VARCHAR(10) NOT NULL,
    language VARCHAR(5) DEFAULT 'grc'
);

-- Concept registry
CREATE TABLE concepts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    polarity VARCHAR(5) DEFAULT NULL,  -- '+', '-', or NULL (neutral)
    description TEXT
);

-- Concept-to-lemma mappings
CREATE TABLE concept_lemmas (
    concept_id INTEGER REFERENCES concepts(id),
    lemma TEXT NOT NULL,
    language VARCHAR(5) DEFAULT 'grc',
    confidence FLOAT DEFAULT 1.0,
    PRIMARY KEY (concept_id, lemma, language)
);

-- Polarity inverse relationships
CREATE TABLE concept_inverses (
    concept_id INTEGER REFERENCES concepts(id),
    inverse_concept_id INTEGER REFERENCES concepts(id),
    PRIMARY KEY (concept_id, inverse_concept_id)
);
```

### Key indexes
- `tokens(book, chapter, verse, position)` — verse-scoped sequence search
- `tokens(lemma)` — lemma lookup
- `tokens(global_position)` — cross-verse sequence search
- `concept_lemmas(lemma)` — reverse lookup from lemma to concepts

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
- Decisions: DEC-020
- Assumptions: ASM-003, ASM-005
- Prior docs: 04_node-ontology.md, 06_capability-validator.md
