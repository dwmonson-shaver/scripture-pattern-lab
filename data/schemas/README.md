# Database Schemas

SQL files for the corpus database. Applied explicitly via `psql` or a migration
runner — not auto-loaded by the Postgres container, so changes are visible
in the dev loop instead of running silently on first boot.

Schema sketch lives in `docs/canonical/08_mvp-corpus-scope.md` (REQ:08.token-schema,
REQ:08.concept-table, REQ:08.concept-lemma-table, REQ:08.concept-inverse-table).

Files will be added in pickup step 5 (load corpus into Postgres).
