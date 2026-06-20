import type { ChapterReadResponse, VersionInfoOut, VersionsResponse } from '~~/types/api'
import { unwrapErrorBody, type ProxyErrorShape } from '~~/composables/useQuery'

/**
 * Reader navigation + chapter-fetch state for the Slice 1 concept reader.
 *
 * Component-local refs (no Pinia — DEC: state stays local until concrete
 * cross-page state appears). `error` is normalized to the same
 * `ProxyErrorShape` `useQuery` / `useConceptDocument` produce so `<ErrorPanel>`
 * renders it without branching.
 *
 * The default anchor is the prototype's: nt / rom / 8 / kjv.
 */
export interface UseReaderOptions {
  corpus?: string
  book?: string
  chapter?: number
  version?: string
}

function toProxyError(err: unknown): ProxyErrorShape {
  const fetchErr = err as { status?: number; statusCode?: number; data?: unknown }
  return {
    status: fetchErr.status ?? fetchErr.statusCode ?? 0,
    body: unwrapErrorBody(fetchErr.data) ?? {
      detail: {
        error: 'network_error',
        message: 'request did not reach the proxy',
        details: null,
      },
    },
  }
}

export const useReader = (opts: UseReaderOptions = {}) => {
  const corpus = ref(opts.corpus ?? 'nt')
  const book = ref(opts.book ?? 'rom')
  const chapter = ref(opts.chapter ?? 8)
  const version = ref(opts.version ?? 'kjv')
  const greekOn = ref(false)

  const chapterData = ref<ChapterReadResponse | null>(null)
  const versions = ref<VersionInfoOut[]>([])
  const pending = ref(false)
  const error = ref<ProxyErrorShape | null>(null)

  const loadVersions = async (): Promise<void> => {
    try {
      const res = await $fetch<VersionsResponse>('/api/sp/read/versions')
      versions.value = res.versions
    } catch (err) {
      // Version list is chrome, not the main content — surface the error but
      // don't clobber a loaded chapter. The reader still works with whatever
      // version is selected.
      error.value = toProxyError(err)
    }
  }

  const loadChapter = async (): Promise<void> => {
    if (pending.value) return
    pending.value = true
    error.value = null
    try {
      chapterData.value = await $fetch<ChapterReadResponse>(
        `/api/sp/read/${encodeURIComponent(corpus.value)}/${encodeURIComponent(book.value)}/${encodeURIComponent(String(chapter.value))}`,
        { query: { version: version.value } },
      )
    } catch (err) {
      error.value = toProxyError(err)
      chapterData.value = null
    } finally {
      pending.value = false
    }
  }

  const nextChapter = (): void => {
    chapter.value += 1
  }

  const prevChapter = (): void => {
    if (chapter.value > 1) chapter.value -= 1
  }

  return {
    corpus,
    book,
    chapter,
    version,
    greekOn,
    chapterData,
    versions,
    pending,
    error,
    loadChapter,
    loadVersions,
    nextChapter,
    prevChapter,
  }
}
