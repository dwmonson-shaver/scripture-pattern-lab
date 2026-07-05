import { beforeAll, describe, expect, it, vi } from 'vitest'

// Mirror concepts.post.test.ts: stub the Nitro auto-imports referenced at load
// time, then assert the exported requestSchema's zod contract directly.
beforeAll(() => {
  vi.stubGlobal('defineEventHandler', (fn: unknown) => fn)
  vi.stubGlobal('readValidatedBody', vi.fn())
  vi.stubGlobal('useRuntimeConfig', vi.fn())
  vi.stubGlobal('createError', vi.fn())
})

describe('connections POST requestSchema', () => {
  it('accepts two members + one type', async () => {
    const { requestSchema } = await import('~~/server/api/sp/connections/index.post')
    const parsed = requestSchema.parse({
      member_names: ['righteousness', 'faith'],
      types: ['interchange'],
    })
    expect(parsed.member_names).toHaveLength(2)
    expect(parsed.types).toEqual(['interchange'])
  })

  it('accepts multiple types', async () => {
    const { requestSchema } = await import('~~/server/api/sp/connections/index.post')
    const parsed = requestSchema.parse({
      member_names: ['faith', 'hope'],
      types: ['sequence', 'prerequisite'],
      note: 'seen in order across the chapter',
    })
    expect(parsed.types).toEqual(['sequence', 'prerequisite'])
  })

  it('rejects fewer than two members', async () => {
    const { requestSchema } = await import('~~/server/api/sp/connections/index.post')
    expect(() => requestSchema.parse({ member_names: ['faith'], types: ['sequence'] })).toThrow()
  })

  it('rejects an empty types array', async () => {
    const { requestSchema } = await import('~~/server/api/sp/connections/index.post')
    expect(() => requestSchema.parse({ member_names: ['faith', 'hope'], types: [] })).toThrow()
  })

  it('rejects an unknown type', async () => {
    const { requestSchema } = await import('~~/server/api/sp/connections/index.post')
    expect(() =>
      requestSchema.parse({ member_names: ['faith', 'hope'], types: ['causation'] }),
    ).toThrow()
  })
})
