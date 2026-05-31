import type { ConceptDocument } from '~~/types/api'
import { unwrapErrorBody, type ProxyErrorShape } from '~~/composables/useQuery'

/**
 * Fetch the persisted Conceptual Document for a concept by name.
 *
 * Wraps `useFetch` so it works under SSR (the page route can be hit by
 * direct URL load) and keyed on the concept name so navigating between
 * documents triggers a refetch.
 *
 * Returns the same `data` / `pending` / `error` triple as Nuxt's
 * `useFetch`, with `error` normalized to the project's `ProxyErrorShape`
 * (the same envelope `useQuery` produces) so `<ErrorPanel>` can render
 * either without branching. The H3-wrapping `unwrapErrorBody` pitfall
 * that Bucket-J1-4 closed applies here identically — re-use the same
 * unwrapper.
 *
 * Slice N (DEC-106 / DEC-110): the document is store-once on the
 * backend, so successive calls are cheap and cacheable; we still let
 * Nuxt's per-request cache do its thing without explicit `getCachedData`.
 */
export function useConceptDocument(name: Ref<string> | string) {
  const nameRef = isRef(name) ? name : ref(name)
  const url = computed(
    () => `/api/sp/concepts/${encodeURIComponent(nameRef.value)}/document`,
  )

  const { data, pending, error, refresh } = useFetch<ConceptDocument>(url, {
    key: () => `concept-document-${nameRef.value}`,
    watch: [nameRef],
    server: true,
  })

  const normalizedError = computed<ProxyErrorShape | null>(() => {
    if (!error.value) return null
    const fetchErr = error.value as unknown as {
      statusCode?: number
      status?: number
      data?: unknown
    }
    return {
      status: fetchErr.statusCode ?? fetchErr.status ?? 0,
      body: unwrapErrorBody(fetchErr.data) ?? {
        detail: {
          error: 'network_error',
          message: 'request did not reach the proxy',
          details: null,
        },
      },
    }
  })

  return { document: data, pending, error: normalizedError, refresh }
}
