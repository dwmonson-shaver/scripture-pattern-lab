# pages/

File-based routes. `pages/foo.vue` → `/foo`, `pages/users/[id].vue` → `/users/:id`.

## Patterns

- Filenames are kebab-case (route segments)
- Use `useFetch` / `useAsyncData` for data, never raw `fetch`
- Declare layout/middleware via `definePageMeta({ ... })`
- Compose UI from `components/` — pages should be thin glue

## Key Files

- `index.vue` — home page; placeholder in Phase J1.1, real query UI in Phase J1.3
- `reader.vue` — Slice 1 (DEC-149) concept-identification reader workbench.
  Wires `ReaderBar` + `ChapterView` + `ConceptPanel` + `SelectionPopup` +
  `SpanHandles`. Owns the cross-component state (reader nav, concepts, marks,
  the panel's sub-view + the associate/pending context + the multi-select
  concept-highlight set + the layout mode); the composables own fetch/CRUD.
  Default anchor nt / rom / 8 / kjv. Uses the `reader` layout for the app-shell
  (spec #screen — only the text column + panel scroll). Owns the three-state
  dismissal grammar (Esc / click-off / ✕ / Clear) and the scroll-spy chapter
  handler (`@chapter-in-view`, single-chapter no-op today; multi-chapter book
  scroll is a follow-up). Scope is concept identification only — no connections
  / axes / patterns / AI explainer; a "Just highlight" (no-concept mark) IS in
  scope.
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
