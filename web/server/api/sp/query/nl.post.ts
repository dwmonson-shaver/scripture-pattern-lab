import { z } from 'zod'
import { proxyToBackend, type BackendError } from '~~/server/utils/backend'

// Defense in depth: match backend's max_length=2000 to fail fast at the
// proxy before sending an oversized request. The backend has the
// authoritative limit; this is just first-line input hygiene.
const requestSchema = z.object({
  nl_query: z.string().min(1).max(2000),
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
      path: '/api/v1/query/nl',
      body,
    })
  } catch (err) {
    // BackendError carries the upstream status + body; mirror them to
    // the browser so the page dispatches UI off body.detail.error
    // consistently with direct-backend behavior.
    const backendErr = err as BackendError
    throw createError({
      statusCode: backendErr.status,
      data: backendErr.body,
    })
  }
})
