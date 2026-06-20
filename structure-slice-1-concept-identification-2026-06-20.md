# Structure: Slice 1 — Concept Identification UI

> Vertical phases; each independently testable. Commit after each. Run
> `UV_CACHE_DIR=/tmp/uvcache uv run pytest` (unit) between phases; integration
> tests written but DATABASE_URL-gated (may not run this session). Design:
> `design-slice-1-concept-identification-2026-06-20.md` (DEC-144..150).

## Phase 1 — English translation layer (schema + ingest)
**New files:**
- `data/schemas/06_translations.sql` — `translations(id SERIAL PK, code
  VARCHAR(16) UNIQUE NOT NULL, name TEXT NOT NULL, license TEXT,
  is_public_domain BOOL NOT NULL DEFAULT false)`; `translation_verses(id SERIAL
  PK, translation_id INT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
  corpus_id VARCHAR(10) NOT NULL DEFAULT 'nt', book VARCHAR(10) NOT NULL,
  chapter INT NOT NULL, verse INT NOT NULL, text TEXT NOT NULL,
  UNIQUE(translation_id, corpus_id, book, chapter, verse))`; index
  `translation_verses_bcv_idx (translation_id, corpus_id, book, chapter, verse)`.
- `src/ingestion/translations/__init__.py`, `parser.py` — `TranslationVerse`
  (frozen Pydantic: code, name, book BB, chapter, verse, text), `parse_kjv_json(path)
  -> Iterator[TranslationVerse]` (maps a public-domain KJV JSON's book names →
  BB via book_codes), `db.py` (Core mirror + `truncate_translations`), `loader.py`
  (`load_translation(engine, code, name, license, is_public_domain, verses, *,
  progress_callback) -> int`, batched `engine.begin()` + `pg_insert ON CONFLICT`).
- `scripts/db/ingest_translation.py` — argparse `--source PATH --code kjv
  --name "King James Version" --license "Public Domain" --public-domain`,
  two-factor `--truncate` (+ `SPL_TRANSLATION_CONFIRM_TRUNCATE=1`), exit 0/1/2/3.
- `scripts/ingest/fetch_kjv.sh` — fetch a reputable PD KJV JSON from GitHub into
  `data/raw/translations/` (gitignored). Update `data/raw/README.md`.
**Test checkpoint (unit):** `tests/unit/test_translation_parser.py` — book-name→BB
mapping, verse row shape, malformed-input raise. `tests/unit/test_translation_loader.py`
— batch counts + callback (MagicMock/_FakeEngine). `tests/unit/test_ingest_translation_cli.py`
— truncate env gate, missing-file exit 3.
**Integration (gated):** `tests/integration/test_translation_ingest.py` —
ingest a known chapter; assert a known verse text round-trips.

## Phase 2 — Chapter-read API
**New:**
- `src/retrieval/reader.py` — `ChapterVerse`/`GreekToken`/`ChapterRead` Pydantic
  models; `read_chapter(engine, *, corpus_id, book_bb, chapter, version_code)
  -> ChapterRead` (one SELECT on `translation_verses` ordered by verse; one
  SELECT on `tokens` ordered by verse,position; assemble per-verse English +
  greek_tokens). `list_versions(engine) -> list[VersionInfo]`.
- `src/app/schemas.py` — `ChapterReadResponse`, `VerseRead{ref, verse,
  english_text, greek_tokens}`, `GreekTokenOut`, `VersionsResponse`,
  `VersionInfo`.
- `src/app/routes/read.py` — `GET /api/v1/read/versions`,
  `GET /api/v1/read/{corpus}/{book}/{chapter}?version=kjv`. `book` accepts an
  abbrev (book_abbrev_to_bb) — 404 `book_not_found` on KeyError, 404
  `chapter_empty` when no verses. Register in `main.py`.
