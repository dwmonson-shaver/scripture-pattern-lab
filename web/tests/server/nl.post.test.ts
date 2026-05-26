import { beforeAll, describe, expect, it, vi } from 'vitest'

// The route module calls the Nuxt auto-import `defineEventHandler` at
// module-load time. Stub it (and the other auto-imports the handler body
// references) as inert passthroughs so importing the module only exercises
// the exported `requestSchema`, not the handler. We assert the zod contract
// directly — the proxy forwarding is covered by tests/server/backend.test.ts.
beforeAll(() => {
  vi.stubGlobal('defineEventHandler', (fn: unknown) => fn)
  vi.stubGlobal('readValidatedBody', vi.fn())
  vi.stubGlobal('useRuntimeConfig', vi.fn())
  vi.stubGlobal('createError', vi.fn())
})

describe('nl.post requestSchema (Slice M prior_turns passthrough)', () => {
  it('accepts a single-shot body with no prior_turns', async () => {
    const { requestSchema } = await import('~~/server/api/sp/query/nl.post')
    const parsed = requestSchema.parse({ nl_query: 'what is faith?' })
    expect(parsed.nl_query).toBe('what is faith?')
    expect(parsed.prior_turns).toBeUndefined()
  })

  it('accepts and preserves a valid prior_turns array', async () => {
    const { requestSchema } = await import('~~/server/api/sp/query/nl.post')
    const body = {
      nl_query: '20 tokens',
      prior_turns: [
        { role: 'user', content: 'faith near hope' },
        { role: 'assistant', content: 'What window size? (10, 20, 50)' },
      ],
    }
    const parsed = requestSchema.parse(body)
    expect(parsed.prior_turns).toEqual(body.prior_turns)
  })

  it('rejects a prior_turns array longer than 20', async () => {
    const { requestSchema } = await import('~~/server/api/sp/query/nl.post')
    const tooMany = Array.from({ length: 21 }, () => ({
      role: 'user' as const,
      content: 'x',
    }))
    expect(() =>
      requestSchema.parse({ nl_query: 'q', prior_turns: tooMany }),
    ).toThrow()
  })

  it('rejects an invalid role', async () => {
    const { requestSchema } = await import('~~/server/api/sp/query/nl.post')
    expect(() =>
      requestSchema.parse({
        nl_query: 'q',
        prior_turns: [{ role: 'system', content: 'x' }],
      }),
    ).toThrow()
  })

  it('rejects empty turn content', async () => {
    const { requestSchema } = await import('~~/server/api/sp/query/nl.post')
    expect(() =>
      requestSchema.parse({
        nl_query: 'q',
        prior_turns: [{ role: 'user', content: '' }],
      }),
    ).toThrow()
  })
})
