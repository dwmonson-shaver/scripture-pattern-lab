# Slice P — Design Review (claude-fallback, adversarial)

- **Date:** 2026-06-13
- **Reviewer:** claude-fallback (independent adversarial sub-agent). Authoritative Codex pass **OWED** — blocked by `~/.codex/sessions` ownership (Bucket-5 perms class; needs `sudo chown -R $(whoami) /Users/dwmonson/.codex` from the user's terminal). Tracked as **Bucket-P-Codex**.
- **Artifact under review:** `thoughts/design-tier2-curator-evidence-promotion-2026-06-13.md`
- **Scope:** Slice P — Tier-2 corpus-evidence finder (C) + human curator promotion gate (B).
- **Verdict:** DEC-119 SOUND · DEC-122 SOUND · **DEC-120 RISKY (HIGH — confirmation-bias trap), revised before any code.**

## Decisions assessed
- **DEC-119 (split provenance vs curator state):** SOUND. Keeps the auto-create guard's literal/validator untouched. Disciplines required: distinct identifier (`curator_state`, never `verification_state`); blob field read-only/omitted in the response.
- **DEC-122 (evidence in `src/retrieval/`):** SOUND, verified against the tree — `src/retrieval` already imports the engine; `src/ontology` imports it nowhere; `src/scoring` is an empty ranking stub; a new `src/evidence` would duplicate retrieval.
- **DEC-120 (auto-set `corpus_observed`):** RISKY/HIGH. Placing a deterministic co-occurrence result on the `unverified→corpus_observed→human_confirmed` endorsement axis advances a prior's standing without a human and makes `corpus_observed` a mandatory pre-confirmation rung — inverting DEC-024/DEC-081. Co-occurrence ≠ conceptual neighborhood (antonyms co-occur constantly). **Revised:** evidence reports, never promotes; every advance is human-actored; deterministic signal moved off-axis as descriptive `cooccurrence_threshold_met` reporting match-type/polarity, not a bare count.

## Findings
1. **[HIGH]** DEC-120 puts a deterministic result on the endorsement axis → confirmation-bias ratchet. *Fix applied:* evidence off-axis + every lifecycle advance human-actored. (Design DEC-120 rewritten.)
2. **[HIGH]** Bare `match_count ≥ 1` misleads the curator (antonyms/co-pericope terms). *Fix applied:* report match-type/polarity discriminator + raw counts + sample refs. (Design DEC-121.)
3. **[MEDIUM]** Two sources of truth for curator state (column + audit table) can drift. *Fix applied:* audit table authoritative; state = latest row; column is write-through cache only. (Design DEC-124.)
4. **[MEDIUM]** Promotion path could silently weaken the DEC-081 guard during implementation. *Fix applied:* new anti-regression test (DEC-126).
5. **[MEDIUM]** DEC-120 field-name leakage couples all three phases. *Fix applied:* naming/axis settled in design before Phase 1 writes the `GroupingEvidence` model.
6. **[LOW]** `src/ontology` must never import `grouping_evidence`. *Fix applied:* OQ-6 — app layer passes evidence snapshot into the ontology promotion writer; import-boundary test in structure.
7. **[LOW]** Default threshold `≥1` too permissive to flip a lifecycle-adjacent flag. *Fix applied:* threshold descriptive only, explicit/advertised; OQ-3.
8. **[LOW]** Never reuse the identifier `verification_state` for the curator field; blob field read-only/omitted in response. *Fix applied:* DEC-119.

## Disposition
All HIGH/MEDIUM findings folded into the design before implementation. Authoritative Codex re-pass on the cumulative slice diff owed at slice close (Bucket-P-Codex); the DEC-120 epistemic call in particular should get Codex's independent eyes once the perms blocker clears.
