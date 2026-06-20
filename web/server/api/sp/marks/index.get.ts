import { getFromBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy GET /api/v1/marks?corpus=&book=&chapter=&version=.
 *
 * Slice 1 (DEC-149): the marks for the currently-open chapter. All four
 * filters are forwarded as query params when present; the backend decides
 * which are required. Same GET error contract as the other read proxies.
 */
export default defineEventHandler(async (event) => {
  const runtimeConfig = useRuntimeConfig(event)
  const query = getQuery(event)

  const params = new URLSearchParams()
  for (const key of ['corpus', 'book', 'chapter', 'version'] as const) {
    const value = query[key]
    if (typeof value === 'string' && value.length > 0) {
      params.set(key, value)
    } else if (typeof value === 'number') {
      params.set(key, String(value))
    }
  }
  const qs = params.toString()
  const path = '/api/v1/marks' + (qs ? `?${qs}` : '')

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
