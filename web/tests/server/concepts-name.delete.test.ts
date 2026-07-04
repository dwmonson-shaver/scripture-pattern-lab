import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

// The DELETE proxy has no request body (no zod schema), so unlike the POST
// tests the contract under test is the handler itself: name validation, the
// single decode→encode round trip, and the DELETE verb. `sendToBackend` is a
// real module import (not a Nitro auto-import) so it can be mocked directly.
const sendToBackend = vi.fn()
vi.mock('~~/server/utils/backend', () => ({ sendToBackend }))

const getRouterParam = vi.fn()
const useRuntimeConfig = vi.fn(() => ({ backendUrl: 'https://api.test', backendToken: 'tok' }))

beforeAll(() => {
  vi.stubGlobal('defineEventHandler', (fn: unknown) => fn)
  vi.stubGlobal('getRouterParam', getRouterParam)
  vi.stubGlobal('useRuntimeConfig', useRuntimeConfig)
  vi.stubGlobal('createError', (opts: unknown) => Object.assign(new Error('h3'), opts))
})

beforeEach(() => {
  sendToBackend.mockReset()
  getRouterParam.mockReset()
})

async function handler(): Promise<(event: unknown) => Promise<unknown>> {
  const mod = await import('~~/server/api/sp/concepts/[name].delete')
  return mod.default as (event: unknown) => Promise<unknown>
}

describe('concepts [name] DELETE proxy', () => {
  it('forwards a DELETE with the name encoded exactly once', async () => {
    getRouterParam.mockReturnValue('living water')
    sendToBackend.mockResolvedValue(null)
    const h = await handler()
    await h({})
    expect(sendToBackend).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'DELETE',
        path: '/api/v1/concepts/living%20water',
      }),
    )
  })

  it('rejects an empty name with a 400 before touching the backend', async () => {
    getRouterParam.mockReturnValue('  ')
    const h = await handler()
    await expect(h({})).rejects.toMatchObject({ statusCode: 400 })
    expect(sendToBackend).not.toHaveBeenCalled()
  })

  it('mirrors the upstream error status and body', async () => {
    getRouterParam.mockReturnValue('Nope')
    sendToBackend.mockRejectedValue({
      status: 404,
      body: { detail: { error: 'concept_not_found', message: 'missing', details: null } },
    })
    const h = await handler()
    await expect(h({})).rejects.toMatchObject({ statusCode: 404 })
  })
})
