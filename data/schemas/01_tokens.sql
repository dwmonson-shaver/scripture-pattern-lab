-- Canonical DDL for the corpus token table.
-- Mirrors REQ:08.token-schema (docs/canonical/08_mvp-corpus-scope.md), with
-- normalized_form and corpus_id added per design-corpus-parser-2026-04-26.md.
-- Applied via scripts/db/apply_schemas.sh; never created from Python code.

CREATE TABLE IF NOT EXISTS tokens (
    id              SERIAL PRIMARY KEY,
    book            VARCHAR(10) NOT NULL,
    chapter         INTEGER     NOT NULL,
    verse           INTEGER     NOT NULL,
    position        INTEGER     NOT NULL,
    global_position INTEGER     NOT NULL,
    surface_form    TEXT        NOT NULL,
    normalized_form TEXT        NOT NULL,
    lemma           TEXT        NOT NULL,
    morph_code      VARCHAR(20) NOT NULL,
    pos             VARCHAR(10) NOT NULL,
    language        VARCHAR(5)  DEFAULT 'grc',
    corpus_id       VARCHAR(10) DEFAULT 'nt'
);

CREATE INDEX IF NOT EXISTS tokens_bcvp_idx
    ON tokens (book, chapter, verse, position);
CREATE INDEX IF NOT EXISTS tokens_lemma_idx
    ON tokens (lemma);
CREATE INDEX IF NOT EXISTS tokens_global_position_idx
    ON tokens (global_position);
