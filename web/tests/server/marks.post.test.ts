import { beforeAll, describe, expect, it, vi } from 'vitest'

beforeAll(() => {
  vi.stubGlobal('defineEventHandler', (fn: unknown) => fn)
  vi.stubGlobal('readValidatedBody', vi.fn())
  vi.stubGlobal('useRuntimeConfig', vi.fn())
  vi.stubGlobal('createError', vi.fn())
})

const base = {
  book: 'rom',
  chapter: 8,
  verse_start: 24,
  verse_end: 24,
  char_start: 0,
  char_end: 18,
}

describe('marks POST requestSchema', () => {
  it('accepts a single-verse mark with no concept (Just highlight)', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/index.post')
    const parsed = requestSchema.parse(base)
    expect(parsed.concept_names).toBeUndefined()
    expect(parsed.verse_start).toBe(24)
  })

  it('accepts a mark with concept names', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/index.post')
    const parsed = requestSchema.parse({ ...base, concept_names: ['Hope'] })
    expect(parsed.concept_names).toEqual(['Hope'])
  })

  it('accepts a cross-verse mark (DEC-143)', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/index.post')
    const parsed = requestSchema.parse({
      ...base,
      verse_start: 24,
      verse_end: 25,
      char_start: 5,
      char_end: 3,
    })
    expect(parsed.verse_end).toBe(25)
  })

  it('rejects verse_end < verse_start', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/index.post')
    expect(() =>
      requestSchema.parse({ ...base, verse_start: 25, verse_end: 24 }),
    ).toThrow()
  })

  it('rejects a zero-width single-verse span', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/index.post')
    expect(() =>
      requestSchema.parse({ ...base, char_start: 5, char_end: 5 }),
    ).toThrow()
  })

  it('rejects a missing book', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/index.post')
    const { book: _book, ...noBook } = base
    expect(() => requestSchema.parse(noBook)).toThrow()
  })
})

describe('marks PATCH requestSchema', () => {
  it('accepts a span-only partial update (handle drag)', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/[id].patch')
    const parsed = requestSchema.parse({ char_start: 4, char_end: 22 })
    expect(parsed.char_start).toBe(4)
    expect(parsed.concept_names).toBeUndefined()
  })

  it('accepts a concept-only partial update', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/[id].patch')
    const parsed = requestSchema.parse({ concept_names: ['Hope', 'Patience'] })
    expect(parsed.concept_names).toEqual(['Hope', 'Patience'])
  })

  it('accepts an empty body (no-op patch)', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/[id].patch')
    expect(requestSchema.parse({})).toEqual({})
  })

  it('rejects a non-integer char offset', async () => {
    const { requestSchema } = await import('~~/server/api/sp/marks/[id].patch')
    expect(() => requestSchema.parse({ char_start: 1.5 })).toThrow()
  })
})

describe('concepts PATCH requestSchema', () => {
  it('accepts a partial authored-field update', async () => {
    const { requestSchema } = await import('~~/server/api/sp/concepts/[name].patch')
    const parsed = requestSchema.parse({ authored_color: '#C44A63' })
    expect(parsed.authored_color).toBe('#C44A63')
  })

  it('rejects an invalid polarity', async () => {
    const { requestSchema } = await import('~~/server/api/sp/concepts/[name].patch')
    expect(() => requestSchema.parse({ authored_polarity: '!' })).toThrow()
  })
})
