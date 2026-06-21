/**
 * Vitest global setup.
 *
 * - Stubs Nuxt auto-imports that the SUT references at module-load time
 *   (`ref`, `computed`, `useState`, `$fetch`, etc.). Component tests
 *   import Vue helpers explicitly; the stubs cover Nuxt-only globals.
 * - Mounts a CSS resolver tolerant of Vuetify's runtime style queries
 *   (happy-dom by default rejects some CSS selectors Vuetify emits).
 */

import { vi } from 'vitest'
import { computed, ref, watch, onMounted } from 'vue'

// Nuxt auto-imports — make them available globally in tests.
const globalScope = globalThis as Record<string, unknown>
if (!globalScope.ref) globalScope.ref = ref
if (!globalScope.computed) globalScope.computed = computed
if (!globalScope.watch) globalScope.watch = watch
if (!globalScope.onMounted) globalScope.onMounted = onMounted

// $fetch — Nuxt's universal fetch helper. Tests that exercise the
// composable's network path stub it with `vi.fn`; this default avoids
// crashes if a component touches it incidentally.
if (!globalScope.$fetch) {
  globalScope.$fetch = vi.fn(async () => {
    throw new Error('$fetch was not stubbed in this test')
  })
}

// useState — Nuxt's SSR-safe shared state. For unit tests, plain ref().
if (!globalScope.useState) {
  globalScope.useState = <T>(_key: string, init?: () => T) => ref(init ? init() : (null as T))
}

// useRuntimeConfig — read-only stub returning a public.appName.
if (!globalScope.useRuntimeConfig) {
  globalScope.useRuntimeConfig = () => ({ public: { appName: 'Scripture Pattern Lab (test)' } })
}
