# Decision Log

## DEC-001 — Product focus is hypothesis exploration, not generic scripture chat
- Status: Accepted
- Rationale: The unique value lies in structured pattern exploration over original-language data.
- Sources: CONV-001

## DEC-002 — Symbolic search is the core engine; AI is an assistant layer
- Status: Accepted
- Rationale: Deterministic matching is required for trustworthy sequence analysis.
- Sources: CONV-001, CONV-002

## DEC-003 — Natural language must compile to DSL rather than bypass it
- Status: Accepted
- Rationale: Preserves reproducibility and prevents unsupported AI behavior.
- Sources: CONV-004

## DEC-004 — Sequence extension analysis is a core capability
- Status: Accepted
- Rationale: Users need predecessor, successor, subpattern, and supersequence analysis.
- Sources: CONV-001, CONV-002

## DEC-005 — Polarity-aware inverse analysis is a core requirement
- Status: Accepted
- Rationale: Important patterns may appear in negative-pole, reversal, or intertwined form.
- Sources: CONV-003

## DEC-006 — Capability validation must be explicit and first-class
- Status: Accepted
- Rationale: The system must say “I can’t do that yet” rather than fabricate unsupported analysis.
- Sources: CONV-004

## DEC-007 — Results must distinguish match types clearly
- Status: Accepted
- Rationale: Exact, conceptual, inverse, expanded, and intertwined matches should not be conflated.
- Sources: CONV-001, CONV-003

## DEC-008 — Build a readable query DSL with simple and advanced modes
- Status: Accepted
- Sources: CONV-002

## DEC-009 — The DSL models sequence graphs, not simple keyword search
- Status: Accepted
- Sources: CONV-002

## DEC-010 — Support typed nodes, gaps, scope, and mode directives in MVP DSL
- Status: Accepted
- Sources: CONV-002

## DEC-011 — Give polarity first-class syntax support
- Status: Accepted
- Sources: CONV-003

## DEC-012 — Use hybrid architecture rather than vector-only retrieval
- Status: Accepted
- Sources: CONV-002, EXT-001, EXT-002

## DEC-013 — Canonical data must be structured at token and scope levels
- Status: Accepted
- Sources: CONV-001

## DEC-014 — The pattern engine must support exact, approximate, conceptual, and inverse-family analysis
- Status: Accepted
- Sources: CONV-001, CONV-003

## DEC-015 — AI should explain, expand, and critique rather than silently decide
- Status: Accepted
- Sources: CONV-002

## DEC-016 — UI should behave like a research workbench rather than a plain chat box
- Status: Accepted
- Sources: CONV-001

## DEC-017 — Multi-stage retrieval is preferred over single-pass RAG
- Status: Accepted
- Sources: CONV-002, EXT-002

## DEC-018 — RAG is supporting infrastructure, not the core pattern engine
- Status: Accepted
- Sources: CONV-002

## DEC-019 — Ranking should be transparent and weighted
- Status: Accepted
- Sources: CONV-002

## DEC-020 — MVP should be narrow but rigorous
- Status: Accepted
- Sources: CONV-002

## DEC-021 — Apply Postgres schemas explicitly, not via initdb auto-load
- Status: Accepted
- Question: How should database schemas be applied to the dev container?
- Decision: Apply schemas via `psql` or a migration tool. Do not mount schema files into `/docker-entrypoint-initdb.d/`.
- Rationale: initdb scripts only run when the data dir is empty. After first boot, schema edits silently no-op — exactly the kind of drift the project's "no slop" rule is meant to prevent. Explicit application keeps schema changes visible during the dev loop.
- Confidence: High
- Made-by: human-approved
- Commit: 99a2477
- Files: docker-compose.yml, data/schemas/README.md
- Spec refs: REQ:08.token-schema (related — mechanism, not schema content)

## DEC-022 — Fail loud when no schema files match in apply_schemas.sh
- Status: Accepted
- Question: What should `scripts/db/apply_schemas.sh` do if the `data/schemas/*.sql` glob is empty?
- Decision: Exit non-zero with a clear "No schema files found" message. Do not silently succeed.
- Rationale: Same spirit as DEC-021 — silent no-ops are exactly the failure mode this project commits to avoiding. An empty schema directory means something is misconfigured, and the user should hear about it on the first run, not three steps later when a query fails for a missing table.
- Confidence: High
- Made-by: human-approved
- Commit: 5ba8aae
- Files: scripts/db/apply_schemas.sh
- Spec refs: REQ:08.ingestion-pipeline (related — mechanism for step 4)

## DEC-023 — Use `psql -v ON_ERROR_STOP=1` in apply_schemas.sh
- Status: Accepted
- Question: Should `apply_schemas.sh` continue running statements within a schema file after one fails, or abort on the first error?
- Decision: Pass `-v ON_ERROR_STOP=1` to `psql` so each schema file aborts on the first error.
- Rationale: Atomic-per-file is the predictable behavior. Half-applied schemas (some indexes created, others skipped) are worse than no schema — a `\d tokens` SELECT cannot distinguish a missing index from one whose creation silently failed mid-script. Failing loud preserves the ability to diagnose.
- Confidence: High
- Made-by: human-approved
- Commit: 5ba8aae
- Files: scripts/db/apply_schemas.sh
- Spec refs: REQ:08.ingestion-pipeline (related — mechanism for step 4)

