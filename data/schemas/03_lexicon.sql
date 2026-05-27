-- Lexicon sourcing tables (Slice N, REQ:08.lexicon-sourcing). Self-hosted open
-- lexicon stack for Tier-1 concept auto-generation (DEC-103): a one-time
-- wholesale ingest (mirrors the corpus/seed ingests) of three permissive
-- datasets that bridge English glosses → Extended Strong's → MorphGNT lemmas →
-- the SBLGNT corpus already loaded in `tokens`.
--
-- Datasets (provenance in data/raw/lexicon/README.md):
--   * jtauber/greek-lemma-mappings  (CC BY-SA 4.0) → lemma_strongs (the bridge)
--   * STEPBible TBESG               (CC BY 4.0)    → strongs_glosses (reverse lookup)
--   * biblicalhumanities Dodson     (Public Domain) → strongs_glosses (fallback)
--
-- The Python Core mirrors live in src/ingestion/lexicon/db.py. This SQL file is
-- canonical; metadata.create_all is never called (same discipline as
-- schemas 01_tokens.sql and 02_concept_registry.sql).
--
-- NO LLM ever writes these rows; they are sourced lookups. They are the
-- authority Tier-1 concepts are cited from (DEC-102/DEC-103).

-- The MorphGNT-lemma ↔ Strong's bridge (jtauber). `morphgnt_lemma` aligns to
-- `tokens.lemma` by construction (same author as MorphGNT/SBLGNT). `strongs` is
-- the Extended Strong's in G-prefixed zero-padded form (e.g. 'G0026') so it
-- joins cleanly to strongs_glosses.
CREATE TABLE IF NOT EXISTS lemma_strongs (
    id              SERIAL PRIMARY KEY,
    morphgnt_lemma  TEXT NOT NULL,
    strongs         VARCHAR(12) NOT NULL,
    UNIQUE (morphgnt_lemma, strongs)
);

-- Strong's ↔ English gloss (TBESG primary, Dodson fallback). One row per
-- (strongs, source). `lemma` is the source dataset's Greek headword (may differ
-- from MorphGNT lemmatization — the bridge reconciles that, do not join on it).
-- `gloss` is the short English rendering used for the reverse `ILIKE` lookup.
CREATE TABLE IF NOT EXISTS strongs_glosses (
    id          SERIAL PRIMARY KEY,
    strongs     VARCHAR(12) NOT NULL,
    lemma       TEXT,
    gloss       TEXT NOT NULL,
    source      VARCHAR(8) NOT NULL,
    UNIQUE (strongs, source, gloss),
    CHECK (source IN ('tbesg', 'dodson'))
);

CREATE INDEX IF NOT EXISTS lemma_strongs_strongs_idx     ON lemma_strongs (strongs);
CREATE INDEX IF NOT EXISTS lemma_strongs_lemma_idx       ON lemma_strongs (morphgnt_lemma);
CREATE INDEX IF NOT EXISTS strongs_glosses_strongs_idx   ON strongs_glosses (strongs);
-- Trigram-free: the reverse lookup uses `gloss ILIKE '%term%'`; a plain index
-- does not serve ILIKE-with-leading-wildcard, so no gloss index (MVP scale).
