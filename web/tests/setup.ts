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

// useState — Nuxt's SSR-safe shared state: keyed singleton, so two calls with
// the same key return the SAME ref (as in the real runtime). A per-call ref
// would make composables that rely on shared state (useToast) untestable.
if (!globalScope.useState) {
  const stateCache = new Map<string, unknown>()
  globalScope.useState = <T>(key: string, init?: () => T) => {
    if (!stateCache.has(key)) stateCache.set(key, ref(init ? init() : (null as T)))
    return stateCache.get(key)
  }
}

// useRuntimeConfig — read-only stub returning a public.appName.
if (!globalScope.useRuntimeConfig) {
  globalScope.useRuntimeConfig = () => ({ public: { appName: 'Scripture Pattern Lab (test)' } })
}

// visualViewport — Vuetify's VOverlay location strategy reads it; happy-dom
// doesn't implement it. A minimal EventTarget-shaped stub is enough for
// dialog/overlay components (VDialog in ConceptLibrary's delete confirm).
if (!globalScope.visualViewport) {
  globalScope.visualViewport = {
    width: 1280,
    height: 800,
    offsetLeft: 0,
    offsetTop: 0,
    scale: 1,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  }
}