## DEC-024 — Corpus is ground truth; registry entries are provisional priors
- Status: Accepted
- Question: Should the concept registry — curated lemma→concept and polarity mappings — be treated as ground truth, or as a working-hypothesis layer over the corpus?
- Decision: The corpus is ground truth. Registry entries (concept seeds, lemma mappings, polarity claims) are provisional priors that must clear corpus evidence before the system treats them as confirmed. Architecture must make this distinction structural, not optional. The system tests priors against the text; it does not confirm them.
- Rationale: The project's load-bearing goal is hypothesis exploration without confirmation bias — surfacing real textual patterns rather than ratifying the user's theological readings. A registry that defaults `confidence` to 1.0 and treats curated assertions as identical to corpus-confirmed ones is the failure mode this project exists to avoid. This decision is the epistemic counterpart to DEC-006 (capability validation must be explicit) and DEC-007 (results must distinguish match types) — those commit to architectural honesty about what the system can do; this one commits to architectural honesty about what it knows. Concrete implications include: provenance fields on registry entries (`origin: curated | corpus_observed | ai_suggested`), evidence-grounded vs prior-grounded match-type axis, polarity as a relational table with evidence counts (not a property of a concept), `confidence` defaulting to NULL (or a low value) rather than 1.0, registry pre-flight that downgrades unverified entries.
- Confidence: High
- Made-by: human-approved (stated explicitly during phase-1 /review on 2026-04-27 after the user asked "am I leading the witness?")
- Commit: pending — landing alongside this entry
- Files: CLAUDE.md (new Non-Negotiable Rules bullet); docs/governance/decision-log.md (this entry)
- Spec refs: REQ:08.concept-registry (architectural implications for concept tables — provenance, polarity-as-relational, etc., to be elaborated in a separate /design before Slice C)
- Cross-refs: DEC-006, DEC-007

## DEC-025 — Add `src/ingestion/` to architecture boundaries; query-side packages stay query-side
- Status: Accepted
- Question: Where does corpus-ingestion code (file IO + bulk DB insert) live? It does not belong in `src/engine/` (DSL parser / pattern engine, query-side), `src/nlp/` (AI layer), or `src/validation/` (capability validator).
- Decision: Add a new `src/ingestion/` subpackage to the architecture-boundaries list in CLAUDE.md. It owns corpus loaders (file IO + DB bulk insert). Query-side packages (`engine/`, `nlp/`, `retrieval/`, `scoring/`, `validation/`, `ontology/`) do not reach into ingestion code, and ingestion does not reach into them.
- Rationale: The existing boundaries are query-side. Ingestion needs its own home so the engine never imports parser-of-corpus-files alongside parser-of-DSL, and so a future second corpus (LXX, Hebrew Bible) can land beside the NT one without touching query code. Documenting the boundary in CLAUDE.md and the decision log keeps the expansion discoverable.
- Confidence: High
- Made-by: human-approved (per design-corpus-parser-2026-04-26.md decision #1)
- Commit: pending — this commit
- Files: CLAUDE.md (architecture-boundaries entry); src/ingestion/__init__.py (new, empty package marker)
- Spec refs: REQ:08.ingestion-pipeline (this is its codebase home)

## DEC-026 — `CorpusToken.book` stores the 2-digit BB code, not a lowercase abbreviation
- Status: Accepted
- Question: What value goes in `CorpusToken.book`? Design decision #5 (`thoughts/design-corpus-parser-2026-04-26.md`) said BB → lowercase abbreviations (`mt`, `mk`, …, `re`). The structure outline (`thoughts/structure-corpus-parser-2026-04-26.md`) overrode this to `"two-digit BB from BBCCVV (e.g. \"25\")"`, and Phase 4's integration test asserts `book='25'`. REQ:08.annotation-layers' illustrative table still shows `"1cor"`-style values.
- Decision: Store the raw 2-digit BB code (`"25"` for 3 John). The design's lowercase-code language is superseded by the structure outline. The annotation-layers illustration in `docs/canonical/08_mvp-corpus-scope.md` will be reconciled to match the BB-digit form during a future canonical edit.
- Rationale: BBCCVV is the on-disk truth of every row; storing it verbatim removes a translation layer, keeps `book` lexicographically sortable for `ORDER BY book, chapter, verse, position`, and matches the test contract Phase 4 already commits to. A lookup table from BB → human-readable abbreviation can live in a query-side helper if downstream consumers need it; it does not belong on the canonical row.
- Confidence: High
- Made-by: human-approved
- Commit: 1f4cf77
- Files: src/ingestion/corpus_parser.py; tests/unit/test_corpus_parser.py
- Spec refs: REQ:08.token-schema, REQ:08.annotation-layers (canonical doc uses `"1cor"`-style examples — flagged for canonical reconciliation; not separate work, fold into next canonical-08 edit)
- Cross-refs: DEC-021 (related: corpus-side mechanics)

## DEC-027 — `parse_corpus_line` takes both `position` and `global_position` as caller-supplied kwargs
- Status: Accepted
- Question: The structure outline's signature for `parse_corpus_line` declared only `*, global_position: int`, but `CorpusToken` requires both `position` and `global_position`. `position` resets per BBCCVV and cannot be derived from a single line in isolation. How should the line-level primitive get `position`?
- Decision: Add `position: int` as a required kwarg alongside `global_position`. Both are caller-supplied state. `parse_corpus_file` owns the per-verse counter (resets on BBCCVV change) and the corpus-wide counter; `parse_corpus_line` stays a pure stateless mapper from `(line, line_no, source, position, global_position)` to `CorpusToken`.
- Rationale: Keeps the line-level primitive testable in isolation without setting up a verse-tracking harness. The structure outline's omission of `position` from the kwarg list appears to have been an oversight, not a design choice (a frozen `CorpusToken` cannot be constructed without a `position` value, and `model_copy(update={...})` post-construction would require either a transient invalid token or a non-frozen model — both worse).
- Confidence: High
- Made-by: human-approved
- Commit: 1f4cf77
- Files: src/ingestion/corpus_parser.py
- Spec refs: REQ:08.ingestion-pipeline (step 3 — sequential token IDs, per-verse and global)
