import { sendToBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy DELETE /api/v1/marks/{id} — remove a mark.
 *
 * Slice 1 (DEC-149): the "Remove mark" action. `id` is a positive integer
 * route param. No body. `sendToBackend` tolerates a 204 / empty response.
 */
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

  const runtimeConfig = useRuntimeConfig(event)

  try {
    return await sendToBackend<undefined, unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path: `/api/v1/marks/${rawId}`,
      method: 'DELETE',
    })
  } catch (err) {
    const backendErr = err as BackendError
    throw createError({
      statusCode: backendErr.status,
      data: backendErr.body,
    })
  }
})
