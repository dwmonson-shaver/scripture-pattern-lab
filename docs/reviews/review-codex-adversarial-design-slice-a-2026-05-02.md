---
type: codex-review
flavor: adversarial-design
date: 2026-05-02
verdict: needs-attention
base: c4d49fc (root commit)
scope: docs/canonical/, docs/governance/decision-log.md
plugin: codex@openai-codex 1.0.4
codex_cli: 0.125.0
findings_summary: 4 total — 2 high, 2 medium
---

# Codex Adversarial Design Review — 2026-05-02

Run before opening Slice B. Adversarial framing per `/codex:adversarial-review`.
Focus text steered Codex to design surface only; a separate code-review pass
follows for `src/` and `tests/`.

## Command

```
/codex:adversarial-review --base c4d49fc --background Review the overall design of this project as captured in docs/canonical/ and docs/governance/decision-log.md. Skip implementation files in src/ and tests/ for this pass — a separate code review will follow. Focus on: (1) coherence between the canonical specs and the decision log; (2) hidden assumptions that could fail under real-world conditions; (3) whether anti-confirmation-bias / corpus-is-ground-truth is enforced by the design or merely stated as a goal; (4) architectural-boundary integrity (src/app, src/engine, src/ingestion, src/nlp, src/ontology, src/retrieval, src/scoring, src/validation); (5) load-bearing decisions whose rationale looks thin or whose alternatives were not explored.
```

## Codex output (verbatim)

# Codex Adversarial Review

Target: branch diff against c4d49fc
Verdict: needs-attention

No-ship: the docs state the right epistemic goals, but the canonical specs still encode paths that can execute curated priors as if they were corpus-grounded facts.

Findings:
- [high] Canonical concept schema contradicts the corpus-ground-truth decision (docs/canonical/08_mvp-corpus-scope.md:152-168)
  DEC-024 says registry entries are provisional priors and explicitly calls out `confidence DEFAULT 1.0`, polarity as a concept property, and missing provenance/evidence as the failure mode. The canonical schema still defines `concepts.polarity`, `concept_lemmas.confidence FLOAT DEFAULT 1.0`, and no `origin`, evidence counts, verification state, or prior-vs-observed match axis. Under real use, conceptual and polarity queries can present manually curated theological mappings as confirmed corpus evidence, which is exactly the anti-confirmation-bias failure this project says it is avoiding.
  Recommendation: Revise the canonical registry schema before shipping the design: make curated provenance structural, default confidence to NULL/low, move polarity/inverse claims into evidence-bearing relational tables, and require result/match metadata to distinguish prior-grounded from corpus-observed matches.
- [high] Polarity examples mark prior-driven concept resolution as supported (docs/canonical/07_query-to-ast-examples.md:83-117)
  The v0.1 example declares `+concept:faith > +concept:hope > +concept:love` supported and says the engine filters to positive-pole realizations only. That depends on the manually curated registry in canonical-08, but the design does not require those polarity mappings to clear corpus evidence first. This turns DEC-024's corpus-is-ground-truth rule into an aspiration rather than an execution guard: a user can get a supported result path whose polarity semantics come from curated priors.
  Recommendation: Change v0.1 validation semantics so polarity-marked concept queries are unsupported or explicitly prior-grounded until registry entries carry verified provenance/evidence; update examples and result labels accordingly.
- [medium] Book scope uses user abbreviations while the canonical token schema stores BB codes (docs/canonical/07_query-to-ast-examples.md:387-403)
  The AST and supported example use book abbreviations like `rom` and `1cor`, and the example declares the query fully supported. Canonical-08, however, makes `tokens.book` the raw 2-digit MorphGNT `BB` code. No canonical spec defines the normalization table, ownership, or validation rule that maps `book:1cor` to `07`. The hidden assumption is likely to surface as empty result sets or inconsistent scope filtering once the query engine hits the database.
  Recommendation: Define canonical book identifiers end to end: either make DSL/AST use BB codes, or specify a versioned abbreviation-to-BB normalization layer with validation errors for unknown aliases and tests/examples covering the translation.
- [medium] Canonical service-boundary map omits the accepted ingestion boundary (docs/canonical/09_backend-service-boundaries.md:265-292)
  DEC-025 adds `src/ingestion/` as a boundary and says query-side packages must not reach into ingestion code. The canonical backend boundary map still lists app, engine, nlp, ontology, retrieval, scoring, and validation only; ingestion appears only as a future background-job extraction point. That leaves the load-bearing import and ownership rule outside the canonical architecture, so later code can place corpus loading, schema application, or registry seeding behind app/ontology/retrieval without visibly violating the canonical spec.
  Recommendation: Add `src/ingestion/` to the canonical directory map and component specs, including explicit dependency direction: ingestion owns corpus file IO and bulk load/write paths; query-side packages consume persisted corpus/registry data through stable read interfaces and do not import ingestion modules.

Next steps:
- Resolve DEC-024 into the canonical ontology, corpus schema, validation, and examples before treating conceptual/polarity MVP behavior as shippable.
- Normalize the canonical architecture docs around ingestion and book identifiers so the implementation has one enforceable contract.

## Pending action (not in this artifact)

Triage of findings into blockers / follow-ups / won't-fix is deferred until the
companion code-review pass (`/codex:review --base origin/main --background`) is
also in hand. Both will be triaged together so doc and code remediation sequence
correctly.