**Test checkpoint (unit):** `tests/unit/test_reader.py` (MagicMock SQL path:
verse assembly, greek-token grouping by verse, empty-chapter). `tests/unit/
test_app_read_route.py` (DI 503; book-abbrev 404; happy path via stubbed reader).
**Integration (gated):** `tests/integration/test_app_read_route.py` — live read
of an ingested chapter returns English + Greek.

## Phase 3 — Concept create/edit (authored metadata)
**New/changed:**
- `data/schemas/02_concept_registry.sql` — add to `concepts`:
  `authored_color VARCHAR(9)`, `authored_polarity VARCHAR(2) CHECK(authored_polarity
  IN ('+','-','±'))`, `authored_opposite_name VARCHAR(64)` (all NULLable) + the
  DEC-146 "NEVER read as evidence" comment. (Idempotent file is re-applied;
  new installs get the columns. Carry-over note: existing DBs need ALTER — see
  last-mile.)
- `src/ontology/registry.py` — add `authored_color/authored_polarity/
  authored_opposite_name` to `concepts_table` + the `Concept`/`ConceptSummary`
  models; **fix the stale "No polarity column" comment** (DEC-146 guardrail b).
- `src/ontology/concept_editor.py` (NEW) — `create_concept(engine, *, name,
  description=None, authored_color=None, authored_polarity=None,
  authored_opposite_name=None, origin='curated') -> Concept` (`engine.begin()`
  + `pg_insert.returning`; raises `ConceptExists` on name conflict);
  `update_concept(engine, name, **fields) -> Concept` (UPDATE ... RETURNING;
  raises `ConceptNotFound`). NEVER writes polarity_claims/inverse_claims.
- `src/app/schemas.py` — `ConceptCreateRequest`, `ConceptUpdateRequest`,
  `ConceptWriteResponse`.
- `src/app/routes/concepts.py` — `POST /api/v1/concepts` (409 `concept_exists`),
  `PATCH /api/v1/concepts/{name}` (404 `concept_not_found`).
**Test checkpoint (unit):** `tests/unit/test_concept_editor.py` — create/update
shapes; **guard test: create_concept(authored_polarity='+') issues zero
INSERT/UPDATE against polarity_claims/inverse_claims** (DEC-146 guardrail c, via
statement-capture). `tests/unit/test_app_concepts_write.py` — route mapping.
**Integration (gated):** extend `tests/integration/` — create then read-back via
`GET /api/v1/concepts` shows authored fields.

## Phase 4 — Span-annotation (mark) model + CRUD
**New:**
- `data/schemas/07_marks.sql` — `marks(id SERIAL PK, corpus_id VARCHAR(10) NOT
  NULL DEFAULT 'nt', book VARCHAR(10) NOT NULL, chapter INT NOT NULL,
  verse_start INT NOT NULL, verse_end INT NOT NULL, char_start INT NOT NULL,
  char_end INT NOT NULL, version_code VARCHAR(16) NOT NULL, actor TEXT NOT NULL
  DEFAULT 'local', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at
  TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK(verse_end >= verse_start),
  CHECK(char_end > char_start))`; `mark_concepts(mark_id INT NOT NULL REFERENCES
  marks(id) ON DELETE CASCADE, concept_id INT NOT NULL REFERENCES concepts(id)
  ON DELETE CASCADE, PRIMARY KEY(mark_id, concept_id))`; index
  `marks_chapter_idx (corpus_id, book, chapter, version_code)`.
- `src/ontology/marks.py` (NEW) — `Mark`/`MarkConcept` Pydantic; `create_mark`,
  `list_marks_for_chapter`, `update_mark` (span + concept-set reassignment in
  one `engine.begin()`), `delete_mark`. Each takes `Engine`.
- `src/app/schemas.py` — `MarkCreateRequest`, `MarkUpdateRequest`, `MarkOut`,
  `MarksResponse`.
- `src/app/routes/marks.py` — `POST /api/v1/marks` (validates concepts exist,
  422 `unknown_concept`), `GET /api/v1/marks` (query: corpus/book/chapter/version),
  `PATCH /api/v1/marks/{id}` (404 `mark_not_found`), `DELETE /api/v1/marks/{id}`.
  Bearer-gated writes. Register in `main.py`.
