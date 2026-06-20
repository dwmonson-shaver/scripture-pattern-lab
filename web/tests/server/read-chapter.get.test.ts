import { beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * Handler test for server/api/sp/read/[corpus]/[book]/[chapter].get.ts.
 * Mirrors tests/server/concept-document.get.test.ts: stub the Nitro
 * auto-imports, then drive the registered handler with a mock event.
 */
interface MockEvent {
  routerParams: Record<string, string>
  query: Record<string, string>
  runtimeConfig: { backendUrl: string; backendToken: string }
}

const globalScope = globalThis as Record<string, unknown>

let lastHandler: ((event: MockEvent) => Promise<unknown>) | null = null
let lastCreateErrorCall: { statusCode: number; data: unknown } | null = null

beforeEach(() => {
  lastHandler = null
  lastCreateErrorCall = null

  globalScope.defineEventHandler = <T,>(handler: (event: MockEvent) => Promise<T>) => {
    lastHandler = handler as (event: MockEvent) => Promise<unknown>
    return handler
  }
  globalScope.getRouterParam = (
    event: MockEvent,
    key: string,
    opts?: { decode?: boolean },
  ) => {
    const raw = event.routerParams[key]
    return raw === undefined ? undefined : opts?.decode ? decodeURIComponent(raw) : raw
  }
  globalScope.getQuery = (event: MockEvent) => event.query
  globalScope.useRuntimeConfig = (event: MockEvent) => event.runtimeConfig
  globalScope.createError = (opts: { statusCode: number; data: unknown }) => {
    lastCreateErrorCall = opts
    const err = new Error(`HTTP ${opts.statusCode}`)
    Object.assign(err, opts)
    return err
  }
})

async function loadHandler() {
  vi.resetModules()
  await import('~~/server/api/sp/read/[corpus]/[book]/[chapter].get')
  if (!lastHandler) throw new Error('handler not registered')
  return lastHandler
}

function makeEvent(
  routerParams: Record<string, string>,
  query: Record<string, string> = {},
): MockEvent {
  return {
    routerParams,
    query,
    runtimeConfig: { backendUrl: 'https://backend.test', backendToken: 'tok' },
  }
}

describe('GET /api/sp/read/:corpus/:book/:chapter', () => {
  it('proxies the chapter and forwards the version query', async () => {
    const upstream = { corpus_id: 'nt', book: 'rom', chapter: 8, verses: [] }
    const fetchSpy = vi.fn(
      async () =>
        new Response(JSON.stringify(upstream), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    )
    globalScope.fetch = fetchSpy as unknown as typeof globalThis.fetch

    const handler = await loadHandler()
    const result = await handler(
      makeEvent({ corpus: 'nt', book: 'rom', chapter: '8' }, { version: 'kjv' }),
    )
    expect(result).toEqual(upstream)
    const [url, init] = fetchSpy.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('https://backend.test/api/v1/read/nt/rom/8?version=kjv')
    expect(init.method).toBe('GET')
  })

  it('omits the query string when no version is given', async () => {
    const fetchSpy = vi.fn(
      async () =>
        new Response('{"verses":[]}', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    )
    globalScope.fetch = fetchSpy as unknown as typeof globalThis.fetch

    const handler = await loadHandler()
    await handler(makeEvent({ corpus: 'nt', book: 'rom', chapter: '8' }))
    const [url] = fetchSpy.mock.calls[0] as unknown as [string]
    expect(url).toBe('https://backend.test/api/v1/read/nt/rom/8')
  })

  it('rejects a non-numeric chapter with 400', async () => {
    const handler = await loadHandler()
    await expect(
      handler(makeEvent({ corpus: 'nt', book: 'rom', chapter: 'eight' })),
    ).rejects.toThrow()
    expect(lastCreateErrorCall?.statusCode).toBe(400)
  })

  it('mirrors an upstream 404 to the browser', async () => {
    const body = { detail: { error: 'chapter_not_found', message: 'no', details: null } }
    const fetchSpy = vi.fn(
      async () =>
        new Response(JSON.stringify(body), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }),
    )
    globalScope.fetch = fetchSpy as unknown as typeof globalThis.fetch

    const handler = await loadHandler()
    await expect(
      handler(makeEvent({ corpus: 'nt', book: 'zzz', chapter: '99' })),
    ).rejects.toThrow()
    expect(lastCreateErrorCall?.statusCode).toBe(404)
    expect(lastCreateErrorCall?.data).toEqual(body)
  })
})
