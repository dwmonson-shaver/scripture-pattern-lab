import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useMarks } from '~~/composables/useMarks'
import type { MarkCreateRequest, MarkOut, MarksResponse } from '~~/types/api'

const SCOPE = { corpus: 'nt', book: 'rom', chapter: 8, version: 'kjv' }

const CREATE_REQ: MarkCreateRequest = {
  book: 'rom',
  chapter: 8,
  corpus_id: 'nt',
  version_code: 'kjv',
  verse_start: 24,
  verse_end: 24,
  char_start: 0,
  char_end: 18,
}

const MARK: MarkOut = {
  id: 1,
  corpus_id: 'nt',
  book: 'rom',
  chapter: 8,
  verse_start: 24,
  verse_end: 24,
  char_start: 0,
  char_end: 18,
  version_code: 'kjv',
  actor: 'user',
  concept_names: [],
}

let fetchStub: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchStub = vi.fn()
  ;(globalThis as Record<string, unknown>).$fetch = fetchStub
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useMarks', () => {
  it('loadForChapter populates marks and records the scope', async () => {
    fetchStub.mockResolvedValue({ marks: [MARK] } satisfies MarksResponse)
    const m = useMarks()
    await m.loadForChapter(SCOPE)
    expect(m.marks.value).toEqual([MARK])
    expect(m.scope.value).toEqual(SCOPE)
    expect(fetchStub).toHaveBeenCalledWith('/api/sp/marks', {
      query: { corpus: 'nt', book: 'rom', chapter: 8, version: 'kjv' },
    })
  })

  it('create posts the request then reloads the chapter marks', async () => {
    const created = { ...MARK, id: 2, concept_names: ['Hope'] }
    // 1) create POST  2) reload GET
    fetchStub
      .mockResolvedValueOnce(created)
      .mockResolvedValueOnce({ marks: [MARK, created] })
    const m = useMarks()
    m.scope.value = SCOPE
    const result = await m.create({ ...CREATE_REQ, concept_names: ['Hope'] })
    expect(result).toEqual(created)
    expect(m.marks.value).toContainEqual(created)
    expect(fetchStub).toHaveBeenNthCalledWith(
      1,
      '/api/sp/marks',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('remove deletes then reloads', async () => {
    fetchStub.mockResolvedValueOnce(null).mockResolvedValueOnce({ marks: [] })
    const m = useMarks()
    m.scope.value = SCOPE
    const ok = await m.remove(1)
    expect(ok).toBe(true)
    expect(m.marks.value).toEqual([])
    expect(fetchStub).toHaveBeenNthCalledWith(1, '/api/sp/marks/1', {
      method: 'DELETE',
    })
  })

  it('normalizes a backend error to ProxyErrorShape', async () => {
    fetchStub.mockRejectedValue({
      status: 422,
      data: { detail: { error: 'overlapping_mark', message: 'overlaps', details: null } },
    })
    const m = useMarks()
    const result = await m.create(CREATE_REQ)
    expect(result).toBeNull()
    expect(m.error.value?.status).toBe(422)
    expect(m.error.value?.body.detail.error).toBe('overlapping_mark')
  })
})
