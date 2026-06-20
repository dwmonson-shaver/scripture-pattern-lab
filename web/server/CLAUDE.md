# server/

Nitro server runtime. Routes in `api/`, utilities in `utils/`.

## Patterns

- Route filename suffix encodes the method: `nl.post.ts` = POST handler
- Use `defineEventHandler` (auto-imported by Nitro)
- Validate inputs with `zod`; use `readValidatedBody` to enforce a schema
- Throw `createError({ statusCode, statusMessage, data })` on bad input
- Read secrets via `useRuntimeConfig()` — never via `process.env`

## Key Files (post Phase J1.2)

- `api/sp/query/nl.post.ts` — proxies the NL query route to the backend
- `api/sp/concepts/[name]/document.get.ts` — proxies the persisted
  Conceptual Document (Slice N, DEC-106)
- `utils/backend.ts` — typed fetch wrappers that inject the bearer token:
  `proxyToBackend` (POST), `getFromBackend` (GET), and `sendToBackend`
  (method-aware POST / PATCH / DELETE; added in Slice 1, tolerates a 204
  empty body). All three share one error contract (`BackendError`).

### Slice 1 — concept-identification reader proxies (DEC-149)

All mirror the `nl.post.ts` pattern (zod where there's a body, the shared
proxy/get/send helpers, `createError` mirroring the upstream status + body):

- `api/sp/read/versions.get.ts` — GET backend `/api/v1/read/versions`
- `api/sp/read/[corpus]/[book]/[chapter].get.ts` — GET the chapter; path
  segments decoded + re-encoded once, `?version=` passed through
- `api/sp/concepts/index.get.ts` — GET concepts (`?language=` passthrough)
- `api/sp/concepts/index.post.ts` — POST create (zod: name 1..64 + optional
  authored fields; polarity enum `+`/`-`/`±`)
- `api/sp/concepts/[name].patch.ts` — PATCH a concept (all fields optional)
- `api/sp/marks/index.get.ts` — GET marks (corpus/book/chapter/version query)
- `api/sp/marks/index.post.ts` — POST a mark (zod mirrors `MarkCreateRequest`;
  cross-verse allowed; empty/absent `concept_names` = "Just highlight")
- `api/sp/marks/[id].patch.ts` — PATCH a mark's span / concepts
- `api/sp/marks/[id].delete.ts` — DELETE a mark (no body)

## Dependencies

- `zod` for input validation
- Generated types from `types/backend.ts`

## Notes

- Code in `server/` runs on Cloudflare Workers — no Node `fs`, no `child_process`. `nodejs_compat` provides most Node builtins (`crypto`, `buffer`, etc.) but not filesystem access
- Worker secrets (`NUXT_BACKEND_URL`, `NUXT_BACKEND_TOKEN`) — set via `wrangler secret put`, never commit
- Every server route needs a Vitest test in `tests/server/<path>.test.ts`
