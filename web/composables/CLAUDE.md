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
- (Phase J1.3) `useQuery.ts` — state + `$fetch` wrapper around `/api/sp/query/nl`

## Dependencies

- Vue reactivity primitives (auto-imported)
- `vuetify` for `useTheme()` in theme-aware composables
- Server routes in `server/api/sp/`

## Notes

- `localStorage` access must be guarded by `import.meta.client` or wrapped in `onMounted` — otherwise SSR will throw
- Every composable needs a Vitest test in `tests/composables/<name>.test.ts`
