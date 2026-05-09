-- Concept registry tables. See REQ:08.registry-epistemics in
-- docs/canonical/08_mvp-corpus-scope.md for the four invariants this schema
-- realizes (provenance, NULL-default confidence, evidence-bearing claims,
-- grounding axis). The Python mirrors live in src/ontology/registry.py.

-- Domain CHECK constraints below enforce REQ:08.registry-epistemics value
-- domains at the DB layer so a direct SQL caller cannot bypass the Pydantic
-- Literal types in src/ontology/registry.py. Closes Codex P2 (2026-05-08
-- review-codex-code-slice-c-track-1-2026-05-08).

CREATE TABLE IF NOT EXISTS concepts (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(64) NOT NULL UNIQUE,
    description         TEXT,
    origin              VARCHAR(20) NOT NULL DEFAULT 'curated',
    verification_state  VARCHAR(20) NOT NULL DEFAULT 'unverified',
    CHECK (origin IN ('curated', 'ai_suggested', 'lexicon_imported')),
    CHECK (verification_state IN ('unverified', 'corpus_observed', 'human_confirmed'))
);

CREATE TABLE IF NOT EXISTS concept_lemmas (
    id                  SERIAL PRIMARY KEY,
    concept_id          INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    lemma               TEXT NOT NULL,
    language            VARCHAR(5) NOT NULL DEFAULT 'grc',
    confidence          FLOAT DEFAULT NULL,
    origin              VARCHAR(20) NOT NULL DEFAULT 'curated',
    verification_state  VARCHAR(20) NOT NULL DEFAULT 'unverified',
    UNIQUE (lemma, language, concept_id),
    CHECK (origin IN ('curated', 'ai_suggested', 'lexicon_imported')),
    CHECK (verification_state IN ('unverified', 'corpus_observed', 'human_confirmed')),
    CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0))
);

CREATE TABLE IF NOT EXISTS polarity_claims (
    id                  SERIAL PRIMARY KEY,
    concept_id          INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    polarity            VARCHAR(2) NOT NULL,
    origin              VARCHAR(20) NOT NULL DEFAULT 'curated',
    evidence_count      INTEGER NOT NULL DEFAULT 0,
    verification_state  VARCHAR(20) NOT NULL DEFAULT 'unverified',
    confidence          FLOAT DEFAULT NULL,
    UNIQUE (concept_id, polarity),
    CHECK (polarity IN ('+', '-', '±')),
    CHECK (origin IN ('curated', 'ai_suggested', 'lexicon_imported')),
    CHECK (verification_state IN ('unverified', 'corpus_observed', 'human_confirmed')),
    CHECK (evidence_count >= 0),
    CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0))
);

CREATE TABLE IF NOT EXISTS inverse_claims (
    id                  SERIAL PRIMARY KEY,
    concept_id          INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    inverse_concept_id  INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    origin              VARCHAR(20) NOT NULL DEFAULT 'curated',
    evidence_count      INTEGER NOT NULL DEFAULT 0,
    verification_state  VARCHAR(20) NOT NULL DEFAULT 'unverified',
    confidence          FLOAT DEFAULT NULL,
    UNIQUE (concept_id, inverse_concept_id),
    CHECK (concept_id <> inverse_concept_id),
    CHECK (origin IN ('curated', 'ai_suggested', 'lexicon_imported')),
    CHECK (verification_state IN ('unverified', 'corpus_observed', 'human_confirmed')),
    CHECK (evidence_count >= 0),
    CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0))
);

CREATE INDEX IF NOT EXISTS concept_lemmas_lemma_idx    ON concept_lemmas (lemma, language);
CREATE INDEX IF NOT EXISTS polarity_claims_concept_idx ON polarity_claims (concept_id);
CREATE INDEX IF NOT EXISTS inverse_claims_concept_idx  ON inverse_claims (concept_id);
