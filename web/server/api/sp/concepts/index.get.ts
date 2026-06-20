import { getFromBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy GET /api/v1/concepts?language=.
 *
 * Slice 1 (DEC-149): the concept library. `language` is an optional query
 * passed straight through. Same GET error contract as the other read proxies.
 */
export default defineEventHandler(async (event) => {
  const runtimeConfig = useRuntimeConfig(event)
  const query = getQuery(event)
  const language = typeof query.language === 'string' ? query.language : undefined

  const path =
    '/api/v1/concepts' +
    (language ? `?language=${encodeURIComponent(language)}` : '')

  try {
    return await getFromBackend<unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path,
    })
  } catch (err) {
    const backendErr = err as BackendError
    throw createError({
      statusCode: backendErr.status,
      data: backendErr.body,
    })
  }
})
