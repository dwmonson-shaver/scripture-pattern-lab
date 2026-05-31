import { describe, expect, it, vi, beforeEach } from 'vitest'

/**
 * The proxy route at `server/api/sp/concepts/[name]/document.get.ts`
 * uses Nitro auto-imports (`defineEventHandler`, `getRouterParam`,
 * `createError`, `useRuntimeConfig`). Stub those on globalThis before
 * importing the handler; this mirrors `tests/server/nl.post.test.ts`.
 */

interface MockEvent {
  routerParams: Record<string, string>
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
  globalScope.getRouterParam = (event: MockEvent, key: string) => event.routerParams[key]
  globalScope.useRuntimeConfig = (event: MockEvent) => event.runtimeConfig
  globalScope.createError = (opts: { statusCode: number; data: unknown }) => {
    lastCreateErrorCall = opts
    const err = new Error(`HTTP ${opts.statusCode}`)
    Object.assign(err, opts)
    return err
  }
})

async function loadHandler() {
  // Fresh import per test (no cache) so the module-level
  // `defineEventHandler` is re-invoked under the current stub.
  vi.resetModules()
  await import('~~/server/api/sp/concepts/[name]/document.get')
  if (!lastHandler) throw new Error('handler not registered')
  return lastHandler
}

function makeEvent(name: string): MockEvent {
  return {
    routerParams: { name },
    runtimeConfig: {
      backendUrl: 'https://backend.test',
      backendToken: 'test-token',
    },
  }
}

describe('GET /api/sp/concepts/:name/document', () => {
  it('proxies the backend GET response on success', async () => {
    const upstreamBody = {
      concept_name: 'humility',
      short_summary: 'machine/lexicon-sourced — unverified — starting prior',
      part1_comparative: {
        english_term: 'humility',
        rows: [],
        generated_from: ['TBESG'],
      },
      part1_educational: null,
      part2_grouping_placeholder: null,
    }
    const fetchSpy = vi.fn(
      async () =>
        new Response(JSON.stringify(upstreamBody), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    )
    globalScope.fetch = fetchSpy as unknown as typeof globalThis.fetch

    const handler = await loadHandler()
    const result = await handler(makeEvent('humility'))
    expect(result).toEqual(upstreamBody)
    const [url, init] = fetchSpy.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('https://backend.test/api/v1/concepts/humility/document')
    expect(init.method).toBe('GET')
    expect((init.headers as Record<string, string>).Authorization).toBe(
      'Bearer test-token',
    )
  })

  it('URL-encodes concept names with spaces and Greek characters', async () => {
    const fetchSpy = vi.fn(
      async () =>
        new Response('{"concept_name":"foo","short_summary":"","part1_comparative":{"english_term":"foo","rows":[],"generated_from":[]}}', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    )
    globalScope.fetch = fetchSpy as unknown as typeof globalThis.fetch

    const handler = await loadHandler()
    await handler(makeEvent('fear of the lord'))
    const [url] = fetchSpy.mock.calls[0] as unknown as [string]
    expect(url).toBe(
      'https://backend.test/api/v1/concepts/fear%20of%20the%20lord/document',
    )
  })

  it('rejects empty / whitespace concept names with 400', async () => {
    const handler = await loadHandler()
    await expect(handler(makeEvent(''))).rejects.toThrow()
    expect(lastCreateErrorCall?.statusCode).toBe(400)
    expect(
      (lastCreateErrorCall?.data as { detail: { error: string } }).detail.error,
    ).toBe('invalid_request')
  })

  it('mirrors upstream 404 (document not found) to the browser', async () => {
    const upstreamErrorBody = {
      detail: {
        error: 'document_not_found',
        message: 'no Conceptual Document exists for concept \'humility\'',
        details: { concept_name: 'humility' },
      },
    }
    const fetchSpy = vi.fn(
      async () =>
        new Response(JSON.stringify(upstreamErrorBody), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }),
    )
    globalScope.fetch = fetchSpy as unknown as typeof globalThis.fetch

    const handler = await loadHandler()
    await expect(handler(makeEvent('humility'))).rejects.toThrow()
    expect(lastCreateErrorCall?.statusCode).toBe(404)
    expect(lastCreateErrorCall?.data).toEqual(upstreamErrorBody)
  })
})
