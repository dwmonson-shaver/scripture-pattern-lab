import { z } from 'zod'
import { sendToBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy PATCH /api/v1/marks/{id} — adjust a mark's span or concepts.
 *
 * Slice 1 (DEC-149): used by the draggable word-snapping span handles
 * (verse / char offsets) and by the mark-detail concept change/add/remove
 * controls. All fields optional (a partial update); shape mirrors
 * `MarkUpdateRequest` in types/api.ts. `id` is a positive integer route param.
 * Uses `sendToBackend` because `proxyToBackend` is POST-only.
 */
export const requestSchema = z.object({
  verse_start: z.number().int().min(1).nullish(),
  verse_end: z.number().int().min(1).nullish(),
  char_start: z.number().int().min(0).nullish(),
  char_end: z.number().int().min(0).nullish(),
  concept_names: z.array(z.string().min(1).max(64)).max(32).nullish(),
})

export default defineEventHandler(async (event) => {
  const rawId = getRouterParam(event, 'id')
  if (!rawId || !/^\d+$/.test(rawId)) {
    throw createError({
      statusCode: 400,
      data: {
        detail: {
          error: 'invalid_request',
          message: 'mark id must be a positive integer',
          details: null,
        },
      },
    })
  }

  const body = await readValidatedBody(event, requestSchema.parse)
  const runtimeConfig = useRuntimeConfig(event)

  try {
    return await sendToBackend<typeof body, unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path: `/api/v1/marks/${rawId}`,
      method: 'PATCH',
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