**Test checkpoint (unit):** `tests/unit/test_marks.py` — create/list/update/delete
SQL paths (MagicMock), cross-verse span (verse_end>verse_start), concept-set
replace. `tests/unit/test_app_marks_route.py` — route mapping + DI 503.
**Integration (gated) — SLICE EXIT GATE:** `tests/integration/test_slice1_workbench.py`
— apply 06+07 → ingest a KJV chapter → create_concept → create_mark over a
cross-verse span with that concept → list_marks returns it with the concept →
read_chapter returns English+Greek for the same chapter. Collects cleanly.

## Phase 5 — Frontend reader (code-complete, interim types)
**New under `web/`** (interaction grammar from the prototype; project Vuetify
dark theme; concept color is the one rendered raw color, as content):
- `types/api.ts` — add interim hand-written aliases: `ChapterRead`, `VerseRead`,
  `GreekTokenOut`, `VersionInfo`, `ConceptSummary` (extend w/ authored fields),
  `MarkOut`, request bodies. Top-comment flags DEC-149/125 interim.
- `server/api/sp/read/[corpus]/[book]/[chapter].get.ts`, `server/api/sp/read/
  versions.get.ts`, `server/api/sp/concepts/index.get.ts`,
  `server/api/sp/concepts/index.post.ts`, `server/api/sp/concepts/[name].patch.ts`,
  `server/api/sp/marks/index.{get,post}.ts`, `server/api/sp/marks/[id].{patch,delete}.ts`
  — proxy via `server/utils/backend.ts`.
- `composables/useReader.ts` (chapter + versions + nav), `useConcepts.ts`
  (library + create/edit), `useMarks.ts` (chapter marks CRUD).
- `components/`: `ReaderBar.vue` (canon/book/chapter crumb + version switcher +
  interlinear toggle), `ChapterView.vue` (verses + highlights + greek chips),
  `SelectionPopup.vue`, `ConceptPanel.vue` (slide-over host), `ConceptLibrary.vue`,
  `ConceptEditForm.vue` (color picker + polarity seg + opposite), `MarkDetail.vue`
  (change/add/remove concept + handles), `SpanHandles.vue` (draggable,
  word-snapping, `touch-action:none`), `InterlinearChip.vue`.
- `pages/reader.vue` (or extend `index.vue`) — wires the workbench.
- Tests under `web/tests/components/` + `composables/` + `server/` mirroring the
  existing harness (mountWithVuetify; zod requestSchema tests on proxies).
**Verification:** DEFERRED (DEC-149/125) — `npm install && lint && typecheck &&
vitest && check:no-llm-sdk` is the user's last-mile. Commit code-complete with an
explicit "frontend unverified — web DoD deferred" commit message.

## Phase 6 — Governance close
- Canonical-08: `REQ:08.english-translation`, `REQ:08.span-annotations`,
  `REQ:08.concept-authoring` (with the DEC-146 evidence-firewall note).
- Canonical-09: `REQ:09.reader-api`, `REQ:09.marks-api`, `REQ:09.concept-write-api`;
  amend the §1 routes table with the new routes.
- `docs/governance/decision-log.md`: DEC-144..150.
- `docs/governance/spec-coverage.md`: rows for the 6 new markers.
- `docs/governance/reviews-log.md`: slice-close row (Codex attempt → fallback;
  Bucket-P-Codex re-defer; this slice's findings).
- Slice-close independent review artifact in `docs/reviews/`.
- `project_status.md` memory: closing SHA chain, DECs, buckets, last-mile, OWED.

## Exit gate (observable)
Backend unit suite green; `test_slice1_workbench.py` collects cleanly (live run =
last-mile). Frontend code-complete with interim types. After the last-mile
checklist (apply schemas → ingest KJV → start backend → npm run dev) the user
opens the reader on iPad and can read Romans-8-style chapter, select, mark, and
manage a concept library.
