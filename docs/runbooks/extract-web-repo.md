# Runbook: Extract `web/` to its own GitHub repo

Audience: anyone moving the frontend code out of `scripture-pattern-lab/web/` into a sibling `scripture-pattern-lab-web` repo, then deploying it to Cloudflare Workers.

This runbook is part of **Slice J1**. It runs after the slice closes, when the frontend code is code-complete and ready to live in its own repo.

---

## Prerequisites

- The slice's J1.4 commit has landed (full frontend code is in `web/`).
- You have a personal Cloudflare account (free plan is fine).
- You have admin on a personal GitHub account where the new repo can live.
- Render deploy is done (per `docs/runbooks/render-deploy.md`) so the `NUXT_BACKEND_URL` and `NUXT_BACKEND_TOKEN` exist.
- **SBL Greek font file is in place.** `web/public/fonts/SBLGreek.woff2` is **not** committed to the parent repo (only the README placeholder). Without it, the Step 6 smoke check ("rendered in SBL Greek") will silently fall back to a CSS default font — the deploy will look successful when the asset is actually missing. Follow `web/public/fonts/README.md` to download from SBL and convert via `pyftsubset`, then commit the `.woff2` to `web/` **before** running the extraction in Step 2.

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

The export branch will contain exactly the J1-slice commits that touched `web/`, with each commit re-rooted as if `web/` were the repo root. (Dry-run confirmed: at the Slice J1 close SHA, this is 5 commits — J1.1 through J1.4 plus close-review closures. Confirms the user's expectation before pushing.)

Pros: PRs that touched `web/` are still traceable through `git log`.
Cons: scripture-pattern-lab's full history (including non-web commits referenced from web-touching ones) does not transfer — only the re-rooted web subset.

### Option B — Fresh init (fallback only; DEC-088 chose Option A)

DEC-088 selected Option A (history-preserving subtree split). Option B is kept here as a fallback if subtree split later proves problematic. **Default to Option A.** Use Option B only if (a) you decide history doesn't matter and want a clean slate, or (b) subtree split fails for an unexpected reason.

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

`NUXT_BACKEND_URL` is needed at build time so `npm run gen:types` can fetch the backend's OpenAPI schema and generate `types/backend.ts`. **Note:** `NUXT_BACKEND_URL` is ALSO needed as a Worker runtime secret (set in Step 4). Same value, two different consumers (build-time type generation vs. runtime proxy dispatch). Don't skip the runtime set just because you set the build-time one here.

---

## 4. Configure Worker runtime secrets

These are server-only secrets the deployed Worker reads via `useRuntimeConfig()`. They are different from the GitHub repo secrets above — those are CI-time secrets; these are runtime secrets.

**First:** clone the new repo down separately (outside `scripture-pattern-lab/`), then `cd` into it. `wrangler` reads the local `wrangler.toml` to know which CF account/Worker to target, so running it from the wrong directory will set secrets against the wrong Worker.

```bash
# In a sibling directory, e.g. ~/Documents/Claude-Personal/:
git clone git@github.com:<your-account>/scripture-pattern-lab-web.git
cd scripture-pattern-lab-web

# Now set the runtime secrets:
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

**Soft cutover recommended.** Do NOT run the removal immediately after the first deploy. Keep `web/` in the parent repo until at least one substantive frontend change has been merged into the new repo and re-deployed cleanly. This confirms the new repo is self-sufficient (no hidden cross-references back into the parent) before you burn the source-of-truth bridge. Once that's verified:

```bash
# From scripture-pattern-lab root:
git rm -r web
git commit -m "Slice J1 followup: remove web/ subdir after extraction to scripture-pattern-lab-web"
git push
```

The slice's history is preserved in `git log` on both repos (each holds its own subset). Note: the `web/.github/workflows/deploy.yml` workflow is dormant in the parent repo (GitHub only auto-runs workflows in the root `.github/workflows/`, not nested subdirs), so there's no stale workflow to clean up separately after this removal.

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
