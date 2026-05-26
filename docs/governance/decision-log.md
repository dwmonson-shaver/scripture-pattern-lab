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
- Commit: `f46ebbd` (Establish anti-confirmation-bias as project's epistemic charter)
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
- Commit: `974ff49` (Phase 2: ingestion package skeleton + DEC-025 boundary expansion)
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

## DEC-049 — Registry epistemics: provenance + NULL-default confidence + evidence-bearing relational claims + grounding axis on results
- Status: Accepted
- Question: How does DEC-024 ("corpus is ground truth; registry entries are provisional priors") become a structural commitment in the schema and the validator, not an aspirational principle?
- Decision: Four invariants, realized by Slice C Track 1: (a) every registry row carries `origin VARCHAR(20) NOT NULL DEFAULT 'curated'` (allowed: `curated` / `ai_suggested` / `lexicon_imported`); (b) `concept_lemmas.confidence` and the new claim tables' `confidence` columns default to `NULL`, never `1.0`; (c) polarity and inverse mappings are evidence-bearing relational tables (`polarity_claims`, `inverse_claims`) with `evidence_count INTEGER NOT NULL DEFAULT 0` and `verification_state` ∈ {`unverified`, `corpus_observed`, `human_confirmed`} — NOT columns on `concepts`; (d) `ValidationResult.grounding` ∈ {`evidence-grounded`, `prior-grounded`, `mixed`} | None labels a query result by whether the backing claims are corpus-evidenced. Validator rule 13 (`_rule_13_registry_grounding`) is **additive-not-blocking**: it emits a `RULE13_PRIOR_GROUNDED` warning and sets the grounding axis but never pushes status to `unsupported` or `partial`. SQL CHECK constraints enforce all value domains at the DB layer (closed Codex P2 from the interim review).
- Rationale: A registry that defaulted `confidence` to `1.0` and stored polarity as a column on `concepts` would silently convert curator hypotheses into corpus-confirmed facts — the failure mode DEC-024 exists to prevent. Making the four invariants structural prevents future canonical edits from quietly reverting them. Grounding-as-orthogonal-axis (not a fifth `match_mode` value) keeps `match_mode` answering "how do we resolve the node" while `grounding` answers "is the resolution backed by corpus evidence" — different questions, separate columns.
- Confidence: High — landed and tested through the slice-exit gate.
- Made-by: orchestrator-mode (per `feedback_dec_autonomy.md`); approved Track 1 design at `thoughts/design-registry-epistemics-2026-05-03.md` (status: approved 2026-05-03); reviewed at slice-close.
- Commit: chain `9251a11` … `99d4214` (Phases 1–6 + interim P1/P2 closure)
- Files: docs/canonical/08_mvp-corpus-scope.md (REQ:08.registry-epistemics + revised schema sketch); data/schemas/02_concept_registry.sql; src/ontology/registry.py; src/validation/validator.py (rule 13, ValidationResult.grounding, validate signature); scripts/db/seed_registry.py; data/seeds/registry/*.csv
- Spec refs: REQ:08.registry-epistemics (NEW); REQ:08.polarity-claims-table (NEW); REQ:08.inverse-claims-table (NEW); REQ:08.concept-table (revised); REQ:08.concept-lemma-table (revised); REQ:06.partial-reduction (validator extension)
- Cross-refs: DEC-024, DEC-007 (results distinguish match types), DEC-015 (AI explains rather than silently decides)

## DEC-050 — Pattern engine MVP contract: SequenceExpr of NodeRef (LEMMA/CONCEPT) leaves with PRECEDENCE operators; everything else raises UnsupportedPlanShape
- Status: Accepted
- Question: What AST shapes does `src/engine/executor.py` handle in MVP, and what happens to anything outside that contract?
- Decision: MVP supports `plan.sequence` as `SequenceExpr` (NOT `InverseExpr`) of `NodeRef` leaves where `type ∈ {LEMMA, CONCEPT}`, `OperatorType.PRECEDENCE` operators only, optional `GapConstraint`, `ScopeConstraint{corpus, language, books, unit=verse}`, `negated=False`, `morph_filters=[]`, and `len(operators) == len(steps) - 1`. Anything outside this contract — Adjacency / Cooccurrence operators, Alternative / Optional / Group steps, ROOT/DOMAIN/MORPH/WILDCARD nodes, InverseExpr at the top level, expansion directives, ranking weights, scope units other than verse, negated nodes, morph filters, malformed operator counts, unknown book abbreviations — raises `UnsupportedPlanShape(message, *, path)` immediately. Empty match list is the answer for "no matches"; raise is the answer for "I can't run this plan." Concept nodes whose registry returns `[]` raise the dedicated `ConceptNotMapped(concept_name)` exception (distinct from `RegistryRequired`, which fires when no registry was supplied at all) so the CLI can map it to a specific exit code.
- Rationale: The validator's `_reduce_plan` already drops most unsupported shapes during partial reduction. The executor is the **second wall**: if the validator misses something, fail loudly rather than return wrong results. Canonical-09 §5 explicitly endorses "not elegant at scale but correct and sufficient for 138K tokens" — correctness over elegance. The shape-gate covers every modifier the resolution path ignores, so a future regression that relaxes one without updating the other can't silently produce wrong answers.
- Alternatives considered: (a) Have the executor degrade gracefully on out-of-contract shapes — rejected; the canonical "results must distinguish match types clearly" (DEC-007) requires unambiguous semantics, and silent coercion is the opposite. (b) Fold the shape gate into the validator instead of duplicating — rejected; the validator's role is "is this plan declaratively supported", the executor's is "can I actually execute this exact plan", and the second wall is what catches a validator bug.
- Confidence: High.
- Made-by: orchestrator-mode (low-stakes / high-confidence per `feedback_dec_autonomy.md`); design at `thoughts/design-pattern-engine-executor-2026-05-09.md` (status: approved 2026-05-09).
- Commit: chain `0eef8f5` … `1a2cf93` (executor + close-review fixes)
- Files: src/engine/executor.py (`_validate_plan_shape` + raises); src/engine/models.py (`UnsupportedPlanShape`, `RegistryRequired`, `ConceptNotMapped`); tests/unit/test_executor.py
- Spec refs: REQ:09.pattern-engine (NEW implementation); REQ:04.matching-rules (LEMMA + CONCEPT rows implemented; others raise); REQ:08.token-schema (consumed)
- Cross-refs: DEC-014 (engine match-type support), DEC-007 (results distinguish match types), DEC-024 (no silent coercion)

## DEC-051 — Track 2 (result contextualization) implementation deferred to Slice D, with sharpened trigger
- Status: Accepted
- Question: Slice C was originally scoped to ship Track 1 (registry epistemics) AND Track 2 (result contextualization). Mid-slice, the user surfaced that they could not meaningfully review calibration-shape decisions for results that did not yet exist (no `src/engine/executor.py`, no `MatchCandidate` stream, no observable counts). Should Slice C ship Track 2 anyway, or defer?
- Decision: Defer Track 2 implementation to **Slice D**. Track 2's `/design` artifact (`thoughts/design-result-contextualization-2026-05-03.md`) lands at status `design-stable-implementation-deferred` with 4 of 6 OQs resolved and 2 (canonical-01 amendment, Pydantic dump-shape) marked deferred-pending-interface. Slice C re-scopes to ship Track 1 + executor + thin CLI so the user can run real queries before Track 2's calibration shape is finalized. Sharpened trigger for Slice D: *after CLI ships and the user has interacted with real result counts*. Bucket 2 closure now requires Track 1 code (Slice C) + Track 2 code (Slice D), with closing SHA pending Slice D close.
- Rationale: Calibration-shape decisions (alternative-ordering caps, null-distribution presentation, opt-in defaulting) are forms of judgment about what numbers feel meaningful — and that judgment needs concrete numbers to react to. Designing Track 2 in the abstract while the user rubber-stamps the OQs reproduces the failure mode (silent unverified priors becoming structural decisions) that Track 1 exists to prevent. The honest move is to admit the feedback-loop gap and re-sequence.
- Alternatives considered: (a) Ship Track 2 in Slice C with the user's rubber-stamped OQ resolutions — rejected; the user explicitly named the rubber-stamping as the problem. (b) Ship Track 2 design only, defer everything — rejected; Track 1 + executor + CLI is exactly the runnable thin slice that closes the feedback loop.
- Confidence: High — the user explicitly endorsed the re-scope and the orchestrator-mode handoff that realized it.
- Made-by: human-approved (re-scope decision 2026-05-08 in conversation; recorded autonomously into the DEC log per orchestrator-mode rule)
- Commit: `fed3b98` (re-scope governance) and chain `0eef8f5` … `1a2cf93` (executor + CLI realizing the re-scoped shape)
- Files: docs/governance/reviews-log.md (Bucket 2 closure column); thoughts/design-result-contextualization-2026-05-03.md (status flip to design-stable); user's project_status.md memory
- Spec refs: REQ:09.contextualization (planned, Slice D)
- Cross-refs: DEC-024 (corpus-is-ground-truth — Track 2 is its result-side companion); DEC-049 (Track 1 realizes the input-side companion)

## DEC-052 — `src/engine/_schema.py` owns a private `tokens_table` mirror; query-side packages do not import `src/ingestion/`
- Status: Accepted
- Question: The Codex slice-close review (`docs/reviews/review-codex-code-slice-c-close-2026-05-09.md` C-CLOSE-005) flagged that `src/engine/executor.py` imported `tokens_table` from `src/ingestion/db.py`, breaching DEC-025. Where should the engine's read view of the `tokens` table live?
- Decision: Each query-side package that reads a corpus or registry table maintains its own private `Table` mirror with its own `MetaData()` instance. `src/engine/_schema.py` (private — leading underscore) owns a `_metadata` plus a `tokens_table` definition column-for-column matching `data/schemas/01_tokens.sql`. The SQL file is canonical; Python mirrors are independent per-package views on the same DDL. This pattern is already established by `src/ontology/registry.py`, which mirrors `02_concept_registry.sql` independently of any ingestion-side mirror.
- Rationale: DEC-025 says ingestion does not import from query-side AND query-side does not import from ingestion. A literal read of that boundary forbids `src/engine/X` from importing `src/ingestion/Y`. The fix could have been (a) move `tokens_table` to a new neutral package (would require a CLAUDE.md architecture-list edit and a new top-level package), or (b) duplicate the Python mirror in the query-side package. Option (b) matches the existing precedent (ontology already does this) and avoids inventing a new architectural layer for one Table.
- Alternatives considered: (a) New `src/persistence/` package — rejected as over-architecture for one Table mirror (CLAUDE.md's architecture list does not include a persistence package; adding one is its own DEC). (b) Leave the import and weaken DEC-025 — rejected; DEC-025 is the boundary that lets ingestion and query-side ship independently.
- Risks: drift between the two `tokens_table` definitions (`src/ingestion/db.py` and `src/engine/_schema.py`). Mitigation: integration test `test_schema_three_way_consistency` (Slice A) verifies live DB ↔ Python mirror ↔ Pydantic; extending it to verify both Python mirrors against the live DB is a follow-up if the divergence cost ever bites.
- Confidence: High — closes Codex P2 cleanly and follows the established ontology-side precedent.
- Made-by: orchestrator-mode (in response to Codex finding); reviewed at slice-close.
- Commit: `1a2cf93` (slice-close fix bundle)
- Files: src/engine/_schema.py (NEW); src/engine/executor.py (import change)
- Spec refs: REQ:08.token-schema (consumed); REQ:09.pattern-engine (uses the new mirror)
- Cross-refs: DEC-025 (boundary preserved); DEC-024 (no silent ingestion-side coupling that could leak unverified state)

## DEC-053 — `src/ontology/book_codes.py` owns the abbrev↔BB↔display map; closes Bucket 3
- Status: Accepted
- Question: DSL `book:rom,1cor,...` directives use lowercase abbreviations; `tokens.book` stores 2-digit BB codes (DEC-026). Where does the normalization between the two forms live, and how is the future explainer's `BB → "1Cor"` reference formatting kept aligned with the executor's `"1cor" → "07"` query-build?
- Decision: A single module `src/ontology/book_codes.py` owns three module-level dicts (`_ABBREV_TO_BB`, `_BB_TO_DISPLAY`, both 27 NT books) and two helpers (`book_abbrev_to_bb`, `bb_to_display`). Both raise on unknown — silent miss is worse than "no result" per `REQ:08.apparatus-marks` discipline. The executor consumes `book_abbrev_to_bb` at WHERE-clause build time; the future explainer (Slice D+) consumes `bb_to_display` for `MatchCandidate.reference` formatting. Centralized canonicalization prevents the two directions from drifting.
- Rationale: Bucket 3 (book-id normalization) was scoped into Slice C as a prerequisite for the executor. Putting the map under `src/ontology/` (not `src/engine/`) lets Slice D's explainer reuse the same source of truth without depending on `src/engine/`. The unit test `test_canonical_07_examples_all_resolve` is the silent-miss guard: every abbreviation appearing in a canonical-07 DSL example must resolve.
- Confidence: High.
- Made-by: orchestrator-mode (low-stakes / high-confidence; mechanical mapping from MorphGNT BBCCVV ordering).
- Commit: `0eef8f5` (executor foundation, includes the new module + tests)
- Files: src/ontology/book_codes.py (NEW); tests/unit/test_book_codes.py (NEW); src/engine/executor.py (consumer)
- Spec refs: REQ:08.token-schema (consumed); REQ:09.pattern-engine (uses)
- Cross-refs: DEC-026 (BB-digit storage decision); reviews-log.md Bucket 3 (closing SHA recorded in this commit)

## DEC-054 — REQ:09.contextualization umbrella: result-set calibration is an orthogonal axis on the result envelope, not a per-match concern
- Status: Accepted
- Question: Where does result contextualization live in the canonical service-boundary spec, and what invariants does it commit to?
- Decision: A new `REQ:09.contextualization` marker lands in `docs/canonical/09_backend-service-boundaries.md` between `REQ:09.scoring-ranking` (§7) and `REQ:09.result-explainer` (§9). It encodes four invariants: (a) every result set produced with `contextualize=True` carries node-level baseline counts for every constituent node; (b) every result set carries alternative-ordering counts for the same node-set, capped at `min(N!, 24)` permutations; (c) a null-distribution slot is reserved on the envelope (always `None` in MVP); (d) the explainer must surface contextualization, not just the raw observed count. The `Contextualization` envelope hangs on `RetrievalResult` (carrier through the pipeline) and on `ExplainedResultSet` (user-facing); per-match types (`MatchCandidate`, `ScoredMatch`) are unchanged.
- Rationale: Per the design, contextualization calibrates the result *set* against alternatives — a different axis from per-match scoring. Folding it into `REQ:09.scoring-ranking` would conflate "rank within set" with "calibrate set vs alternatives." A new marker draws the boundary cleanly without amending existing scoring text. DEC-024 (corpus-is-ground-truth) makes this load-bearing: raw counts presented without baseline context invite confirmation bias the same way unverified registry entries do.
- Alternatives considered: (a) Amend `REQ:01.transparent-evidence` instead — deferred (OQ #5; revisit when explainer slice ships and user-facing wording is concrete). (b) Place under `REQ:09.scoring-ranking` — rejected; conflates two axes.
- Confidence: High.
- Made-by: orchestrator-mode (low-stakes / high-confidence per `feedback_dec_autonomy.md`; design at `thoughts/design-result-contextualization-2026-05-03.md` status: design-stable).
- Commit: `0f8b553` (D1 canonical amendment); refined by `e3d557b` (request lifecycle text) and `37ed192` (signature alignment).
- Files: docs/canonical/09_backend-service-boundaries.md (REQ marker, §8, RetrievalResult/ExplainedResultSet text blocks, request lifecycle, directory map)
- Spec refs: REQ:09.contextualization (NEW); REQ:09.retrieval-pipeline (extension); REQ:09.scoring-ranking (boundary clarified); REQ:09.result-explainer (extension)
- Cross-refs: DEC-024 (corpus-is-ground-truth); DEC-049 (registry-epistemics input-side); DEC-051 (Track 2 deferred to Slice D)

## DEC-055 — `src/retrieval/contextualization.py` is the code home (resolves design OQ #2)
- Status: Accepted
- Question: Should contextualization live under `src/scoring/` (calibration is a scoring-adjacent concern) or `src/retrieval/` (the dominant work is alternative-ordering re-entries through the retrieval pipeline)?
- Decision: `src/retrieval/contextualization.py`. Reverses the design draft's decision #3 (which paired scoring + a callback-injection pattern). Eliminates the callback by letting `contextualization` import `execute()` directly — `src/retrieval/` importing from `src/engine/` is the natural dependency direction and creates no cycle. Boundary precedent: CLAUDE.md's architecture list defines `src/retrieval/` as "Multi-stage retrieval orchestration"; alt-ordering re-entries are exactly that.
- Rationale: The dominant work is *re-running queries* (retrieval activity). The CLAUDE.md boundary calls scoring "Scoring and ranking logic" — contextualization is calibration, not ranking. Moving the home to retrieval simplifies the call graph (no callback inversion) and matches OQ #1's middle-path resolution which puts the `contextualize` flag on `retrieve()`.
- Alternatives considered: (a) `src/scoring/contextualization.py` with retrieve-fn callback — rejected per OQ #2 walkthrough; the callback is plumbing-tax for a non-existent benefit (no producer/consumer split). (b) New top-level `src/calibration/` package — rejected; CLAUDE.md's architecture list does not include one and adding a layer for a single module is over-architecture.
- Confidence: High.
- Made-by: orchestrator-mode (resolves design OQ #2; consistent with CLAUDE.md architecture).
- Commit: `1144075` (D3 introduces the file); `f0ad909` (D5 lands `contextualize()` orchestrator); `44fc697` (D6 adds the consumer).
- Files: src/retrieval/contextualization.py (NEW); src/retrieval/retrieve.py (NEW)
- Spec refs: REQ:09.contextualization (implementation home); REQ:09.retrieval-pipeline (consumer)
- Cross-refs: DEC-025 (engine ⊥ ingestion boundary preserved); DEC-054 (REQ marker)

## DEC-056 — Contextualize defaults: engine-layer `False`, API/CLI-layer `True` (resolves design OQ #1, middle path)
- Status: Accepted
- Question: Should `retrieve(contextualize=...)` default to `True` (epistemic argument: don't hide calibration from users) or `False` (test/batch determinism + cost control)?
- Decision: Middle path. The engine-layer Python function `retrieve()` defaults `contextualize=False`. UI-layer consumers (CLI today; FastAPI route when it lands) pass `contextualize=True`. The CLI in `scripts/query.py` does so explicitly.
- Rationale: Both arguments are correct in their layer. Engine-layer callers (tests, batch ETL, programmatic introspection) want determinism + cost control: contextualization re-enters the engine N≤24 times and runs N small COUNT queries, which is wasted work when the caller already knows what they want. UI-layer callers want the anti-confirmation-bias choice (DEC-024): raw counts presented without context recreate the failure mode the slice exists to prevent. Splitting the default by layer respects both.
- Alternatives considered: (a) Default `True` everywhere — rejected; engine-layer callers pay performance + non-determinism tax for no benefit. (b) Default `False` everywhere — rejected; UI users get the anti-pattern by default. (c) No default; require explicit kwarg — rejected; ergonomically painful for the dominant case (CLI) and ignores the design's epistemic stance.
- Confidence: High.
- Made-by: orchestrator-mode (resolves design OQ #1; the middle path was explicitly named in the OQ-walkthrough).
- Commit: `f0ad909` (D5 wires the defaults); `44fc697` (D6 confirms CLI-layer behavior).
- Files: src/retrieval/retrieve.py; scripts/query.py
- Spec refs: REQ:09.contextualization; REQ:09.retrieval-pipeline
- Cross-refs: DEC-024 (corpus-is-ground-truth, the epistemic argument); DEC-054 (REQ marker)

## DEC-057 — Null-distribution is a schema slot only in MVP (resolves design OQ #3)
- Status: Accepted
- Question: Ship null-distribution sampling in MVP with a fixed seed and a documented protocol, or defer entirely and ship the schema slot only?
- Decision: Defer entirely. `Contextualization.null_distribution: NullDistribution | None` exists in the schema, populated as `None` in MVP. The CLI prints "Null distribution: not computed in MVP (schema slot reserved)". A future `/research` + `/design` will define the sampling protocol (what counts as a "comparable-frequency" lemma, how comparability is bounded, how the seed propagates).
- Rationale: Sampling-based stats need their own reproducibility infrastructure (fixed seed, documented sampling protocol, edge-case handling for low-N comparability classes). Shipping that without the design pass would either produce false-precision numbers (σ on small samples) or burn slice budget on infrastructure that the user can't yet evaluate against real output. The schema slot keeps the future addition non-breaking — when null-distribution lands, it's adding a populated `NullDistribution` value to a field that already exists, not introducing a new field.
- Alternatives considered: (a) Ship sampling now with arbitrary seed — rejected; presentation concerns (false precision) bleed into the explainer's design space and need their own pass. (b) Drop the schema slot entirely — rejected; future addition would then require a breaking schema change; reserving the field is a minor cost for major future flexibility.
- Confidence: High.
- Made-by: orchestrator-mode (resolves design OQ #3; aligns with the MVP scope decision in the design's "Resolution" block).
- Commit: `cbd27b5` (D2 schema slot); `f0ad909` (D5 always-None); `44fc697` (D6 CLI rendering).
- Files: src/engine/models.py (NullDistribution + Contextualization.null_distribution); src/retrieval/contextualization.py; scripts/query.py
- Spec refs: REQ:09.contextualization (invariant (c))
- Cross-refs: DEC-054 (REQ marker)

## DEC-058 — Alternative-ordering permutation cap: enumerate full N! through N=4; for N≥5 use identity + reverse + (N−1) adjacent swaps, truncated at 24
- Status: Accepted
- Question: How does the contextualization layer cap the permutation set so engine re-entries stay bounded?
- Decision: For sequences of length N ≤ 4, enumerate all N! permutations (≤ 24, lexicographic order). For N ≥ 5, use the deterministic fallback subset = identity + reverse + (N−1) adjacent pairwise swaps, truncated at `_MAX_PERMUTATIONS = 24`. The truncation honors canonical-09 §8 invariant (b) for direct-call plans whose length exceeds the validator's supported max. `Contextualization.alternative_orderings_capped` is `True` whenever the fallback ran; consumers can show "showing 6 of 120 alternative orderings" in the explainer.
- Rationale: 4! = 24 sets a natural ceiling. N=5 → 120 permutations is too many to re-execute the engine for; the fallback gives a "neighborhood" sample (the identity, the most-distant ordering, and every adjacent reversal) that captures the most-informative siblings without combinatorial blowup. N=10 (validator max) → 11 fallback perms = 11 engine re-entries — fully bounded. The truncation handles direct-call plans bypassing the validator; in normal MVP traffic it never binds.
- Alternatives considered: (a) Cap at 6 (= 3!) — rejected; loses the N=4 full set, which is a common query shape. (b) Cap at 720 (= 6!) — rejected; engine re-entry cost is too high. (c) Use a uniformly-random subset — rejected; non-determinism is the wrong property for a calibration layer.
- Confidence: High — design decision 5 names the cap; D-D3D4-001 closure tightens the fallback to honor it for direct-call long plans.
- Made-by: orchestrator-mode (the cap value is heuristic; the shape is design-decision-anchored).
- Commit: `d48aaca` (D4 fallback shape); `d52b491` (truncation closure on D-D3D4-001).
- Files: src/retrieval/contextualization.py (`_fallback_permutations`, `_FULL_ENUMERATION_THRESHOLD`, `_MAX_PERMUTATIONS`); tests/unit/test_contextualization.py (boundary tests)
- Spec refs: REQ:09.contextualization (invariant (b))
- Cross-refs: DEC-050 (executor MVP contract — re-entry preserves the same shape gate)

## DEC-059 — Executor helpers `resolve_step_lemmas`, `build_scope_where`, `validate_plan_shape` are public (DEC-025 boundary mechanics)
- Status: Accepted
- Question: The retrieval layer needs the same step-lemma resolution, scope WHERE construction, and MVP plan-shape validation that the executor does. Should these be code-duplicated (engine-private + retrieval-private), extracted into a shared module, or promoted to public on `src/engine/executor.py`?
- Decision: Promote in place. `_resolve_step_lemmas` → `resolve_step_lemmas`, `_build_scope_where` → `build_scope_where`, `_validate_plan_shape` → `validate_plan_shape`. The functions stay in `src/engine/executor.py`; only the leading underscore is dropped. `src/retrieval/contextualization.py` imports them via the public name. No other modules consume them today.
- Rationale: All three functions are general utilities (single-step resolution; scope WHERE construction; MVP plan-shape validation), not executor-specific internals. Making them public on the engine module is the cheapest move that respects intent. Code duplication would create drift risk. Extracting to a new shared module (`src/engine/_resolution.py`) is a refactor for refactor's sake — the executor module is already the natural home.
- Alternatives considered: (a) Code-duplicate in `src/retrieval/contextualization.py` — rejected; the design's "Patterns to Follow" explicitly names DEC-025-style boundaries, and duplicating drift-prone logic across packages violates the spirit. (b) Extract to a new `src/engine/utils.py` or `src/engine/_resolution.py` — rejected; refactor without a value driver. The promoted public API can move later if the engine module grows uncomfortable.
- Confidence: High.
- Made-by: orchestrator-mode (low-stakes / high-confidence; mechanical rename).
- Commit: `1144075` (D3 introduces the rename; updates executor's internal callers and one test comment).
- Files: src/engine/executor.py (rename); tests/unit/test_executor.py (comment update)
- Spec refs: REQ:09.pattern-engine (consumer-side); REQ:09.contextualization (consumer-side); REQ:04.matching-rules (resolution rules referenced by both)
- Cross-refs: DEC-025 (boundary preserved — retrieval imports engine, not the reverse); DEC-052 (engine schema mirror — analogous pattern: shared utilities live in their natural home, mirrored only when boundaries forbid imports)

## DEC-060 — Agent-facing caller documentation lives in `docs/agent/`, separate from canonical specs
- Status: Accepted
- Question: When introducing a cookbook + prompt template designed to be the single source of truth for an LLM agent calling the system, where should the docs live? Inside `docs/canonical/` (alongside invariant specs)? In a new `docs/user/` (parallel to a future novice-doc slice)? Or in a new `docs/agent/`?
- Decision: New top-level subdirectory `docs/agent/`. Slice E lands `docs/agent/dsl-cookbook.md` and `docs/agent/prompt-template.md` there. `docs/canonical/` remains reserved for invariant contracts (REQ markers, schemas, service boundaries). `docs/user/` is reserved for the future novice-doc slice (target audience: human researcher, not an LLM agent).
- Rationale: Audience separation. Canonical docs target implementers and protect contracts via REQ markers. Agent-facing docs target LLM callers and consolidate the executable surface for fast in-context onboarding. Mixing them risks (a) cookbook drift when canonical is amended for invariant changes that do not affect what executes today and (b) REQ-marker pollution onto documentation that is descriptive rather than contractual. Three named buckets — canonical (invariants), agent (caller convenience for LLMs), user (caller convenience for humans) — keeps each artifact's purpose clean.
- Alternatives considered: (a) Single `docs/user/` shared by humans and agents — rejected; an agent reading "set up your IDE" header text is wasted context, and a human reading "your role as an LLM" is misleading. (b) Inside `docs/canonical/` as e.g. `99_agent-cookbook.md` — rejected; not invariant-shaped, would dilute REQ-marker meaning. (c) `docs/external/` umbrella — rejected; too vague.
- Confidence: High.
- Made-by: orchestrator-mode (low-stakes / high-confidence; consistent with the existing canonical-vs-governance separation).
- Commit: `63fe651` (E1 creates the directory and the cookbook skeleton). Closing SHA chain: `63fe651`..`9e08096`.
- Files: docs/agent/dsl-cookbook.md (created); docs/agent/prompt-template.md (created)
- Spec refs: (none — agent docs are descriptive, not contractual; reference-only links to REQ:02.*, REQ:06.*, REQ:09.*)
- Cross-refs: DEC-003 (NL must compile to DSL — cookbook teaches DSL, not NL bypass); DEC-006 (capability validation must be explicit and first-class); DEC-024 (corpus is ground truth — prompt template anchors the no-fabrication constraint in operational behavior)

## DEC-061 — Result explainer takes RetrievalResult (not list[ScoredMatch]); LLM-backed prose deferred to a named bucket
- Status: Accepted
- Question: Two material divergences between canonical-09 §9 and the as-shipped Slice F code: (a) the canonical signature was `explain(matches: list[ScoredMatch], ...)` but `ScoredMatch` does not exist in code (no scoring layer ships in MVP); (b) the canonical MVP-implementation note said "LLM explanation for conceptual matches" but no LLM client (anthropic/openai/etc.) is installed. How does Slice F close those divergences?
- Decision: (a) Amend canonical-09 §9 to take `RetrievalResult`. `ExplainedResult.score` becomes `float | None = None`; populated when scoring lands. (b) Slice F ships a deterministic, template-based explainer for ALL match types — including conceptual. The canonical "LLM explanation for conceptual matches" sentence is deferred to **Bucket 7** with sharpened trigger: "Slice H ships an LLM dependency for translation OR the deterministic explainer prose is judged inadequate against a real research question."
- Rationale: (a) `ScoredMatch` is vaporware; the explainer needs `MatchCandidate.alignment` (which it consumes) and `Contextualization` (which it consumes) — both already on `RetrievalResult`. Inventing a wrapper to satisfy a pre-MVP spec is cosmetic. The honest path is amending the spec to match the actual MVP pipeline. (b) Adding an LLM client solely for prose generation is overkill before the user has seen a deterministic baseline. Slice H (NL→DSL translator) is the natural home for the project's first LLM dep because translation is impossible without it; explanation is not. The bucket's trigger preserves the canonical intent ("LLM-backed prose for conceptual matches") while honoring DEC-051 / DEC-057 precedent: defer interface-dependent decisions until the runnable surface exists.
- Alternatives considered: (a-1) Invent `ScoredMatch` as a thin wrapper with `score=None`. Rejected — a one-field wrapper just to satisfy the canonical wording would require updating every caller for no behavior change. (b-1) Add the LLM dep now and ship LLM-backed conceptual prose. Rejected — adds a new dep + an entirely new test discipline (LLM output is non-deterministic; substring assertions become flaky) before the user has anything to compare against. (b-2) Strip the LLM-implementation language from canonical entirely. Rejected — would lose the canonical intent. The bucket-with-trigger preserves the option without committing the slice budget.
- Confidence: High. The deterministic explainer prose was unit-tested across 37 cases (all four alt-ordering branches, multi-verse, zero-match, capped-permutation, validation-notes pass-through, cap/wrap boundaries) before slice close. The LLM deferral is bounded by a specific trigger.
- Made-by: orchestrator-mode (low-stakes / high-confidence per `/orchestrate-slice` skill rule: choosing between two well-bounded options where canonical specs and codebase patterns clearly favor one. The LLM deferral specifically follows DEC-051 / DEC-057 precedent.).
- Commit: `62c5fd3` (F4 models with `score: float | None = None`); `5e8bf1b` (F5 deterministic explainer); `de364a8` (F7 canonical amendment).
- Files: src/engine/models.py (ExplainedResult, ExplainedResultSet); src/nlp/explainer.py (entire module); scripts/query.py (CLI integration); docs/canonical/09_backend-service-boundaries.md §9 (amendment)
- Spec refs: REQ:09.result-explainer (amended this slice)
- Cross-refs: DEC-015 (AI explains, expands, critiques — honored via deterministic templating); DEC-024 (corpus is ground truth — every prose claim is field-derived); DEC-051 (Slice C rescope precedent for "defer interface-dependent decision until runnable surface exists"); DEC-056 (default-on for UI consumers — explainer prose ON by default in CLI); DEC-057 (null-distribution = schema slot — same defer-pending-interface pattern); DEC-058 (alt-ordering cap policy — explainer reads `alternative_orderings_capped`).

## DEC-062 — `src/app/` architecture: factory pattern + lifespan-scoped resources + sync `def` handlers + `Depends()` DI
- Status: Accepted
- Question: How does the FastAPI layer obtain the `Engine` and `ConceptRegistry`? Should handlers be `async def` or `def`? Should there be a module-level `app` for `uvicorn`?
- Decision: (a) `src/app/main.py` exposes `create_app() -> FastAPI` factory + module-level `app = create_app()` for `uvicorn src.app.main:app`. (b) FastAPI `lifespan` async context manager constructs `Engine` (via `src.ingestion.db.get_engine`) and `ConceptRegistry(engine)` once at startup, stashes them on `app.state.engine` / `app.state.registry`, and calls `engine.dispose()` on shutdown. (c) `src/app/dependencies.py` exposes `get_engine(request)` / `get_concept_registry(request)` providers that read from `app.state` and raise 503 if the lifespan didn't construct them. (d) Route handlers are sync `def`, not `async def`. (e) Tests bypass the providers via `app.dependency_overrides` so unit-shape tests don't require `DATABASE_URL`. (f) Pipeline composition extracted to `src/app/orchestration.py::run_dsl_query(dsl, engine, registry) -> QueryDSLResponse` so the handler is HTTP-only.
- Rationale: (a) Factory + module-level dual export is the standard FastAPI pattern and lets each test get an isolated `app.dependency_overrides` namespace without process restart. (b) Engine construction has nontrivial cost; CLI does it once per invocation, so FastAPI does it once per process. The lifespan also gives `engine.dispose()` a guaranteed home. (c) Reading from `app.state` keeps the Depends providers thin; raising 503 when state is None makes operator misconfiguration (DATABASE_URL unset) loud. (d) All upstream code is sync (`engine.connect()`, `validate()`, `retrieve()`, `explain()`); declaring `async def` then calling sync I/O blocks the event loop, while sync handlers are correctly offloaded to FastAPI's thread pool. SQLAlchemy `Engine` is thread-safe across `connect()` calls. (e) Bypassing via `dependency_overrides` keeps the test surface DB-free without inventing a parallel app-construction path. (f) Extracting orchestration keeps the handler ≤120 lines focused on HTTP concerns; the orchestrator is unit-testable without `TestClient`.
- Alternatives considered: (a-1) No factory; only module-level `app`. Rejected — every test would mutate the same singleton's `dependency_overrides`, leaking state across tests. (b-1) Per-request engine construction. Rejected — `create_engine()` cost is wasteful per request; canonical-09's "monolith-first" framing implies process-level resource scoping. (b-2) `sessionmaker` + request-scoped session. Rejected — codebase has no `sessionmaker` anywhere; introducing one for HTTP would diverge from the established `engine.connect()` per-call pattern in `src/retrieval/`, `src/engine/executor.py`, `src/ontology/registry.py`. (d-1) `async def` handlers + `asyncpg`. Rejected — would require migrating SQLAlchemy to async-capable, rewriting executor/contextualization/retrieval; ten times the work for no Slice G value. (f-1) Inline orchestration in the handler. Rejected — couples HTTP concerns to pipeline concerns; orchestration becomes untestable without `TestClient`.
- Confidence: High. Pattern matches the FastAPI + SQLAlchemy 2.x community baseline; the design point (sync handlers + threadpool offload) is endorsed by FastAPI's own docs. The lifespan's robustness against startup-step failure was tightened in `e08fca5` (G4b checkpoint closure) per Codex finding G-G1G4-004.
- Made-by: orchestrator-mode (low-stakes / high-confidence; well-bounded options where the codebase's existing sync + engine-as-parameter pattern clearly favors the chosen path).
- Commit: `c46ca65` (G2 orchestration helper); `5fe4bd7` (G3 factory + lifespan + DI); `e08fca5` (G4b lifespan robustness fix).
- Files: src/app/main.py; src/app/dependencies.py; src/app/orchestration.py; src/app/routes/query.py (consumer)
- Spec refs: REQ:09.api-gateway (canonical-09 §1, amended in `0c85848`); REQ:09.request-lifecycle (canonical-09 — first end-to-end realization in HTTP form)
- Cross-refs: DEC-025 (engine⊥ingestion boundary — `src/app/main.py` imports `get_engine` from `src.ingestion.db`, the same carve-out CLI uses); DEC-052 (`src/engine/_schema.py` precedent for keeping cross-layer access narrow); DEC-056 (engine-default-False / API-CLI-default-True for `contextualize` — the route consumes `retrieve(contextualize=True)`).

## DEC-063 — Response envelope = `QueryDSLResponse` composing existing project models verbatim
- Status: Accepted
- Question: What does `POST /api/v1/query/dsl` return as JSON? A wrapped/re-derived schema (HTTP-specific copies of `ValidationResult`, `RetrievalResult`, `ExplainedResultSet`)? Or compose them verbatim? Should the response include scope-override request fields? Should the explainer prose be optional (`?explain=false` query param)?
- Decision: Single response model `QueryDSLResponse { query: str, validation: ValidationResult, result: RetrievalResult, explanation: ExplainedResultSet }`. All four fields always emitted. Composes the existing project models verbatim — no wrapping, no re-derivation. Request body is `QueryDSLRequest { dsl: str (min_length=1) }` — no scope-override fields. No flag to suppress the `explanation` field.
- Rationale: (a) Every wire-bound model is already frozen Pydantic v2 with full JSON round-trip coverage in `tests/unit/test_models.py` (≈20 round-trip assertions). Wrapping creates a parallel hierarchy to maintain. Canonical-09 step 11 commits to "API returns ExplainedResultSet as JSON"; including `validation` + `result` alongside is non-breaking and gives consumers the raw counts (DEC-024 transparency). (b) Scope is already populated from DSL `book:` / `lang:` constraints by the parser. Adding a parallel HTTP-side scope-override API expands slice scope without strengthening the exit gate. Defer to follow-up if a consumer asks for it. (c) The CLI's `--no-prose` is a CLI affordance for terminal-output control; service consumers who want raw can read `response.result` and ignore `response.explanation.summary`. Adding a query-param flag would split the response shape into two variants (with/without `explanation`) for no real consumer benefit.
- Alternatives considered: (a-1) Wrap each project model in an HTTP-specific copy. Rejected — duplicates ~10 model definitions for cosmetic separation. (b-1) Add `scope: ScopeConstraint | None` to `QueryDSLRequest`. Rejected — pre-MVP; would also force a merge policy with DSL-level scope constraints. (c-1) `?explain=false` query param. Rejected — proliferates response shapes. (c-2) Move `explanation` to a dedicated route `POST /api/v1/query/dsl/explain`. Rejected — would re-execute the entire pipeline, doubling cost.
- Confidence: High. The composition was verified at unit + integration level (response round-trips, dump-shape assertions, live-DB integration test confirming the documented baselines surface in JSON exactly as in the CLI).
- Made-by: orchestrator-mode (low-stakes / high-confidence; the codebase's frozen-Pydantic-v2 models are designed to compose).
- Commit: `281afaf` (G1 schemas); `37c1cda` (G5 handler binds the response model); `4ef1217` (G6 integration verifies envelope shape against real corpus).
- Files: src/app/schemas.py (QueryDSLRequest, QueryDSLResponse); src/app/routes/query.py (response_model binding); tests/unit/test_app_schemas.py; tests/integration/test_app_dsl_route.py
- Spec refs: REQ:09.api-gateway (response envelope formalized in canonical-09 §1 amendment, `0c85848`); REQ:09.request-lifecycle (step 11 "API returns ExplainedResultSet as JSON" expanded to include the wrapping envelope's siblings)
- Cross-refs: DEC-024 (corpus is ground truth — including `result` lets consumers see raw counts); DEC-061 (RetrievalResult signature for explainer — same envelope shape on the wire).

## DEC-064 — HTTP status code mapping for pipeline exceptions
- Status: Accepted
- Question: Canonical-09 specified the route surface but is silent on HTTP status codes and error envelope shape. Which HTTP status does each pipeline exception produce, and what JSON body shape do they share?
- Decision: Common envelope `ErrorResponse { error: str, message: str, details: dict | None }` returned via `raise HTTPException(status_code, detail=ErrorResponse(...).model_dump())`. Mapping table:

  | Exception / state | HTTP | `error` |
  |---|---|---|
  | `ParseError` | 422 | `parse_error` |
  | `ValidationUnsupported` (validator status="unsupported") | 422 | `validation_unsupported` |
  | `UnsupportedPlanShape` | 422 | `unsupported_plan_shape` |
  | `ConceptNotMapped` | 422 | `concept_not_mapped` |
  | `RegistryRequired` | 503 | `registry_required` |
  | Engine missing in app.state | 503 | `engine_unavailable` |
  | Registry missing in app.state | 503 | `registry_unavailable` |
  | Uncaught Exception | 500 | `internal_error` (generic message; full traceback logged server-side) |

  `partial` and `supported` validation statuses both return 200; warnings carried via `validation.findings`. New service-layer exception `ValidationUnsupported` (in `src/app/orchestration.py`) wraps validator-rejected results so the catch chain treats all failure modes uniformly. The 500 path's public message is generic — `"an unexpected error occurred"` — and the test `test_uncaught_exception_returns_500` asserts internal exception text is not leaked.

- Rationale: 422 (FastAPI convention for "request was understood but not processable") fits client-fixable issues — DSL syntax, validator rejection, executor plan-shape rejection, unmapped concept. 503 fits server-side state issues — registry not seeded / not constructed. 500 fits truly uncaught failures and must not leak internal exception text. The error envelope's `error` field is a stable machine code consumers can branch on; `details` carries error-type-specific data (parse position, concept name, plan path, finding list).
- Alternatives considered: (a) 400 for all DSL syntax / validator / executor errors. Rejected — 400 is "request was malformed at the protocol level"; 422 is the more specific Pydantic-conventional code for "body parsed fine but is semantically invalid." (b) 404 for `ConceptNotMapped` (concept-not-found-in-registry). Rejected — 404 is for URL paths; the resource here is in the request body, and 422 keeps the consumer story consistent. (c) Echo the internal exception text in the 500 message. Rejected — leaks stack traces / SQL errors / file paths to clients. (d) No common envelope; each route invents its own error shape. Rejected — proliferates schemas.
- Confidence: High. Each mapping is unit-tested in `tests/unit/test_app_routes.py::TestErrorMapping` (six cases) and four are end-to-end-tested in `tests/integration/test_app_dsl_route.py`. The 500 leak-prevention is asserted explicitly.
- Made-by: orchestrator-mode (low-stakes / high-confidence; the FastAPI / Pydantic conventions clearly favor 422 for body-semantic issues).
- Commit: `37c1cda` (G5 handler maps exceptions); `0c85848` (G7 canonical-09 §1 codifies the table).
- Files: src/app/routes/query.py; src/app/dependencies.py (engine/registry-unavailable 503); src/app/schemas.py (ErrorResponse); src/app/orchestration.py (ValidationUnsupported); docs/canonical/09_backend-service-boundaries.md §1 (status table)
- Spec refs: REQ:09.api-gateway (error envelope + status table now codified); REQ:09.request-lifecycle (step 5a "return error response with explanation" now has a concrete shape)
- Cross-refs: DEC-024 (corpus is ground truth — error responses surface the structured findings list rather than a free-form prose string); DEC-061 (defer-when-shape-not-yet-concrete precedent — these mappings became concrete only when the route landed).

## DEC-065 — Null-field emission policy: emit nullable fields as JSON `null` (resolves design OQ #6)
- Status: Accepted
- Question: When `Contextualization.null_distribution` is `None` (always-`None` in MVP per DEC-057), should the JSON response emit `"null_distribution": null` or omit the key entirely? More broadly: what is the project's Pydantic dump-shape policy for nullable fields on the wire?
- Decision: Emit nullable fields as JSON `null`. Default Pydantic v2 behavior is preserved: every `model_dump()` / `model_dump_json()` call across the codebase passes no kwargs (no `exclude_none=True`, no `exclude_defaults=True`). Verified at runtime — `Contextualization.null_distribution`, `RetrievalResult.contextualization`, `ExplainedResultSet.contextualization` and `nl_source`, `ValidationResult.grounding`, `ValidationFinding.remediation`, `ExplainedResult.score`, etc., all surface as keys with value `null` when their value is `None`.
- Rationale: (a) Zero existing call sites pass dump kwargs; introducing `exclude_none=True` here would diverge from the established pattern and require auditing every other place project models are serialized. (b) The MVP `null_distribution` is structurally always-`None`, so emit-as-null vs omit are observably equivalent until sampling lands — but the field's *presence* in the response with value `null` is informationally meaningful (it tells API consumers the schema slot exists and they can branch on `null` vs object). (c) Consumers can branch on `response.contextualization.null_distribution is None` ergonomically; key-presence checks (`'null_distribution' in response.contextualization`) are clunkier and prone to spelling bugs. (d) Symmetric with all other nullable fields project-wide — choosing exclude_none for one nullable would force the same policy everywhere, breaking round-trip equivalence with the codebase's existing JSON tests.
- Alternatives considered: (a) `exclude_none=True` per-call in `src/app/`. Rejected — diverges from project-wide pattern; consumers depending on key presence break. (b) Field-level `Field(..., exclude=)` on `null_distribution` only. Rejected — would singular-out one field with no consistency principle. (c) New project-wide policy `exclude_none=True` everywhere. Rejected — breaks ~20 existing JSON-round-trip tests in `tests/unit/test_models.py` and is a much larger commitment than this OQ warrants.
- Confidence: High. Verified by a dedicated unit test (`test_response_emits_null_for_nullable_fields` in `tests/unit/test_app_routes.py`) and an integration assertion (`tests/integration/test_app_dsl_route.py` checks `ctx["null_distribution"] is None` and that the key is present).
- Made-by: orchestrator-mode (low-stakes / high-confidence; the project's existing zero-kwargs model_dump pattern clearly indicates the policy).
- Commit: `281afaf` (G1 schemas designed without exclude_none); `0c85848` (G7 canonical-09 §1 codifies "Null-field policy").
- Files: src/app/schemas.py; src/app/routes/query.py; tests/unit/test_app_routes.py; tests/unit/test_app_schemas.py; tests/integration/test_app_dsl_route.py; docs/canonical/09_backend-service-boundaries.md §1
- Spec refs: REQ:09.api-gateway (null-field-policy paragraph)
- Cross-refs: DEC-057 (null-distribution = schema slot, always-None in MVP — DEC-065 is the wire-format companion); DEC-024 (transparency: emitting the key signals the slot's existence to consumers).

## DEC-066 — `/api/v1/health` is liveness-only; `/api/v1/capabilities` and `/api/v1/concepts` deferred
- Status: Accepted
- Question: Canonical-09 §1 names six MVP routes. Slice G's exit gate is `POST /api/v1/query/dsl`. Which other routes ship in this slice?
- Decision: (a) `GET /api/v1/health` ships as process-liveness only — returns `{"status": "ok"}` unconditionally, no DB ping, no registry-non-empty check. ~5 lines of code. (b) `GET /api/v1/capabilities` and `GET /api/v1/concepts` are explicitly deferred to a follow-up endpoint slice — not in Slice G. (c) `POST /api/v1/query/nl` is Slice H (NL→DSL translator) by prior plan. (d) `POST /api/v1/query/validate` is deferred — useful but not on Slice G's critical path.
- Rationale: (a) Health-as-liveness costs nothing and is a deployment hygiene staple (process-up signal for orchestrators). Mentioned in canonical-09 §1; deferring would be silly. (b) `capabilities` and `concepts` each require their own response-schema design (e.g., does `capabilities` expose `polarity_support: bool` directly or hide it as internal? Does `concepts` paginate? Does it filter by `verification_state`?). Each is a small but real design problem; bundling them into Slice G would expand scope without strengthening the slice's exit gate. The follow-up slice can scope them properly. (d) `query/validate` is "validate without executing" — useful for client-side what-if checks, but adds nothing the existing 422-on-unsupported path doesn't already give consumers (call `/dsl`, see the 422 + findings). Defer until a real consumer asks for the cheaper variant.
- Alternatives considered: (a-1) Defer health entirely. Rejected — the cost is trivial and orchestration tooling expects it. (a-2) Make health a deeper check (DB ping + registry-non-empty). Rejected — coupling liveness to DB availability turns transient DB blips into health-check failures, defeating the point. (b-1) Ship `capabilities` as a stub returning `CapabilityRegistry.mvp().model_dump()`. Tempting but rejected — "stub" decisions tend to set policy by accident; the actual public-vs-internal split for the capabilities response deserves its own design pass. (b-2) Ship all four routes thin. Rejected — slice budget would balloon and the exit gate (the DSL route working live against the corpus) would be deferred.
- Confidence: High for (a) — health is mechanical. High for (b)/(d) — the deferred decisions are explicit, with named follow-up.
- Made-by: orchestrator-mode (low-stakes / high-confidence; clear scope decision aligned with the slice's exit gate).
- Commit: `0d02c47` (G4 health endpoint).
- Files: src/app/routes/health.py; src/app/main.py (router registration)
- Spec refs: REQ:09.api-gateway (only 2 of 6 routes shipped this slice; remainder in follow-up + Slice H)
- Cross-refs: DEC-051 (Slice C rescope precedent: defer endpoints whose response shape isn't yet concrete); follow-up slice will scope `capabilities` / `concepts` / `query/validate` together.

## DEC-067 — `LLMClient` is a concrete class, not `typing.Protocol`
- Status: Accepted
- Question: Slice H introduces the project's first external-service abstraction. The codebase has zero `typing.Protocol` usage today (all IoC is via `monkeypatch.setattr` against module-bound imports). Should `LLMClient` be a `Protocol` (modern idiom for IoC interfaces) or a concrete base class?
- Decision: Concrete base class with one abstract method `complete(system_prompt, user_message) -> str`. Sole concrete child for MVP: `AnthropicLLMClient`. Tests stub via `MagicMock(spec=LLMClient)` or plain subclasses; production uses `app.dependency_overrides[get_llm_client]` for unit-shape and lifespan-built clients for integration.
- Rationale: (a) Project pattern is concrete classes + `monkeypatch.setattr("module.NAME", stub)` against the import-binding inside the module under test — `tests/unit/test_app_orchestration.py` is the canonical example. Introducing the first Protocol-typed seam would set a new architectural precedent without a forcing function. (b) Pydantic v2 frozen models, deterministic exception classes, and FastAPI's `Depends()` resolution all work cleanly with concrete classes; nothing in the codebase needs structural typing today. (c) Adding a second provider (OpenAI, etc.) means subclassing — no architectural change, no Protocol-vs-ABC migration cost. (d) `MagicMock(spec=LLMClient)` works identically against concrete and Protocol-typed seams; tests don't gain anything from Protocol.
- Alternatives considered: (a) `Protocol` typing. Rejected — would set a new precedent; project has zero existing Protocol usage; no concrete benefit. (b) ABC with `@abstractmethod`. Rejected — ABC plus `NotImplementedError` is what we already have; the abstractmethod decoration adds nothing the runtime doesn't already enforce.
- Confidence: High. Decision aligns with all 5 prior IoC seams in the codebase (validate, retrieve, explain, parse, plus orchestration internal stubbing).
- Made-by: orchestrator-mode (low-stakes / high-confidence; pattern match against existing IoC).
- Commit: `3c8afda` (H1 LLMClient seam).
- Files: src/nlp/llm_client.py; tests/unit/test_llm_client.py
- Spec refs: REQ:09.nl-to-dsl
- Cross-refs: DEC-052 (boundary precedent: concrete imports over abstractions); DEC-068 (live_llm marker companion to this seam).

## DEC-068 — New `live_llm` pytest marker; default `pytest` excludes it
- Status: Accepted
- Question: Slice H's exit-gate test runs against the live Anthropic API and consumes tokens. CI must not run it on every commit. What's the gating mechanism?
- Decision: New pytest marker `live_llm: tests that require ANTHROPIC_API_KEY and a live LLM API; excluded by default`. Default `addopts = "-m 'not integration and not live_llm'"`. The exit-gate test in `tests/integration/test_app_nl_route_live_llm.py` declares `pytestmark = [pytest.mark.integration, pytest.mark.live_llm]` (both markers) plus explicit env-var assertions in the fixture (`assert os.environ.get("ANTHROPIC_API_KEY")` and `assert os.environ.get("DATABASE_URL")`).
- Rationale: (a) Mirrors the `integration` + `DATABASE_URL` pattern from Slice G — same shape, same default-excluded posture, same explicit runtime assertion. (b) Default `pytest` stays runnable in CI without API tokens; live verification is opt-in with `pytest -m live_llm`. (c) Two markers (not one combined `live_or_integration`) preserves orthogonality: a future test that needs only a live LLM (no DB) can use `live_llm` alone.
- Alternatives considered: (a) `pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"))`. Rejected — tests would silently skip in CI without surfacing why; markers are more discoverable. (b) Separate `tests/live_llm/` directory with no marker. Rejected — diverges from existing `tests/{unit,integration}` structure.
- Confidence: High. Pattern proven in Slice G's `integration` marker.
- Made-by: orchestrator-mode.
- Commit: `3c8afda` (H1 pyproject.toml marker registration).
- Files: pyproject.toml; tests/integration/test_app_nl_route_live_llm.py (consumer)
- Spec refs: REQ:09.nl-to-dsl
- Cross-refs: DEC-067 (LLMClient seam — `live_llm` is its companion testing posture).

## DEC-069 — `QueryNLResponse(QueryDSLResponse)` subclass envelope
- Status: Accepted
- Question: The NL route must surface the compiled DSL string + translator metadata. Two options: (a) re-use `QueryDSLResponse` and put translator metadata in an optional sibling field; (b) define `QueryNLResponse` that wraps `QueryDSLResponse` + adds metadata.
- Decision: `class QueryNLResponse(QueryDSLResponse): translation: TranslationMetadata`. Pydantic v2 subclass that inherits the four DSL-route fields verbatim and adds one new required field. The `query` field carries the *compiled* DSL (what the corpus actually saw); the original NL query lives in the request body, not the response.
- Rationale: (a) Subclass extension is the simplest possible composition — no wrapper indirection, no second-tier `dsl_response: QueryDSLResponse` field. (b) Pydantic v2 subclasses serialize cleanly via `model_dump_json`; subclass relation enables `isinstance` checks (`isinstance(resp, QueryDSLResponse)` is True for a `QueryNLResponse`). (c) The `translation` field is required (not Optional) on the NL response — the route is contractually a *compiled* response. The DSL route's response stays unchanged. (d) FastAPI's `response_model=QueryNLResponse` correctly narrows serialization to subclass fields.
- Alternatives considered: (a) Wrapper: `QueryNLResponse{dsl_response: QueryDSLResponse, translation: TranslationMetadata}`. Rejected — adds a layer of indirection consumers must traverse for every field. (b) Add optional `translation: TranslationMetadata | None = None` to `QueryDSLResponse` directly and emit `null` on the DSL route. Rejected — pollutes the DSL response with NL-route concerns; consumers of the DSL route would have to acknowledge a perpetually-null field.
- Confidence: High. Subclass pattern is idiomatic Pydantic v2.
- Made-by: orchestrator-mode (medium-stakes; surfaced for slice review per DEC autonomy memory).
- Commit: `4448d59` (H3 schemas).
- Files: src/app/schemas.py; src/app/orchestration.py (run_nl_query assembly); tests/unit/test_app_schemas.py
- Spec refs: REQ:09.api-gateway (response envelope); REQ:09.nl-to-dsl
- Cross-refs: DEC-063 (Slice G response envelope — DEC-069 extends it).

## DEC-070 — HTTP error mapping for translator failures (canonical-09 §1 status table extension)
- Status: Accepted
- Question: Canonical-09 §1's status code table covers DSL-pipeline exceptions but is silent on LLM-side failures. Slice H must extend it. How are LLM errors classified?
- Decision: Three new rows in the §1 status code table:
  - `LLMUnavailable` (network, auth, rate-limit, 5xx server) → 503 `llm_unavailable`
  - LLM client missing (lifespan didn't construct, ANTHROPIC_API_KEY unset) → 503 `llm_unavailable`
  - Translation context missing → 503 `translation_context_unavailable`
  - `NLCompileError` (LLM output couldn't be parsed as DSL) → 422 `nl_compile_error`
  4xx anthropic.* errors (BadRequestError, NotFoundError, UnprocessableEntityError, ConflictError) propagate raw and become 500 `internal_error` — they're translator-side request bugs, not availability faults (H-H1H2-001).
- Rationale: (a) 5xx vs 4xx semantic split: 5xx means "the LLM API or our infrastructure failed; retry shortly," 4xx means "we built a bad request to the LLM API; this is a code bug." The route layer must distinguish so callers don't retry-spam on translator bugs. (b) The narrowed except chain in `AnthropicLLMClient.complete` enforces the split at the seam: only availability + auth + 5xx wrap as `LLMUnavailable`. (c) The 422 `nl_compile_error` is distinct from 422 `parse_error`: `nl_compile_error` means the LLM emitted output that couldn't be extracted as a DSL string; `parse_error` means the extracted DSL string failed the project's DSL parser. Different remediation: `nl_compile_error` → reword the NL query; `parse_error` → translator emitted DSL the parser doesn't accept (rare; would indicate a translator bug or cookbook drift).
- Alternatives considered: (a) Wrap all `anthropic.APIError` as `LLMUnavailable`. Rejected per H-H1H2-001 mid-slice review — conflates availability faults with code bugs. (b) Single `nl_route_error` umbrella code covering both translator and downstream errors. Rejected — loses signal; consumers want to distinguish "LLM gave us bad output" from "DSL pipeline rejected good output."
- Confidence: High. The 5xx/4xx split is a well-understood HTTP semantic; the `nl_compile_error` vs `parse_error` distinction is grounded in the orchestration boundary.
- Made-by: orchestrator-mode (low-stakes / high-confidence; extends an established §1 table).
- Commit: `0dda204` (H4 route handler maps exceptions); `b0f097f` (H2b narrows except chain per H-H1H2-001); `43a71e6` (H6 canonical-09 §1 codifies the new rows).
- Files: src/app/routes/nl.py; src/nlp/llm_client.py; src/nlp/translator.py; docs/canonical/09_backend-service-boundaries.md §1
- Spec refs: REQ:09.api-gateway (status table extension); REQ:09.nl-to-dsl (translator failure semantics)
- Cross-refs: DEC-064 (Slice G's status code mapping table that DEC-070 extends).

## DEC-071 — System prompt assembled at module import from `docs/agent/dsl-cookbook.md`
- Status: Accepted
- Question: Canonical-09 §2 says the LLM receives the capability + concept registry as context. Two implementation paths: (a) static system prompt assembled once at startup from the cookbook + a translator framing; (b) programmatic registry serialization injected at request time.
- Decision: Static assembly. `src/nlp/prompts/system_prompt.py` reads `docs/agent/dsl-cookbook.md` at module import and prepends a compile-only translator framing. Cached as module constant `SYSTEM_PROMPT`. Cookbook edits require app restart to take effect.
- Rationale: (a) Slice E shipped the cookbook (500 lines) specifically as the LLM-facing surface. Re-using it is the cheapest move that respects the existing investment. (b) Static prompt enables Anthropic prompt caching trivially — `cache_control` block on the system prompt + per-request user message keeps marginal cost low. (c) Cookbook drift between sessions is tolerable for MVP — the cookbook is human-curated and changes infrequently. (d) Programmatic serialization (option b) is a bigger lift: it requires designing the registry-summary schema, deciding what fraction of the registry to embed, handling growth as the registry adds rows. Premature for MVP. (e) The cookbook's "Coming Soon" / unsupported-features section is critical — it tells the LLM what NOT to emit. Re-deriving that list from the capability registry is non-trivial.
- Alternatives considered: (b) Programmatic serialization. Rejected — premature; revisit if the cookbook proves inadequate against real research questions (OQ-H1). (c) Hybrid: cookbook + small dynamic block listing currently-verified concepts. Rejected — adds complexity for marginal benefit; the cookbook's concept-registry section is already informative.
- Confidence: Medium-high. The cookbook's 500-line size is acceptable for MVP system prompts; revisit if context-window or cache-hit-rate becomes a problem.
- Made-by: orchestrator-mode (low-stakes / re-uses prior work).
- Commit: `18a8d1a` (H2 system_prompt module).
- Files: src/nlp/prompts/system_prompt.py; src/nlp/translator.py (consumer); docs/canonical/09_backend-service-boundaries.md §2 (codifies)
- Spec refs: REQ:09.nl-to-dsl
- Cross-refs: DEC-060 (Slice E agent-facing-docs directory boundary — cookbook lives in `docs/agent/`); OQ-H1 (slice review: is the static cookbook embedding sufficient?).
- Amended: 2026-05-26 (Slice M, design Decision 5): Single-shot translation remains the default and the cache-friendly base case. Multi-turn refinement is an explicit, caller-driven opt-in carried in the request body as `prior_turns`; when `prior_turns` is non-empty the translator assembles a multi-message array (system prompt unchanged and still cached per DEC-071) instead of a single user message. The server holds no conversation state between requests (proposed DEC-098). The `llm_client.py` base-class docstring now cites both DEC-071 and DEC-098. This amendment scopes "single-shot" as the default while authorizing the opt-in; it does NOT rewrite the original decision — the static cached system prompt is intact and unchanged. The opt-in is carried in the request body (not an env var) because the conversation is per-request data, not deployment config. Files: src/nlp/llm_client.py (`complete_turns` seam + docstring). Cross-refs: proposed DEC-098 (stateless echo-back; finalized in Slice M Phase M5).

## DEC-072 — No confidence-threshold gate; confidence is informational, not control
- Status: Accepted
- Question: The translator emits `confidence: float`. Should the system gate execution on a confidence threshold (reject low-confidence translations as 422)?
- Decision: No threshold gate. The translator emits its self-reported confidence; the route surfaces it in `translation.confidence`; the caller decides whether to execute, re-prompt, or display alternatives. The system never silently filters or rejects based on confidence.
- Rationale: (a) Per DEC-024 + project epistemic charter: the system tests priors, it does not pre-empt them. A confidence gate would silently substitute the system's judgment for the user's. (b) LLMs report confidence inconsistently; threshold gating would calibrate to LLM-reported values that aren't trustworthy. (c) The honest user-facing affordance is the `alternatives` list — if confidence is low, surfaces alternatives, let the caller pick. (d) Future iteration: the explainer could flag low-confidence translations in prose, but the route's HTTP response stays informational.
- Alternatives considered: (a) Reject confidence < 0.5 with 422. Rejected — silent rejection is opaque; user gets no recourse without understanding the threshold. (b) Filter alternatives by confidence. Rejected — same problem. (c) Issue a `validation.findings` warning at low confidence. Possible future addition but beyond Slice H scope; the surface today is the `confidence` value itself.
- Confidence: High. Aligns with DEC-024 and the corpus-is-ground-truth charter.
- Made-by: orchestrator-mode.
- Commit: `18a8d1a` (H2 translator); `43a71e6` (H6 canonical-09 §2 codifies).
- Files: src/nlp/translator.py; docs/canonical/09_backend-service-boundaries.md §2
- Spec refs: REQ:09.nl-to-dsl
- Cross-refs: DEC-024 (corpus is ground truth — output-side companion); H-CLOSE-003 (defaulting confidence to 0.0 on missing-from-LLM is the structural-honesty companion to "no threshold gate" — never claim certainty the LLM didn't claim).

## DEC-073 — Alternatives surfaced in response, NOT used internally for retry
- Status: Accepted
- Question: The translator returns `alternatives: list[str]` (alternative DSL interpretations). Should the system auto-execute alternatives in parallel and surface a combined result, or surface alternatives as data for the caller to inspect?
- Decision: Alternatives are surfaced verbatim in `translation.alternatives`. Each is a DSL string. The caller can re-submit any alternative via `POST /api/v1/query/dsl` if they want to explore it. The system does NOT auto-execute alternatives.
- Rationale: (a) Auto-executing alternatives silently expands the search beyond what the user asked for. (b) Alternatives are a transparency affordance, not a retry mechanism — surfacing them honors canonical-09 §2 constraint #3 ("must surface ambiguity rather than silently resolve it"). (c) Token + DB cost concerns: each alternative would multiply executor cost without user authorization. (d) The user's research workflow benefits from seeing alternatives explicitly: "here are 3 ways your question could compile to DSL; pick one and re-submit."
- Alternatives considered: (a) Auto-execute alternatives in parallel; merge result sets. Rejected — silently broadens the search. (b) Auto-execute the highest-confidence alternative if primary fails to match. Rejected — fallback chain becomes unpredictable.
- Confidence: High.
- Made-by: orchestrator-mode.
- Commit: `4448d59` (H3 schemas surface `alternatives`); `43a71e6` (H6 canonical-09 §2 codifies).
- Files: src/app/schemas.py; src/nlp/translator.py; docs/canonical/09_backend-service-boundaries.md §2
- Spec refs: REQ:09.nl-to-dsl (constraint #3 ambiguity-surfacing)
- Cross-refs: DEC-072 (companion: confidence-as-information, not control).

## DEC-074 — `LLMClient` and `TranslationContext` lifespan-scoped; `get_llm_client` provider raises 503 if state None
- Status: Accepted
- Question: Where do the `LLMClient` and `TranslationContext` instances live? When are they constructed and destroyed?
- Decision: Both are process-scoped resources constructed once during the FastAPI `lifespan` async context manager and stashed on `app.state.llm_client` / `app.state.translation_context`. Lifespan reads `ANTHROPIC_API_KEY` independently from `DATABASE_URL` — the DSL route stays serviceable when only `ANTHROPIC_API_KEY` is missing. Construction failures (e.g., import-time anthropic.Anthropic() raises) are intentionally fail-fast — the lifespan startup raises and uvicorn refuses to serve. The `get_llm_client(request)` and `get_translation_context(request)` providers raise 503 (`llm_unavailable` / `translation_context_unavailable`) when state is `None`. Tests bypass via `app.dependency_overrides`.
- Rationale: (a) Mirrors `get_engine` / `get_concept_registry` exactly (DEC-G2, Slice G). Same shape, same failure mode, same canonical-09 §1 envelope. Consistency is the point. (b) Independent degradation: missing `ANTHROPIC_API_KEY` shouldn't take the DSL route offline. The lifespan branches explicitly on each env var. (c) Fail-fast on construction errors: hiding deployment problems behind runtime 503s makes them harder to diagnose. The `try/finally` block in lifespan disposes the engine on shutdown but doesn't catch construction errors — they propagate, uvicorn refuses to start, the operator sees the actual problem (H-H3H4-001 docstring clarification).
- Alternatives considered: (a) Construct LLMClient lazily on first request. Rejected — would add cold-start latency to the first NL request, and would couple request handling to a side-effecting construction step. (b) Read ANTHROPIC_API_KEY at request time inside the route. Rejected — defeats the lifespan-scoped pattern; would re-construct the client per request. (c) Catch construction errors in lifespan and degrade to None. Rejected — masks deployment problems.
- Confidence: High. The pattern is the natural extension of Slice G's DI architecture.
- Made-by: orchestrator-mode.
- Commit: `0dda204` (H4 lifespan + providers); `e289499` (H4b independent-degradation contract clarification).
- Files: src/app/main.py (lifespan); src/app/dependencies.py (providers); src/app/routes/nl.py (consumer); docs/canonical/09_backend-service-boundaries.md §2 (codifies)
- Spec refs: REQ:09.nl-to-dsl; REQ:09.api-gateway (DI parity)
- Cross-refs: DEC-G2 (Slice G DI architecture — DEC-074 mirrors it for the LLM seam); H-H3H4-001 (independent-degradation contract clarification).

## DEC-075 — `GET /api/v1/capabilities` returns `CapabilityRegistry` directly (no envelope)
- Status: Accepted
- Question: Slice I lights up the deferred capabilities endpoint. Should the response wrap the existing `CapabilityRegistry` Pydantic model in a new envelope, or return the model itself?
- Decision: Return `CapabilityRegistry.mvp()` directly. Route declares `response_model=CapabilityRegistry`. No new schema class.
- Rationale: (a) The existing model is already a frozen Pydantic v2 with JSON-native fields (13 string/list/int/bool fields, no nested models). Wrapping invents work without value. (b) UI clients can branch on `version` for forward compat — the field is in the model itself. (c) Consistency with Slice G's design philosophy: compose existing project models verbatim, no re-derivation.
- Alternatives considered: (a) `CapabilitiesResponse{capability_registry: CapabilityRegistry}` envelope. Rejected — a one-field wrapper that consumers must traverse. (b) Flatten internal flags into a curated public-facing surface. Rejected — internal flags are honest; the UI can interpret them.
- Confidence: High.
- Made-by: orchestrator-mode.
- Commit: `d5e7681` (I1).
- Files: src/app/routes/capabilities.py; src/app/main.py; tests/unit/test_app_routes_capabilities.py
- Spec refs: REQ:09.api-gateway
- Cross-refs: DEC-063 (Slice G envelope precedent: compose existing models verbatim).

## DEC-076 — `/api/v1/concepts` flat list with embedded lemmas; no pagination at MVP scale
- Status: Accepted
- Question: Slice I lights up the concepts endpoint. Should the response embed lemma lists per concept (one round-trip) or return concept stubs that the client looks up separately (N+1)? Should it paginate?
- Decision: Flat list of `ConceptSummary{name, description, verification_state, lemma_count, lemmas: list[str]}`. Lemmas embedded inline. `lemma_count` redundant with `len(lemmas)` but kept for UI ergonomics. NO pagination at MVP scale; Bucket 9 tracks the sharpened pagination trigger.
- Rationale: (a) MVP seed has ~30 concepts × ~2-5 lemmas each = ~150 inline strings. Response payload well under 10KB. One round-trip vs N+1 is the obvious win. (b) `lemma_count` separate field lets UI render counts without traversing the array. (c) Concepts with no lemmas in the requested language are surfaced with `lemmas=[]` (not dropped) — forward-compat invariant for multi-language registry growth, locked by `test_language_filter_with_no_matches_keeps_concept_with_empty_lemmas`. (d) Pagination would add request/response complexity (cursor/offset, total count, partial pages) without benefit at MVP scale.
- Alternatives considered: (a) Paginate by default (limit/offset). Rejected — premature; Bucket 9 fires when actually needed. (b) Stub list with N+1 client lookups. Rejected — round-trip cost dominates payload size at MVP scale. (c) GraphQL-style field selection. Rejected — overkill for one endpoint.
- Confidence: High at MVP scale; Bucket 9 carries the trigger for re-evaluation.
- Made-by: orchestrator-mode.
- Commit: `43a2ca2` (I2).
- Files: src/app/routes/concepts.py; src/app/schemas.py (ConceptsResponse); src/ontology/registry.py (ConceptSummary, list_all_concepts); tests/unit/test_app_routes_concepts.py; tests/unit/test_ontology_registry.py (ConceptSummary + SQL-path tests)
- Spec refs: REQ:09.api-gateway
- Cross-refs: DEC-066 (Slice G deferral being closed); Bucket 9 (pagination trigger).

## DEC-077 — `ConceptRegistry.list_all_concepts(language)` reader; SQL aggregation in Python
- Status: Accepted
- Question: `/api/v1/concepts` needs a method that returns all concepts with their lemma lists. The existing `ConceptRegistry` has no such reader. Should aggregation happen in SQL (Postgres `array_agg`) or Python?
- Decision: Add `list_all_concepts(language: str = "grc") -> list[ConceptSummary]` that issues a single `SELECT concepts LEFT JOIN concept_lemmas ORDER BY concepts.name, concept_lemmas.lemma` and aggregates in Python. LEFT JOIN ensures concepts with no lemmas in the requested language still appear (with `lemmas=[]`). Returns `[]` on `engine=None` (consistent with the other reader methods).
- Rationale: (a) MVP scale (~30 concepts) makes Python aggregation trivial; the SQL+row processing is one-shot, not per-request critical-path. (b) `array_agg` adds Postgres-specific SQL that complicates the SQLAlchemy Core mirror; staying in vanilla SQL keeps the reader portable to SQLite for unit tests if that's ever needed. (c) Python aggregation makes the language filter trivial — drop lemmas not in the requested language while keeping the parent concept. SQL would need a more complex CASE/FILTER clause. (d) Mirrors the reader pattern of the other ConceptRegistry methods (single `engine.connect()` context, single `select(...)` with optional `where()`, list comprehension over rows).
- Alternatives considered: (a) Postgres `array_agg(concept_lemmas.lemma)`. Rejected for MVP — SQL complexity not justified by the row count. Reconsider when Bucket 9's trigger fires. (b) Two SELECTs (concepts then per-concept lemmas). Rejected — N+1 query pattern. (c) Drop concepts with no lemmas. Rejected — breaks the forward-compat invariant.
- Confidence: High at MVP scale.
- Made-by: orchestrator-mode.
- Commit: `43a2ca2` (I2 method); `786ac6c` (I3b SQL-path tests).
- Files: src/ontology/registry.py; tests/unit/test_ontology_registry.py
- Spec refs: REQ:08.registry-epistemics (registry reader extension); REQ:09.api-gateway (HTTP consumer)
- Cross-refs: DEC-076 (response shape this method feeds); I-MID-001 (Codex flag that drove the 4 SQL-path tests).

## DEC-078 — `POST /api/v1/query/validate` envelope: `QueryValidateResponse{query, validation}`
- Status: Accepted
- Question: How should the validate endpoint's response be shaped? Reuse `ValidationResult` directly, wrap it like `QueryDSLResponse`, or invent a third shape?
- Decision: New `QueryValidateResponse{query: str, validation: ValidationResult}` envelope. Mirrors `QueryDSLResponse`'s shape (echoes input + carries structured output) but omits `result` and `explanation` — neither runs on this path.
- Rationale: (a) Consistency with `/query/dsl` and `/query/nl` (both echo input via `query` field + carry structured output). UI clients have a predictable response pattern. (b) Echoing `query` is the transparency rule (DEC-024 + DEC-G7) — the response shows what was actually validated. (c) Omitting `result`/`explanation` is honest — keeping them as null fields would mislead consumers into thinking the engine ran. (d) Reusing `ValidationResult` directly (as `response_model=ValidationResult`) was tempting but loses the input echo.
- Alternatives considered: (a) `response_model=ValidationResult` (no envelope). Rejected — no input echo; consumers can't correlate response with request without round-trip context. (b) Subclass `QueryDSLResponse` with optional `result`/`explanation` fields set to null. Rejected — perpetually-null fields invite confusion. (c) Combine validate output into `QueryDSLResponse` with `executed: bool` flag. Rejected — adds a boolean to a response that should structurally not have execution data.
- Confidence: High.
- Made-by: orchestrator-mode.
- Commit: `88556be` (I3).
- Files: src/app/schemas.py; src/app/routes/validate.py; tests/unit/test_app_routes_validate.py (TestValidateNoExecutionFields locks the keys-are-exactly-{query,validation} invariant)
- Spec refs: REQ:09.api-gateway
- Cross-refs: DEC-063 (Slice G envelope philosophy); DEC-079 (HTTP semantics for this route).

## DEC-079 — `validation.status='unsupported'` returns HTTP 200 (not 422)
- Status: Accepted
- Question: When `/query/validate` reaches a validation outcome of `unsupported`, should the route translate that into a 422 (consistent with how `/query/dsl` treats validator-rejected plans) or return 200 with the verdict in the body?
- Decision: Return HTTP 200 for ALL `validation.status` values (supported, partial, unsupported). The only 422 path on `/query/validate` is `parse_error` raised on syntactically malformed DSL. Caller branches on `body.validation.status`, NOT on HTTP code, when consuming this endpoint.
- Rationale: (a) Validate's contract is "tell me everything you found" — it's a query, not a command. Returning 422 on unsupported would force consumers to handle the same information in two places (HTTP code + body) with no benefit. (b) Semantic split: HTTP error = the request itself was malformed; HTTP 200 = the request was processed and here's what we found. `unsupported` is processing output, not a malformed request. (c) The `/query/dsl` route raises `ValidationUnsupported` from `run_dsl_query` because it CAN'T proceed to execute — that's a real error in the DSL pipeline. `/query/validate` doesn't have that constraint; the validator's output IS the response. (d) Symmetric with REST best practice: GET-shaped queries return 200 with structured findings; only malformed input merits a 4xx.
- Alternatives considered: (a) 422 on unsupported, mirroring `/query/dsl`. Rejected — different semantics; consuming `/validate` differently from `/dsl` for the same DSL is the whole point. (b) New 4xx code like 419 "Validation Failed". Rejected — non-standard, surprises consumers, doesn't add information.
- Confidence: High. The contract is locked at three layers: route handler (one 422 path = ParseError only), unit test (TestValidateUnsupportedReturnsTwoHundredNotFourTwentyTwo regression guard), integration test (test_validate_unsupported_returns_200_not_422 against live registry).
- Made-by: orchestrator-mode.
- Commit: `88556be` (I3 route + helper + regression guard); `95f9eab` (I4 live regression guard).
- Files: src/app/routes/validate.py; src/app/orchestration.py (run_validate_only never raises ValidationUnsupported); tests/unit/test_app_routes_validate.py; tests/unit/test_app_orchestration.py; tests/integration/test_app_endpoint_followup.py
- Spec refs: REQ:09.api-gateway (status table extension implicit; DEC-079 distinguishes /validate from /dsl semantics)
- Cross-refs: DEC-070 (Slice H translator failure mapping — symmetric "5xx vs 4xx" reasoning applied here as "200 vs 4xx"); DEC-G6/DEC-G7 (Slice G's request-shape-is-error vs request-was-processed split).

## DEC-080 — `run_validate_only(dsl, registry)` orchestration helper
- Status: Accepted
- Question: Should the validate endpoint call `parse + validate` inline in the route handler, or factor out an orchestration helper like Slice G's `run_dsl_query` and Slice H's `run_nl_query`?
- Decision: Add `run_validate_only(dsl, registry) -> ValidationResult` to `src/app/orchestration.py`. Composes `parse + validate(plan, CapabilityRegistry.mvp(), concept_registry=registry)`. Returns the ValidationResult unchanged. Raises `ParseError` on malformed DSL; never raises `ValidationUnsupported` (DEC-079 contract).
- Rationale: (a) Mirrors `run_dsl_query` / `run_nl_query` shape — single seam where deeper-layer functions are imported, which gives unit tests a clean monkeypatch target (`monkeypatch.setattr("src.app.routes.validate.run_validate_only", boom)`). (b) Keeps the route handler thin — under 30 lines including the try/except chain. (c) Future extension: if `/query/validate` ever needs to do more than parse+validate (e.g., resolve concepts to give the caller a preview of what would execute), the helper is the place to add it without bloating the route.
- Alternatives considered: (a) Inline in route handler. Rejected — duplicates the parse/validate composition; creates two seams (the route and the imports inside the route module) that future tests would have to monkey-patch separately. (b) Reuse `run_dsl_query` and discard `result`/`explanation`. Rejected — wastes the executor and registry call for an endpoint that explicitly doesn't need them.
- Confidence: High.
- Made-by: orchestrator-mode.
- Commit: `88556be` (I3).
- Files: src/app/orchestration.py; src/app/routes/validate.py; tests/unit/test_app_orchestration.py (TestRunValidateOnly + sentinel test that retrieve/explain are NOT called)
- Spec refs: REQ:09.api-gateway
- Cross-refs: DEC-062 (Slice G factory + lifespan + DI architecture); run_dsl_query + run_nl_query precedents.

## DEC-081 — LLM as Translator: probabilistic translation at boundaries; deterministic computation throughout
- Status: Accepted
- Question: Slice J brings the LLM into a new role (driving curator actions via a conversational layer). Earlier slices have an LLM at NL→DSL translation (Slice H) and may eventually add one at result→prose rendering (Bucket 7). The agentic-publication tier (long-term-architecture vision) will put an LLM in the reader's hand. What is the project's binding rule for what an LLM may and may not do?
- Decision: **The LLM is a translator at boundaries. Computation is deterministic throughout.** Specifically:

  **What the LLM is allowed to do:**
  - Translate natural-language input into a precise computational artifact: NL→DSL (Slice H translator), NL intent → CLI subcommand invocation (Slice J1 curator agent layer), NL reader question → query against the research pool (Tier 3 agentic publication, future).
  - Translate deterministic output into human-readable prose: structured RetrievalResult → narrative prose (Slice F explainer; Bucket 7 LLM-augmented variant).
  - Suggest possibilities, ask questions, surface candidates for the human to consider.

  **What the LLM is NOT allowed to do:**
  - Render result content that is not grounded in deterministic output. Every claim in a result-shaped response must trace to a structured field. No invented cross-references, fabricated counts, or made-up theological assertions.
  - Validate concepts, mappings, or claims autonomously. Verification state transitions are gated on explicit human action (DEC-079-style; Slice J1 enforces via TTY-required `synthesize` subcommand + rationale requirement).
  - Modify code in environments outside its scope. The research-environment LLM may not write code in the tool repo; the tool-environment LLM may not perform exegesis on scripture. Cross-environment changes happen via human-mediated handoff (feedback findings + slice scoping).
  - Inject probabilistic claims into structurally factual outputs. If the LLM's contribution touches a result envelope, the contribution must be either (a) a translation of deterministic output, or (b) a clearly-marked auxiliary annotation that the consumer can ignore.

- Rationale:
  - **(a) The project's epistemic charter (DEC-024)** — "corpus is ground truth, registry entries are priors" — requires that the system's truth claims trace to corpus evidence. Probabilistic generation directly contradicts this if it enters the truth-rendering path. The LLM-as-translator boundary is what makes DEC-024 enforceable in a system that nevertheless wants to use LLMs.
  - **(b) Translation is what LLMs are good at.** They are very strong at NL ↔ structured-data conversion when the target structure is well-specified. They are weak (and dangerous) at autonomous factual claims. The boundary aligns the LLM's deployment with its actual competence.
  - **(c) Composability with future LLM-aware clients.** When the MCP server ships and an arbitrary LLM client connects (Claude Desktop, custom agents, future systems), the API surface must already enforce these boundaries — the boundaries can't depend on client cooperation. The deterministic CLI / API is the foundation; whatever LLM is in front of it must operate within the boundary by construction, not by promise.
  - **(d) Auditability and forkability.** If the LLM never writes uncontrolled content into the data layer, the system's findings are reproducible from corpus + registry + queries. A fork of the tool gets the same answers. Without this rule, findings become contingent on which LLM you used and when.
  - **(e) The cumulative-evidence model (Bucket 8 schema design) requires it.** Evidence rows are factual claims (a citation said this, a corpus pattern occurred at these positions). Allowing LLM-generated content to enter as "evidence" without provenance would corrupt the body of evidence. LLMs may *propose* evidence rows; humans (or deterministic systems) record their content.

- Alternatives considered:
  - **(a)** "Allow LLM-generated content anywhere in the system as long as it's marked as `origin: ai_suggested`." Rejected — labeling is insufficient; rendering paths that show ai_suggested content to readers as if it were factual erode the labeling over time. The boundary must be structural.
  - **(b)** "Allow LLM autonomous validation under specific high-confidence conditions (e.g., translation confidence > 0.95)." Rejected — confidence is self-reported by the LLM; the threshold becomes a knob that decays toward "trust the model." DEC-072 (Slice H) already established this for translator confidence. Same reasoning applies broadly.
  - **(c)** "Allow LLM augmentation of result content with disclaimers ('this paragraph is LLM-elaborated')." Rejected for primary rendering; *accepted* for clearly-marked auxiliary annotations that the consumer can opt into or out of. The distinction is who controls the rendering — the LLM's augmentation must be opt-in, separable, and never part of the canonical structured response.

- Confidence: High. This is a foundational constraint that should be revisited only if the project's epistemic charter (DEC-024) is itself revised.
- Made-by: orchestrator-mode in collaboration with user (Slice I close-out conversation, 2026-05-10).
- Commit: `8babb5a` (Slice J0 governance: lands DEC-081 + vision doc together).
- Files: docs/vision/long-term-architecture.md (the principle is cited in the vision doc); docs/governance/decision-log.md (this entry); future src/ enforcement points referenced when slices land.
- Spec refs: Will be cited by future REQ markers around the curator and LLM-augmented explainer. Not yet tied to a specific REQ.
- Cross-refs: DEC-003 (NL compiles to DSL, never bypass — DEC-081 generalizes), DEC-006 (system says when it cannot do something — boundary case of DEC-081), DEC-024 (corpus is ground truth — the epistemic backbone DEC-081 enforces), DEC-061 (deterministic-first explainer; LLM augmentation deferred to Bucket 7 — Bucket 7 must conform to DEC-081 if it ever ships), DEC-067 (concrete LLMClient seam — the seam where DEC-081 is enforceable), DEC-070 (HTTP error mapping for translator failures — codifies that translator errors are 5xx/4xx, not silently masked), DEC-072 (no confidence-threshold gate — companion: no autonomous LLM authority).

## DEC-082 — Frontend stack: Nuxt 3 + Vue 3 + TypeScript + Vuetify 3 on Cloudflare Workers (personal CF account)
- Status: Accepted
- Question: What stack does the scripture-pattern-lab frontend use, and where is it deployed?
- Decision: **Nuxt 3 + Vue 3 (Composition API, `<script setup lang="ts">`) + TypeScript strict + Vuetify 3 + Cloudflare Workers (user's personal CF free-plan account).** Derived in scaffolding terms from TovutiLMS/pattern-mapping but with all hub coupling stripped and zero deployment in Tovuti infrastructure. The frontend lives in its own GitHub repo (`scripture-pattern-lab-web` — see DEC-088) under the user's personal account.
- Rationale: (a) Nuxt's Nitro server layer is the structural seam for the inter-service proxy (DEC-083) — same-origin in the browser, server-only secrets. SPA + browser-direct alternatives require CORS on the backend (which we explicitly forbid, DEC-090's predecessor) and ship the bearer token client-side (security failure). (b) Vuetify 3 ships a comprehensive Material component library + theme system with built-in light/dark; speed-to-MVP without a design-system tax. The aesthetic is consciously deferred for rebrand if/when it bites (no DEC; tracked as a polish backlog). (c) TypeScript strict mirrors the backend's Python type-hint discipline. (d) Cloudflare Workers free plan covers research-tool traffic; *.workers.dev gives a working URL without buying a domain.
- Alternatives considered: (a) SvelteKit on CF Workers. Rejected — smaller ecosystem, user familiarity favors Vue. (b) Plain Vite + Vue SPA. Rejected — browser-direct-to-FastAPI requires CORS + client-side bearer token; both fail the security boundary. (c) Next.js on Vercel. Rejected — Vercel costs vs. CF free; React vs. Vue is orthogonal. (d) Tovuti App Hub deployment. Rejected — the project is personal/forkable (vision doc Tier 1); coupling it to employer infrastructure creates IP and continuity risks.
- Confidence: High. Stack choice was deliberated extensively pre-slice; user confirmed each piece.
- Made-by: orchestrator-mode in collaboration with user (Slice J1 pre-slice conversation, 2026-05-22).
- Commit: `09ebd24` (Slice J1 Phase J1.1).
- Files: web/package.json, web/nuxt.config.ts, web/vuetify.config.ts, web/wrangler.toml, web/tsconfig.json, web/eslint.config.mjs, web/app.vue, web/layouts/default.vue, web/composables/useThemeToggle.ts, web/.github/workflows/deploy.yml.
- Spec refs: None (frontend is a consumer of canonical-09 §1 routes).
- Cross-refs: DEC-081 (LLM-as-translator — the structural reason Nuxt's server layer matters); DEC-083 (Nitro proxy); DEC-088 (repo separation).

## DEC-083 — Nitro server proxy at `/api/sp/*`: browser never sees backend URL or bearer token
- Status: Accepted
- Question: How does the browser communicate with the Render-hosted FastAPI backend? Direct (with CORS + client-side token) or via a server-side proxy in the Worker?
- Decision: **Nuxt's Nitro server layer proxies every backend call through `/api/sp/*` routes on the Worker.** The browser only makes same-origin requests to the Worker; the Worker holds `NUXT_BACKEND_URL` and `NUXT_BACKEND_TOKEN` as server-only secrets (via `useRuntimeConfig()`) and forwards JSON POSTs with `Authorization: Bearer <token>` to Render. Upstream responses (success + error envelopes) pass through unchanged so the frontend dispatches UI off `body.detail.error` consistently.
- Rationale: (a) Backend bearer token never reaches the browser — eliminates client-side token exposure entirely. (b) No CORS needed on the FastAPI service (DEC-090) — the backend can stay locked down to the Worker. (c) Pass-through error envelope means one error-handling discipline at the frontend, whether the failure originates in the proxy (`backend_unreachable`, `backend_misconfigured`) or the backend (parse_error, validation_unsupported, llm_unavailable). (d) The proxy is a discrete unit-testable seam (pure `proxyToBackend` function in `server/utils/backend.ts` with 9 Vitest tests; route handlers thin wrappers).
- Alternatives considered: (a) Browser-direct to backend with CORS + client-side token. Rejected — token exposure is a hard security failure. (b) Browser-direct to backend with cookie session. Rejected — adds an auth surface we don't need and complicates the deterministic-API story. (c) CF Service Bindings between Worker and a CF-Container-hosted backend. Rejected for MVP (DEC-084 keeps the backend on Render); door-open for future CF migration.
- Confidence: High.
- Made-by: orchestrator-mode in collaboration with user (Slice J1 pre-slice + design phase).
- Commit: `a645241` (Slice J1 Phase J1.2).
- Files: web/server/utils/backend.ts, web/server/api/sp/query/nl.post.ts, web/tests/server/backend.test.ts, web/nuxt.config.ts (runtimeConfig keys).
- Spec refs: None.
- Cross-refs: DEC-082 (Nitro is part of the stack choice); DEC-085 (bearer middleware on the receiving end); DEC-090 (no CORS); DEC-081 (proxy is the structural enforcement of "no client-side LLM").

## DEC-084 — Backend hosting: Render web service + Render Postgres
- Status: Accepted
- Question: Where does the FastAPI service + Postgres database live?
- Decision: **Render web service (Starter plan, $7/mo) + Render Postgres add-on (Basic plan, $7/mo).** First-time deploy follows `docs/runbooks/render-deploy.md`. The user's personal Render account; deployment unrelated to any employer infrastructure.
- Rationale: (a) One-vendor story is simplest at MVP — auto-deploys on git push, managed Postgres, internal DB URL routed via Render's private network. (b) Starter plan stays warm (Free plan cold-starts make the frontend feel broken). (c) FastAPI + Postgres is a well-known Render combo with no friction. (d) Cloudflare Containers (the alternative that would keep everything on CF) was evaluated and deferred: CF Containers is newer/less battle-tested, requires Workers Paid plan, and the architectural benefit (service bindings between Worker and container) doesn't materialize a meaningful difference at this scale. CF Containers stays as a documented future option (`docs/runbooks/extract-web-repo.md` and the structure outline reference the migration path).
- Alternatives considered: (a) Fly.io + Neon Postgres. Rejected — two vendors; comparable cost; Render's UX wins at this scale. (b) AWS / GCP. Rejected — over-engineered for a research tool. (c) Tovuti infrastructure. Rejected per DEC-082 reasoning. (d) Local-only / no hosting. Rejected — the slice's exit gate requires a deployed URL the user can verify.
- Confidence: High at MVP; medium long-term (CF Containers migration plausible if user gains admin or sets up own CF account container).
- Made-by: orchestrator-mode in collaboration with user (Slice J1 pre-slice conversation).
- Commit: `2d88117` (Slice J1 Phase J1.0 — runbook); future Render account creation is user-side bootstrap (Bucket J1-1).
- Files: docs/runbooks/render-deploy.md.
- Spec refs: None.
- Cross-refs: DEC-083 (the proxy talks to whatever lives at NUXT_BACKEND_URL); DEC-085 (bearer auth between Worker and Render).

## DEC-085 — Inter-service auth: bearer-token middleware on FastAPI; project-wide ErrorResponse 401 envelope
- Status: Accepted
- Question: How does the FastAPI service authenticate requests from the Worker proxy?
- Decision: **`BearerAuthMiddleware` reads `SPL_BEARER_TOKEN` from env at app-construction time. When set, every route except `GET /api/v1/health` requires `Authorization: Bearer <token>` (case-insensitive scheme per RFC 7235; `secrets.compare_digest` for constant-time comparison). 401 responses use the project-wide `ErrorResponse{error, message, details}` envelope so the Worker proxy and frontend dispatch UI off `body.detail.error` uniformly. When `SPL_BEARER_TOKEN` is unset or empty, the middleware is a no-op (preserves existing local-dev + TestClient ergonomics).** Token rotation is manual (no automated cadence in S1); the runbook documents the swap procedure.
- Rationale: (a) `/api/v1/health` is exempt because Render's healthcheck pings it without credentials; exposing it doesn't leak query semantics. (b) `secrets.compare_digest` prevents timing oracles. (c) No-op-when-unset preserves the 485 existing unit tests without modification — none of them set the env var, so the middleware doesn't fire. (d) Same `ErrorResponse` envelope as parse/validation/registry errors means the frontend `ErrorPanel` component has one dispatch surface; one rendering discipline, not two. (e) Empty-string-as-disabled is documented + logged as a WARNING (J1-CLOSE-009 closure) so a misconfigured `SPL_BEARER_TOKEN=""` doesn't silently expose all routes.
- Alternatives considered: (a) OAuth / OIDC between services. Rejected — over-engineered for two-party MVP. (b) HMAC-signed requests. Rejected — bearer + HTTPS is simpler and sufficient for the threat model (the only adversary is "someone who got the token"; HMAC adds replay protection that's not load-bearing for read-mostly traffic). (c) Mutual TLS. Rejected — Render doesn't offer easy mTLS termination. (d) IP allowlist on Render. Rejected — Cloudflare Worker egress IPs are not stable.
- Confidence: High. Threat model is "the Worker is the only legitimate client"; bearer + HTTPS + constant-time compare is the standard.
- Made-by: orchestrator-mode (low-stakes; well-established pattern).
- Commit: `2d88117` (Slice J1 Phase J1.0); `b522452` (slice-close closures, J1-CLOSE-009 log line).
- Files: src/app/auth.py, src/app/main.py, tests/unit/test_app_auth.py.
- Spec refs: None (security-implicit on canonical-09 §1 routes).
- Cross-refs: DEC-G6/DEC-G7 (HTTP error mapping discipline that 401 follows); DEC-090 (no CORS — bearer is the only auth surface).

## DEC-086 — Type generation: `openapi-typescript` from FastAPI's `/openapi.json`; generated file committed
- Status: Accepted
- Question: How does the frontend stay in sync with the backend's response shapes? Hand-typed interfaces vs. generated types?
- Decision: **`openapi-typescript` generates `web/types/backend.ts` from `${NUXT_BACKEND_URL}/openapi.json` via the `npm run gen:types` script (also wired as `prebuild` so production builds regenerate on every push). The generated file is committed so PRs visibly show schema drift.** Hand-typed interfaces (currently in place as the Slice J1 placeholder) are replaced by the generated content on first user bootstrap.
- Rationale: (a) **DEC-081 structural enforcement at the type layer.** If the backend doesn't declare a field in its OpenAPI schema, the frontend cannot import a type for it; cannot render it; cannot accidentally fabricate. The structural seam is mechanical, not disciplinary. (b) Committing the generated file means schema drift surfaces in PR diffs — a backend Pydantic change that breaks frontend assumptions is visible at review time, not at runtime. (c) Tradeoff: regeneration requires the backend's `/openapi.json` to be reachable at build time. The deploy workflow exposes `NUXT_BACKEND_URL` as a CI secret for this. (d) The Slice J1 placeholder hand-typed interfaces in `web/types/backend.ts` are wrong about a few fields (J1-CLOSE-001 closed in `b522452`); the placeholder is now structurally identical to what `openapi-typescript` will produce on first regeneration.
- Alternatives considered: (a) Hand-typed indefinitely. Rejected — DEC-081 enforcement weakens to discipline alone; drift is silent. (b) Generated but not committed. Rejected — PRs lose the schema-drift signal; first-time clones need the backend running to typecheck. (c) Generated at runtime rather than build time. Rejected — adds a runtime dependency; runtime drift would surface as errors users see, not errors developers fix.
- Confidence: High.
- Made-by: orchestrator-mode (low-stakes; well-established pattern; user signed off on the DEC-081 framing pre-slice).
- Commit: `a645241` (Slice J1 Phase J1.2: pipeline + script + placeholder); `ffc1f4f` (Phase J1.3: placeholder consumed); `b522452` (placeholder corrected to match backend Pydantic).
- Files: web/package.json (gen:types + prebuild scripts), web/types/backend.ts (placeholder; regenerated on first deploy), web/.github/workflows/deploy.yml (gen:types step).
- Spec refs: None.
- Cross-refs: DEC-081 (load-bearing constraint this DEC enforces); DEC-089 (bundle-grep is the runtime enforcement layer; this DEC is the type-layer enforcement).

## DEC-087 — Source-language rendering: self-hosted SBL Greek woff2 with `.text-grc` / `.text-heb` classes
- Status: Accepted
- Question: How does the frontend render polytonic Greek (and eventually Hebrew) text from the backend's citations?
- Decision: **`SBLGreek.woff2` is self-hosted at `web/public/fonts/SBLGreek.woff2`, loaded via `@font-face` in `web/assets/styles/globals.css`, and applied via the `.text-grc` class. A `<GreekText>` component wraps the idiom for consistency. A parallel `.text-heb` class is declared with `direction: rtl` + system-font fallback, but no Hebrew font ships in S1 (NT-only corpus).** The font file is downloaded by the user from sbl-site.org per the runbook (`web/public/fonts/README.md` documents conversion to woff2).
- Rationale: (a) Self-hosted is the right choice — third-party font CDNs are an availability dependency the project shouldn't have, and SBL Greek isn't on Google Fonts. (b) `font-display: swap` means initial paint isn't blocked by the font load. (c) The Hebrew hook exists so a future slice can drop in `SBLHebrew.woff2` without restructuring — the structural cost is one CSS rule. (d) `.text-grc` as a class (vs. setting font-family on a CSS selector that targets a specific component) lets the same class apply to any element rendering Greek — including ones the backend's `text_display` field passes through.
- Alternatives considered: (a) Cardo. Rejected — less common in scholarly publishing than SBL Greek. (b) System fonts only (Times New Roman, Greek-supporting subset). Rejected — most system Greek fonts have inconsistent polytonic diacritic support across platforms. (c) Google Fonts (Noto Sans/Serif). Rejected — runtime CDN dependency.
- Confidence: High on Greek; the Hebrew hook is intentionally provisional.
- Made-by: orchestrator-mode in collaboration with user (Slice J1 pre-slice question; user confirmed source-lang rendering from day 1).
- Commit: `09ebd24` (Slice J1 Phase J1.1 — @font-face + class declarations); `ffc1f4f` (Phase J1.3 — `<GreekText>` component + use in `ResultEnvelope.vue`). User-side bootstrap downloads the actual font file (tracked as part of Bucket J1-2).
- Files: web/assets/styles/globals.css, web/components/GreekText.vue, web/public/fonts/README.md.
- Spec refs: None.
- Cross-refs: None (orthogonal to other slice DECs).

## DEC-088 — Repo separation: `scripture-pattern-lab-web` is a separate personal GitHub repo; `web/` subdir during slice development
- Status: Accepted
- Question: Does the frontend code live in scripture-pattern-lab or in its own repo? If separate, how does it get there during slice development given the assistant's writes are scoped to the current repo?
- Decision: **Frontend code lives in a separate personal GitHub repo `scripture-pattern-lab-web` under the user's account. During Slice J1 development, the code lives in a `web/` subdir of `scripture-pattern-lab/` for sandbox-write reasons. At slice close, `docs/runbooks/extract-web-repo.md` guides the user through extraction via either `git subtree split` (preserves history) or fresh-init (drops history).** Governance (DECs, reviews-log, spec-coverage, project_status memory) stays in `scripture-pattern-lab/` because that's the canonical project repo.
- Rationale: (a) The vision doc says Tier 1 (the tool) is "generic — anyone can fork and use for their own research." Coupling the canonical Python repo to a specific frontend implementation would break that promise. The frontend is one consumer of the API; forkers should be able to take the Python repo + bring their own UI. (b) IP/ownership: the project lives in `Documents/Claude-Personal/`, signaling personal scope. The frontend repo should be personal too — not in any employer's GitHub org. (c) Continuity: if the user ever leaves Tovuti or anywhere else, the personal repo continues to exist and deploy. (d) The `web/` subdir during development is a sandbox accommodation — the assistant's writes are restricted to the current working tree. Extraction at slice close cleanly resolves this; the runbook documents both methods.
- Alternatives considered: (a) Monorepo (web/ subdir as the permanent home). Rejected — couples generic tool to specific frontend per (a) above. (b) Sibling directory creation via `dangerouslyDisableSandbox`. Rejected — the user has not authorized sandbox bypass, and the `web/` subdir + extraction pattern works cleanly within constraints. (c) Frontend repo created upfront by user, code written into it by other means. Rejected — slows iteration; the in-slice scaffold is a coherent code-complete artifact the user can extract whenever convenient.
- Confidence: High.
- Made-by: orchestrator-mode in collaboration with user (Slice J1 pre-slice + design phase).
- Commit: `09ebd24` (Slice J1 Phase J1.1: web/ subdir created); `docs/runbooks/extract-web-repo.md` documents the extraction; future user-side bootstrap will run the runbook (Bucket J1-2).
- Files: web/ (entire subdir), docs/runbooks/extract-web-repo.md.
- Spec refs: None.
- Cross-refs: DEC-082 (stack choice tied to this repo); `docs/vision/long-term-architecture.md` (Tier 1 generic / Tier 2 per-researcher framing).

## DEC-089 — DEC-081 structural enforcement: bundle-grep CI check on `.output/` for forbidden LLM SDKs
- Status: Accepted
- Question: How is DEC-081's "no LLM SDK in the frontend bundle" enforced beyond discipline?
- Decision: **`web/scripts/check-no-llm-sdk.mjs` greps `.output/` after `nuxt build` for forbidden package names (`@ai-sdk/anthropic`, `@anthropic-ai/sdk`, `google-generative-ai`) and import patterns (`from 'openai'`, `require('openai')`). CI fails the deploy if any leaks; the check is wired as `npm run check:no-llm-sdk` and runs in `.github/workflows/deploy.yml` between `nuxt build` and `wrangler deploy`.** This is the **second line of defense**; the first line is that the package never enters `package.json`. Dynamic imports with variable specifiers (e.g., `await import(someVar)`) could bypass the grep — substantive review of every dep addition remains required (documented in the script header).
- Rationale: (a) DEC-081 is too important to rely on discipline alone. The "one-line-of-code path" failure mode is exactly what structural enforcement prevents. (b) Bundle-grep at the CI layer + type-layer enforcement (DEC-086) + dependency-list scrutiny gives three layers; bypassing all three requires deliberate effort. (c) Cost: <1 second of CI time; near-zero false positive rate. (d) Tradeoff: dynamic imports with non-static specifiers escape the grep. Acknowledged in the script docstring; the structural answer is package-list review, not improved grep.
- Alternatives considered: (a) AST-based check via `acorn` or similar. Rejected — adds complexity; the package-list grep catches the realistic failure mode. (b) ESLint rule. Rejected — ESLint runs on source, not built output, and tree-shaking might still pull in code that ESLint approved. (c) Discipline-only. Rejected — DEC-081's rationale (b) explicitly cites that this fails.
- Confidence: High at the package-import level; medium against motivated bypass (which would require a code review to catch anyway).
- Made-by: orchestrator-mode (low-stakes; DEC-081 enforcement requirement is explicit).
- Commit: `09ebd24` (Slice J1 Phase J1.1 — script + CI wiring); `b522452` (Slice J1 close — script docstring expanded with second-line-of-defense framing).
- Files: web/scripts/check-no-llm-sdk.mjs, web/.github/workflows/deploy.yml, web/package.json (the `check:no-llm-sdk` script).
- Spec refs: None.
- Cross-refs: DEC-081 (the constraint this DEC enforces); DEC-086 (type-layer enforcement; complementary).

## DEC-090 — Bucket 7 closure: opt-in LLM paraphrase for conceptual-match prose; deterministic baseline preserved as default and fallback
- Status: Accepted
- Question: Bucket 7 (LLM-backed conceptual-match prose) — declared at Slice F close (DEC-061), re-deferred at Slice H close — fires by the path (b) trigger ("user explicitly authorized wiring the LLM client into the explainer's conceptual-match path"). How is the LLM client wired into the explainer without violating DEC-061's deterministic-baseline contract or DEC-081's no-fabrication clause?
- Decision: **Inject `LLMClient` via a kw-only optional argument on `explain()`**:
  - `src/nlp/explainer.py::explain(result, plan, validation, *, llm_client: LLMClient | None = None)` — backwards-compatible; the default `None` preserves existing behavior for 540 existing callers + tests.
  - When `llm_client is not None` AND a candidate has `match_type == "conceptual"`, that candidate's `ExplainedResult.explanation` is produced by `_per_candidate_prose_llm`, which calls `llm_client.complete(EXPLAINER_SYSTEM_PROMPT, build_explainer_user_message(...))`. The user message exposes ONLY grounded structured fields (verse reference, sequence label, match type, per-step lemma + node value + resolved lemmas). The LLM has no other inputs — this is the structural enforcement of DEC-081's no-fabrication clause.
  - Variant + exact match types always get the deterministic `_per_candidate_prose` helper regardless of `llm_client`. Summary, `Contextualization` baselines, alt-ordering phrases, and `validation_notes` are always deterministic — LLM augmentation touches **only** per-candidate `explanation` strings.
  - Airtight fallback: any LLM failure (`LLMUnavailable`, any other `Exception`, the LLM's explicit `FALLBACK` sentinel, or empty output) returns the deterministic prose with a WARNING log (`exc_info=True` for unexpected exceptions). The deterministic baseline is the source of truth and the airtight fallback (DEC-061 preserved).
  - The route layer opts in via the env var `SPL_EXPLAINER_LLM` (truthy: `1` or `true`, case-insensitive). The flag is read at call time inside `src/app/orchestration.py::run_nl_query`; recognized falsy values + unset default to disabled; unrecognized values log a WARNING and disable (avoid silent misconfigure exposing the LLM path).
  - The DSL surface (`run_dsl_query`) stays explicitly LLM-free. The CLI does not opt into the env flag — deterministic prose only at the CLI surface.
  - LLM output is post-truncated to 300 chars in `_truncate_llm_prose` as defense-in-depth (the system prompt requests ≤200 chars; the truncation guarantees bounded output if the LLM ignores the prompt).
  - The slice exit gate (`tests/integration/test_explainer_llm_prose_live.py::test_llm_prose_only_contains_grounded_numbers_and_refs`) is the structural DEC-081 conformance test: every digit substring and every verse-shape token in the LLM-paraphrased prose must trace to a grounded input field.
- Rationale: (a) **DEC-061 framing held**: the deterministic baseline is the source of truth + the airtight fallback. The slice does not replace deterministic prose; it adds an opt-in paraphrase layer on top. (b) **DEC-081 conformance is structural, not behavioral**: the LLM's input is restricted to grounded fields via the user message; the live-LLM exit gate asserts every number/ref in the output traces to grounded input. The LLM has no opportunity to fabricate references or counts because it has no inputs from which to fabricate. (c) **Backwards compatibility**: the kw-only optional arg keeps all 540 existing tests passing without modification. (d) **DEC-067 pattern reused**: `LLMClient` (concrete base class) is the same seam used by the translator; tests use the same stub pattern (`FakeLLMClient`, `FailingLLMClient`); no new infrastructure. (e) **Deployment safety**: env-var opt-in means deployed servers default to deterministic prose; the operator opts in deliberately. (f) **DEC-070 pattern reused**: `LLMUnavailable` is the failure-mode signal the helper catches; the broader `Exception` catch is justified by DEC-061 (the deterministic path must never fail). (g) **No new dependencies**: the slice reuses Slice H's `anthropic` client via the `LLMClient` seam.
- Alternatives considered:
  - (a) **Refactor `explain()` into a class** with constructor injection. Rejected — would break the 540 existing callers' import signature; the kw-only arg is the minimum-change pattern.
  - (b) **Always LLM-paraphrase when client is configured** (no env var). Rejected — exposes the LLM path to every NL query by default; the env var lets the operator opt in deliberately. Future slice can flip the default once user has compared deterministic vs. LLM prose against research questions.
  - (c) **LLM-paraphrase summary + baselines + alt-orderings too**. Rejected — DEC-081's no-fabrication clause is hardest to enforce on summary-level claims; restricting the LLM to per-candidate prose where every input is a token from a frozen Pydantic instance is the cleanest structural enforcement.
  - (d) **Pass the LLM client through FastAPI `Depends()`** into `explain`. Rejected — couples the explainer to FastAPI; the explainer is a pure function called by both CLI and HTTP layers. Constructor injection at the route layer is cleaner.
  - (e) **Lifespan-scoped `app.state.explainer_llm_enabled` flag** instead of env-var read at call time. Rejected for this slice — adds a new state field + provider + tests for marginal cleanliness gain. Acceptable to revisit if a second consumer of the flag emerges.
- Confidence: High. The DEC-081 conformance is structurally enforced (grounded-only user message + grounded-substring exit gate); the DEC-061 deterministic-baseline contract is preserved by the airtight fallback (4 fallback triggers cover all failure modes); 37 new unit tests + 5 live_llm tests cover the load-bearing contracts.
- Made-by: orchestrator-mode in collaboration with user (Slice K — user explicitly authorized Bucket 7 closure via path (b) at slice-start).
- Commit: `2d29076` (K.0 design review) → `b76e15e` (K.1 prompt module) → `4cb6983` (K.2 helper + fallback) → `947f1a6` (K.3 explain() signature) → `cbab605` (mid-slice closures K-MID-001 / -003 / -006) → `f2c96f9` (K.4 orchestration env-var opt-in) → `8c71b75` (K.5 live-LLM tests) → `d0244eb` (K.6 canonical + spec-coverage).
- Files: `src/nlp/explainer.py` (helpers + signature); `src/nlp/prompts/explainer_prompt.py` (NEW); `src/app/orchestration.py` (env-var read + helper); `docs/canonical/09_backend-service-boundaries.md` (REQ:09.result-explainer invariant (b)+(c)+(e) amended); `docs/governance/spec-coverage.md` (REQ:09.result-explainer row); `tests/unit/test_explainer.py` (+17 tests); `tests/unit/test_explainer_prompt.py` (NEW, 17 tests); `tests/unit/test_app_orchestration.py` (+7 tests); `tests/integration/test_explainer_llm_prose_live.py` (NEW, 5 live_llm tests).
- Spec refs: `REQ:09.result-explainer` (invariants (b), (c), (e) amended).
- Cross-refs: DEC-061 (Slice F deferral that this DEC closes; deterministic baseline preserved as default + fallback per DEC-061's framing); DEC-081 (no fabrication — structural enforcement via grounded-only user message + grounded-substring exit gate); DEC-067 (concrete LLMClient base — pattern reused); DEC-070 (HTTP error mapping for `LLMUnavailable` — fallback contract); DEC-072 (no confidence-threshold gating — applies here too: dispatch rule is `match_type == "conceptual"`, not a confidence threshold); DEC-024 (corpus-is-ground-truth — output-side companion).
- Sources: `thoughts/design-explainer-llm-prose-2026-05-23.md`; `thoughts/research-explainer-llm-prose-2026-05-23.md`; `thoughts/structure-explainer-llm-prose-2026-05-23.md`; `docs/reviews/review-claude-fallback-slice-k-design-2026-05-23.md`; `docs/reviews/review-claude-fallback-slice-k-mid-2026-05-23.md`; `docs/reviews/review-claude-fallback-slice-k-close-2026-05-23.md`. Codex blocked by `~/.codex/sessions` permission throughout the slice (Bucket 5 stays open); review pass ran as claude-fallback flavor per the established protocol.

## DEC-091 — Hosting path for the personal-lab deployment: Render Free web + Neon free Postgres + Cloudflare Workers free (Path B); deviates from runbook default Path E ($14/mo)
- Status: Accepted
- Question: Bucket J1-1 (Render deploy live verification) fires. The `docs/runbooks/render-deploy.md` runbook prescribed Render Starter ($7/mo) + Render Postgres Basic ($7/mo) = $14/mo. User asked whether the free tiers are viable for a personal-lab instance they will actually use themselves. What hosting topology does the personal-lab deploy adopt, and what runbook deltas does that imply?
- Decision: **Path B — Render Free web service + Neon free Postgres + Cloudflare Workers free = $0/mo recurring.** The web service spins down after 15 min idle (≈60s cold-start on first request after idle); Neon Postgres on free tier autosuspends but does NOT have a 30-day creation-expiry like Render's free Postgres does, so the DB persists. Backend lives at `https://scripture-pattern-lab-api.onrender.com`; Worker frontend lives at `https://scripture-pattern-lab-web.david-w-monson.workers.dev`. Region pairing: Neon us-west-2 (Oregon) ↔ Render Oregon. The ingest step deviates from the runbook: Render Free has no Shell tab (Standard+ only), so corpus + registry seed run from local with `DATABASE_URL=<neon-direct-url>` exported, using the **direct** Neon connection string. The app's runtime `DATABASE_URL` env var uses the **pooled** Neon URL (PgBouncer endpoint with `-pooler` in hostname) to avoid hitting Neon's per-connection cap when the Worker fans out.
- Rationale: (a) **Cost match to use case**: this is a personal exploration tool used episodically by one researcher. Cold-start latency is annoying but tolerable; paying $14/mo monotonically for capacity that's idle 99% of the time is not. (b) **Neon over Render free Postgres**: Render's free Postgres deletes after 30 days (creation expiry + 14-day grace = 44 days max). Verified directly from Render docs during this session. That makes Render free Postgres a 30-day trial, not a hosting option. Neon's free tier persists, autoscaling 0.25–2 CU, no creation expiry. (c) **Reversible**: the only divergence from Path E that creates lock-in is `DATABASE_URL` pointing at Neon instead of Render Postgres. Migration to Path E ($14/mo) is one env-var swap + a pg_dump/restore. (d) **No code changes required**: the runbook's commands work against Neon out-of-the-box once `DATABASE_URL` is set; the deployed FastAPI service is agnostic to which Postgres host serves the URL. (e) **The runbook's existing "Free tier idles after 90 days" warning was stale** — Render's actual policy is 30-day creation expiry, much harsher than the runbook implied. This DEC documents the correct policy; the runbook gets updated as part of the carry-over (task #7 still pending).
- Alternatives considered: (a) **Path E (runbook default)**: Render Starter $7 + Render Postgres Basic $7 = $14/mo. Rejected here as oversized for use case; rebudgetable later. (b) **Path D**: Render Starter $7 + Neon free = $7/mo. Rejected because cold-start was acceptable; if the cold-start becomes annoying in practice, upgrade to D is a single Render dashboard click. (c) **Pure Render Free (Path A)**: free web + free Postgres. Rejected on Postgres 30-day expiry alone. (d) **Cloudflare Containers + Hyperdrive**: keeps everything on CF. Rejected during research as bleeding-edge (CF Containers GA-but-young in 2026); we'd be fighting platform constraints against a well-trodden Render path. (e) **Self-host on a $5 VPS**: rejected on operational burden (patches, monitoring, Postgres tuning) for solo dev.
- Confidence: High for cost/topology fit; **medium** for cold-start tolerance (depends on actual usage patterns — first browser visit per session after >15 min idle pays the cold-start tax).
- Made-by: User (cost decision) + assistant (research on Render/Neon free-tier terms via WebSearch since render.com pricing page is a JS SPA WebFetch couldn't render).
- Commit: No code change — env-var routing only. Backend env `DATABASE_URL` = Neon pooled URL; ingest performed against Neon direct URL. Worker secrets set via `wrangler secret put NUXT_BACKEND_URL` + `NUXT_BACKEND_TOKEN`.
- Files: None modified by this decision directly. The follow-up runbook update (`docs/runbooks/render-deploy.md` — fix the stale "90-day idle" claim, add Neon-as-Postgres section, note Render Free has no Shell) is the residual work tracked as task #7 / runbook hygiene.
- Spec refs: None.
- Cross-refs: DEC-082 (stack choice tied to this repo); `docs/runbooks/render-deploy.md` (runbook this DEC documents the deviation from); `docs/runbooks/extract-web-repo.md` (frontend-side runbook, executed cleanly).

## DEC-092 — Exempt `/openapi.json` from bearer-auth middleware (matches `/api/v1/health` exemption pattern)
- Status: Accepted
- Question: Bucket J1-2 (Cloudflare Worker first deploy) CI failed at the `Generate API types from backend OpenAPI` step with HTTP 401: the bearer-auth middleware was gating `/openapi.json` and `openapi-typescript` doesn't send an Authorization header. How should the OpenAPI schema endpoint be authenticated relative to data routes?
- Decision: **Add `/openapi.json` to `BearerAuthMiddleware._EXEMPT_PATHS` (frozenset) alongside `/api/v1/health`.** Both are non-data endpoints whose request paths get matched and short-circuited before the token check. Every data-bearing route (capabilities/concepts/validate/query/dsl/query/nl) continues to require `Authorization: Bearer <token>`.
- Rationale: (a) **Convention**: OpenAPI schemas are public by design — they describe the API *shape*, not its data. Swagger UI / Redoc / openapi-typescript / IDE tooling all expect schema endpoints to be unauthenticated. Gating the schema gives no security benefit (the shape is also derivable by inspecting the Worker proxy JS bundle and observing 4xx responses) while breaking conventional tooling. (b) **CI need**: the frontend's `gen:types` step runs on every CI build to detect backend-schema drift (committed `types/backend.ts` vs. freshly-generated). Without unauthenticated access, every CI run would require carrying the bearer token, which means another GitHub Actions secret AND a more brittle CLI invocation. (c) **Exempt-set, not exempt-prefix**: the change uses an exact-path frozenset (not a prefix match), so any future endpoint with `/openapi.json` *contained* in its path doesn't accidentally inherit the exemption. (d) **Pattern reused**: `/api/v1/health` is already exempt for the same class of reason (non-data endpoint that breaks tooling if gated). Generalizing to a set is the minimum-change pattern.
- Alternatives considered: (a) **Pass the bearer token to `openapi-typescript` in CI** via its `--header "Authorization: Bearer $TOKEN"` flag, gated on `NUXT_BACKEND_TOKEN` as a new GitHub Actions secret. Rejected as more brittle (CI depends on more secrets, secret rotation requires two updates instead of one) and as backward — the *standard* posture is public schema. (b) **Disable bearer auth entirely** on Render. Rejected: the bearer auth is the only thing between the public internet and the LLM-bearing backend. (c) **Move the schema endpoint to a private path** (e.g., `/openapi.json` → `/_internal/openapi.json`) and exempt that. Rejected: gratuitous; the conventional public path is what tooling expects.
- Confidence: High. The exemption pattern is established; the schema endpoint is conventionally public; the live-LLM data path stays bearer-gated; the new unit test asserts the exemption holds when the token is configured.
- Made-by: User (chose option A in close-step decision menu) + assistant (proposed both alternatives + recommended A).
- Commit: `b9246a7` (parent repo: auth.py + main.py docstring + tests/unit/test_app_auth.py +1 test). Verified: 11/11 auth tests pass locally (`pytest tests/unit/test_app_auth.py`); `/openapi.json` returns 200 unauthenticated on the live Render service post-deploy; CI gen:types step subsequently went green.
- Files: `src/app/auth.py` (single `_HEALTH_PATH` constant → `_EXEMPT_PATHS = frozenset({"/api/v1/health", "/openapi.json"})`; docstring expansion); `src/app/main.py` (docstring update); `tests/unit/test_app_auth.py` (+1 test `test_openapi_json_always_unauthenticated`).
- Spec refs: None (no canonical REQ marker tracks the middleware exempt-set; the docstring is the authoritative description).
- Cross-refs: None.

## DEC-093 — `ScopeUnit` becomes a Pydantic v2 discriminated union; this slice ships `ScopeUnitVerse` + `ScopeUnitWindow(n)` only
- Status: Accepted (Slice L design Decision #1)
- Question: The MVP `ScopeUnit(StrEnum)` declared `token | clause | verse | sentence | pericope | chapter` but only `verse` executed; everything else was inert. To ship cross-verse proximity (`within:window(N)`) the AST needs a parametric kind that carries an integer N — a flat StrEnum cannot. What shape replaces it?
- Decision: `ScopeUnit = Annotated[Union[ScopeUnitVerse, ScopeUnitWindow], Field(discriminator="kind")]`. Two siblings ship: `ScopeUnitVerse(kind="verse")` (legacy MVP unit) and `ScopeUnitWindow(kind="window", n: int)` (cross-verse window of N tokens). Future slices that ship `clause`/`sentence`/`pericope`/`chapter` add one sibling per kind. The previously-inert StrEnum values now fail at parse time (cleaner than letting them parse into the AST and bounce at execute).
- Rationale: (a) **Pydantic v2 idiom**: discriminated unions via `Annotated[Union[...], Field(discriminator="kind")]` are the canonical shape for parametric tagged unions; type narrowing works (`isinstance(unit, ScopeUnitWindow)` → `unit.n: int`); JSON round-trips cleanly. (b) **Adding new units is local**: a future slice that ships `ScopeUnitSentence` adds one Pydantic class + one parser branch + one executor branch; no consumer-wide refactor. (c) **The previously-inert units were a footgun**: they parsed successfully but were rejected at runtime, leaving users with an unhelpful UnsupportedPlanShape rather than a parse error pointing at the offending text. Moving the rejection up to parse time is a clearer failure surface. (d) **Forward compatibility**: the chosen union shape is identical to `StepExpr`'s existing discriminator pattern — established in-codebase precedent.
- Alternatives considered: (a) **Keep StrEnum, smuggle window N through a separate field on `ScopeConstraint`** (e.g., `scope.window_n: int | None`). Rejected — couples two fields that must move together; future `ScopeUnitSentence` adding its own parametric data would expand the smuggling. (b) **Make `ScopeConstraint.unit` polymorphic via `dict | str`**. Rejected — defeats Pydantic's type-narrowing benefits. (c) **Skip the union and ship just window(N) as a string `"window:50"` with regex parsing in the validator**. Rejected — pushes parsing into a validation layer, violates the AST-as-contract pattern.
- Confidence: High. Pattern is well-established in Pydantic v2 and in this codebase (StepExpr discriminated union); test surface is small (~6 call sites touched in tests, all mechanical).
- Made-by: Design discussion 2026-05-24; orchestrator implementation 2026-05-25.
- Commit: `c814d79` (Phase 1).
- Files: `src/engine/models.py` (`ScopeUnitVerse`, `ScopeUnitWindow`, `ScopeUnit` union); `src/engine/parser.py` (parse_directives extended); `src/engine/executor.py` (validate_plan_shape accepts both kinds); tests across `test_models.py`, `test_parser.py`, `test_executor.py`, `test_validator.py`, `test_models.py`; integration test consumer updated.
- Spec refs: REQ:05.scope-constraint.
- Cross-refs: DEC-010 (typed nodes + gaps + scope in MVP DSL); DEC-013 (canonical data structured at token + scope levels); the StepExpr discriminator pattern in models.py.

## DEC-094 — Cross-verse window execution via `global_position`; `book` boundary blocks, chapter crossable; anchor on chain[0]
- Status: Accepted (Slice L design Decision #3)
- Question: Once `ScopeUnitWindow(n)` lands as an AST kind, how does the executor implement "tokens within N of each other across verse boundaries"? What address space anchors the window? Which structural boundaries are crossable?
- Decision: Executor uses `tokens.global_position` (1-based monotonic across the whole corpus, already indexed) for the window predicate. The window anchors on the first matched token (`chain[0].global_position`) and extends forward to `chain[0].gp + N` for PRECEDENCE (preserves ordering) or symmetrically to `[chain[0].gp - N, chain[0].gp + N]` for COOCCURRENCE (preserves "either direction" semantics — Codex P2 fix L-CLOSE-002). Within the window, every token must share `chain[0].book`; chapter boundaries are crossable. Book boundaries are blocked because different NT books are different authors/scrolls and crossing them produces hits that are semantically incoherent at scale.
- Rationale: (a) **`global_position` is the only existing addressing primitive that crosses verses**, already indexed (`tokens_global_position_idx`); no schema migration needed. (b) **Editorial overlay**: verses and chapters are 13th-century Stephanus-Mauricean edits; the underlying text is continuous. Letting the engine cross those boundaries reveals patterns the verse-divided view obscures. (c) **Books are genuine**: different scrolls / authors / dates; crossing them silently is an easy footgun (a hit "across" Romans-1Corinthians is not a hit). (d) **Anchor on chain[0]**: the user's pattern identity is "starting at the first match, what falls within N tokens." Floating the anchor across the chain would over-match (any contiguous N-window containing the matches would satisfy) and erase the "anchored at the lead term" semantic. (e) **Symmetric range for `~`**: ordering-free operators must see candidates in either direction; a forward-only range made `A ~ B` order-dependent in practice (Codex L-CLOSE-002).
- Alternatives considered: (a) **Add a `paragraph_id` or `pericope_id` column** to tokens. Rejected — premature schema migration; the design question "what counts as a paragraph" needs its own slice; current MorphGNT source has no such annotation. (b) **Float the window**: any contiguous N-token span containing all chain members satisfies. Rejected — too permissive; loses the "anchored at the lead term" semantic that lets users compare findings at N=20 vs N=50. (c) **Allow book crossings with a warning**: Rejected — silent surprises violate "the system must say when it cannot do something yet"; harder to explain at the result envelope than just rejecting at the executor.
- Confidence: High for global_position + anchor + book-block; **medium** for symmetric COOCCURRENCE range (open question whether a long-chain unordered query — e.g. `A ~ B ~ C ~ D` — anchored at A with N=50 produces useful results; will revisit if reports surface).
- Made-by: Design discussion 2026-05-24; orchestrator implementation 2026-05-25; Codex review surfaced the forward-only-range bug 2026-05-25 and the fix landed inline.
- Commit: `51d0c5d` (Phase 2 forward range), `6453975` (Codex closure: symmetric for COOCCURRENCE).
- Files: `src/engine/executor.py` (`_extend_chains_window_step`, `_gap_satisfied_unordered`, `_step_pair_satisfied`).
- Spec refs: REQ:05.scope-constraint, REQ:09.pattern-engine.
- Cross-refs: DEC-093 (the AST shape this DEC executes); DEC-024 (corpus-is-ground-truth — book boundaries are real).

## DEC-095 — `match_type` stays a 3-value Literal; new `proximity: ProximityInfo | None` axis is orthogonal
- Status: Accepted (Slice L design Decision #4)
- Question: A cross-verse window match has two distinct identity questions: *how* it matched (exact / variant / conceptual) and *where* it landed (verse / window=20 / window=50). Should `match_type` be widened to include a `"proximity"` value, or should a separate axis carry the where?
- Decision: `MatchCandidate.match_type` stays `Literal["exact", "variant", "conceptual"]` (DEC-007). A new optional field `proximity: ProximityInfo | None = None` carries the where-it-landed axis. `None` on every verse-scope candidate; populated on every windowed candidate. A conceptual hit at window=50 is `match_type="conceptual"` AND `proximity=ProximityInfo(window_n=50, ...)`. The two axes are orthogonal.
- Rationale: (a) **The two axes answer different questions**. *How* it matched governs lemma → concept expansion and inverse semantics (DEC-014); *where* it matched governs the scope-vs-pattern-identity tradeoff. Collapsing them loses the conceptual signal — a conceptual proximity hit would be indistinguishable from an exact one. (b) **Violates "results must distinguish match types"** (project rule from CLAUDE.md). The match_type axis is the project's load-bearing distinction for evidence quality; adding a new value to it would dilute that. (c) **Optional field is the cheap addition**: `proximity: ProximityInfo | None = None` is a single field on the existing MatchCandidate; verse-scope candidates pay zero cost.
- Alternatives considered: (a) **Add `"proximity"` to the Literal**. Rejected per rationale above. (b) **A combined `match_label` string** (e.g., `"conceptual_window50"`). Rejected — string types defeat type-narrowing and require client-side parsing. (c) **Separate response envelope for window queries**. Rejected — fragments the API into two parallel shapes.
- Confidence: High.
- Made-by: Design discussion 2026-05-24; orchestrator implementation 2026-05-25.
- Commit: `0ca1ee3` (Phase 3 ProximityInfo + MatchCandidate.proximity), `60a3239` (Phase 6 ExplainedResult.proximity mirror).
- Files: `src/engine/models.py` (ProximityInfo, MatchCandidate.proximity, ExplainedResult.proximity); `src/engine/executor.py` (`_build_proximity_infos`); `src/nlp/explainer.py` (proximity prose clause).
- Spec refs: REQ:09.pattern-engine.
- Cross-refs: DEC-007 (match-types distinguished); DEC-014 (engine supports exact/approximate/conceptual/inverse-family); DEC-024.

## DEC-096 — No NL→DSL default window; translator returns `TranslationNeedsClarification` when silence detected
- Status: Accepted (Slice L design Decision #6)
- Question: When the user's natural-language question implies cross-verse proximity ("faith and love appear near each other") but doesn't name a window size, what does the translator emit? A default (and which?), or a non-DSL "ask the user" payload?
- Decision: Translator returns a `TranslationNeedsClarification(question, suggested_windows, nl_source)` variant — a discriminated union sibling of `TranslationSuccess`. The route handler surfaces it as HTTP 200 with a `clarification` field populated and the four pipeline fields (validation / result / explanation / translation) absent. No query executes until the user picks a window. `suggested_windows` defaults to `[10, 20, 50]` (every value ≤ `window_max_tokens=50`, Codex P2 closure L-CLOSE-004).
- Rationale: (a) **Window N is part of the pattern's identity**. "faith → hope → love at N=20" is a different finding than at N=50 (Decision #4's where-axis). Silently defaulting erases that distinction. (b) **Honest signal over guessing**: CLAUDE.md's "the system must say when it cannot do something yet" applies. The translator cannot guess what window the user means; making the question explicit is the corpus-is-ground-truth answer. (c) **Auditable**: the clarification → user response → DSL chain is fully visible (NL → clarification → user-chosen N → executed DSL), unlike a silent default that the user might never realize was applied. (d) **Frontend follow-up scope**: the backend surface ships the payload now; the frontend's choice-rendering UX (inline panel vs modal) is a separate slice — tracked but not blocking.
- Alternatives considered: (a) **Default N=20** (or some other value): Rejected — see rationale. (b) **Reject the NL with 422**: Rejected — too aggressive; the question is well-formed, the system just needs one more piece of input. (c) **Let the LLM guess and surface low confidence**: Rejected — confidence is informational (DEC-072) and doesn't gate execution, so this slips a guess into the pipeline. (d) **Two-shot: translator picks a default, returns it as the only Alternative, executes**: Rejected — the user has to read the response carefully to notice the assumed window; failure mode is silent-acceptance.
- Confidence: High. The mechanism is small (one new union variant, one parser branch in `_parse_output`, one if-branch in `run_nl_query`); the failure surface is contained (translator either emits DSL or asks); the user-friction tradeoff (one extra question per silent-proximity NL) is intentional.
- Made-by: Design discussion 2026-05-24; orchestrator implementation 2026-05-25; Codex review tightened the `suggested_windows` default to honor `window_max_tokens` (L-CLOSE-004).
- Commit: `a8edce6` (Phase 5 clarification path + cookbook), `6453975` (Codex closure: defaults to [10, 20, 50]).
- Files: `src/nlp/translator.py` (TranslationSuccess + TranslationNeedsClarification union); `src/nlp/prompts/system_prompt.py` (two response shapes documented); `src/app/schemas.py` (ClarificationPayload + QueryNLResponse reshape); `src/app/orchestration.py` (short-circuit on clarification); `docs/agent/dsl-cookbook.md` (Proximity Vocabulary section).
- Spec refs: REQ:09.nl-to-dsl.
- Cross-refs: DEC-072 (confidence is informational, not control); DEC-024 (corpus-is-ground-truth); the Slice K explainer LLM dispatch precedent for opt-in LLM paths.

## DEC-097 — `~` (cooccurrence) activates in this slice with `~{m,n}` step-level gap support; abs-distance semantics
- Status: Accepted (Slice L design Decision #7)
- Question: The DSL has parsed `~` since the parser's inception (`OperatorType.COOCCURRENCE`) but execution was always rejected. Cross-verse proximity is the natural use case for "near each other, either order." Does `~` activate in this slice? Does it support `~{m,n}` step-level gap like `>{m,n}`?
- Decision: `~` activates this slice. Validator advertises `cooccurrence` in `CapabilityRegistry.operators`. Executor adds a COOCCURRENCE branch in `_step_pair_satisfied` that uses `_gap_satisfied_unordered(prev, next, gap)` — `abs(next.position - prev.position)` against the gap window. Identity (`prev == next`) is rejected. Parser extends `~` to consume an optional `LBRACE INT COMMA INT RBRACE` suffix so `lemma:πίστις ~{0,5} lemma:ἀγάπη` parses, meaning "within 5 tokens of each other, either order." Chain extension rejects any candidate whose `id` is already in the chain so patterns like `A ~ B ~ A` cannot satisfy by reusing the first A's token (Codex P2 closure L-CLOSE-003).
- Rationale: (a) **NL "near each other" naturally maps to unordered cooccurrence**; shipping window without `~` would force the translator to emit `>` for unordered phrasings, distorting intent. (b) **Gap-on-`~` is essentially free**: the parser already accepts `~`; the executor already has gap arithmetic. The marginal code is one helper (`_gap_satisfied_unordered`) and one operator-dispatch branch. (c) **Without gap support on `~`, the only tightness control for unordered queries is the outer window**, which forces a follow-up slice to revisit the same parser + executor for a one-line change. (d) **abs-distance is the unambiguous unordered semantic**: distance d between positions means d-1 tokens lie strictly between, so `~{0,5}` allows up to 5 tokens between in either direction. (e) **Identity rejection + chain-id check**: a single SELECT can return the same lemma at multiple positions; without the rejection a chain could satisfy by hitting the same token twice (degenerate match).
- Alternatives considered: (a) **Ship `~` without gap support** (`~{m,n}` raises ParseError). Rejected per rationale (c). (b) **Ship `~` with forward-only window** (anchored on chain[0], forward range only). Rejected during slice close — Codex P2 surfaced the asymmetry; the symmetric range fix (DEC-094 update) restores the unordered semantic. (c) **Defer `~` to a separate slice**. Rejected — the NL-translation slice (DEC-096) needs `~` to honor "near each other, either order"; deferring would force the translator to either emit `>` (distorts intent) or emit a clarification for every such NL.
- Confidence: High for activation + gap arithmetic; **medium** for the symmetric-range fix at scale (verified by unit tests; integration suite covers ordered windows but not ordered+unordered chains; if real queries surface fan-out problems, the inner-loop predicate is the hot spot to revisit).
- Made-by: Design discussion 2026-05-24; orchestrator implementation 2026-05-25; Codex review tightened the symmetric range (L-CLOSE-002) and chain-id check (L-CLOSE-003) inline.
- Commit: `c814d79` (Phase 1 parser ~{m,n}), `51d0c5d` (Phase 2 executor branch), `6453975` (Codex closures: symmetric range + chain-id check).
- Files: `src/engine/parser.py` (parse_operator TILDE branch with optional gap); `src/engine/executor.py` (`_gap_satisfied_unordered`, `_step_pair_satisfied`, chain-id filter); `src/validation/registry.py` (operators includes "cooccurrence").
- Spec refs: REQ:05.order-operator, REQ:09.pattern-engine.
- Cross-refs: DEC-094 (window predicate this dispatches on); DEC-007 (match types stay distinct — `~` doesn't introduce a new match_type).

## DEC-098 — Multi-turn refinement is stateless echo-back; the server holds no conversation state
- Status: Accepted (Slice M design Decision 1)
- Question: Slice L's `TranslationNeedsClarification` dead-ends — the caller gets a question but has no way to answer and continue. To close the loop (translator asks → caller answers → translator re-attempts → executes), where does the conversation state live: a server-side session store keyed by a conversation id, or echoed back by the client on each request?
- Decision: **Stateless echo-back.** The server holds no conversation state, no session id, no storage between requests. The caller re-sends the full conversation as an optional `prior_turns: list[ConversationTurn]` on each request; each request is fully self-contained. When `prior_turns` is non-empty the translator assembles a real multi-message array (system + [user(original), assistant(question), user(answer), …]) via the additive `complete_turns()` seam (DEC-071 amendment); when empty the single-shot `complete()` path is byte-identical to before. (Resolves OQ-1 in favor of a real message array over concatenating turns into one user string — turn-role fidelity; the assistant's prior question is semantically an assistant turn.)
- Rationale: (a) **Extends the house philosophy across turns**: DEC-072 (confidence is informational, caller decides) + DEC-073 (alternatives surfaced, caller re-submits) already establish "the caller drives; the server surfaces options statelessly." A refinement loop is that pattern across turns. (b) **Fits the deliberately stateless backend**: the system carries no per-request state at any layer; a session store would be the first exception. (c) **Fits the hosting**: the $0/mo Render free tier spins down when idle and has no persistent local store — server-held session state would evaporate. (d) **Cache-friendly**: the static `SYSTEM_PROMPT` prefix (DEC-071) stays byte-identical on both seams; only the per-request `messages` array grows, so the prompt-cache prefix still hits. (e) **Echo-back is cheap**: a refinement conversation is a handful of short strings.
- Alternatives considered: (a) **Server-side session store (conversation id + Redis/DB)**. Rejected — premature abstraction for a single-user MVP, contradicts the stateless design and the ephemeral free tier, and re-litigates DEC-072/073. (b) **Concatenate the conversation into one augmented user string** (keep the single-message seam). Rejected (OQ-1) — loses turn-role fidelity; the model can't cleanly separate its own prior question from the user's answer from the original query.
- Confidence: High for stateless echo-back (three existing decisions point the same way); medium-high for the message-array seam over concatenation (reversible internal detail; the cache-prefix guard test proves `system=` is identical across both seams). Codex advisory on OQ-1 was deferred to slice close because Codex was quota-blocked all session; the Claude-fallback review confirmed the seam.
- Made-by: Design discussion 2026-05-26; orchestrator implementation across M1–M5.
- Commit: `6cee834` (M2 complete_turns + DEC-071 amendment), `48707e9` (M3 translate affordance), `129747f` (M4 orchestration conversion + route).
- Files: `src/nlp/llm_client.py` (complete_turns seam + Message); `src/nlp/translator.py` (prior_turns branch + _build_turns); `src/app/orchestration.py` (ConversationTurn→Message conversion); `docs/canonical/09_backend-service-boundaries.md` §2.
- Spec refs: REQ:09.nl-to-dsl.
- Cross-refs: DEC-071 (amended — single-shot stays default, system prompt still cached); DEC-072 + DEC-073 (caller-drives philosophy this extends); DEC-099 (same route); DEC-100 (schema + shape validation); DEC-024 (corpus is ground truth — why forged turns are immaterial).

## DEC-099 — Extend the existing `POST /api/v1/query/nl` route; do not add a refinement route
- Status: Accepted (Slice M design Decision 3)
- Question: Does multi-turn refinement get a new endpoint (e.g. `POST /api/v1/query/nl/refine`), or extend the existing NL route with the optional `prior_turns` field?
- Decision: **Extend the existing route.** `prior_turns=[]` (the default) is byte-identical to today's single-shot call; a non-empty `prior_turns` is a refinement turn on the same path. No new route, no duplicated exception-mapping chain, no new proxy route.
- Rationale: (a) One envelope, one path; the request is the same shape with one optional field. (b) A `/nl/refine` route would duplicate the 8-branch exception mapping in `routes/nl.py` and the Nuxt proxy. (c) **Governance consequence**: Bucket J1-4's trigger is "before a v0.2 slice that adds additional proxy routes beyond `/api/sp/query/nl`." Extending the existing route adds no new proxy route, so J1-4 does NOT fire and stays deferred. (Had we chosen `/nl/refine`, J1-4 would have fired and scoped in.)
- Alternatives considered: (a) **New `/nl/refine` route**. Rejected — duplication + fires J1-4 for no benefit. The single-shot vs refinement distinction is data (`prior_turns` present or not), not a separate resource.
- Confidence: High.
- Made-by: Design discussion 2026-05-26; orchestrator implementation M4.
- Commit: `129747f` (M4 route + proxy passthrough).
- Files: `src/app/routes/nl.py`; `web/server/api/sp/query/nl.post.ts`.
- Spec refs: REQ:09.api-gateway.
- Cross-refs: DEC-098 (the refinement mechanism); reviews-log Bucket J1-4 (does not fire — see Slice M start triage).

## DEC-100 — `ConversationTurn` schema + deterministic conversation-shape validation + resource guards (no semantic round cap)
- Status: Accepted (Slice M design Decision 4; hardened at slice-close review)
- Question: What carries a turn on the wire, and how is a malformed conversation handled? Should there be a cap on refinement rounds?
- Decision: New frozen `ConversationTurn{role: Literal["user","assistant"], content: str(1..2000)}`. `QueryNLRequest.prior_turns: list[ConversationTurn]` defaults to `[]`, bounded `max_length=20`. A deterministic (AI-free) `@model_validator` enforces the conversation shape — `prior_turns` must begin with a user turn, strictly alternate roles, and end with an assistant turn (because `run_nl_query` appends the current `nl_query` as the next user turn) — and an aggregate content cap of 16000 characters. A malformed conversation is a clean **422**, never an Anthropic 400 that propagates to a 500 (M-CLOSE-001). The caps are **resource guards only (OQ-2 resolution), NOT a semantic round cap**: the server never decides to stop clarifying — the caller quits by not resubmitting.
- Rationale: (a) **Boundary discipline**: `ConversationTurn` is the app-schema (wire) type; `src/nlp` uses its own `Message` type and the app layer converts at the boundary (`src/nlp` never imports `src/app`, mirroring DEC-052). (b) **The shape validator closes a real 500**: without it, a schema-valid body like `[user, user]` or one not ending in an assistant turn makes the assembled array have consecutive same-role messages → Anthropic 400 → raw propagation → caller-triggerable 500 (the 4xx-propagates-raw rule from DEC-070). Catching it deterministically at request validation is honest and AI-free. (c) **Resource guards, not judgment**: `max_length=20` + per-turn 2000 + aggregate 16000 bound the per-request token cost on the metered LLM (M-CLOSE-002); they are the same category as the existing `nl_query max_length=2000`, not a "your query is too vague, giving up" gate, which DEC-072 forbids.
- Alternatives considered: (a) **No shape validation** (let Anthropic 400 → 500). Rejected — a validation-passing request must not yield an internal error. (b) **A semantic round cap** ("refuse past N rounds"). Rejected — DEC-072: confidence is informational and the caller decides when to give up; the server must not substitute its judgment. (c) **Echo `prior_turns` back in `ClarificationPayload`** (server-assembled convenience). Rejected (OQ-4 default) — the client reconstructs from what it holds; keeps stateless purity.
- Confidence: High. The validator is small and deterministic; the resource caps are generous for a real refinement conversation (original question + many short Q&A turns).
- Made-by: Design discussion 2026-05-26; orchestrator implementation M1; shape + aggregate validator added at slice-close (Claude-fallback review M-CLOSE-001/002).
- Commit: `886f487` (M1 schema), `f81c089` (slice-close validator: shape + aggregate cap).
- Files: `src/app/schemas.py` (ConversationTurn, QueryNLRequest._validate_conversation_shape, _MAX_PRIOR_TURNS_CONTENT_CHARS).
- Spec refs: REQ:09.api-gateway, REQ:09.nl-to-dsl.
- Cross-refs: DEC-098 (the refinement mechanism); DEC-070 (4xx propagates raw → why the unguarded path was a 500); DEC-072 (no judgment gate); DEC-052 (the app↔nlp boundary precedent).

## DEC-101 — Frontend multi-turn UI is out of scope for Slice M; only the proxy passthrough lands
- Status: Accepted (Slice M design Decision 6)
- Question: Does Slice M wire the multi-turn refinement UI (render the clarification, capture the answer, resubmit) into the Nuxt frontend?
- Decision: **No.** Slice M widens the Nuxt proxy zod schema to ACCEPT and forward an optional `prior_turns` array (so the contract is honest and the backend is reachable), but the multi-turn UI panel is a follow-on slice with its own design discussion.
- Rationale: The project consistently splits backend-API-first from frontend-wiring (Slice J1, Slice L's deferred frontend chip). The proxy passthrough is the minimum to keep the contract honest; full UX (rendering, answer capture, resubmit) is its own scope and would over-extend this slice.
- Alternatives considered: (a) **Build the UI now**. Rejected — over-scopes a backend-contract slice. (b) **Don't touch the proxy at all**. Rejected — the proxy would silently strip `prior_turns`, making the deployed contract a lie.
- Confidence: High.
- Made-by: Design discussion 2026-05-26; orchestrator implementation M4.
- Commit: `129747f` (M4 proxy zod passthrough).
- Files: `web/server/api/sp/query/nl.post.ts`.
- Spec refs: REQ:09.api-gateway.
- Cross-refs: DEC-099 (same route, no new proxy route → Bucket J1-4 does not fire); a future frontend-refinement slice owns the UI.
