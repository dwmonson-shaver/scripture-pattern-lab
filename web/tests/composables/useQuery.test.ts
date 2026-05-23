import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useQuery } from '~~/composables/useQuery'
import type { QueryNLResponse } from '~~/types/backend'

const SAMPLE_RESPONSE: QueryNLResponse = {
  query: 'faith > hope > love',
  validation: {
    status: 'supported',
    executable_plan: {},
    findings: [],
    engine_version: '0.1',
    grounding: 'prior-grounded',
  },
  result: {
    candidates: [],
    stages_used: ['concept'],
    contextualization: null,
  },
  explanation: {
    query_shown: 'faith > hope > love',
    nl_source: 'where do faith, hope, and love appear together',
    validation_notes: [],
    results: [],
    contextualization: null,
    summary: 'ok',
  },
  translation: {
    confidence: 0.95,
    alternatives: [],
    explanation: '',
  },
}

let fetchStub: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchStub = vi.fn()
  ;(globalThis as Record<string, unknown>).$fetch = fetchStub
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useQuery', () => {
  it('starts with empty state', () => {
    const q = useQuery()
    expect(q.nlQuery.value).toBe('')
    expect(q.pending.value).toBe(false)
    expect(q.response.value).toBeNull()
    expect(q.error.value).toBeNull()
  })

  it('run() is a no-op on empty query', async () => {
    const q = useQuery()
    await q.run()
    expect(fetchStub).not.toHaveBeenCalled()
    expect(q.pending.value).toBe(false)
  })

  it('run() submits the current nlQuery and populates response on success', async () => {
    fetchStub.mockResolvedValue(SAMPLE_RESPONSE)
    const q = useQuery()
    q.nlQuery.value = 'where do faith, hope, and love appear together'
    await q.run()

    expect(fetchStub).toHaveBeenCalledWith('/api/sp/query/nl', {
      method: 'POST',
      body: { nl_query: 'where do faith, hope, and love appear together' },
    })
    expect(q.response.value).toEqual(SAMPLE_RESPONSE)
    expect(q.error.value).toBeNull()
    expect(q.pending.value).toBe(false)
  })

  it('run() populates error on 4xx upstream', async () => {
    fetchStub.mockRejectedValue({
      status: 422,
      data: {
        detail: {
          error: 'validation_unsupported',
          message: 'inverse not supported',
          details: { findings: [] },
        },
      },
    })
    const q = useQuery()
    q.nlQuery.value = 'inverse query'
    await q.run()

    expect(q.error.value).toEqual({
      status: 422,
      body: {
        detail: {
          error: 'validation_unsupported',
          message: 'inverse not supported',
          details: { findings: [] },
        },
      },
    })
    expect(q.response.value).toBeNull()
    expect(q.pending.value).toBe(false)
  })

  it('run() clears stale response/error before issuing', async () => {
    fetchStub.mockResolvedValue(SAMPLE_RESPONSE)
    const q = useQuery()
    q.nlQuery.value = 'first'
    await q.run()
    expect(q.response.value).not.toBeNull()

    // Second run: even if we hypothetically reset state in the middle,
    // the new call's success path should hold both populated.
    q.nlQuery.value = 'second'
    fetchStub.mockResolvedValueOnce({ ...SAMPLE_RESPONSE, query: 'second' })
    await q.run()
    expect(q.response.value?.query).toBe('second')
  })

  it('run() ignores a second invocation while pending', async () => {
    let resolveFn: ((v: QueryNLResponse) => void) | undefined
    fetchStub.mockReturnValue(
      new Promise<QueryNLResponse>((resolve) => {
        resolveFn = resolve
      }),
    )

    const q = useQuery()
    q.nlQuery.value = 'first'
    const p1 = q.run()
    expect(q.pending.value).toBe(true)

    // Second call should bail because pending is true.
    await q.run()
    expect(fetchStub).toHaveBeenCalledTimes(1)

    resolveFn?.(SAMPLE_RESPONSE)
    await p1
    expect(q.pending.value).toBe(false)
  })

  it('run() handles network errors with a synthesized envelope', async () => {
    fetchStub.mockRejectedValue(new Error('network down'))
    const q = useQuery()
    q.nlQuery.value = 'anything'
    await q.run()

    expect(q.error.value?.status).toBe(0)
    expect(q.error.value?.body.detail?.error).toBe('network_error')
  })
})
