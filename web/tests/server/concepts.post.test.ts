import { beforeAll, describe, expect, it, vi } from 'vitest'

// Mirror tests/server/nl.post.test.ts: stub the Nitro auto-imports the route
// module references at load time, then assert the exported requestSchema's
// zod contract directly.
beforeAll(() => {
  vi.stubGlobal('defineEventHandler', (fn: unknown) => fn)
  vi.stubGlobal('readValidatedBody', vi.fn())
  vi.stubGlobal('useRuntimeConfig', vi.fn())
  vi.stubGlobal('createError', vi.fn())
})

describe('concepts POST requestSchema', () => {
  it('accepts a minimal body with just a name', async () => {
    const { requestSchema } = await import('~~/server/api/sp/concepts/index.post')
    const parsed = requestSchema.parse({ name: 'Hope' })
    expect(parsed.name).toBe('Hope')
  })

  it('accepts all authored fields', async () => {
    const { requestSchema } = await import('~~/server/api/sp/concepts/index.post')
    const body = {
      name: 'Patience',
      description: 'steadfast endurance',
      authored_color: '#2E8C99',
      authored_polarity: '+',
      authored_opposite_name: 'Restlessness',
    }
    expect(requestSchema.parse(body)).toMatchObject(body)
  })

  it('rejects an empty name', async () => {
    const { requestSchema } = await import('~~/server/api/sp/concepts/index.post')
    expect(() => requestSchema.parse({ name: '' })).toThrow()
  })

  it('rejects a name longer than 64 chars', async () => {
    const { requestSchema } = await import('~~/server/api/sp/concepts/index.post')
    expect(() => requestSchema.parse({ name: 'x'.repeat(65) })).toThrow()
  })

  it('rejects an invalid polarity', async () => {
    const { requestSchema } = await import('~~/server/api/sp/concepts/index.post')
    expect(() =>
      requestSchema.parse({ name: 'Hope', authored_polarity: 'positive' }),
    ).toThrow()
  })

  it('accepts each valid polarity symbol', async () => {
    const { requestSchema } = await import('~~/server/api/sp/concepts/index.post')
    for (const p of ['+', '-', '±'] as const) {
      expect(requestSchema.parse({ name: 'Hope', authored_polarity: p }).authored_polarity).toBe(p)
    }
  })
})
