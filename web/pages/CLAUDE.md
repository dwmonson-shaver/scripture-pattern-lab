# pages/

File-based routes. `pages/foo.vue` → `/foo`, `pages/users/[id].vue` → `/users/:id`.

## Patterns

- Filenames are kebab-case (route segments)
- Use `useFetch` / `useAsyncData` for data, never raw `fetch`
- Declare layout/middleware via `definePageMeta({ ... })`
- Compose UI from `components/` — pages should be thin glue

## Key Files

- `index.vue` — home page; placeholder in Phase J1.1, real query UI in Phase J1.3

## Dependencies

- Server routes in `server/api/sp/`
- Auto-imported components from `components/`

## Notes

- `useFetch` returns `{ data, pending, error, refresh }` — destructure all four; UI states matter
- Avoid `onMounted` for data fetching; use `useFetch`/`useAsyncData` so the page works under SSR
