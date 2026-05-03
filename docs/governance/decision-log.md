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

## DEC-028 — Use `TRUNCATE … RESTART IDENTITY` (not subprocess re-apply) for integration-test reset
- Status: Accepted
- Question: The integration test needs a clean `tokens` table at start. `thoughts/design-corpus-parser-2026-04-26.md` left the choice open between `subprocess.run(['bash', 'scripts/db/apply_schemas.sh'])` and `TRUNCATE tokens`. Which is the right reset strategy?
- Decision: A module-scoped fixture issues `TRUNCATE TABLE tokens RESTART IDENTITY` once at session start; the schema is assumed already applied (`apply_schemas.sh` is run as a one-time prereq, not from the test harness). A separate one-off check that `apply_schemas.sh` is idempotent on a fresh schema-less DB is owed and tracked under `/coverage` follow-up.
- Rationale: Sub-millisecond reset vs. spawning psql via subprocess on every run; no shell-out coupling between Python tests and bash scripts; schema is canonical from Phase 1's apply (preserved across container restarts in the `spl_pgdata` volume) and the Phase 4 drift trap (DEC-030) catches mirror divergence directly without needing the apply script in the test path. `RESTART IDENTITY` makes the SERIAL `id` counter predictable across test runs.
- Confidence: High
- Made-by: human-approved
- Commit: 381117e
- Files: tests/integration/test_corpus_ingest.py
- Spec refs: REQ:08.ingestion-pipeline (step 4 — load into Postgres)
- Cross-refs: DEC-021 (apply schemas explicitly), DEC-030 (drift trap that compensates for not re-running the apply script)

