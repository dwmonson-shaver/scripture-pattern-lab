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

## DEC-034 — `progress_callback` hook on `load_tokens`; loader stays I/O-pure
- Status: Accepted
- Question: How should `load_tokens` expose progress to a CLI script (and any future worker / UI subscriber) without owning a logger or stderr inside `src/ingestion/`?
- Decision: Add `progress_callback: ProgressCallback | None = None` as a keyword-only parameter on `load_tokens`. `ProgressCallback` is a module-level alias `Callable[[ProgressEvent], None]`. The loader emits events; observability output (prints, logs, metrics) is owned entirely by the caller. The default `None` is a behavioral no-op so existing call sites are unchanged. The loader does not import `logging`, does not call `print`, and writes nothing to stderr.
- Rationale: Keeps `loader.py` testable without log capture, matches the function-style discipline already in `corpus_parser.py`, and gives the upcoming `scripts/db/ingest_corpus.py` (Slice B Phase 3) a typed subscription point. A typed callback also lets future workers or UIs subscribe without parsing strings — pertinent because canonical-09's ingestion boundary (REQ:09.ingestion) explicitly anticipates non-CLI invocation paths (workers).
- Alternatives considered: (a) Add a logger inside `loader.py` — rejected because it forces tests to capture log output to make assertions, and embeds a stdlib choice into a library that callers may want to wire through their own observability stack. (b) Yield events from `load_tokens` as a generator instead of a callback — rejected because `load_tokens` already returns the inserted-row count; mixing a generator return with a count would force callers to either drive the generator and lose the count or wrap it in a sentinel-bearing protocol. A callback keeps the return-shape simple. (c) Pass an event queue object — rejected as over-engineered for synchronous, single-process ingestion.
- Confidence: High
- Made-by: human-approved
- Commit: 5cadd8c
- Files: src/ingestion/loader.py; tests/unit/test_loader.py
- Spec refs: REQ:08.ingestion-pipeline; REQ:09.ingestion

## DEC-035 — `ProgressEvent` is a single frozen Pydantic model with a `kind` literal
- Status: Accepted
- Question: Should the loader's progress events be a single Pydantic model with `kind: Literal["batch","file_boundary","done"]`, or three separate event classes (`BatchEvent` / `FileBoundaryEvent` / `DoneEvent`)?
- Decision: Single model. `ProgressEvent(kind: Literal["batch","file_boundary","done"], book: str | None, tokens_loaded: int)`, `model_config = ConfigDict(frozen=True)`. The `book` field is populated only on `kind="file_boundary"` (otherwise `None`); `tokens_loaded` is populated for all kinds.
- Rationale: Matches the project's Pydantic-everywhere convention (CLAUDE.md "Pydantic models for all data crossing boundaries"). A `kind` literal is sufficient discrimination at MVP scale — there are three event kinds and they share two of three fields. The frozen flag mirrors `CorpusToken` and the AST models, so events can be safely buffered, compared, and cached. Splitting into per-kind classes is a pure cost at this scale (more imports, more types for callers to handle, no payload divergence to model).
- Alternatives considered: (a) Separate `BatchEvent` / `FileBoundaryEvent` / `DoneEvent` classes — rejected as premature; revisit if a future event kind grows kind-specific fields that don't generalize. (b) A `dataclass` instead of Pydantic — rejected for consistency with the rest of `src/ingestion/` and `src/engine/`, all of which use frozen Pydantic v2.
- Confidence: Medium (not High because future event kinds could plausibly diverge enough to warrant a split; the cost of migrating later is bounded — one find/replace plus a Union type).
- Made-by: human-approved
- Commit: 5cadd8c
- Files: src/ingestion/loader.py; tests/unit/test_loader.py
- Spec refs: REQ:08.ingestion-pipeline

## DEC-036 — `ProgressEvent` emission semantics: committed count, post-commit done, ceil-batch, first-token boundary
- Status: Accepted
- Question: `/design` and `/structure` defined the event surface but left several runtime semantics implicit. (a) What does `tokens_loaded` count? (b) Does the first token of the iterator fire a `file_boundary`? (c) Does the trailing partial batch fire its own `batch` event? (d) Does `done` fire inside or outside the transaction's `with` block?
- Decision: Pin all four:
  1. `tokens_loaded` = the **committed** `inserted` counter at the moment of emission. File-boundary events therefore report the count *before* the new book's tokens are committed; batch events report the count *after* the just-flushed batch.
  2. Yes — the first token's book always differs from `last_book = None`, so a `file_boundary` event fires for it. This makes the production line-count "27 file_boundary events" rather than "26 transitions".
  3. Yes — the trailing partial batch fires a `batch` event. Total batch events = `ceil(N / BATCH_SIZE)` (e.g. 137,554 / 1000 → 137 full + 1 partial = 138).
  4. `done` fires **after** the `with engine.begin()` block exits, so it represents truly-committed state, not a pre-commit "done iterating" signal.
