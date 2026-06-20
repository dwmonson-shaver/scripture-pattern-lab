-- 07_marks.sql — span-annotation (mark) layer (Slice 1, DEC-129/143/145).
--
-- A mark anchors a selected phrase in a named English version to 0..n concepts.
-- The span is char offsets into the English text of the named version (the
-- surface the human selects on), plus a verse range (cross-verse selection is
-- allowed — DEC-143). Greek alignment is derived at read time, not stored here.
-- A mark with no concept rows is a "plain highlight". Idempotent DDL; Python
-- mirror in src/ontology/marks.py.

CREATE TABLE IF NOT EXISTS marks (
    id            SERIAL PRIMARY KEY,
    corpus_id     VARCHAR(10) NOT NULL DEFAULT 'nt',
    book          VARCHAR(10) NOT NULL,
    chapter       INTEGER NOT NULL,
    verse_start   INTEGER NOT NULL,
    verse_end     INTEGER NOT NULL,
    char_start    INTEGER NOT NULL,
    char_end      INTEGER NOT NULL,
    version_code  VARCHAR(16) NOT NULL,
    actor         TEXT NOT NULL DEFAULT 'local',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (verse_end >= verse_start),
    -- char_start/char_end are PER-VERSE offsets (start into the first verse,
    -- end into the last). For a single-verse mark, char_end must exceed
    -- char_start; for a cross-verse mark the end may sit earlier on its own
    -- line than the start did on the first verse (DEC-143). So the strict
    -- ordering only applies within one verse.
    CHECK (char_end > char_start OR verse_end > verse_start)
);

CREATE INDEX IF NOT EXISTS marks_chapter_idx
    ON marks (corpus_id, book, chapter, version_code);

CREATE TABLE IF NOT EXISTS mark_concepts (
    mark_id     INTEGER NOT NULL REFERENCES marks(id) ON DELETE CASCADE,
    concept_id  INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (mark_id, concept_id)
);
