-- Persisted Conceptual Document (Slice N, REQ:08.concept-document). A
-- first-class per-concept document with two parts (DEC-102):
--   Part 1 = the Tier-1 article (this slice): a deterministic comparative
--            lexicon section + a clearly-labeled, cited LLM educational section.
--   Part 2 = a placeholder/structure slot for the Tier-2 grouping artifact that
--            grows over time (NOT built this slice — always NULL for now).
--
-- The document is STORED on first creation and RETRIEVED later — never
-- regenerated per query (design "Output" section). The concept it documents is
-- the deterministic ground truth (concepts/concept_lemmas); this document is
-- presentation layered ON TOP and NEVER feeds back into the concept's lemma set
-- or verification state.
--
-- The article parts are stored as JSONB blobs of the Pydantic models in
-- src/ontology/concept_document.py (comparative) and src/nlp/concept_article.py
-- (educational). The deterministic comparative section and the short summary
-- are NOT NULL; the LLM educational section is nullable (persisted Part 1 §1
-- only when the LLM was unavailable, regenerated later).
--
-- The Python Core mirror lives in src/ontology/concept_document.py. This SQL is
-- canonical; metadata.create_all is never called.

CREATE TABLE IF NOT EXISTS concept_documents (
    id                  SERIAL PRIMARY KEY,
    concept_name        VARCHAR(64) NOT NULL UNIQUE REFERENCES concepts(name)
                            ON DELETE CASCADE ON UPDATE CASCADE,
    short_summary       TEXT NOT NULL,
    part1_comparative   JSONB NOT NULL,
    part1_educational   JSONB,          -- nullable: LLM section, layered on top
    part2_grouping      JSONB,          -- Tier-2 placeholder; always NULL this slice
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS concept_documents_name_idx ON concept_documents (concept_name);
