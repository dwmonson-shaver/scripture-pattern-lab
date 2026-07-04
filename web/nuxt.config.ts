export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',

  devtools: { enabled: true },

  modules: ['vuetify-nuxt-module', '@nuxt/eslint', 'nitro-cloudflare-dev'],

  typescript: {
    strict: true,
    typeCheck: false,
  },

  // We don't use the client-side app manifest. Disabling it avoids a known
  // Vite dep-optimizer issue with the `#app-manifest` virtual import in dev.
  experimental: {
    appManifest: false,
  },

  // SSR HTML ships with NO cache-control by default, so browsers heuristically
  // cache it. Stale HTML then references the previous deploy's content-hashed
  // /_nuxt chunks (replaced on deploy) → 404 → the app never mounts. HTML must
  // always revalidate; hashed assets keep their immutable header (set via the
  // generated _headers file on the assets binding — the rule here is a guard).
  routeRules: {
    '/_nuxt/**': { headers: { 'cache-control': 'public, max-age=31536000, immutable' } },
    '/**': { headers: { 'cache-control': 'no-cache' } },
  },

  nitro: {
    preset: 'cloudflare-module',
    cloudflare: {
      nodeCompat: true,
    },
    cloudflareDev: {
      configPath: 'wrangler.dev.toml',
      silent: true,
    },
  },

  vuetify: {
    moduleOptions: {
      ssrClientHints: {
        reloadOnFirstRequest: false,
        viewportSize: true,
        // Dark is the locked default; users can toggle via the app-bar.
        prefersColorScheme: false,
      },
    },
    vuetifyOptions: './vuetify.config.ts',
  },

  css: ['@mdi/font/css/materialdesignicons.css', '~/assets/styles/globals.css'],

  runtimeConfig: {
    // Server-only secrets — set via NUXT_BACKEND_URL / NUXT_BACKEND_TOKEN env
    // vars (or wrangler secret put for the deployed Worker). Never put values
    // here; never move them under `public:` (that namespace ships to the
    // browser).
    backendUrl: '',
    backendToken: '',
    public: {
      appName: 'Scripture Pattern Lab',
    },
  },

  app: {
    head: {
      title: 'Scripture Pattern Lab',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
    },
  },
})
