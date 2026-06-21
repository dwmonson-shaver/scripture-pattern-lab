import { describe, expect, it, vi } from 'vitest'
import { sendToBackend, type BackendError } from '~~/server/utils/backend'

const baseConfig = { url: 'https://backend.test', token: 'test-token-abc' }

function mockFetch(status: number, body: string | null): typeof globalThis.fetch {
  return vi.fn(async () =>
    body === null
      ? new Response(null, { status })
      : new Response(body, {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
  ) as unknown as typeof globalThis.fetch
}

describe('sendToBackend', () => {
  it('sends a PATCH with bearer auth + JSON body', async () => {
    const fetchSpy = mockFetch(200, JSON.stringify({ id: 7 }))
    const res = await sendToBackend({
      config: baseConfig,
      path: '/api/v1/marks/7',
      method: 'PATCH',
      body: { char_end: 30 },
      fetchImpl: fetchSpy,
    })
    expect(res).toEqual({ id: 7 })
    const [url, init] = (fetchSpy as unknown as { mock: { calls: [string, RequestInit][] } }).mock
      .calls[0]
    expect(url).toBe('https://backend.test/api/v1/marks/7')
    expect(init.method).toBe('PATCH')
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer test-token-abc')
    expect(headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body as string)).toEqual({ char_end: 30 })
  })

  it('sends a DELETE with no body and tolerates a 204 empty response', async () => {
    const fetchSpy = mockFetch(204, null)
    const res = await sendToBackend({
      config: baseConfig,
      path: '/api/v1/marks/7',
      method: 'DELETE',
      fetchImpl: fetchSpy,
    })
    expect(res).toBeNull()
    const [, init] = (fetchSpy as unknown as { mock: { calls: [string, RequestInit][] } }).mock
      .calls[0]
    expect(init.method).toBe('DELETE')
    expect(init.body).toBeUndefined()
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined()
  })

  it('throws a BackendError mirroring the upstream status + body on non-2xx', async () => {
    const upstream = { detail: { error: 'not_found', message: 'gone', details: null } }
    const fetchSpy = mockFetch(404, JSON.stringify(upstream))
    await expect(
      sendToBackend({
        config: baseConfig,
        path: '/api/v1/marks/9',
        method: 'DELETE',
        fetchImpl: fetchSpy,
      }),
    ).rejects.toMatchObject({ status: 404, body: upstream } satisfies Partial<BackendError>)
  })

  it('throws backend_misconfigured when the token is missing', async () => {
    await expect(
      sendToBackend({
        config: { url: 'https://backend.test', token: '' },
        path: '/api/v1/marks/1',
        method: 'DELETE',
        fetchImpl: mockFetch(200, '{}'),
      }),
    ).rejects.toMatchObject({ status: 500 })
  })
})
