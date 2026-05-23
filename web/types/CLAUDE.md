# types/

Shared TypeScript types — used by both client (pages, components) and server (API routes).

## Patterns

- One type or related cluster per file
- File name matches the primary exported type
- PascalCase filenames
- Pure types only — no runtime code

## Key Files

- `backend.ts` — **GENERATED** from the FastAPI backend's OpenAPI schema via `openapi-typescript`. Regenerated on every `npm run build` (prebuild hook). Committed so PRs visibly show schema drift. **Do not hand-edit.**

## Notes

- Types in this directory are NOT auto-imported. Import explicitly:
  ```ts
  import type { components, paths } from '~/types/backend'
  type QueryNLResponse = components['schemas']['QueryNLResponse']
  ```
- For runtime validators (zod schemas) that double as types, prefer co-locating with the consumer in `server/utils/` or `composables/`, not here
- DEC-081 enforcement: the frontend cannot render a field the backend doesn't declare. `backend.ts` is the structural seam.
