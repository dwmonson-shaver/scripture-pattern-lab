import type {
  ConnectionCreateRequest,
  ConnectionOut,
  ConnectionsResponse,
} from '~~/types/api'
import { unwrapErrorBody, type ProxyErrorShape } from '~~/composables/useQuery'

/**
 * Typed-connection state for the Slice 2 reader.
 *
 * `connections` is the full list surfaced in the panel. `create` and `remove`
 * write through the proxy then reload so the list stays consistent. Connections
 * are corrigible human-authored priors (the backend never auto-promotes them);
 * this composable only carries the authored structure. Component-local refs,
 * no Pinia.
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

export const useConnections = () => {
  const connections = ref<ConnectionOut[]>([])
  const pending = ref(false)
  const error = ref<ProxyErrorShape | null>(null)

  const load = async (): Promise<void> => {
    pending.value = true
    error.value = null
    try {
      const res = await $fetch<ConnectionsResponse>('/api/sp/connections')
      connections.value = res.connections
    } catch (err) {
      error.value = toProxyError(err)
    } finally {
      pending.value = false
    }
  }

  const create = async (req: ConnectionCreateRequest): Promise<ConnectionOut | null> => {
    error.value = null
    try {
      const created = await $fetch<ConnectionOut>('/api/sp/connections', {
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

  const remove = async (id: number): Promise<boolean> => {
    error.value = null
    try {
      await $fetch(`/api/sp/connections/${id}`, { method: 'DELETE' })
      await load()
      return true
    } catch (err) {
      error.value = toProxyError(err)
      return false
    }
  }

  return { connections, pending, error, load, create, remove }
}
