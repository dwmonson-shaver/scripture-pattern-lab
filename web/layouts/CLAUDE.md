# layouts/

Nuxt layouts. `default.vue` wraps every page unless a page sets `definePageMeta({ layout: 'other' })`.

## Patterns

- Root element is `<v-app>` (required by Vuetify for theming + overlays)
- Page content goes inside `<v-main>` via `<slot />`
- Use `<v-container>` for content padding; pages should not re-wrap

## Key Files

- `default.vue` — app bar with title (from runtime config) + theme toggle button

## Dependencies

- `useThemeToggle` composable for the light/dark switch
- `useRuntimeConfig().public.appName` for the title

## Notes

- The theme toggle reads/writes `localStorage` via `useThemeToggle`; SSR returns Vuetify's default theme on first paint, then re-syncs on mount
