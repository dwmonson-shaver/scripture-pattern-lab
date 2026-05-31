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

## Dependencies

- Vuetify (auto-registered globally)
- Composables auto-imported from `composables/`
- Generated types from `types/backend.ts` (import explicitly)

## Notes

- Components rendered server-side: any `window` / `document` / `localStorage` access must go in `onMounted` or inside `<ClientOnly>`
- Subdirectories under `components/` work but require either nested folder names in the tag (`<UiButton>` for `components/ui/Button.vue`) or `pathPrefix: false`
- Every component needs a Vitest test in `tests/components/<name>.test.ts`
