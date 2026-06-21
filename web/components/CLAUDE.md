# components/

Auto-imported Vue components. Use these from any page, layout, or other component without an `import` statement.

## Patterns

- `<script setup lang="ts">` only; never Options API
- Define props with `defineProps<{}>()` and emits with `defineEmits<{}>()` — generic-based, no runtime declarations
- Use Vuetify components for UI primitives (`v-card`, `v-btn`, etc.); never raw `<button>` / `<div class="card">`
- Add `data-testid` attributes for stable Playwright + Vitest test targets
- For source-language text, use `<GreekText>` (lands in Phase J1.3)

## Key Files (post Phase J1.3)

- `QueryForm.vue` — textbox + Run button + loading state; emits `@run`
- `ResultEnvelope.vue` — renders compiled DSL + result + explanation + contextualization
- `ErrorPanel.vue` — renders the backend error envelope (`body.detail.error` dispatch)
- `GreekText.vue` — wraps polytonic Greek strings with `.text-grc`
- `AutoCreatedConceptNote.vue` — first-class surface for Slice N (DEC-102/104/105)
  Tier-1 auto-creation event. Renders the backend's authoritative
  "machine/lexicon-sourced — unverified — starting prior" wording verbatim,
  the pulled-in lemmas in Greek, and (when `document_available`) a link to
  `/concept/:name` (the persisted two-part Conceptual Document view).
- `ConceptDocumentView.vue` — top-level renderer for the persisted Conceptual
  Document (DEC-106 / DEC-111). Composes header + §1 + §2 + Part 2 placeholder
  in epistemic order (ground truth first).
- `ComparativeLexiconSection.vue` — §1 deterministic comparative lexicon table.
  Outlined card, green "Lexicon data" chip — visually distinct so a reader
  who skims registers this as ground truth, not commentary.
- `EducationalArticleSection.vue` — §2 LLM-generated educational prose.
  Tonal purple card, "LLM-generated commentary" chip + disclaimer alert.
  Renders prose, model label, and cited sources. DEC-081: prose is **rendered,
  not generated** here — the backend generates and persists it.
- `Tier2GroupingPlaceholder.vue` — Part 2 stub; renders a "not yet built"
  card until the Tier-2 curator slice lands.

### Slice 1 — concept-identification reader (DEC-149)

- `ReaderBar.vue` — sticky `v-toolbar` (NOT a `v-app-bar` — that's layout
  chrome): canon / book / chapter selectors, version switcher, the Versed /
  Continuous **mode** toggle (`v-btn-toggle`, `v-model:mode`), and the
  interlinear toggle. The interlinear toggle hides when the corpus has no
  original language (per-corpus `CORPUS_META`; NT = Greek). `v-model:*` per
  control, `@prev` / `@next` for chapter arrows.
- `ChapterView.vue` — the reading pane. Study-edition (DEC-152): illuminated
  chapter opening (rubric book label, display chapter numeral, gilt rule),
  gilt versal drop-cap on the opening verse's first letter (via
  `.verse--opening .verse-text::first-letter` so mark segmentation is
  untouched), serif scripture body (`--font-read`), rubric verse numbers.
  Concept-highlighted `<mark>` spans use the spec `.cm` multiply-blend
  marker-stroke keyed off a `--c` custom property; per-verse interlinear chips
  when `greekOn`. Emits `select` (verse range + char offsets into the rendered
  English; cross-verse allowed, DEC-143), `mark-click`, `chip-tap`. The
  concept's `authored_color` is the ONE sanctioned raw-color render (USER DATA,
  inline `:style="{ '--c': color }"` only); unconcepted marks fall back to the
  gilt secondary token. Ports the prototype's flashGloss (approximate Slice-1
  alignment — see P3 alignment-honesty note). Opening animations guarded by
  `prefers-reduced-motion`.
- `SelectionPopup.vue` — floating popup shown while a phrase is selected
  (dismissal state ①): "Mark as concept" (primary), "Just highlight" (with a
  gilt swatch dot), and "✕" Cancel (`@cancel`). The prototype's "Tell me about
  this" is OUT of scope. The page owns the three-state dismissal grammar (Esc /
  click-off / ✕ for the live selection; mark click for the committed mark;
  empty-space / Esc / Clear for the concept highlight).
- `ConceptPanel.vue` — workbench panel host: `v-navigation-drawer` slide-over
  on narrow / persistent aside on wide (via `useDisplay()`). `v-model:drawer`.
  Header shows the Clear affordance (spec .clearbtn) when concepts are
  highlighted; `@clear-highlight` + `@toggle-concept` forwarded. The drawer
  requires a Vuetify layout ancestor — the `reader` layout's `<v-app>` supplies
  it in-app; ConceptPanel.test mounts inside `<v-app>` for the same context.
- `ConceptPanelBody.vue` — the four-way view router (library / search / edit /
  mark) shared by both panel hosts; pure event-forwarding glue.
- `ConceptLibrary.vue` — search-as-you-type + concept list (authored-color
  swatch, name, polarity chip, state) + "New concept". Library mode: a row
  click emits `toggle` (multi-select highlight, spec dim-others); selected rows
  carry `data-selected="true"` + the active style. Doubles as the
  associate-concept search when `contextLabel` is set: emits `pick` instead.
  Swatch is the only raw-color render.
- `ConceptEditForm.vue` — create / edit form: title, color (palette swatches +
  custom picker — sanctioned raw color), polarity `v-btn-toggle`, opposite.
  Never sets verification_state / origin (backend-owned, DEC-102).
- `MarkDetail.vue` — the marked phrase + Change / Add / Remove actions and a
  note that the handles adjust the span. Handles the "Just highlight"
  (no-concept) mark case.
- `SpanHandles.vue` — two draggable, word-snapping gilt handles (34px touch
  targets, `touch-action:none`, pointer capture) over the active single-verse
  mark; emits `span-change` with new char offsets. Ports the prototype's
  pointer logic. Lifecycle/reactivity hooks are explicitly imported from `vue`
  so the component mounts under the Vitest unit env. Cross-verse resize is the
  known open hard case (DEC-143): the page only activates handles for
  single-verse marks; `MarkDetail` shows a cross-verse note instead of faking
  it.
- `InterlinearChip.vue` — one Greek token chip (lemma via `<GreekText>` + a
  contextual sub-label); emits `tap`.

## Dependencies

- Vuetify (auto-registered globally)
- Composables auto-imported from `composables/`
- Generated types from `types/backend.ts` (import explicitly)

## Notes

- Components rendered server-side: any `window` / `document` / `localStorage` access must go in `onMounted` or inside `<ClientOnly>`
- Subdirectories under `components/` work but require either nested folder names in the tag (`<UiButton>` for `components/ui/Button.vue`) or `pathPrefix: false`
- Every component needs a Vitest test in `tests/components/<name>.test.ts`
