# CLAUDE.md — scripture-pattern-lab-web

This is a Nuxt 3 application with Vue 3 (Composition API) and Vuetify 3, deployed to Cloudflare Workers. It is the frontend for the [scripture-pattern-lab](https://github.com/dwmonson-shaver/scripture-pattern-lab) backend (FastAPI on Render).

## The load-bearing rule (DEC-081)

**No LLM SDK ships in the frontend bundle.** Period.

The backend owns every LLM call. The frontend's job is to render deterministic backend output. The Vercel AI SDK, `@ai-sdk/anthropic`, `@anthropic-ai/sdk`, `openai`, `google-generative-ai` — none of these belong here. The `scripts/check-no-llm-sdk.mjs` script enforces this at build time; CI fails if any of them reach `.output/`.

If a UI feature feels like it needs an LLM, the right move is **add an endpoint on the backend** (which is allowed to call Anthropic), not import an SDK here.

## Build & Run

```bash
npm install
npm run dev         # http://localhost:3000
npm run build       # production build → .output/
npm run preview     # serve the built output locally
```

## Test

```bash
npm test                                # Vitest unit tests
npm run test:watch                      # Vitest watch mode
npm run test:e2e                        # Playwright (needs PLAYWRIGHT_BASE_URL)
```

## Lint, Format, Typecheck

```bash
npm run lint               # eslint with --fix
npm run lint:check         # eslint without --fix (for CI)
npm run format             # prettier --write
npm run format:check       # prettier --check (for CI)
npm run typecheck          # vue-tsc --noEmit
npm run check:no-llm-sdk   # bundle-grep for forbidden LLM SDKs
```

## Code Style & Conventions

### Vue / Nuxt

- ALWAYS use `<script setup lang="ts">` — never Options API
- ALWAYS use Composition API (`ref`, `computed`, `watch`) — never `data()` / `methods` / `computed:` blocks
- Do NOT manually import auto-imported functions (`ref`, `computed`, `watch`, `useState`, `useFetch`, `useRoute`, `navigateTo`, `definePageMeta`, etc.) — Nuxt auto-imports these
- Do NOT manually import components — Nuxt auto-imports from `components/`
- Use `defineProps<{}>()` and `defineEmits<{}>()` with TypeScript generics, not runtime declarations
- Use `useFetch` or `useAsyncData` for client-side data fetching
- Use `$fetch` for server-route invocations from event handlers
- Server routes go in `server/api/` — Nitro handles routing
- Composables go in `composables/` — name files as `use*.ts`
- Pages go in `pages/` — file-based routing, use `definePageMeta` for layout/middleware

### Vuetify

- Use Vuetify components for all UI — do not use raw HTML when a Vuetify component exists (e.g., `v-btn` not `<button>`, `v-card` not `<div class="card">`)
- Use Vuetify's grid (`v-container`, `v-row`, `v-col`)
- Use built-in props for styling (`color="primary"`, `variant="outlined"`, `density="compact"`)
- Theme colors are defined in `vuetify.config.ts` — use semantic names (`primary`, `secondary`, `error`, `success`) not hex values
- Use `useDisplay()` for responsive logic, `useTheme()` for programmatic theme access
- Both light and dark mode must remain readable — see `THEME.md` for the full discipline

### Theme colors + text contrast — MANDATORY

The single most common bug in generated UIs is **text that's invisible in one theme**. Always-correct text classes (adapt to both themes):

- (no class) — default text color on the page background, theme-aware
- `text-medium-emphasis` — secondary / descriptive text
- `text-disabled` — disabled text
- `text-on-primary`, `text-on-secondary`, `text-on-surface-variant`, etc. — for text inside a Vuetify component with an explicit `color=` prop

NEVER use: `text-white`, `text-black`, Tailwind classes (`text-gray-500`), hardcoded hex colors. See `THEME.md` for worked examples.

Definition-of-done for any UI change: toggle the theme and verify every piece of text remains readable.

### TypeScript

- Strict mode is enabled — no `any` without justification
- API response types are GENERATED from the backend's OpenAPI schema at build time:
  ```bash
  NUXT_BACKEND_URL=https://... npm run gen:types
  ```
  The generated file `types/backend.ts` is committed so PRs visibly show schema drift.
- Use `components["schemas"]["QueryNLResponse"]` style imports from the generated file.
- Hand-written types live in `types/`; runtime validators (zod) live next to their consumers.

### Server routes (Nitro)

- Route filename suffix encodes the method: `nl.post.ts`, `health.get.ts`
- Use `defineEventHandler` (auto-imported)
- Validate request bodies with `zod` and `readValidatedBody`
- Throw `createError({ statusCode, statusMessage, data })` on bad input
- Read secrets via `useRuntimeConfig()` — never via `process.env`
- The backend URL and bearer token live in the server-only root of `runtimeConfig`, never under `public:`

### State Management

- Pinia is **deferred**. Use component-local `ref()` and composables for state until cross-component state actually appears.
- The slice will add Pinia when concrete cross-page state (saved queries, history, user prefs) lands.

### File Naming

- Components: PascalCase (`QueryForm.vue`)
- Composables: camelCase with `use` prefix (`useQuery.ts`)
- Pages: kebab-case (`query.vue` would map to `/query`)
- Types: PascalCase or matched to schema names
- Server routes: kebab-case + method suffix (`nl.post.ts`)

## Architecture

```
├── assets/styles/        # Global CSS (SBL Greek @font-face, theme hooks)
├── components/           # Auto-imported Vue components
├── composables/          # Auto-imported composables (use*.ts)
├── layouts/              # Nuxt layouts (default.vue with theme toggle)
├── pages/                # File-based routing (currently just /)
├── public/fonts/         # SBL Greek woff2 served at /fonts/SBLGreek.woff2
├── scripts/              # Build-time helpers (check-no-llm-sdk.mjs)
├── server/api/sp/        # Nitro proxy routes to the FastAPI backend
├── tests/                # Vitest + Playwright
├── types/                # Hand-written + GENERATED (backend.ts) TypeScript
├── app.vue               # Entry: NuxtLayout > NuxtPage
├── nuxt.config.ts        # Nuxt + Nitro + Vuetify config
├── vuetify.config.ts     # Theme + component defaults
└── wrangler.toml         # Cloudflare Worker config
```

## Definition of Done

A change is not complete until:

1. Code is written and behaves correctly in both light and dark mode
2. `npm run lint:check` passes
3. `npm run typecheck` passes
4. `npm test` passes (unit tests for components, composables, server routes)
5. `npm run check:no-llm-sdk` passes
6. Any directory's `CLAUDE.md` is updated to reflect file additions/changes

## Directory-level CLAUDE.md files

Every working directory has its own `CLAUDE.md` covering Purpose / Patterns / Key Files / Dependencies / Notes. These persist project context across Claude Code sessions. Update them as you add/rename/remove files in their directories.

## Common Pitfalls

- Do NOT use `reactive()` for primitives — use `ref()`
- Do NOT destructure props directly — use `toRefs(props)` or access via `props.x`
- Do NOT use `onMounted` for data fetching — use `useFetch` / `useAsyncData`
- No `window`, `document`, or `localStorage` outside `onMounted` or `<ClientOnly>`
- Bindings on Cloudflare (KV, D1, R2) — none are configured for this app at MVP; if you add them, update `wrangler.toml` and the relevant `CLAUDE.md`
- Worker secrets (`NUXT_BACKEND_URL`, `NUXT_BACKEND_TOKEN`) — set via `wrangler secret put`, NEVER commit
