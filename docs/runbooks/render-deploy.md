# Runbook: Deploy the FastAPI backend to Render

Audience: anyone provisioning a hosted instance of the scripture-pattern-lab backend for the first time.

This runbook is part of **Slice J1**. The frontend (`scripture-pattern-lab-web`, separate repo) consumes the URL produced by this deploy.

---

## Prerequisites

- A [Render](https://render.com) account.
- This repository (`scripture-pattern-lab`) pushed to a GitHub remote Render can read.
- An Anthropic API key (for `/api/v1/query/nl`). MVP routes work without it but the NL route returns 503.

---

## 1. Generate a bearer token

The frontend Worker proxy and the FastAPI service share a single opaque secret. Generate one locally:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Save the output as **`SPL_BEARER_TOKEN`**. It will be set as an env var on both the Render service and the Cloudflare Worker. Treat it as you would any production secret.

Rotation: change the value on both sides simultaneously. Static-until-rotated is acceptable for MVP (no automated rotation cadence in S1).

---

## 2. Provision the Render Postgres database

1. Render dashboard → **New +** → **PostgreSQL**.
2. Name: `scripture-pattern-lab-db`. Region: match where you'll put the web service.
3. Plan: **Basic** ($7/mo). The Free tier idles after 90 days of inactivity and makes the frontend feel broken; don't use it.
4. Create. Wait for `Status: Available`.
5. Copy the **Internal Database URL** (starts with `postgresql://`). You'll paste it into the web service env vars.

---

## 3. Create the Render web service

1. Render dashboard → **New +** → **Web Service**.
2. Connect this repository's GitHub remote.
3. Name: `scripture-pattern-lab-api`. Region: same as the DB.
4. Branch: `main`.
5. Runtime: **Python 3**.
6. Build command:
   ```
   pip install -e .
   ```
7. Start command:
   ```
   uvicorn src.app.main:create_app --factory --host 0.0.0.0 --port $PORT
   ```
8. Health check path: `/api/v1/health` (the middleware exempts this route from auth so Render can poll it).
9. Plan: **Starter** ($7/mo). Sleeping plans cause cold-start delays on the first query of every session; not what you want.

**Do NOT deploy yet.** Set env vars first.

### Env vars on the web service

| Key | Value |
|---|---|
| `DATABASE_URL` | (paste the Internal Database URL from step 2) |
| `ANTHROPIC_API_KEY` | (your Anthropic key) |
| `SPL_BEARER_TOKEN` | (the secret from step 1) |
| `PYTHONUNBUFFERED` | `1` (so logs stream to Render's log viewer) |

Save → Render triggers the first deploy.

---

## 4. First deploy + corpus load

Wait for the build to go green. The service comes up but the DB is empty — every query against `/api/v1/query/dsl` will return either 503 (engine works but registry returns no concepts) or empty result sets.

Load the corpus + registry from Render's **Shell** tab (or via `render-cli` exec) — Render's shell inherits the service's env vars so `DATABASE_URL` is already set:

```bash
# Inside Render Shell (DATABASE_URL is pre-set via service env):
SPL_INGEST_CONFIRM_TRUNCATE=1 python scripts/db/ingest_corpus.py --truncate
SPL_REGISTRY_CONFIRM_TRUNCATE=1 python scripts/db/seed_registry.py --truncate
```

**Order matters:** ingest first (writes the `tokens` table), then seed (writes `concepts` + `concept_lemmas`, which depend on `tokens` existing for the registry's lemma-presence checks). Reversing the order leaves the registry seed unable to verify lemma coverage.

Expect ~30 seconds for ingest (NT corpus, ~137k tokens) and a few seconds for the registry seed.

If you're running these from a local shell instead of Render's Shell, you must `export DATABASE_URL=...` first using the **External Database URL** (NOT the Internal one — the Internal URL is only reachable from inside Render's network).

---

## 5. Verify the deploy

From your local machine:

```bash
SERVICE_URL=https://scripture-pattern-lab-api.onrender.com
TOKEN=...  # the SPL_BEARER_TOKEN value

# Health (unauthenticated):
curl -sf "$SERVICE_URL/api/v1/health"
# → {"status":"ok"}

# Capabilities (authenticated):
curl -sf -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/api/v1/capabilities" | jq .version
# → "0.1"

# Flagship DSL query (authenticated):
curl -sf -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dsl":"faith > hope > love"}' \
  "$SERVICE_URL/api/v1/query/dsl" | jq '.result.candidates[].reference'
# → "1Cor 13:13"
# → "1Cor 13:13"

# Unauthorized check (should 401):
curl -sf "$SERVICE_URL/api/v1/capabilities" -o /dev/null -w "%{http_code}\n"
# → 401
```

If any of these fail, check Render's logs for the actual error. The bearer-auth middleware logs nothing on a 401 (we don't want timing-channel info-leaks); a 401 means either the env var is missing on the server or the token in the header doesn't match.

---

## 6. (Slice J1 next phase) Wire the Worker proxy

The frontend Worker reads `NUXT_BACKEND_URL` and `NUXT_BACKEND_TOKEN` as runtime config. Set them on the Cloudflare Worker's secrets (NOT in source code):

```bash
# Inside the scripture-pattern-lab-web repo (created in Phase J1.1):
npx wrangler secret put NUXT_BACKEND_URL
# enter: https://scripture-pattern-lab-api.onrender.com

npx wrangler secret put NUXT_BACKEND_TOKEN
# enter: the SPL_BEARER_TOKEN value
```

Subsequent pushes to `main` redeploy the Worker; the secrets persist across deploys.

---

## Cost summary

| Item | Plan | Monthly |
|---|---|---|
| Render Postgres | Basic | $7 |
| Render Web Service | Starter | $7 |
| **Total** | | **$14** |

Cloudflare Workers free plan + free `*.workers.dev` subdomain = $0.

---

## Troubleshooting

**"503 engine_unavailable" on every route except /health**
- `DATABASE_URL` is unset, malformed, or the DB is unreachable. Check Render's "Environment" tab + the Postgres service's status.

**"503 llm_unavailable" only on /api/v1/query/nl**
- `ANTHROPIC_API_KEY` is unset. DSL route still works.

**"401 unauthorized" from a curl that includes the header**
- Token mismatch. Check the env var on the server matches the one in the curl exactly (no trailing newline; copy from a single `python -c "print(secrets.token_hex(32))"` output).

**Cold-start delay on first query of the day**
- Render's Starter plan keeps the service warm. Free plans sleep. Upgrade if you see this.

**Concept queries return zero results despite the corpus loaded**
- The registry seed ran against an empty DB but the concepts never linked. Re-run `seed_registry.py --truncate` after `ingest_corpus.py --truncate` (order matters because of FK constraints).
