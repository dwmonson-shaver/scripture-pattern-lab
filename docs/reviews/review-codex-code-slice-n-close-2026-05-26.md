---
type: code-review
flavor: claude-fallback
slice: N
checkpoint: slice-close
verdict: minor-fixes-recommended (no P0/P1/P2)
base_sha: a549160
head_sha: 894fb61
scope: >
  Full cumulative Slice N diff, git diff a549160..894fb61 (34 files, +3383 / -76):
  Tier-1 concept auto-generation core (lexicon ingest N1-2, resolver N3, writer
  N4, dead-end-killer wire-in N5) + persisted two-part Conceptual Document
  (deterministic N6) + LLM educational article section (N7).
reviewer_note: >
  Codex was the intended slice-close reviewer but remains BLOCKED by the
  recurring ~/.codex/sessions permission-denied issue (verified twice this
  session: mid-slice and slice-close attempts both errored with "Codex cannot
  access session files ... Operation not permitted"). The user-side fix is
  `sudo chown -R $(whoami) /Users/dwmonson/.codex` from their own terminal,
  which the orchestrator cannot run. Per the established fallback protocol
  (Slices E/F/J1/K/M), this slice-close pass runs as `claude-fallback` flavor
  with the same six focus categories and the same P-number severity language;
  the slice owes an authoritative Codex pass tracked as Bucket-N1.
findings_summary: "0 P0, 0 P1, 0 P2, 2 P3, 2 info"
---

# Slice N slice-close review: Tier-1 auto-generation + Conceptual Document

## Method

Reviewed `git diff a549160..894fb61` (the full slice) against six categories:
correctness, the non-negotiable epistemic invariants (DEC-024 / DEC-081 /
DEC-102 / DEC-106), SQL correctness + injection, resource hygiene, architecture
boundaries, and test fragility. The N1-N4 mid-slice findings (review-codex-code-
slice-n-n1n4-checkpoint) were verified to still hold; this pass adds N5-N7
(orchestration wire-in, persisted document, LLM article).

## Epistemic line (the heart of the slice) — PASS

- **The concept is deterministic ground truth.** `resolve_english_term` and
  `auto_create_cited_concept` contain no LLM import; the concept rows are
  written `origin='lexicon_imported'`, `verification_state='unverified'`,
  `confidence=None`, never auto-promoted. Re-verified at N4 + the integration
  invariant test.
- **The LLM article §2 never feeds the concept.** `build_educational_section`
  (src/nlp/concept_article.py) returns an `EducationalArticleSection` that is
  stored on the *document*, not the concept; there is no code path from the
  article back to `concepts` / `concept_lemmas`. The article is generated from
  the handed `ComparativeLexiconSection` ONLY (structural DEC-081), is labeled
  `generated=True`, carries `cited_sources`, and degrades to None on any LLM
  trouble. **PASS.**
- **Auto-creation never depends on the LLM.** `article_llm` is threaded as an
  optional kwarg; the concept + comparative §1 always persist regardless, and
  the `/dsl` surface never passes an article LLM (test
  `TestArticleLLMOptIn::test_dsl_path_passes_no_article_llm`). **PASS.**
- **Not-silent (DEC-105).** Every auto-creation attaches an
  `AutoCreatedConceptNote`; the honest 422 is preserved for unresolvable terms
  (`test_unresolvable_term_*`). **PASS.**

## Architecture boundaries — PASS

- `grep` confirms zero `src.app` imports under `src/ontology/`,
  `src/ingestion/lexicon/`, and `src/nlp/` (only docstring prose mentions).
- `src/nlp/concept_article.py` imports `src/ontology/concept_document` models —
  nlp→ontology, which is allowed (the AI layer reads ontology types; the
  explainer already does similar). No circular import (verified by importing
  both `src.app.orchestration` and `src.nlp.concept_article`).
- `concept_writer` / `concept_document` write via the Core `Table` mirrors
  (ingestion-shaped mutation, DEC-025), not the read-only reader. **PASS.**

## SQL correctness + injection — PASS

- All statements are SQLAlchemy Core; user input is bound (resolver `ilike`,
  `in_`; writer/document `pg_insert(...).values(...)`; `text()` helpers use
  named params). ON CONFLICT targets match the declared UNIQUE constraints
  (`lemma_strongs`, `strongs_glosses`, `concepts`, `concept_lemmas`,
  `concept_documents.concept_name`). The `concept_documents.concept_name` FK to
  `concepts(name)` is satisfied because `auto_create_cited_concept` runs before
  `persist_document`. JSONB round-trips the Pydantic `model_dump()` and
  `model_validate()` symmetrically. **PASS.**

## Resource hygiene — PASS

- The auto-create-and-retry loop is bounded to ONE retry (`attempts >= 1` guard
  + `test_retry_is_bounded_to_one_attempt`); no spin on multi-unmapped queries.
- The resolver does bounded queries; document persistence is one transaction;
  the LLM article is a single `complete()` call. No fan-out. **PASS.**

## Findings

### N-CLOSE-001 — P3 (store-once vs later opt-in) — §2 not backfilled if doc pre-exists
`_attempt_auto_create_concept` persists the document only `if get_document(...)
is None`. If a concept was first auto-created via the `/dsl` path (no LLM
article), a later `/nl` query with `SPL_CONCEPT_ARTICLE_LLM=1` will NOT add §2
because the document already exists (store-once, ON CONFLICT DO NOTHING).
**Disposition: accepted by design (DEC-106) — the document is store-once and an
explicit regenerate path is out of scope this slice.** A future "regenerate
article" affordance (UPDATE) is the right home. No inline fix; documented in the
DEC and the `persist_document` docstring.

### N-CLOSE-002 — P3 (resolver recall) — ILIKE over-broadening (carried from N1-N4)
The mid-slice finding (gloss `ILIKE '%term%'` matches substrings like
"beloved"/"faithfulness") still stands. **Disposition: re-affirmed; deferred to
the Tier-2 slice** where graded membership is the explicit subject. The corpus-
presence filter + dedup bound the blast radius at MVP.

### N-CLOSE-003 — info — exact-name dedup only (carried from N1-N4)
`find_existing_concept_id` dedups on exact name; case/whitespace variants could
create near-dups. Accepted for MVP (the orchestration passes the
`ConceptNotMapped.concept_name` verbatim, which is itself the DSL token).
Re-evaluate with Tier-2 alias dedup.

### N-CLOSE-004 — info — TBESG Greek Unicode (NFC/NFD) differs from corpus
The TBESG `lemma` column's Greek is NOT byte-equal to the corpus lemma (NFC vs
NFD), which is precisely why the bridge runs through Strong's + the jtauber
keys (verified byte-equal to the corpus, NFC). The `strongs_glosses.lemma` field
is provenance-only and never joined on. No action — this is the design working
as intended; noted so a future author does not "fix" it by joining on Greek.

## Verdict

`minor-fixes-recommended` — no P0/P1/P2. Two P3 (store-once backfill +
ILIKE recall) are design-accepted/Tier-2-deferred; two info notes need no
action. The epistemic line (deterministic concept, cited/labeled LLM commentary
that never feeds back) is structurally sound. Slice exit gate
(`tests/integration/test_concept_auto_create.py`) is shape-correct and collects;
it requires DATABASE_URL + corpus + lexicon to execute (deferred to the user —
flagged below). 685 unit tests pass; ruff clean. An authoritative Codex re-run
is owed (Bucket-N1).

## Exit-gate execution status (transparency)

The slice exit gate and all Slice-N integration/live_llm tests are
DATABASE_URL- and/or ANTHROPIC_API_KEY-gated and were NOT executed in this
orchestrator session (no live DB/API; sandbox blocks `.env`). They collect
cleanly. Live verification is deferred to the user with the corpus + lexicon
ingested. Per the project transparency rule (CLAUDE.md: "the system must say
when it cannot do something yet"), this is stated rather than papered over.
