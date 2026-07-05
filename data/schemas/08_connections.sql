-- 08_connections.sql — typed connections between concepts (Slice 2, 2026-07-05).
--
-- A connection is a HUMAN-AUTHORED hypothesis that two (later: n) concepts are
-- related. It is a prior, not a corpus-tested fact: it carries no
-- verification_state and is never auto-promoted. Ordering evidence (how often
-- the member concepts are marked in a given order) is COMPUTED later from the
-- marks table and REPORTS; it never advances a connection's standing on its own
-- (same discipline as DEC-119/135/146). The Python mirror lives in
-- src/ontology/connections.py. This SQL is canonical; metadata.create_all is
-- never called.
--
-- Multi-type by design: one edge can hold several typed claims at once
-- (e.g. faith→hope may be both a `sequence` and a `prerequisite`). Each claim
-- is a row in connection_claims so it can grow its own evidence/notes over
-- time. Directional types (prerequisite/produces/sequence/compound) read
-- member order from connection_members.position; symmetric types
-- (opposite/association/interchange/unknown) ignore it.

CREATE TABLE IF NOT EXISTS connections (
    id          SERIAL PRIMARY KEY,
    note        TEXT,
    actor       TEXT NOT NULL DEFAULT 'local',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ordered concept endpoints. `position` is 0-based; it is meaningful for
-- directional claim types and ignored by symmetric ones. A concept appears at
-- most once per connection (PK). If a member concept is deleted, its membership
-- row cascades away — a connection can thereby drop below two members and
-- becomes incomplete; incomplete connections are surfaced as such, not treated
-- as evidence (cleanup is a tracked follow-up).
CREATE TABLE IF NOT EXISTS connection_members (
    connection_id INTEGER NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    concept_id    INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    PRIMARY KEY (connection_id, concept_id),
    CHECK (position >= 0)
);

CREATE INDEX IF NOT EXISTS connection_members_conn_idx
    ON connection_members (connection_id, position);

-- Typed claims on a connection. Multi-type: (connection_id, claim_type) is the
-- PK so a connection carries a SET of types. `note` records the human's
-- rationale for that specific type. Evidence columns are intentionally absent
-- for now; the computed ordering evidence lives in the retrieval layer and is
-- joined at read time, never written back here as a fact.
CREATE TABLE IF NOT EXISTS connection_claims (
    connection_id INTEGER NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    claim_type    VARCHAR(20) NOT NULL,
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (connection_id, claim_type),
    CHECK (claim_type IN (
        'opposite', 'prerequisite', 'produces', 'sequence',
        'compound', 'association', 'interchange', 'unknown'
    ))
);
