import type { BackendErrorBody, QueryNLResponse } from '~~/types/backend'

export interface ProxyErrorShape {
  status: number
  body: BackendErrorBody
}

/**
 * State + run() for the flagship NL query.
 *
 * - `nlQuery` — bound to the textbox via v-model
 * - `pending` — true between submit and response/error
 * - `response` — populated on 2xx; null otherwise
 * - `error` — populated on 4xx/5xx/network; null otherwise
 * - `run()` — submits the current `nlQuery` to /api/sp/query/nl
 *
 * Component-local state only — no Pinia (deferred until cross-page state
 * actually appears).
 */
export const useQuery = () => {
  const nlQuery = ref('')
  const pending = ref(false)
  const response = ref<QueryNLResponse | null>(null)
  const error = ref<ProxyErrorShape | null>(null)

  const run = async (): Promise<void> => {
    if (!nlQuery.value.trim() || pending.value) return
    pending.value = true
    error.value = null
    response.value = null
    try {
      response.value = await $fetch<QueryNLResponse>('/api/sp/query/nl', {
        method: 'POST',
        body: { nl_query: nlQuery.value },
      })
    } catch (err) {
      // $fetch errors carry .status and .data (the upstream body).
      const fetchErr = err as { status?: number; statusCode?: number; data?: BackendErrorBody }
      error.value = {
        status: fetchErr.status ?? fetchErr.statusCode ?? 0,
        body: fetchErr.data ?? {
          detail: {
            error: 'network_error',
            message: 'request did not reach the proxy',
            details: null,
          },
        },
      }
    } finally {
      pending.value = false
    }
  }

  return { nlQuery, pending, response, error, run }
}
