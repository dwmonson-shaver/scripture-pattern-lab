import { z } from 'zod'
import { proxyToBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy POST /api/v1/concepts — create a concept.
 *
 * Slice 1 (DEC-149): the human-authored concept create path. `name` is
 * required (1..64, the backend's authoritative bound mirrored here for
 * fail-fast input hygiene); the authored display fields are optional. The
 * polarity enum matches `AuthoredPolarity` in types/api.ts. The backend owns
 * verification_state / origin — this proxy never sets them (DEC-102: authored
 * concepts are corrigible priors, never auto-confirmed).
 */
export const requestSchema = z.object({
  name: z.string().min(1).max(64),
  description: z.string().max(2000).nullish(),
  authored_color: z.string().max(32).nullish(),
  authored_polarity: z.enum(['+', '-', '±']).nullish(),
  authored_opposite_name: z.string().max(64).nullish(),
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
      path: '/api/v1/concepts',
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
