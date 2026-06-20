import { getFromBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy GET /api/v1/read/versions.
 *
 * Slice 1 (DEC-149): the available English versions for the version switcher.
 * No params; mirrors the GET error contract used by the Conceptual Document
 * proxy so the browser sees the same `{ detail }` envelope regardless of verb.
 */
export default defineEventHandler(async (event) => {
  const runtimeConfig = useRuntimeConfig(event)

  try {
    return await getFromBackend<unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path: '/api/v1/read/versions',
    })
  } catch (err) {
    const backendErr = err as BackendError
    throw createError({
      statusCode: backendErr.status,
      data: backendErr.body,
    })
  }
})
