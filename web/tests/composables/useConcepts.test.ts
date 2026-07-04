import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useConcepts } from '~~/composables/useConcepts'
import type { ConceptSummary, ConceptsResponse } from '~~/types/api'

function concept(name: string, color: string | null = null): ConceptSummary {
  return {
    name,
    description: null,
    verification_state: 'unverified',
    lemma_count: 0,
    lemmas: [],
    authored_color: color,
    authored_polarity: null,
    authored_opposite_name: null,
  }
}

let fetchStub: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchStub = vi.fn()
  ;(globalThis as Record<string, unknown>).$fetch = fetchStub
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useConcepts', () => {
  it('load populates the concept list', async () => {
    fetchStub.mockResolvedValue({
      concepts: [concept('Hope'), concept('Patience')],
    } satisfies ConceptsResponse)
    const c = useConcepts()
    await c.load()
    expect(c.concepts.value.map((x) => x.name)).toEqual(['Hope', 'Patience'])
  })

  it('search filters case-insensitively by name', async () => {
    fetchStub.mockResolvedValue({ concepts: [concept('Hope'), concept('Patience')] })
    const c = useConcepts()
    await c.load()
    expect(c.search('pat').map((x) => x.name)).toEqual(['Patience'])
    expect(c.search('').length).toBe(2)
  })

  it('create posts then reloads the list', async () => {
    const written = {
      name: 'Glory',
      description: null,
      origin: 'human_authored',
      verification_state: 'unverified',
      authored_color: '#B98A1E',
      authored_polarity: '+',
      authored_opposite_name: 'Shame',
    }
    fetchStub
      .mockResolvedValueOnce(written) // POST
      .mockResolvedValueOnce({ concepts: [concept('Glory', '#B98A1E')] }) // reload
    const c = useConcepts()
    const result = await c.create({ name: 'Glory', authored_color: '#B98A1E' })
    expect(result).toEqual(written)
    expect(c.concepts.value[0].name).toBe('Glory')
    expect(fetchStub).toHaveBeenNthCalledWith(
      1,
      '/api/sp/concepts',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('update patches the named concept then reloads', async () => {
    fetchStub
      .mockResolvedValueOnce({ name: 'Hope' })
      .mockResolvedValueOnce({ concepts: [concept('Hope', '#E0A12E')] })
    const c = useConcepts()
    await c.update('Hope', { authored_color: '#E0A12E' })
    expect(fetchStub).toHaveBeenNthCalledWith(
      1,
      '/api/sp/concepts/Hope',
      expect.objectContaining({ method: 'PATCH' }),
    )
    expect(c.concepts.value[0].authored_color).toBe('#E0A12E')
  })

  it('surfaces a backend error as ProxyErrorShape', async () => {
    fetchStub.mockRejectedValue({
      status: 409,
      data: { detail: { error: 'concept_exists', message: 'dup', details: null } },
    })
    const c = useConcepts()
    const result = await c.create({ name: 'Hope' })
    expect(result).toBeNull()
    expect(c.error.value?.body.detail.error).toBe('concept_exists')
  })

  it('remove deletes the named concept then reloads', async () => {
    fetchStub
      .mockResolvedValueOnce(null) // DELETE (204, empty)
      .mockResolvedValueOnce({ concepts: [] }) // reload
    const c = useConcepts()
    const ok = await c.remove('Hope')
    expect(ok).toBe(true)
    expect(fetchStub).toHaveBeenNthCalledWith(
      1,
      '/api/sp/concepts/Hope',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(c.concepts.value).toEqual([])
  })

  it('remove url-encodes the concept name', async () => {
    fetchStub.mockResolvedValueOnce(null).mockResolvedValueOnce({ concepts: [] })
    const c = useConcepts()
    await c.remove('living water')
    expect(fetchStub).toHaveBeenNthCalledWith(
      1,
      '/api/sp/concepts/living%20water',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('remove surfaces a 404 as ProxyErrorShape and reports failure', async () => {
    fetchStub.mockRejectedValue({
      status: 404,
      data: { detail: { error: 'concept_not_found', message: 'missing', details: null } },
    })
    const c = useConcepts()
    const ok = await c.remove('Nope')
    expect(ok).toBe(false)
    expect(c.error.value?.body.detail.error).toBe('concept_not_found')
  })
})
