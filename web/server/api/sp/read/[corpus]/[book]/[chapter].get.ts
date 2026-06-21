import { getFromBackend, type BackendError } from '~~/server/utils/backend'

/**
 * Proxy GET /api/v1/read/{corpus}/{book}/{chapter}?version=.
 *
 * Slice 1 (DEC-149): the chapter reader. The three path segments are read
 * from the route params; `version` is an optional query passed through. Path
 * segments are decoded (`{ decode: true }`) then re-encoded exactly once, the
 * same single-round-trip discipline the Conceptual Document proxy uses
 * (Codex Slice-NP1 P2 / DEC-118 follow-up) so book abbreviations / corpus ids
 * survive transport intact.
 */
export default defineEventHandler(async (event) => {
  const corpus = getRouterParam(event, 'corpus', { decode: true })
  const book = getRouterParam(event, 'book', { decode: true })
  const chapter = getRouterParam(event, 'chapter', { decode: true })

  if (!corpus?.trim() || !book?.trim() || !chapter?.trim() || !/^\d+$/.test(chapter.trim())) {
    throw createError({
      statusCode: 400,
      data: {
        detail: {
          error: 'invalid_request',
          message: 'corpus, book, and a numeric chapter are required',
          details: null,
        },
      },
    })
  }

  const runtimeConfig = useRuntimeConfig(event)
  const query = getQuery(event)
  const version = typeof query.version === 'string' ? query.version : undefined

  const path =
    `/api/v1/read/${encodeURIComponent(corpus)}/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}` +
    (version ? `?version=${encodeURIComponent(version)}` : '')

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
