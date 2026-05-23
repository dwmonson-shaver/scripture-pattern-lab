# Runbook: Extract `web/` to its own GitHub repo

Audience: anyone moving the frontend code out of `scripture-pattern-lab/web/` into a sibling `scripture-pattern-lab-web` repo, then deploying it to Cloudflare Workers.

This runbook is part of **Slice J1**. It runs after the slice closes, when the frontend code is code-complete and ready to live in its own repo.

---

## Prerequisites

- The slice's J1.4 commit has landed (full frontend code is in `web/`).
- You have a personal Cloudflare account (free plan is fine).
- You have admin on a personal GitHub account where the new repo can live.
- Render deploy is done (per `docs/runbooks/render-deploy.md`) so the `NUXT_BACKEND_URL` and `NUXT_BACKEND_TOKEN` exist.

---

## 1. Create the GitHub repo

1. Go to github.com → New repository.
2. Owner: your personal account (NOT TovutiLMS — this is your project).
3. Name: `scripture-pattern-lab-web`.
4. Public or private: your choice.
5. **Do NOT initialize with README/license/.gitignore.** We're importing existing content.
6. Create.

Note the SSH URL: `git@github.com:<your-account>/scripture-pattern-lab-web.git`.

---

## 2. Choose extraction method

You have two options. They differ in what history the new repo gets.

### Option A — `git subtree split` (preserves history)

The new repo inherits every commit that touched `web/` in scripture-pattern-lab's history (each commit re-rooted as if `web/` was the repo root).

```bash
# From the scripture-pattern-lab root:
git subtree split --prefix=web -b web-export

# Push the export branch to the new remote as main:
git push git@github.com:<your-account>/scripture-pattern-lab-web.git web-export:main
```

Pros: PRs that touched `web/` are still traceable through `git log`.
Cons: scripture-pattern-lab's full history (including non-web commits referenced from web-touching ones) does not transfer — only the re-rooted web subset.

### Option B — Fresh init (drops history)

The new repo starts at a single "Initial commit" with the current state of `web/`. Faster, cleaner if history doesn't matter.

```bash
# From outside scripture-pattern-lab, e.g. ~/Documents/Claude-Personal/:
cp -r scripture-pattern-lab/web scripture-pattern-lab-web
cd scripture-pattern-lab-web
rm -rf .nuxt .output node_modules  # in case they got copied
git init
git branch -m main
git add .
git commit -m "Initial commit: extracted from scripture-pattern-lab/web/ at <SLICE-J1-CLOSE-SHA>"
git remote add origin git@github.com:<your-account>/scripture-pattern-lab-web.git
git push -u origin main
```

Replace `<SLICE-J1-CLOSE-SHA>` with the actual SHA of the slice-close governance commit so the lineage is recorded in the commit message.

---

## 3. Configure GitHub repo secrets

In the new repo's Settings → Secrets and variables → Actions:

| Secret name | Value |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Generate at dash.cloudflare.com → My Profile → API Tokens → "Edit Cloudflare Workers" template |
| `CLOUDFLARE_ACCOUNT_ID` | Top-right of the Workers dashboard |
| `NUXT_BACKEND_URL` | `https://scripture-pattern-lab-api.onrender.com` (from your Render web service) |

`NUXT_BACKEND_URL` is needed at build time so `npm run gen:types` can fetch the backend's OpenAPI schema and generate `types/backend.ts`.

---

## 4. Configure Worker runtime secrets

These are server-only secrets the deployed Worker reads via `useRuntimeConfig()`. They are different from the GitHub repo secrets above — those are CI-time secrets; these are runtime secrets.

```bash
# From the scripture-pattern-lab-web clone:
npx wrangler secret put NUXT_BACKEND_URL
# enter: https://scripture-pattern-lab-api.onrender.com

npx wrangler secret put NUXT_BACKEND_TOKEN
# enter: the SPL_BEARER_TOKEN value from docs/runbooks/render-deploy.md
```

These persist across deploys; you only set them once.

---

## 5. First deploy

```bash
git push origin main
```

GitHub Actions runs the workflow at `.github/workflows/deploy.yml`. Expected steps:

1. Checkout
2. Cache restore
3. `npm install`
4. Lint, typecheck, unit tests
5. Generate API types from `NUXT_BACKEND_URL/openapi.json`
6. `nuxt build`
7. `check-no-llm-sdk` bundle grep
8. `wrangler deploy`

After ~2 minutes, the Worker is live at:

```
https://scripture-pattern-lab-web.<your-cf-subdomain>.workers.dev
```

(Your `<your-cf-subdomain>` is set once for your CF account at workers.cloudflare.com → Workers & Pages → Subdomain.)

---

## 6. Verify the deploy

Visit the URL. You should see the placeholder page from Phase J1.1, or — after Phases J1.2-J1.4 land — the query form.

Smoke check: run the flagship query, confirm `1Cor 13:13` appears with `πίστις`, `ἐλπίς`, `ἀγάπη` rendered in SBL Greek. Toggle the theme; verify contrast holds.

---

## 7. Remove `web/` from scripture-pattern-lab

Once the new repo is live and the deploy is verified, the parent repo no longer needs the subdir.

```bash
# From scripture-pattern-lab root:
git rm -r web
git commit -m "Slice J1 followup: remove web/ subdir after extraction to scripture-pattern-lab-web"
git push
```

The slice's history is preserved in `git log` on both repos (each holds its own subset).

---

## Troubleshooting

**CI step "Generate API types" fails**
- `NUXT_BACKEND_URL` repo secret is missing, or the Render service isn't reachable from GitHub Actions. Check the Render service is awake; check the URL exactly matches.

**CI step "Bundle check — no LLM SDK in output" fails**
- A forbidden package leaked into the bundle. Read the failure message; remove the dep from `package.json` and re-push.

**Worker deploys but `/api/sp/*` returns 401**
- The `NUXT_BACKEND_TOKEN` Worker secret doesn't match the `SPL_BEARER_TOKEN` env var on Render. Re-run `wrangler secret put NUXT_BACKEND_TOKEN`.

**Page renders but query button does nothing**
- `NUXT_BACKEND_URL` Worker secret is missing. The Nitro proxy reads it via `useRuntimeConfig()`; absence means proxy can't dispatch the upstream call.
