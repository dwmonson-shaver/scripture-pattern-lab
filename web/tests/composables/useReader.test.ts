import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useReader } from '~~/composables/useReader'
import type { ChapterReadResponse, VersionsResponse } from '~~/types/api'

const CHAPTER: ChapterReadResponse = {
  corpus_id: 'nt',
  book: 'rom',
  book_display: 'Romans',
  chapter: 8,
  version_code: 'kjv',
  verses: [
    { verse: 24, reference: 'Romans 8:24', english_text: 'we are saved by hope', greek_tokens: [] },
  ],
}

let fetchStub: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchStub = vi.fn()
  ;(globalThis as Record<string, unknown>).$fetch = fetchStub
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useReader', () => {
  it('defaults to the prototype anchor nt / rom / 8 / kjv', () => {
    const r = useReader()
    expect(r.corpus.value).toBe('nt')
    expect(r.book.value).toBe('rom')
    expect(r.chapter.value).toBe(8)
    expect(r.version.value).toBe('kjv')
    expect(r.greekOn.value).toBe(false)
  })

  it('loadChapter fetches the current target with the version query', async () => {
    fetchStub.mockResolvedValue(CHAPTER)
    const r = useReader()
    await r.loadChapter()
    expect(fetchStub).toHaveBeenCalledWith('/api/sp/read/nt/rom/8', {
      query: { version: 'kjv' },
    })
    expect(r.chapterData.value).toEqual(CHAPTER)
    expect(r.pending.value).toBe(false)
  })

  it('loadVersions populates the versions list', async () => {
    fetchStub.mockResolvedValue({
      versions: [{ code: 'kjv', name: 'King James Version', is_public_domain: true }],
    } satisfies VersionsResponse)
    const r = useReader()
    await r.loadVersions()
    expect(r.versions.value[0].code).toBe('kjv')
  })

  it('nextChapter / prevChapter step the chapter and clamp at 1', () => {
    const r = useReader({ chapter: 2 })
    r.nextChapter()
    expect(r.chapter.value).toBe(3)
    r.prevChapter()
    r.prevChapter()
    expect(r.chapter.value).toBe(1)
    r.prevChapter()
    expect(r.chapter.value).toBe(1)
  })

  it('normalizes a fetch failure to ProxyErrorShape and clears chapter', async () => {
    fetchStub.mockRejectedValue({
      status: 404,
      data: { detail: { error: 'chapter_not_found', message: 'no', details: null } },
    })
    const r = useReader()
    await r.loadChapter()
    expect(r.chapterData.value).toBeNull()
    expect(r.error.value?.body.detail.error).toBe('chapter_not_found')
  })
})
