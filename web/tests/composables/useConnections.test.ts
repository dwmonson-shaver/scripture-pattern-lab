import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useConnections } from '~~/composables/useConnections'
import type { ConnectionOut, ConnectionsResponse } from '~~/types/api'

function conn(id: number, members: string[], types: ConnectionOut['types']): ConnectionOut {
  return { id, note: null, actor: 'local', members, types }
}

let fetchStub: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchStub = vi.fn()
  ;(globalThis as Record<string, unknown>).$fetch = fetchStub
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useConnections', () => {
  it('load populates the connection list', async () => {
    fetchStub.mockResolvedValue({
      connections: [conn(1, ['righteousness', 'faith'], ['interchange'])],
    } satisfies ConnectionsResponse)
    const c = useConnections()
    await c.load()
    expect(c.connections.value[0].members).toEqual(['righteousness', 'faith'])
  })

  it('create posts the ordered members + types then reloads', async () => {
    const created = conn(7, ['righteousness', 'faith'], ['interchange'])
    fetchStub
      .mockResolvedValueOnce(created)
      .mockResolvedValueOnce({ connections: [created] })
    const c = useConnections()
    const result = await c.create({
      member_names: ['righteousness', 'faith'],
      types: ['interchange'],
      note: 'Rom 1:17',
    })
    expect(result?.id).toBe(7)
    expect(fetchStub).toHaveBeenNthCalledWith(
      1,
      '/api/sp/connections',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(c.connections.value).toHaveLength(1)
  })

  it('remove deletes by id then reloads', async () => {
    fetchStub.mockResolvedValueOnce(null).mockResolvedValueOnce({ connections: [] })
    const c = useConnections()
    const ok = await c.remove(7)
    expect(ok).toBe(true)
    expect(fetchStub).toHaveBeenNthCalledWith(
      1,
      '/api/sp/connections/7',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('surfaces a backend error as ProxyErrorShape', async () => {
    fetchStub.mockRejectedValue({
      status: 404,
      data: { detail: { error: 'unknown_concept', message: 'nope', details: null } },
    })
    const c = useConnections()
    const result = await c.create({ member_names: ['a', 'b'], types: ['sequence'] })
    expect(result).toBeNull()
    expect(c.error.value?.body.detail.error).toBe('unknown_concept')
  })
})
