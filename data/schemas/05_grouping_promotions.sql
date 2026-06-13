-- Tier-2 curator promotion audit log (Slice P, Scope B).
--
-- Append-only record of every human-actored advance of a grouping's curator
-- state along unverified -> corpus_observed -> human_confirmed (DEC-124). This
-- table is the AUTHORITATIVE source of truth for a grouping's curator_state:
-- the current state is the to_state of the latest row for that anchor (or
-- 'unverified' if there are no rows). Nothing is ever updated or deleted here.
--
-- This is deliberately SEPARATE from concept_documents.part2_grouping: the
-- grouping blob's own verification_state stays 'unverified' forever (the
-- auto-create guard, DEC-081/DEC-115/DEC-119). Provenance ("born unverified")
-- and human judgment ("a curator advanced it") are distinct facts.
--
-- evidence_snapshot freezes the GroupingEvidence the human saw at decision
-- time. It is INERT DATA — never rehydrated into an elevated-state grouping
-- (DEC-126).

CREATE TABLE IF NOT EXISTS grouping_promotions (
    id            SERIAL PRIMARY KEY,
    anchor_name   VARCHAR(64) NOT NULL
                    REFERENCES concepts(name) ON DELETE CASCADE ON UPDATE CASCADE,
    from_state    VARCHAR(20) NOT NULL
                    CHECK (from_state IN ('unverified', 'corpus_observed', 'human_confirmed')),
    to_state      VARCHAR(20) NOT NULL
                    CHECK (to_state   IN ('unverified', 'corpus_observed', 'human_confirmed')),
    actor         TEXT NOT NULL,
    rationale     TEXT NOT NULL,
    evidence_snapshot JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Latest-row-per-anchor lookups (current_curator_state) hit this index.
CREATE INDEX IF NOT EXISTS grouping_promotions_anchor_idx
    ON grouping_promotions (anchor_name, created_at DESC);
