---
type: code-review
flavor: codex-code
slice: N
checkpoint: slice-close
verdict: PASS-WITH-NOTES
base_sha: a549160
head_sha: b352fb6
date: 2026-06-01
reviewer: Codex
scope: >
  Authoritative Codex pass over git diff a549160..b352fb6 (9 commits:
  N1..N7 implementation, mid-slice fallback review, and slice-close governance).
  Scope: Tier-1 concept auto-generation (lexicon ingest, English-to-lemma
  resolver, auto-create writer, concept_not_mapped retry wire-in) and the
  persisted two-part Conceptual Document (deterministic comparative section plus
  opt-in cited/labeled LLM educational section).
findings_summary:
  P0: 0
  P1: 0
  P2: 0
  P3: 2
  info: 2
---

# Codex Review - Slice N Close (authoritative pass)

## Header

- **Review ID:** review-codex-code-slice-n-close-2026-06-01
- **Date:** 2026-06-01
- **Reviewer:** Codex
- **Slice:** N
- **Diff range:** `a549160..b352fb6`
- **Scope:** Tier-1 concept auto-generation and persisted two-part Conceptual Document. Line anchors below are as of `b352fb6`.

## Executive Summary

**Verdict: PASS-WITH-NOTES.** No P0/P1/P2 findings. The DEC-081 epistemic line holds: resolver/writer auto-creation is deterministic, the LLM article path has no write path back to `concepts` or `concept_lemmas`, and LLM failure degrades to a Part 1 §1-only document.

Finding counts: **0 P0, 0 P1, 0 P2, 2 P3, 2 info.** The two P3s are known design limitations: store-once documents do not backfill §2 after a prior deterministic create, and resolver recall is broad because it uses substring `ILIKE`. Both are non-blocking for Slice N's charter.

## Checklist Results

| # | Check | Result | Evidence / note |
|---|-------|--------|-----------------|
| 1 | DEC-081 epistemic line | PASS | Resolver/writer path has no LLM import (`src/ontology/lexicon_resolver.py:21-25`, `src/ontology/concept_writer.py:26-36`). Article generation is isolated in `src/nlp/concept_article.py:69-118` and returns a document section only. Auto-create degrades to §1-only because `build_educational_section` returns `None` on LLM trouble (`src/nlp/concept_article.py:85-111`). |
| 2 | DEC-102 Tier-1 provenance | PASS | Fresh concept rows use `origin=LEXICON_ORIGIN` and `verification_state=LEXICON_VSTATE` (`src/ontology/concept_writer.py:38-39`, `src/ontology/concept_writer.py:111-119`); lemma rows set `confidence=None`, same origin/state (`src/ontology/concept_writer.py:125-138`). No auto-promotion path found. |
| 3 | DEC-103 lexicon-sourced provenance | PASS | TBESG/Dodson records carry `source` with DB CHECK (`data/schemas/03_lexicon.sql:34-42`) and parser constants (`src/ingestion/lexicon/datasets.py:136-138`, `src/ingestion/lexicon/datasets.py:161-163`). jtauber bridge rows land in the dedicated `lemma_strongs` table (`data/schemas/03_lexicon.sql:23-28`). |
| 4 | DEC-104 dead-end killer | PASS | Retry counter is local and hardcoded: `attempts = 0`, `if attempts >= 1: raise`, `attempts += 1` (`src/app/orchestration.py:336-368`). No config value controls the retry bound. |
| 5 | DEC-105 not-silent inline envelope | PASS | `AutoCreatedConceptNote` is part of both response models (`src/app/schemas.py:55-70`, `src/app/schemas.py:81-97`, `src/app/schemas.py:167-188`) and is populated on auto-create success (`src/app/orchestration.py:162-167`, `src/app/orchestration.py:299-310`). |
| 6 | DEC-106 persisted two-part document schema | PASS | SQL has `part1_comparative JSONB NOT NULL`, nullable `part1_educational JSONB`, and nullable `part2_grouping JSONB` (`data/schemas/04_concept_documents.sql:23-31`). Python mirror and read/write paths match (`src/ontology/concept_document.py:56-73`, `src/ontology/concept_document.py:200-251`). |
| 7 | DEC-107 article LLM opt-in | PASS | Only `run_nl_query` threads `article_llm` from `SPL_CONCEPT_ARTICLE_LLM` (`src/app/orchestration.py:283-297`). `run_dsl_query` passes no article LLM (`src/app/orchestration.py:200-205`). LLM failures return `None`, not errors (`src/nlp/concept_article.py:85-111`). Related P3: N-CODEX-N-001. |
| 8 | DEC-108 vertical phasing N1..N7 | PASS | Each phase has focused tests: parser/loader (`tests/unit/test_lexicon_datasets.py`, `tests/unit/test_lexicon_loader.py`), resolver (`tests/unit/test_lexicon_resolver.py`, `tests/integration/test_lexicon_resolver.py`), writer (`tests/unit/test_concept_writer.py`, `tests/integration/test_concept_writer.py`), retry wire-in (`tests/unit/test_app_auto_create_concept.py`, `tests/integration/test_concept_auto_create.py`), document (`tests/unit/test_concept_document.py`, `tests/integration/test_concept_document.py`), article (`tests/unit/test_concept_article.py`, `tests/integration/test_concept_article_live_llm.py`). |
| 9 | Architectural isolation | PASS | Targeted grep found no `src.nlp` or `src.app` imports under `src/ontology`, and no `src.app` imports under `src/nlp`. `src/nlp` imports ontology document models only (`src/nlp/concept_article.py:27-30`). |
| 10 | SQL safety | FINDING (P3) | SQL uses SQLAlchemy Core or named `text()` params; no f-string SQL interpolation found. ON CONFLICT targets match declared UNIQUE constraints. JSONB writes/readbacks are symmetric. P3 N-CODEX-N-002 notes resolver recall broadness from `ILIKE '%term%'`, not injection. |
| 11 | Idempotency | PASS | Auto-create checks exact-name reuse and uses `ON CONFLICT DO NOTHING` (`src/ontology/concept_writer.py:55-65`, `src/ontology/concept_writer.py:111-139`). Lexicon ingest uses table UNIQUE constraints plus `ON CONFLICT DO NOTHING` (`src/ingestion/lexicon/loader.py:63-81`). Info N-CODEX-N-003 notes exact-name-only dedup. |
| 12 | General correctness | FINDING (Info) | No P0/P1 correctness bug found in the diff. Info N-CODEX-N-004 records a `git diff --check` governance whitespace issue. |

