# composables/

Auto-imported composables. Named `use*.ts`.

## Patterns

- File name and exported function name must match (`useFoo.ts` exports `useFoo`)
- Return objects, not arrays, for readability at call sites
- Reactive params accept `MaybeRefOrGetter<T>`; unwrap with `toValue(...)`
- For SSR-shared state use `useState(key, init)`, not bare `ref()` (bare refs leak between requests on the server)
- For server data, wrap `useFetch` with a key so multiple components share one request

## Key Files

- `useThemeToggle.ts` — wraps Vuetify's `useTheme()`, persists to `localStorage` (client-only, via `onMounted` and `import.meta.client`)
- `useQuery.ts` — state + `$fetch` wrapper around `/api/sp/query/nl`. Also
  exports `unwrapErrorBody` + `ProxyErrorShape` (re-used by other composables
  so the H3-wrapping error-extraction logic lives in one place).
- `useConceptDocument.ts` — Slice N (DEC-106 / DEC-110): SSR-safe `useFetch`
  wrapper around `/api/sp/concepts/:name/document`. Returns
  `{ document, pending, error, refresh }` with `error` normalized to the
  same `ProxyErrorShape` `useQuery` produces.
- `useReader.ts` — Slice 1 (DEC-149): reader navigation + chapter fetch.
  Refs `corpus / book / chapter / version / greekOn`, plus `chapterData`,
  `versions`, `pending`, `error` (`ProxyErrorShape`). `loadChapter()`,
  `loadVersions()`, `nextChapter()` / `prevChapter()` (clamps at 1). Default
  anchor nt / rom / 8 / kjv. `$fetch` (component-local; no Pinia).
- `useConcepts.ts` — Slice 1: concept library. `concepts` ref, `load()`,
  `create(req)`, `update(name, req)` (both reload after write), `search(filter)`
  case-insensitive name helper. Errors normalized to `ProxyErrorShape`.
- `useMarks.ts` — Slice 1: marks for the current chapter. `marks` ref,
  `loadForChapter(scope)` (records the scope), `create` / `update` / `remove`
  (each reloads). Errors normalized to `ProxyErrorShape`.
- `useConceptSelection.ts` — Slice 1 reader-alignment: pure UI state for the
  multi-select concept highlight (spec dim-others-keep-underline). `selected`
  (Set ref), `lastActive`, `hasSelection`, `isSelected`, `toggle`, `add`,
  `clear`. No fetch / no persistence — the reader page owns one instance and
  feeds the name set to ChapterView + ConceptLibrary.

## Dependencies

- Vue reactivity primitives (auto-imported)
- `vuetify` for `useTheme()` in theme-aware composables
- Server routes in `server/api/sp/`

## Notes

- `localStorage` access must be guarded by `import.meta.client` or wrapped in `onMounted` — otherwise SSR will throw
- Every composable needs a Vitest test in `tests/composables/<name>.test.ts`
