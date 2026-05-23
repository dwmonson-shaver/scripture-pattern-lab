import { describe, expect, it, vi } from 'vitest'
import { proxyToBackend, type BackendError } from '~~/server/utils/backend'

const SAMPLE_NL_REQUEST = { nl_query: 'sequences where faith leads to hope' }
const SAMPLE_NL_RESPONSE = {
  query: 'faith > hope',
  validation: { status: 'supported', findings: [] },
  result: { candidates: [], stages_used: ['concept'] },
  explanation: { summary: 'ok', results: [] },
  translation: { confidence: 0.9, alternatives: [], explanation: '' },
}

const baseConfig = {
  url: 'https://backend.test',
  token: 'test-token-abc',
}

function mockFetchOk(body: unknown): typeof globalThis.fetch {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  ) as unknown as typeof globalThis.fetch
}

function mockFetchStatus(status: number, body: unknown): typeof globalThis.fetch {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  ) as unknown as typeof globalThis.fetch
}

describe('proxyToBackend', () => {
  it('forwards the body to the backend with bearer auth', async () => {
    const fetchSpy = mockFetchOk(SAMPLE_NL_RESPONSE)
    await proxyToBackend({
      config: baseConfig,
      path: '/api/v1/query/nl',
      body: SAMPLE_NL_REQUEST,
      fetchImpl: fetchSpy,
    })

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const [url, init] = (fetchSpy as unknown as { mock: { calls: [string, RequestInit][] } }).mock
      .calls[0]
    expect(url).toBe('https://backend.test/api/v1/query/nl')
    expect(init.method).toBe('POST')
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer test-token-abc')
    expect(headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body as string)).toEqual(SAMPLE_NL_REQUEST)
  })

  it('returns the backend body on 2xx', async () => {
    const fetchSpy = mockFetchOk(SAMPLE_NL_RESPONSE)
    const result = await proxyToBackend({
      config: baseConfig,
      path: '/api/v1/query/nl',
      body: SAMPLE_NL_REQUEST,
      fetchImpl: fetchSpy,
    })
    expect(result).toEqual(SAMPLE_NL_RESPONSE)
  })

  it('throws BackendError with upstream status + body on 4xx', async () => {
    const upstreamErrorBody = {
      detail: {
        error: 'validation_unsupported',
        message: 'inverse not supported',
        details: { findings: [{ code: 'UNSUPPORTED_INVERSE' }] },
      },
    }
    const fetchSpy = mockFetchStatus(422, upstreamErrorBody)

    await expect(
      proxyToBackend({
        config: baseConfig,
        path: '/api/v1/query/nl',
        body: SAMPLE_NL_REQUEST,
        fetchImpl: fetchSpy,
      }),
    ).rejects.toMatchObject({ status: 422, body: upstreamErrorBody })
  })

  it('throws BackendError with upstream 503 envelope unchanged', async () => {
    const upstreamErrorBody = {
      detail: {
        error: 'llm_unavailable',
        message: 'ANTHROPIC_API_KEY missing',
        details: null,
      },
    }
    const fetchSpy = mockFetchStatus(503, upstreamErrorBody)

    await expect(
      proxyToBackend({
        config: baseConfig,
        path: '/api/v1/query/nl',
        body: SAMPLE_NL_REQUEST,
        fetchImpl: fetchSpy,
      }),
    ).rejects.toMatchObject({ status: 503, body: upstreamErrorBody })
  })

  it('rejects when backend URL is unset', async () => {
    const fetchSpy = mockFetchOk(SAMPLE_NL_RESPONSE)
    await expect(
      proxyToBackend({
        config: { url: '', token: 'tok' },
        path: '/api/v1/query/nl',
        body: SAMPLE_NL_REQUEST,
        fetchImpl: fetchSpy,
      }),
    ).rejects.toMatchObject({
      status: 500,
      body: { detail: { error: 'backend_misconfigured' } },
    })
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('rejects when backend token is unset', async () => {
    const fetchSpy = mockFetchOk(SAMPLE_NL_RESPONSE)
    await expect(
      proxyToBackend({
        config: { url: 'https://backend.test', token: '' },
        path: '/api/v1/query/nl',
        body: SAMPLE_NL_REQUEST,
        fetchImpl: fetchSpy,
      }),
    ).rejects.toMatchObject({
      status: 500,
      body: { detail: { error: 'backend_misconfigured' } },
    })
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('rejects with backend_unreachable on network error', async () => {
    const fetchSpy = vi.fn(async () => {
      throw new Error('connection refused')
    }) as unknown as typeof globalThis.fetch

    await expect(
      proxyToBackend({
        config: baseConfig,
        path: '/api/v1/query/nl',
        body: SAMPLE_NL_REQUEST,
        fetchImpl: fetchSpy,
      }),
    ).rejects.toMatchObject({
      status: 502,
      body: { detail: { error: 'backend_unreachable' } },
    })
  })

  it('rejects with backend_response_not_json when upstream returns garbage', async () => {
    const fetchSpy = vi.fn(
      async () =>
        new Response('not json', {
          status: 200,
          headers: { 'Content-Type': 'text/plain' },
        }),
    ) as unknown as typeof globalThis.fetch

    await expect(
      proxyToBackend({
        config: baseConfig,
        path: '/api/v1/query/nl',
        body: SAMPLE_NL_REQUEST,
        fetchImpl: fetchSpy,
      }),
    ).rejects.toMatchObject({
      status: 502,
      body: { detail: { error: 'backend_response_not_json' } },
    })
  })

  it('strips trailing slash from backend URL before concatenating path', async () => {
    const fetchSpy = mockFetchOk(SAMPLE_NL_RESPONSE)
    await proxyToBackend({
      config: { url: 'https://backend.test/', token: 'tok' },
      path: '/api/v1/query/nl',
      body: SAMPLE_NL_REQUEST,
      fetchImpl: fetchSpy,
    })
    const [url] = (fetchSpy as unknown as { mock: { calls: [string][] } }).mock.calls[0]
    expect(url).toBe('https://backend.test/api/v1/query/nl')
  })
})
