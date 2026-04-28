# Spec Coverage Tracker

Last updated: 2026-04-28 (partial — phase 1 of corpus parser; full table pending `/coverage` run)

## Summary
- Requirements identified: 0
- Implemented: 0 (0%)
- Tested: 0 (0%)
- Both: 0 (0%)
- Neither: 0 (0%)

> Summary numbers reflect the full canonical-doc population once `/coverage` has run. Below, partial rows are populated by hand during `/review` for the REQ markers each phase touches.

## Coverage Matrix

| Req ID | Description | Code | Test | Decision |
|--------|-------------|------|------|----------|
| REQ:08.token-schema | Database schema for the corpus token table | `data/schemas/01_tokens.sql` | — | DEC-021 |
| REQ:08.ingestion-pipeline | Steps for ingesting MorphGNT data into Postgres | `scripts/db/apply_schemas.sh` (step 4 only; steps 1–3, 5–6 pending) | — | DEC-021, DEC-022, DEC-023 |
| REQ:08.annotation-layers | Per-token surface form, lemma, morph, POS, book, chapter, verse, position | `data/schemas/01_tokens.sql` (column structure only; ingestion code pending phases 3–4) | — | — |

_Run `/coverage` to populate this table from `<!-- REQ:... -->` markers in `docs/canonical/`._

## Gaps

### Specced but not coded
_None tracked yet — pending `/coverage` run for full audit._

### Coded but not tested
- `REQ:08.token-schema` — schema applies, but no tests exercise it (integration test arrives in phase 4).
- `REQ:08.ingestion-pipeline` step 4 — apply script verified manually (idempotency check via container psql); no automated test covers it.
- `REQ:08.annotation-layers` — column structure is in place, no rows yet, no tests.
