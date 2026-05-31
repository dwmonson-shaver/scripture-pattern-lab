import type { BackendErrorBody, QueryNLResponse } from '~~/types/api'

/**
 * Client-visible error shape. Parallel to but deliberately not identical
 * to `server/utils/backend.ts:BackendError`:
 * - Server-side (the proxy): `body: unknown` — upstream can be anything,
 *   the proxy doesn't validate, just mirrors.
 * - Client-side (this file): `body: BackendErrorBody` — typed to the
 *   project envelope because by the time the composable receives the
 *   error, the proxy has either passed through the canonical shape or
 *   synthesized a network_error envelope of the same shape.
 *
 * The asymmetry is intentional. If the two ever need to be unified, move
 * both into `types/backend.ts` (currently the placeholder) — but keep
 * the unknown/typed distinction so server-side can stay tolerant.
 */
export interface ProxyErrorShape {
  status: number
  body: BackendErrorBody
}

/**
 * Extract the canonical backend error envelope (`{ detail: {...} }`) from a
 * `$fetch` error's `.data`.
 *
 * The Nitro proxy re-throws backend errors via `createError({ data: envelope })`.
 * H3 serializes that with the payload nested under a SECOND `data` key, and
 * `ofetch` exposes the whole error response on `err.data` — so the canonical
 * envelope actually arrives at `err.data.data`, not `err.data`. Reading it one
 * level too shallow is what surfaced "no message / code unknown" to a user for
 * a backend error that carried a perfectly good message (Bucket J1-4).
 *
 * Returns the first shape that actually carries `detail` — the H3-wrapped inner
 * payload first, then the direct shape — else `null` so the caller synthesizes.
 */
export function unwrapErrorBody(raw: unknown): BackendErrorBody | null {
  if (!raw || typeof raw !== 'object') return null
  const inner = (raw as { data?: unknown }).data
  if (inner && typeof inner === 'object' && 'detail' in inner) {
    return inner as BackendErrorBody
  }
  if ('detail' in raw) return raw as BackendErrorBody
  return null
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
      // $fetch errors carry .status and .data (the proxy's error response).
      // The canonical envelope may be H3-wrapped one level deep — see
      // unwrapErrorBody. Fall back to a synthesized envelope only when no
      // `detail` is present at any level (genuine network/transport failure).
      const fetchErr = err as { status?: number; statusCode?: number; data?: unknown }
      error.value = {
        status: fetchErr.status ?? fetchErr.statusCode ?? 0,
        body: unwrapErrorBody(fetchErr.data) ?? {
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
