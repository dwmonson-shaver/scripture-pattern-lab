import type {
  ConceptCreateRequest,
  ConceptSummary,
  ConceptsResponse,
  ConceptUpdateRequest,
  ConceptWriteResponse,
} from '~~/types/api'
import { unwrapErrorBody, type ProxyErrorShape } from '~~/composables/useQuery'

/**
 * Concept library state for the Slice 1 reader.
 *
 * `concepts` is the full registry surfaced for the library / search panel.
 * `create` and `update` write through the proxy then reload so the list and
 * the write response stay consistent (the backend is authoritative for
 * verification_state / origin — DEC-102, authored concepts are corrigible
 * priors, never auto-confirmed here). Component-local refs, no Pinia.
 */
function toProxyError(err: unknown): ProxyErrorShape {
  const fetchErr = err as { status?: number; statusCode?: number; data?: unknown }
  return {
    status: fetchErr.status ?? fetchErr.statusCode ?? 0,
    body: unwrapErrorBody(fetchErr.data) ?? {
      detail: {
        error: 'network_error',
        message: 'request did not reach the proxy',
        details: null,
      },
    },
  }
}

export const useConcepts = () => {
  const concepts = ref<ConceptSummary[]>([])
  const pending = ref(false)
  const error = ref<ProxyErrorShape | null>(null)

  const load = async (language?: string): Promise<void> => {
    pending.value = true
    error.value = null
    try {
      const res = await $fetch<ConceptsResponse>('/api/sp/concepts', {
        query: language ? { language } : undefined,
      })
      concepts.value = res.concepts
    } catch (err) {
      error.value = toProxyError(err)
    } finally {
      pending.value = false
    }
  }

  const create = async (req: ConceptCreateRequest): Promise<ConceptWriteResponse | null> => {
    error.value = null
    try {
      const created = await $fetch<ConceptWriteResponse>('/api/sp/concepts', {
        method: 'POST',
        body: req,
      })
      await load()
      return created
    } catch (err) {
      error.value = toProxyError(err)
      return null
    }
  }

  const update = async (
    name: string,
    req: ConceptUpdateRequest,
  ): Promise<ConceptWriteResponse | null> => {
    error.value = null
    try {
      const updated = await $fetch<ConceptWriteResponse>(
        `/api/sp/concepts/${encodeURIComponent(name)}`,
        { method: 'PATCH', body: req },
      )
      await load()
      return updated
    } catch (err) {
      error.value = toProxyError(err)
      return null
    }
  }

  /**
   * Case-insensitive name filter — the search-as-you-type helper the library
   * and the associate-concept search both use. Pure; does not touch state.
   */
  const search = (filter: string): ConceptSummary[] => {
    const f = filter.trim().toLowerCase()
    if (!f) return concepts.value
    return concepts.value.filter((c) => c.name.toLowerCase().includes(f))
  }

  return { concepts, pending, error, load, create, update, search }
}
