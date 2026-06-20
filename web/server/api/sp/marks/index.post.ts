import { z } from 'zod'
import { proxyToBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy POST /api/v1/marks — create a mark.
 *
 * Slice 1 (DEC-149): the marking flow. Shape mirrors `MarkCreateRequest` in
 * types/api.ts. `corpus_id` and `version_code` are optional (backend
 * defaults). Cross-verse selection is allowed (DEC-143): `verse_end` may
 * exceed `verse_start`; char offsets are into the rendered English text of the
 * version. `concept_names` is optional — an empty / absent list is a "Just
 * highlight" mark (no concept).
 */
export const requestSchema = z
  .object({
    corpus_id: z.string().min(1).max(64).optional(),
    book: z.string().min(1).max(64),
    chapter: z.number().int().min(1),
    verse_start: z.number().int().min(1),
    verse_end: z.number().int().min(1),
    char_start: z.number().int().min(0),
    char_end: z.number().int().min(0),
    version_code: z.string().min(1).max(32).optional(),
    concept_names: z.array(z.string().min(1).max(64)).max(32).optional(),
  })
  .refine((v) => v.verse_end >= v.verse_start, {
    message: 'verse_end must be >= verse_start',
    path: ['verse_end'],
  })
  .refine((v) => v.char_end > v.char_start || v.verse_end > v.verse_start, {
    message: 'char_end must be greater than char_start within a single verse',
    path: ['char_end'],
  })

export default defineEventHandler(async (event) => {
  const body = await readValidatedBody(event, requestSchema.parse)
  const runtimeConfig = useRuntimeConfig(event)

  try {
    return await proxyToBackend<typeof body, unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path: '/api/v1/marks',
      body,
    })
  } catch (err) {
    const backendErr = err as BackendError
    throw createError({
      statusCode: backendErr.status,
      data: backendErr.body,
    })
  }
})
