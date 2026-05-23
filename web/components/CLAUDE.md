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

## Dependencies

- Vuetify (auto-registered globally)
- Composables auto-imported from `composables/`
- Generated types from `types/backend.ts` (import explicitly)

## Notes

- Components rendered server-side: any `window` / `document` / `localStorage` access must go in `onMounted` or inside `<ClientOnly>`
- Subdirectories under `components/` work but require either nested folder names in the tag (`<UiButton>` for `components/ui/Button.vue`) or `pathPrefix: false`
- Every component needs a Vitest test in `tests/components/<name>.test.ts`
