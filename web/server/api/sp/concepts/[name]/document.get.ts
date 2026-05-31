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
  const rawName = getRouterParam(event, 'name')
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

  // `getRouterParam` returns the decoded value. Re-encode the segment
  // (not the slashes) when building the upstream URL so spaces, Greek,
  // and `/` characters in concept names survive the round trip.
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
