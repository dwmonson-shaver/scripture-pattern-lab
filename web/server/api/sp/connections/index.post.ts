import { z } from 'zod'
import { sendToBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy POST /api/v1/connections — create a typed connection between concepts.
 *
 * Slice 2 (2026-07-05). `member_names` is ordered (>=2); `types` is the set of
 * claim types (>=1) from the fixed vocabulary. Mirrors the concept-create proxy.
 */
export const requestSchema = z.object({
  member_names: z.array(z.string().min(1).max(64)).min(2),
  types: z
    .array(
      z.enum([
        'opposite',
        'prerequisite',
        'produces',
        'sequence',
        'compound',
        'association',
        'interchange',
        'unknown',
      ]),
    )
    .min(1),
  note: z.string().max(2000).nullish(),
})

export default defineEventHandler(async (event) => {
  const body = await readValidatedBody(event, requestSchema.parse)
  const runtimeConfig = useRuntimeConfig(event)
  try {
    return await sendToBackend<typeof body, unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path: '/api/v1/connections',
      method: 'POST',
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
