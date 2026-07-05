import { getFromBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy GET /api/v1/connections — list all typed connections.
 * Same GET error contract as the other read proxies.
 */
export default defineEventHandler(async (event) => {
  const runtimeConfig = useRuntimeConfig(event)
  try {
    return await getFromBackend<unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path: '/api/v1/connections',
    })
  } catch (err) {
    const backendErr = err as BackendError
    throw createError({
      statusCode: backendErr.status,
      data: backendErr.body,
    })
  }
})