## DEC-029 — `get_engine()` normalizes `postgresql://` URLs to `postgresql+psycopg://`
- Status: Accepted
- Question: SQLAlchemy 2.0 defaults a bare `postgresql://` URL to the `psycopg2` DBAPI, but the project's only Postgres driver is `psycopg[binary]>=3` (psycopg3). `.env.example` (and operator muscle memory) uses the bare form. How should `get_engine()` reconcile this?
- Decision: Inside `get_engine()`, rewrite a leading `postgresql://` to `postgresql+psycopg://` before handing the URL to `create_engine`. URLs already carrying an explicit dialect prefix (`postgresql+psycopg://`, `postgresql+asyncpg://`, etc.) pass through unchanged. The fail-loud `RuntimeError` for unset `DATABASE_URL` precedes the rewrite.
- Rationale: Without normalization, the integration test fails with `ModuleNotFoundError: No module named 'psycopg2'` — a confusing, indirect error pointing at a dependency that isn't part of this project. Normalizing in code keeps the documented `.env.example` form working and means new developers don't need to memorize the SQLAlchemy dialect-prefix convention. Three lines, well-commented. The trade-off is a minor "implicit" wart vs. operator friction; chose minimal friction since psycopg3 is the only driver this project will ever ship.
- Confidence: Medium — defensive shim. Reconsider if/when a second Postgres driver (e.g. `asyncpg` for async routes) enters scope; at that point an explicit `.env` prefix may become preferable.
- Made-by: human-approved
- Commit: 381117e
- Files: src/ingestion/db.py
- Spec refs: — (cross-cuts design decision #9 on driver choice in `thoughts/design-corpus-parser-2026-04-26.md`)

## DEC-030 — Three-way schema-drift assertion (live SQL ↔ Core mirror ↔ `CorpusToken`)
- Status: Accepted
- Question: The project's `tokens` schema lives in three places: the canonical `data/schemas/01_tokens.sql`, the SQLAlchemy Core `tokens_table` mirror in `src/ingestion/db.py`, and the `CorpusToken` Pydantic model in `src/ingestion/corpus_parser.py`. The carry-over note from Phase 3 specified a two-way drift check (reflected SQL ↔ `CorpusToken`). Should the integration suite also check the Core mirror?
- Decision: A single integration test (`test_schema_three_way_consistency`) reflects the live `tokens` table into a fresh `MetaData`, then asserts: (a) reflected columns equal `tokens_table.columns.keys()` exactly, and (b) reflected columns minus `{"id"}` equal `CorpusToken.model_fields.keys()`. Failure messages name the only-in-X and only-in-Y sets so divergences read at a glance.
- Rationale: Pair (a) catches Core-mirror drift directly at test time (otherwise the failure surfaces as a low-level driver error during `insert(tokens_table)`); pair (b) catches Pydantic drift. Together they guarantee all three sources stay in lock-step, which matters because future query code (e.g. the pattern engine) is expected to use `tokens_table.c.X` selectors. One extra line of code, covers a third drift path, and gives a clear name to a previously implicit failure mode.
- Confidence: High
- Made-by: human-approved
- Commit: 381117e
- Files: tests/integration/test_corpus_ingest.py
- Spec refs: REQ:08.token-schema

## DEC-031 — Polarity on parenthesized alternatives/groups distributes to NodeRef leaves
- Status: Accepted
- Question: How should polarity be represented when applied to a parenthesized alternative or group, e.g. `+(concept:hope | concept:expectation)`? Polarity is a NodeRef-only attribute today; the form has multiple options.
- Decision: At parse time, detect polarity-then-LPAREN in `parse_step`, consume the polarity, dispatch to `parse_group_or_alternative`, then walk the result via a new module-level `_distribute_polarity` helper that stamps polarity on every NodeRef leaf inside AlternativeExpr/GroupExpr (recursive). Polarity remains a NodeRef-only field; `AlternativeExpr` and `GroupExpr` do **not** gain a `polarity` attribute. NodeRefs are frozen Pydantic models; updates use `model_copy(update={"polarity": ...})`.
- Rationale: Matches `docs/canonical/05_dsl-ast.md:252-271` exactly — the canonical example shows the compiled AST as an AlternativeExpr where each NodeRef option carries `polarity: "+"`. Distributing at parse time means the validator and pattern engine only handle polarity in one place (the leaf), avoiding two-place semantics that would otherwise sprout from a composite-level field.
- Alternatives considered: (a) Add `polarity` to AlternativeExpr/GroupExpr — rejected because it bifurcates polarity logic, makes the canonical example diverge from the AST, and forces every downstream consumer (validator rules, executor, scoring) to look in two places. (b) Reject the syntax until the canonical doc adds a composite-level polarity rule — rejected because the canonical example already specifies the distributed form.
- Confidence: High
- Made-by: human-approved
- Commit: 9aa900a
- Files: src/engine/parser.py; tests/unit/test_parser.py
- Spec refs: REQ:05.dsl-ast (canonical-05:252-271 polarity-with-alternatives example)

## DEC-032 — Composite-step partial-reduction semantics
- Status: Accepted
- Question: When `_reduce_step` recurses into composite step types during partial-plan reduction, how should each composite degrade as its children are dropped?
- Decision: AlternativeExpr — drop unsupported options recursively; if 0 survive return None (drop the alternative entirely); if exactly 1 survives, **collapse** to that single option (not an AlternativeExpr wrapper); if 2+ survive, keep the AlternativeExpr with the reduced options list. GroupExpr — reduce its inner SequenceExpr via `_reduce_sequence`; if the result has fewer than 2 steps, drop the group entirely (return None). OptionalExpr — reduce its inner step; if None, drop the optional entirely.
- Rationale: Mirrors the existing top-level "drop or downgrade" discipline already in `_reduce_plan`, applied recursively. Single-survivor alternative collapse avoids leaving structurally redundant `AlternativeExpr(options=[X])` wrappers downstream — a one-option alternative is semantically just that option, and the engine would otherwise need a special case. The <2-step rule for GroupExpr reuses the same minimum-viable-sequence threshold the top-level `_reduce_sequence` enforces, since GroupExpr's inner is itself a SequenceExpr. OptionalExpr's drop rule is symmetric with NodeRef's — both are single-slot wrappers, both vanish when their content is unsupported.
- Alternatives considered: (a) Keep single-option AlternativeExpr wrappers — rejected because every downstream consumer would need to know `Alternative(options=[X])` is equivalent to `X`, an extra rule for no benefit. (b) Allow GroupExpr to collapse to a 1-step inner — rejected because a 1-step "sequence" has 0 operators and isn't a meaningful sequence; cleaner to drop the wrapper and let surrounding reduction decide. (c) Promote OptionalExpr's inner up if it survived — out of scope; an OptionalExpr already represents "may or may not appear," so dropping it when its inner is unsupported is the conservative choice.
- Confidence: High
- Made-by: human-approved
- Commit: 6d6af2a
- Files: src/validation/validator.py; tests/unit/test_validator.py
- Spec refs: REQ:06.partial-reduction (capability-validator partial-plan reduction contract)

## DEC-033 — Wildcard `*` tokenized as a WORD token (no dedicated TokenKind)
- Status: Accepted
- Question: The DSL wildcard `*` (canonical-05 v0.1 NodeType.WILDCARD) needs to flow from tokenizer to parser. Add a dedicated `TokenKind.STAR` and update the parser, or emit `*` as a `WORD` token and reuse the existing `word_tok.value == "*"` branch in `_parse_typed_value`?
- Decision: Emit `*` as `Token(kind=WORD, value="*")`. Tokenizer change is a single special-case branch immediately after the single-character map; parser is unchanged.
- Rationale: `_parse_typed_value` already had a `word_tok.value == "*"` branch that was unreachable because the tokenizer never produced `*`. The minimal fix makes that branch reachable, no parser changes needed. The v0.1 DSL spec does not use `*` in any compound context (no `*+morph:X`, no `**` operator), so distinguishing wildcard from words at the token-kind level provides no expressive benefit.
- Alternatives considered: Add `TokenKind.STAR` and a STAR-handling branch in `_parse_typed_value` — rejected because it touches both tokenizer and parser, doubling the change footprint, with no v0.1 expressive benefit. Revisit if/when wildcard syntax extends (e.g., `*{N}` for "N consecutive wildcards" or `**` for "any subsequence").
- Confidence: Medium-High
- Made-by: human-approved
- Commit: 9f39f25
- Files: src/engine/parser.py; tests/unit/test_parser.py
- Spec refs: REQ:05.dsl-ast (wildcard NodeType at canonical-05:57 and :308)
