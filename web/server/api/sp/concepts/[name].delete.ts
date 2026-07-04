import { sendToBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy DELETE /api/v1/concepts/{name} — delete a concept.
 *
 * Slice 1 follow-up (2026-07-04): the library's delete action, behind an
 * are-you-sure dialog in the UI. Deleting a registry entry deletes a PRIOR —
 * the corpus is untouched, and dependent rows (lemma links, claims, document,
 * mark-concept associations) go via the schema's ON DELETE CASCADE; marks
 * survive as plain highlights. `name` is decoded then re-encoded exactly once
 * (same discipline as the PATCH proxy). No body; 204 tolerated.
 */
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

  const runtimeConfig = useRuntimeConfig(event)
  const encoded = encodeURIComponent(rawName)

  try {
    return await sendToBackend<undefined, unknown>({
      config: {
        url: runtimeConfig.backendUrl,
        token: runtimeConfig.backendToken,
      },
      path: `/api/v1/concepts/${encoded}`,
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
