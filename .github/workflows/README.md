# `.github/workflows/`

GitHub Actions workflows for the repo.

## `deploy.yml` — Cloudflare Workers deploy for the Nuxt frontend

Runs on every push to `main` that touches `web/**` or this workflow file,
plus on manual `workflow_dispatch`. Installs deps, runs lint / typecheck /
tests / no-LLM-SDK check, regenerates backend types against the live
OpenAPI, builds, and deploys the resulting Worker bundle.

### Required GitHub Secrets

Set these under **Settings → Secrets and variables → Actions** before the
workflow can complete a deploy. Until they're set, the workflow will run
but fail at the corresponding step — that's expected, not a bug.

| Secret | Purpose | Where to get it |
|--------|---------|-----------------|
| `CLOUDFLARE_API_TOKEN` | Authenticates the deploy step. Scope to *Workers Edit* on the account that owns `scripture-pattern-lab-web`. | Cloudflare dashboard → My Profile → API Tokens → Create Token → "Edit Cloudflare Workers" template, scoped to a single account. |
| `CLOUDFLARE_ACCOUNT_ID` | The Cloudflare account UUID. Public-by-policy (already pinned in `web/wrangler.toml`), but the `wrangler-action` reads it from secrets. | Cloudflare dashboard → Workers & Pages → right-hand sidebar shows the account ID. |
| `NUXT_BACKEND_URL` | URL of the deployed FastAPI backend. Read by the `gen:types` step to fetch `/openapi.json` and regenerate `web/types/backend.ts`. | The Render service URL, e.g. `https://scripture-pattern-lab-api.onrender.com`. |

### Worker runtime secrets (not GitHub Secrets)

These do NOT belong in GitHub Secrets — they're set on the deployed Worker
itself via `wrangler secret put`:

- `NUXT_BACKEND_URL` (yes, same name as the GitHub Secret — the GH one
  is build-time, the wrangler one is runtime)
- `NUXT_BACKEND_TOKEN` — bearer token the Worker uses when calling the
  backend.

The fact that two secrets share a name is a quirk: one is used by Node
during `npm run gen:types` in CI; the other is read by the Worker's
`useRuntimeConfig()` at request time. See `web/wrangler.toml` and
`web/CLAUDE.md` for details.

### Manual deploy fallback

If CI is unhealthy or you need a hotfix, the manual flow is:

```bash
cd web
npm install
npm run gen:types        # NUXT_BACKEND_URL must be set in your shell
npm run build
npx wrangler deploy
```

Either path produces the same `.output/server/index.mjs` bundle and the
same `npm run check:no-llm-sdk` gate.
