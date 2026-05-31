# pages/

File-based routes. `pages/foo.vue` → `/foo`, `pages/users/[id].vue` → `/users/:id`.

## Patterns

- Filenames are kebab-case (route segments)
- Use `useFetch` / `useAsyncData` for data, never raw `fetch`
- Declare layout/middleware via `definePageMeta({ ... })`
- Compose UI from `components/` — pages should be thin glue

## Key Files

- `index.vue` — home page; placeholder in Phase J1.1, real query UI in Phase J1.3
- `concept/[name].vue` — Slice N (DEC-106) Conceptual Document view. Dynamic
  segment `:name` is the concept name (auto-decoded by Nuxt, re-encoded by
  the `useConceptDocument` composable when building the proxy URL). Renders
  `<ConceptDocumentView>` with the deterministic §1 + optional LLM §2 +
  Tier-2 placeholder; degrades gracefully on the LLM-failure case where §2
  is null (DEC-107 opt-in).

## Dependencies

- Server routes in `server/api/sp/`
- Auto-imported components from `components/`

## Notes

- `useFetch` returns `{ data, pending, error, refresh }` — destructure all four; UI states matter
- Avoid `onMounted` for data fetching; use `useFetch`/`useAsyncData` so the page works under SSR
