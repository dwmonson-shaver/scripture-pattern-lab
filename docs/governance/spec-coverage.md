# Spec Coverage Tracker

Last updated: 2026-05-02 (partial — Slice A close-out plus Bucket-1 Codex remediation sweep; full table pending `/coverage` run)

## Summary
- Requirements identified: 0
- Implemented: 0 (0%)
- Tested: 0 (0%)
- Both: 0 (0%)
- Neither: 0 (0%)

> Summary numbers reflect the full canonical-doc population once `/coverage` has run. Below, partial rows are populated by hand during `/review` for the REQ markers each phase touches.

## Coverage Matrix

| Req ID | Description | Code | Test | Decision |
|--------|-------------|------|------|----------|
| REQ:08.token-schema | Database schema for the corpus token table | `data/schemas/01_tokens.sql`; `src/ingestion/corpus_parser.py` (`CorpusToken` mirrors all 12 columns); `src/ingestion/db.py` (`tokens_table` Core mirror) | `tests/unit/test_corpus_parser.py::TestParseCorpusLine::test_happy_path_field_by_field`; `tests/integration/test_corpus_ingest.py::test_schema_three_way_consistency` (live SQL ↔ mirror ↔ Pydantic) | DEC-021, DEC-026, DEC-030 |
| REQ:08.ingestion-pipeline | Steps for ingesting MorphGNT data into Postgres | `scripts/db/apply_schemas.sh` (step 4 mechanism); `src/ingestion/corpus_parser.py` (steps 2–3); `src/ingestion/loader.py` (step 4 bulk insert) | `tests/unit/test_corpus_parser.py::TestParseCorpusFile` (steps 2–3); `tests/integration/test_corpus_ingest.py::test_load_tokens_returns_219`, `test_table_row_count_is_219` (step 4 end-to-end on 3 John); `tests/integration/test_apply_schemas.py` (step 4 apply-script idempotency on fresh DB); steps 5–6 pending Slice C | DEC-021, DEC-022, DEC-023, DEC-027, DEC-028, DEC-029 |
| REQ:08.annotation-layers | Per-token surface form, lemma, morph, POS, book, chapter, verse, position | `data/schemas/01_tokens.sql`; `src/ingestion/corpus_parser.py` (all 8 layers populated by `parse_corpus_line`); `src/ingestion/loader.py` (persists all layers via Core insert) | `tests/unit/test_corpus_parser.py::TestParseCorpusLine`, `TestRealCorpusSmoke::test_3jn_first_three_lemmas`; `tests/integration/test_corpus_ingest.py::test_known_row_has_expected_lemma_and_normalized_form` (live-DB persistence) | DEC-026 |
| REQ:08.apparatus-marks | Apparatus marks preserved in `surface_form`, removed from `normalized_form`; queries target `normalized_form` or `lemma` | `data/schemas/01_tokens.sql` (no `surface_form` index); `src/ingestion/corpus_parser.py` (column-3 raw → `surface_form`, column-5 stripped → `normalized_form`) | `tests/unit/test_corpus_parser.py::TestParseCorpusFile::test_apparatus_mark_preserved_in_surface_form`; `tests/integration/test_corpus_ingest.py::test_known_row_has_expected_lemma_and_normalized_form` (asserts `"⸀" not in normalized_form` post-load) | — |
| REQ:05.node-ref | NodeRef AST model with type, value, polarity, morph_filters, negated; types include token/lemma/concept/morph/wildcard | `src/engine/models.py` (`NodeRef`, `NodeType.WILDCARD`); `src/engine/parser.py` (tokenizer emits `*` as WORD; `_parse_typed_value` handles wildcard branch) | `tests/unit/test_parser.py::TestTokenize::test_wildcard_star`; `TestParseNodeRef::test_wildcard`, `test_typed_node`, `test_polarity_*`; `TestParseSequence::test_wildcard_in_sequence` | DEC-033 |
| REQ:05.alternative-expr | AlternativeExpr (`a | b`) — set of options at one step position; supports polarity-on-parens via NodeRef-leaf distribution | `src/engine/models.py` (`AlternativeExpr`); `src/engine/parser.py` (`parse_step` polarity-LPAREN detection; module-level `_distribute_polarity` recursion) | `tests/unit/test_parser.py::TestParseAlternative` (incl. `test_polarity_distributes_to_alternative_options`, `test_minus_polarity_before_alternative`, `test_canonical_05_polarity_alternatives_sequence`) | DEC-031 |
| REQ:06.partial-reduction | Validator must produce a reduced executable plan when status=partial, dropping unsupported features rather than passing them through | `src/validation/validator.py` (`_reduce_step` recurses into AlternativeExpr/GroupExpr/OptionalExpr; `_reduce_sequence` factored out; `_reduce_plan` strips inverse + expansion) | `tests/unit/test_validator.py::TestPartialReduction` (`test_expansion_stripped`, `test_unsupported_node_inside_alternative_collapses`, `test_alternative_dropped_when_all_options_unsupported`, `test_unsupported_inside_optional_dropped`) | DEC-032 |
| REQ:09.ingestion | Corpus ingestion component (non-request-path): parse corpus files, bulk-load tokens, manage schema apply; query-side packages must not import it | `src/ingestion/corpus_parser.py`; `src/ingestion/db.py`; `src/ingestion/loader.py`; `scripts/db/apply_schemas.sh` | `tests/unit/test_corpus_parser.py`; `tests/integration/test_corpus_ingest.py`; `tests/integration/test_apply_schemas.py` | DEC-021, DEC-025, DEC-028 |

_Run `/coverage` to populate this table from `<!-- REQ:... -->` markers in `docs/canonical/`._

## Gaps

### Specced but not coded
_None tracked yet — pending `/coverage` run for full audit._

### Coded but not tested
- `REQ:08.ingestion-pipeline` step 3 cross-file — `parse_corpus_directory` is implemented but unit-tested only against single-file 3 John; cross-file `global_position` continuity and `_BOOK_NUMBER_BY_FILENAME` ordering will first be exercised by Slice B (full 27-book load). A 2-file unit test should land before scaling.
