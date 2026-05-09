---
type: code
verdict: needs-attention
base_sha: 5276462
head_sha: cbd27b5
scope: Slice D D1-D2 schema-foundation checkpoint for REQ:09.contextualization canonical text and Pydantic models
reviewer: Codex
date: 2026-05-09
findings_summary: 0 P0, 0 P1, 2 P2, 1 P3, 0 info
---

## Findings

| ID | Severity | File:Line | Summary |
|----|----------|-----------|---------|
| D-D1D2-001 | P2 | `docs/canonical/09_backend-service-boundaries.md:315-331` | Request lifecycle omits the contextualization step and still says retrieval returns raw candidates |
| D-D1D2-002 | P2 | `src/engine/models.py:399-454` | Count and sample-statistic invariants are documented but not encoded in the Pydantic schema |
| D-D1D2-003 | P3 | `docs/canonical/09_backend-service-boundaries.md:181`, `docs/canonical/09_backend-service-boundaries.md:372-373` | Directory mapping omits the new contextualization module location |

### D-D1D2-001

- severity: P2
- file:line: `docs/canonical/09_backend-service-boundaries.md:315-331`
- summary: Request lifecycle omits the contextualization step and still says retrieval returns raw candidates.
- rationale: The new canonical §8 places contextualization after retrieval and before scoring, and the model docstring mirrors that lifecycle. The request lifecycle still jumps from "Retrieval pipeline returns MatchCandidates" to "Scoring ranks candidates" with no contextualization step or `RetrievalResult` envelope. That leaves canonical-09 internally inconsistent about where the `Contextualization` envelope is produced and can steer D3/D5 implementers back to the pre-D1 flow.

### D-D1D2-002

- severity: P2
- file:line: `src/engine/models.py:399-454`
- summary: Count and sample-statistic invariants are documented but not encoded in the Pydantic schema.
- rationale: Canonical §8 defines these fields as counts, sample sizes, and standard deviation, and the `NodeBaseline` docstring explicitly says `count` is always `>= 0`. The Pydantic models use plain `int` / `float` for `node_index`, `count`, `sample_size`, `std`, `observed_count`, and permutation indices, so invalid negative schema instances can be constructed and round-tripped. Because D1-D2 is the schema foundation, these invariants should be enforced now with constrained fields and negative-value tests rather than left to later computation code.

### D-D1D2-003

- severity: P3
- file:line: `docs/canonical/09_backend-service-boundaries.md:181`, `docs/canonical/09_backend-service-boundaries.md:372-373`
- summary: Directory mapping omits the new contextualization module location.
- rationale: The new contextualization section commits the implementation home to `src/retrieval/contextualization.py`, matching resolved OQ#2 and the DEC-025 query-side boundary. The same canonical document's directory map still shows `src/retrieval/` containing only `pipeline.py`, which makes the boundary commitment less discoverable for future implementers. No code lives there yet in D1-D2, so this is not a schema blocker, but the map should be amended before contextualization logic lands.

## Verdict

Verdict: needs-attention. The REQ marker placement, §9/§10 renumbering, default semantics, null-distribution slot, and canonical §8 field-to-model name alignment are otherwise clean; `tests/unit/test_models.py` covers construction, JSON round-trip, defaults, and frozen assignment behavior for the new schema surface.

Recommended next step: fix the lifecycle text and add constrained numeric/index validation plus negative-value tests before treating D1-D2 as closed; fold the directory-map update into the same canonical cleanup.
