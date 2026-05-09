---
type: code-review
verdict: FAIL
base_sha: fed3b98
scope: Slice C Track 1 — Registry Epistemics (6 commits, ~2439 lines)
date: 2026-05-08
findings_summary: P1: 1, P2: 1, P3: 0, info: 0
---

## Findings

### P1 — `scripts/db/seed_registry.py:186` — Non-empty safety gate can write into a foreign registry when row counts happen to match

The preflight gate only refuses a non-empty `concepts` table when `existing != len(concepts_rows)` (`scripts/db/seed_registry.py:186-193`). If an unrelated database already has exactly 20 concepts, the script proceeds without `--truncate`; the concept insert then uses `ON CONFLICT DO NOTHING` by `name` (`scripts/db/seed_registry.py:216-225`) and may add the canonical concepts alongside the foreign rows or attach seed lemmas/claims to pre-existing same-named rows with non-seed metadata. That is not an overwrite in the destructive `TRUNCATE` sense, but it is a real mutation risk against a non-seed registry and weakens the intended non-empty guard.

Recommendation: make the no-truncate idempotency check prove identity, not count. For example, refuse unless the existing concept name set exactly equals `concepts.csv` and the dependent table counts/content also match the seed declaration, or use a seed-run marker/version table. A simpler safe option is to keep the strict `existing > 0` refusal and test idempotency through `--truncate` or a purpose-built `--allow-existing-seed` check.

### P2 — `data/schemas/02_concept_registry.sql:10` — SQL schema does not enforce declared value domains for registry epistemics

The canonical text declares allowed `origin` values and three verification states, and the Python mirror encodes those as Literals (`src/ontology/registry.py:36-38`), but the SQL schema only defines unconstrained `VARCHAR` columns for `origin`, `verification_state`, and `polarity` (`data/schemas/02_concept_registry.sql:10-11`, `20-21`, `28-31`, `40-42`). The only CHECK in the registry schema is self-inverse prevention (`data/schemas/02_concept_registry.sql:45`). This means direct SQL can insert `verification_state='verified'`, `origin='unknown'`, `polarity='neutral'`, negative `evidence_count`, or out-of-range confidence values; those rows will either fail Pydantic readback later or, worse, be silently misclassified by Rule 13 because it only treats exact `'unverified'` as prior-grounded.

Recommendation: add DB-level CHECK constraints matching the declared domains, at minimum `origin IN (...)`, `verification_state IN (...)`, `polarity IN ('+', '-', '±')`, `evidence_count >= 0`, and `confidence IS NULL OR confidence BETWEEN 0 AND 1` on applicable tables. Mirror the same constraints in `src/ontology/registry.py` table definitions and add integration tests that invalid values raise `IntegrityError`.

## Verdict rationale

Verdict: FAIL. The implementation mostly preserves DEC-024 in its seed path and keeps the DEC-025 ontology boundary intact, but the seed script's relaxed non-empty gate is a pre-close blocker because it can mutate the wrong registry without either factor of the destructive-op confirmation.

Concern review:

- CORRECTNESS: Rule-13 traversal uses `_collect_node_refs` and descends through top-level `InverseExpr.inner`, groups, alternatives, and optional nodes (`src/validation/validator.py:79-112`, `569-574`); no confirmed walker miss. SQL UNIQUEs cover the declared duplicate shapes, but CHECK coverage is incomplete as noted above. The relaxed seed gate is a confirmed mutation risk.
- DEC-024 FIDELITY: Seed inserts explicitly set `origin='curated'`, `verification_state='unverified'`, and `confidence=None` where applicable (`scripts/db/seed_registry.py:216-300`). No confirmed non-NULL confidence or non-unverified state leaks from the CSV seed path.
- DEC-025 BOUNDARY: No `from src.ingestion` imports were found under `src/ontology/`. `scripts/db/seed_registry.py` imports table mirrors from `src.ontology.registry` and does not import `ConceptRegistry`.
- SUBPROCESS HYGIENE: New seed integration tests propagate parent env via `os.environ.copy()` plus overrides (`tests/integration/test_concept_registry_seed.py:68-90`). The script redacts `DATABASE_URL` before printing (`scripts/db/seed_registry.py:102-119`, `166-168`). I did not find credential leakage in the reviewed diff.
- TEST FRAGILITY: `test_inverse_concept_unverified_warns` exercises `InverseExpr` and requires Rule 13 findings from the inverse path (`tests/unit/test_rule_13_registry_grounding.py:233-257`); the stub does not always return prior-grounded because `is_prior_grounded` is keyed by concept and polarity (`tests/unit/test_rule_13_registry_grounding.py:119-124`). No confirmed silent-pass gap in the requested areas.
- RESOURCE HYGIENE: `ConceptRegistry` uses short-lived `engine.connect()` contexts per read (`src/ontology/registry.py:254-310`). `seed_registry.py` does the write phase inside one `engine.begin()` transaction (`scripts/db/seed_registry.py:203-319`). No confirmed connection or transaction lifetime issue.

Verification performed: `git diff fed3b98..HEAD`; `pytest tests/unit/test_ontology_registry.py tests/unit/test_rule_13_registry_grounding.py` passed (37 tests). DB-backed integration tests were not run because `DATABASE_URL` is not set in this environment.