## Findings

1. **N-CODEX-N-001 - P3 - `src/app/orchestration.py:147`; `src/ontology/concept_document.py:200`**

   **Description:** The document is only persisted when `get_document(...) is None`, and `persist_document` is store-once via `ON CONFLICT DO NOTHING`. If a concept is first auto-created through the deterministic `/dsl` path, `part1_educational` is absent; a later `/nl` request with `SPL_CONCEPT_ARTICLE_LLM=1` will not backfill §2 because the document already exists.

   **Recommendation:** Keep store-once as the Slice N default, but add an explicit regenerate/update path if §2 backfill becomes a product requirement.

2. **N-CODEX-N-002 - P3 - `src/ontology/lexicon_resolver.py:60`; `src/ontology/lexicon_resolver.py:65-68`**

   **Description:** Resolver recall is intentionally broad: `_strongs_for_term` builds `pattern = f"%{term}%"` and applies `gloss.ilike(pattern)`. This is parameterized and injection-safe, but semantically it matches substrings inside longer glosses, so it can over-include near terms.

   **Recommendation:** Move recall/precision tuning to the Tier-2 resolver/grouping bucket: token-boundary matching, gloss alias normalization, or curated grouping can narrow/expand results with user-visible provenance.

3. **N-CODEX-N-003 - Info - `src/ontology/concept_writer.py:55-65`**

   **Description:** Existing concept reuse is exact-name only. This satisfies store-once idempotency for repeated identical queries, but case, whitespace, spelling, or alias variants can still become near-duplicate concepts.

   **Recommendation:** Re-evaluate alias/normalization dedup when Tier-2 grouping or curator workflows land. The current MVP behavior is acceptable because the retry path uses the DSL concept token verbatim.

4. **N-CODEX-N-004 - Info - `docs/governance/decision-log.md:1207`**

   **Description:** `git diff --check a549160..b352fb6` reports one trailing whitespace instance in the governance close text. This is not behavior-affecting and does not touch the feature code.

   **Recommendation:** Trim the trailing whitespace on the next governance hygiene edit.

## Disposition

| Finding | Severity | Disposition |
|---------|----------|-------------|
| N-CODEX-N-001 | P3 | design-accepted. Store-once is explicit in DEC-106; an explicit regenerate/update path is out of Slice N scope. |
| N-CODEX-N-002 | P3 | deferred-to-bucket: Bucket-N3 / Tier-2 resolver recall and grouping. |
| N-CODEX-N-003 | Info | deferred-to-bucket: Bucket-N3 / Tier-2 alias and grouping review. |
| N-CODEX-N-004 | Info | fix-required only as hygiene; non-blocking and safe to trim during the next governance edit. |

## Sign-off

Sign-off: Codex approves Slice N close as **PASS-WITH-NOTES** for `a549160..b352fb6`. No P0/P1/P2 findings; Bucket-N1 can close with this authoritative pass.
