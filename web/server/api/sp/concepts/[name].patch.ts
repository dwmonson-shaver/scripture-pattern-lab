import { z } from 'zod'
import { sendToBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy PATCH /api/v1/concepts/{name} — edit a concept's authored fields.
 *
 * Slice 1 (DEC-149): the concept edit form. All fields optional (a partial
 * update); `name` is the route key and is not editable through this path.
 * `name` is decoded then re-encoded exactly once (the single-round-trip
 * discipline from the Conceptual Document proxy). Uses `sendToBackend` because
 * `proxyToBackend` is POST-only.
 */
export const requestSchema = z.object({
  description: z.string().max(2000).nullish(),
  authored_color: z.string().max(32).nullish(),
  authored_polarity: z.enum(['+', '-', '±']).nullish(),
  authored_opposite_name: z.string().max(64).nullish(),
})

export default defineEventHandler(async (event) => {
  const rawName = getRouterParam(event, 'name', { decode: true })
  if (!rawName || rawName.trim().length === 0) {
    throw createError({
      statusCode: 400,
      data: {
        detail: {
          error: 'invalid_request',
          message: 'concept name must be a non-empty string',
          details: null,
        },
      },
    })
  }

  const body = await readValidatedBody(event, requestSchema.parse)
  const runtimeConfig = useRuntimeConfig(event)
  const encoded = encodeURIComponent(rawName)

  try {
    return await sendToBackend<typeof body, unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path: `/api/v1/concepts/${encoded}`,
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