- Rationale: "Loaded N" should mean "committed N" because rollback can erase uncommitted progress; reporting an in-flight count that may later vanish would mislead a watcher. Firing on the first token keeps the script's first stderr line non-empty and gives every book equal observability weight. Counting partial batches keeps the script's batch tally honest at non-multiple-of-1000 corpus sizes. Post-commit `done` lets a watcher / wrapper script trust it as a success signal — receiving `done` guarantees the data is in the table.
- Alternatives considered: (a) `tokens_loaded` = "tokens seen so far" (per-token counter incremented before flush) — rejected because it would over-report during partial batches and mislead in failure cases. (b) Skip the first-token boundary and emit only on actual transitions — rejected because the script's stderr would start mid-load with a `batch` event and make the per-book progress narrative harder to read. (c) Skip the partial-batch event and let `done` cover the residual — rejected because callers tracking "throughput per batch" would see a phantom larger-than-BATCH_SIZE final increment from `done`. (d) Fire `done` inside the `with` block (pre-commit) — rejected; `done` would then be unreliable as a success signal.
- Confidence: High
- Made-by: human-approved
- Commit: 5cadd8c
- Files: src/ingestion/loader.py; tests/unit/test_loader.py (`TestProgressCallback::test_callback_fires_per_batch`, `::test_callback_fires_at_file_boundary`, `::test_callback_emits_done_with_final_count`)
- Spec refs: REQ:08.ingestion-pipeline

## DEC-037 — Unit-test isolation for `parse_corpus_directory` via monkeypatching `_BOOK_NUMBER_BY_FILENAME`
- Status: Accepted
- Question: How should a unit test exercise `parse_corpus_directory` without writing 27 real corpus files into `tmp_path`? The function iterates the module-level `_BOOK_NUMBER_BY_FILENAME` map (all 27 BB-keyed entries) and opens every named file from the supplied directory; pointing it at a 2-file fixture directly raises `FileNotFoundError` on the third book.
- Decision: Use `pytest.MonkeyPatch.setattr("src.ingestion.corpus_parser._BOOK_NUMBER_BY_FILENAME", {<2-entry dict>})` for the duration of each test, and copy the two real-format fixture files into `tmp_path`. The map is module-level config (data, not behavior); replacing it in a test is the correct scope-narrowing technique. Production behavior is untouched — production runs continue to see the full 27-entry map and continue to raise on a missing file.
- Rationale: Establishes a pattern for unit tests that target functions iterating hard-coded config tables in `src/ingestion/`. The test stays a pure unit (no real-file dependencies in `tests/fixtures/morphgnt/multi/` beyond the two it needs), preserves fail-loud production semantics (DEC-021's spirit), and keeps the function's contract intact (the docstring still says "all 27 MorphGNT files in canonical book order"). The `multi_dir` fixture in `tests/unit/test_corpus_parser.py` is the canonical example; future similar tests should follow the same shape.
- Alternatives considered: (a) Create 27 placeholder files in `tmp_path`, with 25 empty stubs — rejected as noisy and as coupling the test to the production map's cardinality (any new BB added to `_BOOK_NUMBER_BY_FILENAME` would require touching the test's setup). (b) Soften `parse_corpus_directory` to skip missing files — rejected; that is a production-behavior change that weakens the fail-loud contract for an unrelated reason (test ergonomics). (c) Point the test at the natural fixture dir `tests/fixtures/morphgnt/multi/` — rejected; the function would try to open `63-Lk-morphgnt.txt` etc. and raise.
- Confidence: Medium — establishes the pattern; revisit if a future ingestion iterator iterates a non-config-driven structure (e.g. directory listing) where monkeypatching is not the natural choice.
- Made-by: human-approved
- Commit: 83685a4
- Files: tests/unit/test_corpus_parser.py (`TestParseCorpusDirectory.multi_dir` fixture; all four test methods)
- Spec refs: REQ:08.ingestion-pipeline; REQ:09.ingestion

