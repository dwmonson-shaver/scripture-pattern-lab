-- 06_translations.sql — English (and future other-language) translation layer.
--
-- Slice 1 (DEC-128, DEC-144). A `translations` registry plus verse-aligned
-- `translation_verses`. Aligned to the Greek corpus by (corpus_id, book BB,
-- chapter, verse) so the reader can join English text to the MorphGNT tokens.
-- KJV is the mandatory public-domain default; other public-domain versions
-- (WEB, ASV, YLT) may be ingested under their own `code`.
--
-- The translation layer is SEPARATE from the corpus ground truth (tokens):
-- English is a reading surface, not the symbolic-retrieval substrate. Idempotent
-- (CREATE IF NOT EXISTS); DDL is canonical here, mirrored for typing in
-- src/ingestion/translations/db.py.

CREATE TABLE IF NOT EXISTS translations (
    id               SERIAL PRIMARY KEY,
    code             VARCHAR(16) NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    license          TEXT,
    is_public_domain BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS translation_verses (
    id             SERIAL PRIMARY KEY,
    translation_id INTEGER NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
    corpus_id      VARCHAR(10) NOT NULL DEFAULT 'nt',
    book           VARCHAR(10) NOT NULL,
    chapter        INTEGER NOT NULL,
    verse          INTEGER NOT NULL,
    text           TEXT NOT NULL,
    UNIQUE (translation_id, corpus_id, book, chapter, verse)
);

CREATE INDEX IF NOT EXISTS translation_verses_bcv_idx
    ON translation_verses (translation_id, corpus_id, book, chapter, verse);
