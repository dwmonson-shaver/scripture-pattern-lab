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
- `utils/backend.ts` — typed fetch wrappers (`proxyToBackend` for POST,
  `getFromBackend` for GET) that inject the bearer token

## Dependencies

- `zod` for input validation
- Generated types from `types/backend.ts`

## Notes

- Code in `server/` runs on Cloudflare Workers — no Node `fs`, no `child_process`. `nodejs_compat` provides most Node builtins (`crypto`, `buffer`, etc.) but not filesystem access
- Worker secrets (`NUXT_BACKEND_URL`, `NUXT_BACKEND_TOKEN`) — set via `wrangler secret put`, never commit
- Every server route needs a Vitest test in `tests/server/<path>.test.ts`
