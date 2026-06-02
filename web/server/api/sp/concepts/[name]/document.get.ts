import { getFromBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy GET /api/v1/concepts/{name}/document.
 *
 * Slice N (DEC-106): the persisted two-part Conceptual Document. Backend
 * URL is plural + `/document`; the user-facing route is singular
 * (`/concept/:name`) per the convention chosen in Phase NP1-1's
 * `<AutoCreatedConceptNote>` link.
 *
 * `name` is read from the route param. Empty / whitespace names are
 * rejected at the proxy with a 400 so we don't waste a round trip on a
 * request the backend would reject anyway.
 */
export default defineEventHandler(async (event) => {
  // h3 v1.x `getRouterParam` returns the RAW (URL-encoded) value by
  // default — pass `{ decode: true }` so spaces / Greek / slashes arrive
  // as the literal concept name. Re-encoding without decoding would
  // double-encode (`%20` → `%2520`) and the backend would never find the
  // concept (fixed under DEC-118 follow-up per Codex Slice-NP1 P2).
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

  // Re-encode the now-decoded segment (single round trip end to end)
  // so spaces / Greek / `/` survive transport to the backend.
  const encoded = encodeURIComponent(rawName)
  const path = `/api/v1/concepts/${encoded}/document`

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
