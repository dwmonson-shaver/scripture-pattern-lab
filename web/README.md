# scripture-pattern-lab-web

Frontend for the [scripture-pattern-lab](https://github.com/dwmonson-shaver/scripture-pattern-lab) project. Nuxt 3 + Vuetify 3 + TypeScript; deployed to Cloudflare Workers on the free plan.

## What this is

A thin web client over the FastAPI backend's six MVP HTTP routes. The browser only ever talks same-origin to this Worker; the Worker proxies to the Render-hosted Python backend over HTTPS with a bearer token. See `CLAUDE.md` for the project conventions; `THEME.md` for theme discipline; the parent project's `docs/canonical/09_backend-service-boundaries.md` for the backend contract.

## Local development

```bash
git clone https://github.com/<your-account>/scripture-pattern-lab-web.git
cd scripture-pattern-lab-web
npm install

# Point the dev server at a running backend (local or Render).
# Either:
#   cp .env.example .env.local  # then edit
# Or:
echo 'NUXT_BACKEND_URL=https://scripture-pattern-lab-api.onrender.com' > .env.local
echo 'NUXT_BACKEND_TOKEN=<the-shared-bearer-token>' >> .env.local

npm run dev   # http://localhost:3000
```

## Deploy

Push to `main` and the GitHub Action runs `wrangler deploy` against your Cloudflare account. Required GitHub repo secrets:

- `CLOUDFLARE_API_TOKEN` — generate at dash.cloudflare.com → My Profile → API Tokens; needs Workers + Workers KV scopes
- `CLOUDFLARE_ACCOUNT_ID` — your account ID (top-right of the Workers dashboard)
- `NUXT_BACKEND_URL` — the Render service URL (for type generation at build time)

Once deployed, set the runtime secrets on the Worker:

```bash
npx wrangler secret put NUXT_BACKEND_URL
npx wrangler secret put NUXT_BACKEND_TOKEN
```

The free `*.workers.dev` subdomain works out of the box. Custom domain is a follow-on.

## DEC-081 enforcement

This frontend ships ZERO client-side LLM code. Specifically:

- No `@ai-sdk/*`, `@anthropic-ai/sdk`, `openai`, or `google-generative-ai` packages.
- The CI step `npm run check:no-llm-sdk` runs after `nuxt build` and fails if any LLM SDK ends up in `.output/`. This is the structural enforcement of [DEC-081](https://github.com/dwmonson-shaver/scripture-pattern-lab/blob/main/docs/governance/decision-log.md): the LLM is a translator at boundaries, owned by the backend.

If you ever find yourself adding an LLM SDK here, stop. The backend's `POST /api/v1/query/nl` is the seam.

## Repo extraction history

This repo was extracted from `scripture-pattern-lab/web/` at the close of Slice J1 (see `docs/runbooks/extract-web-repo.md` in the parent repo). The parent retains the full slice history; this repo can be either history-linked (via `git subtree split`) or fresh-init'd depending on extraction method used.