## DEC-038 — `truncate_tokens` lives in `src/ingestion/db.py` and does not self-gate
- Status: Accepted
- Question: Where should the destructive `TRUNCATE tokens RESTART IDENTITY` helper live, and should the helper itself enforce a confirmation check before issuing the SQL, or should it trust callers to gate?
- Decision: Add `truncate_tokens(engine: Engine) -> None` to `src/ingestion/db.py` alongside `get_engine` and `tokens_table`. The helper wraps a single short-lived `engine.begin()` block around `TRUNCATE TABLE tokens RESTART IDENTITY` and is intentionally **not self-gating** — no env-var check, no flag check, no prompt. The caller is responsible for confirming intent before invoking; the helper just executes.
- Rationale: Same module as `get_engine` (other ingestion callers already import that module), so all `tokens`-table SQL surface lives behind one boundary. No-self-gate keeps the helper testable without env monkeypatching, and forces the destructive-op gate to live one layer up at the call site (where CLI flags, env state, and operator intent are visible). A self-gating helper would have to either re-read env vars (coupling library code to env) or accept a `confirm: bool` parameter (which adds nothing over the caller just deciding before calling).
- Alternatives considered: (a) Put `truncate_tokens` in `scripts/db/ingest_corpus.py` as a private helper — rejected; future tests / future entrypoints (workers) will want the same primitive, and `src/ingestion/db.py` is the natural home for `tokens`-table SQL. (b) Make `truncate_tokens` self-gating on `SPL_INGEST_CONFIRM_TRUNCATE=1` — rejected; couples library code to env-var contract, and re-reading env vars deep inside helpers makes the destructive-op semantics hard to reason about at the call site. (c) Use SQLAlchemy Core `tokens_table.delete()` instead of `TRUNCATE` — rejected; would not reset the SERIAL identity counter and would be slower at scale.
- Confidence: High
- Made-by: human-approved
- Commit: c85081a
- Files: src/ingestion/db.py
- Spec refs: REQ:08.ingestion-pipeline; REQ:09.ingestion
- Cross-refs: DEC-021 (apply schemas explicitly), DEC-028 (TRUNCATE for tests), DEC-039 (the script's two-factor gate)

## DEC-039 — `scripts/db/ingest_corpus.py` is the production entrypoint with a two-factor destructive-op gate
- Status: Accepted
- Question: How should the CLI for full-corpus ingestion be packaged, and what gate prevents accidental wipes against a populated DB? The design discussion (Decision #3) promised "fail-loud + two independent confirmations" but the exact CLI surface was structure-time territory.
- Decision: New executable Python file at `scripts/db/ingest_corpus.py` (sits next to `apply_schemas.sh`; not under `src/app/`, not a `src/__main__`). Argparse surface: `--truncate` (flag), `--corpus-dir DIR` (defaults to `data/raw/morphgnt-sblgnt`). Behavior contract: (1) refuses `--truncate` unless `SPL_INGEST_CONFIRM_TRUNCATE=1` (two independent confirmations); (2) refuses to load when `tokens` is non-empty and `--truncate` is not given; (3) `apply_schemas.sh` is NOT re-run by the script — schema apply remains a distinct step. Validation order in `main()`: env-confirm → corpus-dir → URL print → engine + non-empty check → truncate-or-fail → load (cheapest checks first).
- Rationale: Two independent confirmations (CLI flag + env var) make accidental destructive runs hard. Mirrors `get_engine()`'s fail-loud-on-missing-env style. Keeping the CLI under `scripts/` preserves the DEC-025 (`src/ingestion/` library boundary) and follows the Slice-A `apply_schemas.sh` precedent. Schema apply staying separate keeps the destructive surface minimal — re-applying schema would silently fix a missing `tokens` table, which is exactly the kind of "is your DB the one you think it is" check we want loud.
- Alternatives considered: (a) Single confirmation (just `--truncate`) — rejected; one accidental flag is too cheap. (b) Bundle schema apply into the script — rejected; widens the destructive surface and couples a now-stable schema-apply step to the still-evolving load step. (c) Single-stage prompt (`y/N`) instead of env var — rejected; env var is scriptable for CI and unambiguous in audit logs.
- Confidence: High
- Made-by: human-approved
- Commit: c85081a
- Files: scripts/db/ingest_corpus.py; src/ingestion/db.py (`truncate_tokens` caller)
- Spec refs: REQ:08.ingestion-pipeline (step 4 — bulk-load); REQ:09.ingestion (real entrypoint promised by canonical-09)
- Cross-refs: DEC-021 (apply schemas explicitly), DEC-025 (`src/ingestion/` library boundary), DEC-038 (`truncate_tokens` placement)

## DEC-040 — `ingest_corpus.py` exit-code taxonomy: 0 / 1 / 2 / 3
- Status: Accepted
- Question: What process exit codes should the ingest CLI use, and what should each map to? Shell wrappers and CI scripts will branch on these.
- Decision: `0` = success; `1` = uncaught exception (traceback printed to stderr); `2` = user error (refused destructive op without `--truncate`, or `--truncate` without `SPL_INGEST_CONFIRM_TRUNCATE=1`, or non-empty `tokens` without `--truncate`); `3` = corpus-dir filename-map drift (default-path missing/extra files; `--corpus-dir` extras or empty mapped subset). Exit-code constants are named at the top of the script (`EXIT_OK`, `EXIT_UNCAUGHT`, `EXIT_USER_ERROR`, `EXIT_CORPUS_DRIFT`) and listed in the module docstring.
- Rationale: `1` vs `2` separation lets a wrapper / CI distinguish "the script crashed" from "the script refused on purpose." `3` is its own code so a wrapper can branch specifically on filename drift (e.g. alert differently when MorphGNT renames a file vs. when the operator forgot the env confirm). Conventional Unix CLI practice — argparse itself uses `2` for arg errors, so keeping `2` for user-error preserves consistency with the framework.
- Alternatives considered: (a) Use only 0/1 — rejected; loses the "refused on purpose" signal that CI specifically wants. (b) Use richer codes (4, 5, …) for finer-grained errors — rejected; YAGNI for Slice B's gate set. (c) Reuse `1` for filename drift — rejected; conflates expected-failure with crash.
- Confidence: Medium — 0/1/2/3 mapping is conventional; the specific 3-for-corpus-drift assignment is project-local and may need a wrapper-script handshake when CI wires this up.
- Made-by: human-approved
- Commit: c85081a
- Files: scripts/db/ingest_corpus.py (`EXIT_*` constants and all `return EXIT_*` sites)
- Spec refs: REQ:08.ingestion-pipeline; REQ:09.ingestion
- Cross-refs: DEC-039 (the gate that uses these exit codes)

## DEC-041 — `--corpus-dir` relaxes the strict 27-file guard (Decision A from `/structure`)
- Status: Accepted
- Question: When the script runs against a non-default corpus directory (e.g. the 2-book multi fixture for tests), should the strict 27-file guard apply? `parse_corpus_directory` iterates ALL 27 mapped filenames and would `FileNotFoundError` on any subset, so the script must either bypass the guard or build its own iterator.
- Decision: Default path (no `--corpus-dir`, or path equal to `DEFAULT_CORPUS_DIR`) keeps the strict `_assert_27_files_present` check (exactly the 27 mapped filenames, no missing, no extras). When `--corpus-dir DIR` is supplied with any non-default path, the guard relaxes to: every present file must be a `_BOOK_NUMBER_BY_FILENAME` key (extras still rejected), and at least one mapped file must be present. Implementation requires two additional private helpers in the script (beyond the four named in the structure outline): `_present_filenames_in_bb_order(directory) -> list[str]` (relaxed sort + extras-check) and `_stream_files(directory, filenames) -> Iterator[CorpusToken]` (BB-ordered iteration over an explicit subset, threading `global_position` exactly the way `parse_corpus_directory` does for the full set). `parse_corpus_directory` itself is untouched.
- Rationale: Lets Phase 3 negative-path tests exercise the script against the 2-book multi fixture without bypassing the production guard for production runs. Modifying `parse_corpus_directory` to skip absent files would weaken its fail-loud contract for a test-ergonomics reason — the same anti-pattern DEC-037 rejected for the unit tests. The two extra helpers keep `parse_corpus_directory`'s contract intact (still "all 27 books, fail-loud on a missing file") and isolate the relaxation to the script's CLI surface, where it can be reasoned about per-invocation.
- Alternatives considered: (a) Modify `parse_corpus_directory` to skip missing files — rejected; weakens the fail-loud production contract for a test reason (DEC-037 territory). (b) Force tests to assemble all 27 fixture files — rejected; couples test setup to map cardinality, copies 25 unrelated MorphGNT books for no test value. (c) Keep one helper and inline the relaxed iteration in `main()` — rejected; would duplicate `parse_corpus_directory`'s `global_position` threading logic, which is the kind of duplication a small helper exists to prevent. (d) Add a `filenames=` parameter to `parse_corpus_directory` — possible but premature; would add a public API surface used only by the CLI. Revisit if a third caller needs subset iteration.
- Confidence: Medium — relaxed semantics is right for the script's job; the two-helpers-vs-flag-on-`parse_corpus_directory` tradeoff could be revisited if ingestion grows more callers (e.g. workers that load a single book on demand).
- Made-by: human-approved
- Commit: c85081a
- Files: scripts/db/ingest_corpus.py (`main()`, `_assert_27_files_present`, `_present_filenames_in_bb_order`, `_stream_files`)
- Spec refs: REQ:08.ingestion-pipeline; REQ:09.ingestion
- Cross-refs: DEC-037 (parallel "don't soften production behavior for test ergonomics" decision on the unit-test side)

## DEC-042 — `sys.path` bootstrap pattern for CLI scripts under `scripts/`
- Status: Accepted
- Question: How should a Python script under `scripts/` import from `src/` when invoked directly (`uv run scripts/db/ingest_corpus.py`)? Pytest adds repo root via `pyproject.toml`'s `pythonpath = ["."]`, but standalone CLI invocation does not, so a bare `from src.ingestion.* import ...` fails with `ModuleNotFoundError`.
- Decision: At the top of CLI scripts that need to import from `src/`, add a 4-line idempotent bootstrap: compute repo root from `Path(__file__).resolve().parents[2]`, insert into `sys.path` if not already present. Post-bootstrap imports use `# noqa: E402` to silence ruff's import-position rule. `scripts/` is intentionally NOT made a Python package — no `__init__.py` files, no relative imports. Tests that need to import the script's helpers go through `importlib.util.spec_from_file_location` (see `tests/integration/test_corpus_ingest.py::_import_ingest_module`), preserving the "scripts/ is not a package" boundary.
- Rationale: `scripts/` is for CLI tooling, not library code. Making it a package would invite `from scripts.db.ingest_corpus import x` from production code (e.g. an FastAPI route reaching across), blurring the DEC-025 boundary. The bootstrap is purely an invocation-time concern and is idempotent so re-import (e.g. importlib loader paths) is safe. The `# noqa: E402` markers document the deliberate departure from PEP-8 import ordering.
- Alternatives considered: (a) Make `scripts/` a Python package with `__init__.py` — rejected; pollutes the import surface and weakens `scripts/`-vs-`src/` separation. (b) Require `PYTHONPATH=. uv run scripts/db/...` from callers — rejected; couples invocation to env state and breaks the "the script just works" precedent set by `apply_schemas.sh`. (c) Declare a `[project.scripts]` entry point in `pyproject.toml` — possible but premature; the script is not a published binary and the rebuild step would slow iteration. Revisit when we have a stable CLI surface and want `spl-ingest` as a real command.
- Confidence: Medium — bootstrap is conventional and works today; a future move to packaged entry points would replace it. The pattern should be applied consistently if more `scripts/*.py` files emerge that import from `src/`.
- Made-by: human-approved
- Commit: c85081a
- Files: scripts/db/ingest_corpus.py (lines 26–30: bootstrap; lines 32–40: post-bootstrap imports with `# noqa: E402`); tests/integration/test_corpus_ingest.py (`_import_ingest_module` for the `scripts/`-is-not-a-package import path)
- Spec refs: REQ:09.ingestion
- Cross-refs: DEC-025 (`src/ingestion/` library boundary that the no-package rule preserves)

## DEC-043 — `_redact_database_url` algorithm (no `urllib.parse`, manual rsplit-on-`@`)
- Status: Accepted
- Question: How should the script blot out the password segment of `DATABASE_URL` when printing it to stderr at startup, given that passwords can legally contain `@`, `:`, and other URL-reserved characters?
- Decision: Pure-Python helper `_redact_database_url(url: str) -> str` that performs *no* URL parsing. Algorithm: split scheme on `://`; if absent, return input unchanged. `rsplit('@', 1)` on the rest to find the host boundary; if no `@`, return input unchanged. Split userinfo on the FIRST `:` to separate username from password; if no `:` in userinfo, return input unchanged. Replace the password with the literal string `***`. The helper is intentionally narrow — it redacts only; it does not validate the URL.
- Rationale: `urllib.parse.urlparse` does NOT handle `@` inside passwords reliably — `urlparse('postgresql://u:p@ssw@h/db').hostname` returns `'p@ssw@h'` (or worse, depending on Python version), so it cannot be used as the host extractor. `rsplit('@', 1)` is correct because the LAST `@` always separates userinfo from host (any `@` inside a password must, by URL grammar, come before that). First-`:`-split on userinfo is correct because usernames cannot contain unencoded `:`. Returning input unchanged on missing-`://` / missing-`@` / missing-`:` keeps the helper a pure best-effort redactor — never raises, never throws on weird input — which is the right shape for a stderr-printing helper that must never break the script.
- Alternatives considered: (a) Use `urllib.parse.urlparse` — rejected; password-with-`@` produces wrong hostname. (b) Use a regex like `:[^@:/]+@` — rejected; doesn't handle passwords with `:` (which are valid percent-decoded), and regex on URLs is famously brittle. (c) Use SQLAlchemy's `make_url(...).render_as_string(hide_password=True)` — possible but adds a SQLAlchemy import to the redaction path and binds the helper to a specific URL grammar (Postgres-via-SQLAlchemy). Keep the helper string-shape-agnostic. (d) Print only the host:port — rejected; loses the scheme + username + db, all of which are useful in a "did I just truncate the right DB?" check.
- Confidence: High — directly tested with `test_script_redacts_password_in_database_url_print` covering full userinfo, missing userinfo, missing password, and the pathological `p@ssw0rd` case (literal `@` inside the password).
- Made-by: human-approved
- Commit: c85081a
- Files: scripts/db/ingest_corpus.py (`_redact_database_url`); tests/integration/test_corpus_ingest.py (`test_script_redacts_password_in_database_url_print`)
- Spec refs: REQ:09.ingestion (entrypoint observability surface)
- Cross-refs: DEC-039 (the gate that calls this helper before truncating)

## DEC-044 — Single global `engine.begin()` transaction wraps the whole 27-book load
- Status: Accepted
- Question: Should ingestion commit per-file (138 incremental commits, weaker atomicity, observable progress in the DB mid-load) or in one global transaction (strong atomicity — table is never in a partial state, but no observable mid-load progress)?
- Decision: Single `engine.begin()` wraps all 138 batches across all 27 books. A failure mid-load rolls back the entire ingestion; the `tokens` table is never observed in a partial-load state by any concurrent reader.
- Rationale: 137,554 rows in 138 batches loads in ~4 s on local Postgres — well under any threshold where incremental commits would buy operational value. Atomicity is the load-bearing property: a partial-state table would silently degrade pattern-engine queries that assume corpus completeness, and the failure mode would be hard to diagnose ("why is 1 Corinthians missing tokens?"). Observability of mid-load progress is delivered by the `progress_callback` (DEC-034) and printed to stderr by the script — DB-side observability of partial state is not needed.
- Alternatives considered: (a) Per-file transactions (27 commits) — rejected; partial-state risk outweighs the negligible perf upside at 4 s total. (b) Per-batch transactions (138 commits) — rejected; same problem, more commits. (c) Single transaction with savepoints per file — possible but premature optimization; revisit only if a real "retry just this book" requirement emerges (e.g., remote DB, multi-minute load, transient network failures).
- Confidence: High — atomicity-over-progress is the right call at 137K rows; this would be revisited only if the load becomes long enough that "had to start over" is a meaningful operational cost.
- Made-by: human-approved (design Decision #2 from `thoughts/design-corpus-slice-b-scaling-2026-05-02.md`, ratified at slice-close)
- Commit: code from Slice A (`381117e`); DEC recorded at slice-close (`d622447`)
- Files: src/ingestion/loader.py (`load_tokens` — single `with engine.begin() as conn:` block wraps the whole batch loop)
- Spec refs: REQ:08.ingestion-pipeline; REQ:09.ingestion
- Cross-refs: DEC-034 (`progress_callback` is how mid-load observability is delivered without giving up atomicity)

## DEC-045 — Retain Slice-A `test_load_tokens_returns_219` alongside `test_full_corpus_smoke`
- Status: Accepted
- Question: With `test_full_corpus_smoke` now asserting count, monotonicity, and deduplication across all 27 books, is the Slice-A 3-John-only assertion (`inserted == 219`) redundant?
- Decision: Keep `test_load_tokens_returns_219`. It is a fast, narrow regression alarm specifically for 3 John (book `25`, 219 tokens). It does not duplicate `test_full_corpus_smoke`'s assertions: a parser regression that affects only 3 John might still pass the full-corpus count check (drift in other books could compensate by coincidence) but will fail this test immediately and name the offending book.
- Rationale: Cost to keep is near zero (one assertion, shares the existing `loaded_engine` module-scope fixture). Different jobs: smoke is end-to-end + cross-book invariants; this is a per-book alarm with a known good count. A failure here points the eye directly at 3 John, whereas a smoke failure on the aggregate count is harder to localize.
- Alternatives considered: (a) Delete `test_load_tokens_returns_219` — rejected; loses the per-book alarm. (b) Replace it with a parametrized per-book smoke test for all 27 books — possible but premature; would require pinning 27 counts and would couple test scope to corpus cardinality. Revisit if more per-book alarms are wanted.
- Confidence: Medium — the case for keeping is solid today, but a future parametrized per-book test could subsume this one cleanly.
- Made-by: human-approved (Decision B from `thoughts/structure-corpus-slice-b-scaling-2026-05-02.md`)
- Commit: d622447
- Files: tests/integration/test_corpus_ingest.py (`test_load_tokens_returns_219`); coexists with `test_full_corpus_smoke` in the same file
- Spec refs: REQ:08.ingestion-pipeline

## DEC-046 — `test_full_corpus_smoke` owns its own truncate boundary; does not share `loaded_engine`
- Status: Accepted
- Question: The existing `loaded_engine` module-scope fixture loads 3 John once and yields `(engine, inserted_count)` for several read-only assertions. Should `test_full_corpus_smoke` reuse this fixture, or set up its own DB state?
- Decision: The smoke test does NOT use `loaded_engine`. The script's own `--truncate` (with `SPL_INGEST_CONFIRM_TRUNCATE=1` set on the parent process via `monkeypatch.setenv` and inherited by the subprocess through default env-inheritance) is the function-scoped reset. The smoke test does NOT pre-truncate either — `--truncate` is what's being exercised. The smoke test is placed last in `tests/integration/test_corpus_ingest.py` so that all `loaded_engine`-dependent tests (which assert `count == 219`) run first against the 3-John state, before the smoke wipes and reloads the table to ~138K rows.
- Rationale: Sharing the module-scope `loaded_engine` fixture would either (a) require the smoke to truncate twice (fixture's pre-load + script's `--truncate`) or (b) leave the smoke unable to control the post-load state of its dependents. Function-scoped ownership of the truncate boundary is the cleanest fit. Test ordering by declaration is a stable pytest contract; the comment on the smoke test names the placement intent so a future contributor doesn't reorder it.
- Alternatives considered: (a) Share `loaded_engine` and have the smoke truncate inside its own body — rejected; ugly double-truncate, plus the smoke would still need to bypass the fixture's yielded state. (b) Move `test_full_corpus_smoke` into its own module — possible; cleanly isolates scopes but fragments the integration suite. Two-file split is heavier than one comment. (c) Use a separate function-scoped fixture for the smoke — possible but adds a layer for one consumer; inlining `monkeypatch.setenv` + `_run_ingest_script` is sharper.
- Confidence: High — the placement-comment + monkeypatch.setenv pattern is robust under pytest's default execution-by-declaration order.
- Made-by: human-approved (Decision C from `thoughts/structure-corpus-slice-b-scaling-2026-05-02.md`)
- Commit: d622447
- Files: tests/integration/test_corpus_ingest.py (`test_full_corpus_smoke` placed last, owns its own truncate via `--truncate` + `monkeypatch.setenv`)
- Spec refs: REQ:08.ingestion-pipeline; REQ:09.ingestion

## DEC-047 — `EXPECTED_TOKEN_COUNT = 137_554` pinned; regression-alarm contract on the corpus-and-parser pair
- Status: Accepted
- Question: What integer should `test_full_corpus_smoke` pin as the expected row count, and what is the contract when the integer changes?
- Decision: Pin `EXPECTED_TOKEN_COUNT = 137_554`, observed via the manual ship-gate run on 2026-05-03 (`SPL_INGEST_CONFIRM_TRUNCATE=1 uv run --env-file .env scripts/db/ingest_corpus.py --truncate`) against the SBLGNT edition currently checked into `data/raw/morphgnt-sblgnt/`. Contract: if this integer changes in a subsequent run, either the corpus drifted (MorphGNT released a revised SBLGNT edition) OR the parser drifted (a tokenization regression). The smoke test fails loudly; the dup-detector and per-book aggregate help localize which.
- Rationale: Phase 4 was observe-first-then-pin per the structure outline — the canonical doc said "~138K" and the project_status hint said `137_554`, but the authoritative integer comes from the actual run. Pinning (rather than computing dynamically) IS the regression alarm: a "whatever the corpus produces" assertion would silently absorb both kinds of drift. Re-pinning is cheap (one integer constant + one DEC entry) and explicit.
- Alternatives considered: (a) Compute count dynamically from corpus files — rejected; defeats the regression alarm. (b) Pin a tolerance window (e.g. 137_500 ± 100) — rejected; obscures small drifts which are the most diagnostic. (c) Pin in a separate "expected-counts" config file — possible but premature; one constant in one test does not need its own home yet.
- Confidence: High — the integer is reproducible and the contract is unambiguous.
- Made-by: human-approved
- Commit: d622447
- Files: tests/integration/test_corpus_ingest.py (`EXPECTED_TOKEN_COUNT` constant + module docstring + `test_full_corpus_smoke` assertions)
- Spec refs: REQ:08.ingestion-pipeline

## DEC-048 — Default-path filename guard tolerates extras (e.g. upstream `README.md`); default path derives filenames from `_BOOK_NUMBER_BY_FILENAME` directly. Amends DEC-041.
- Status: Accepted
- Question: Slice B Phase 4's manual ship-gate exposed that `data/raw/morphgnt-sblgnt/` contains a `README.md` alongside the 27 mapped MorphGNT books, and `_assert_27_files_present` rejected the run with `unexpected=['README.md']` (exit 3). Should the strict default-path guard police what else upstream ships in the corpus directory, or only assert that all 27 mapped books are present?
- Decision: Option A. Relax `_assert_27_files_present` from "exactly the 27 mapped filenames, no missing, no extras" to "all 27 mapped filenames present; extras tolerated." On the default path, the script additionally derives its BB-ordered filename list directly from `_BOOK_NUMBER_BY_FILENAME` (no second directory scan), so the relaxed `_present_filenames_in_bb_order` (which still rejects extras for `--corpus-dir` test fixtures) only runs on the `--corpus-dir` path. DEC-041's "extras forbidden on `--corpus-dir`" semantics are preserved unchanged.
- Rationale: The strict guard's load-bearing job is to catch a *missing* book — i.e., a MorphGNT rename that would silently skip a canonical text. It is not the strict guard's job to police upstream housekeeping (`README.md`, `LICENSE`, `.gitignore`, etc.). The vendored MorphGNT repo includes its own README and `.git`; both arrived in commit `78a59ca` and have been there throughout Slice A (which loaded via `parse_corpus_file` directly and never exercised the directory-level guard). Phase 4's ship-gate is the first time the strict guard met the real production directory, exposing the over-strict design.
- Alternatives considered: (a) Filter the strict guard to `*-morphgnt.txt` glob — narrower than option A but no obvious upside; would still need to handle "MorphGNT renamed a book to a non-conforming name" as a missing-book case. (b) Move/delete `README.md` outside the corpus dir — brittle; `git pull` on the vendored repo restores it, and the same fight repeats on every upstream sync. (c) Allowlist `README.md` + `.gitignore` explicitly inside the script — hardcodes upstream's housekeeping inventory into our code; high maintenance cost as upstream evolves.
- Confidence: High — the guard's purpose is clearly "rename detection," and option A makes that purpose explicit. The two-path filename-source split (default = canonical map; `--corpus-dir` = directory scan) cleanly separates production vs. test-fixture concerns.
- Made-by: human-approved
- Commit: d622447
- Files: scripts/db/ingest_corpus.py (`_assert_27_files_present` body + docstring; `main()` default-path filename derivation)
- Spec refs: REQ:08.ingestion-pipeline; REQ:09.ingestion
- Cross-refs: DEC-041 (amends — `--corpus-dir` extras-forbidden semantics unchanged; default-path "no extras" semantics replaced with "extras tolerated")
