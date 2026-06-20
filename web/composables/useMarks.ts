import type {
  MarkCreateRequest,
  MarkOut,
  MarksResponse,
  MarkUpdateRequest,
} from '~~/types/api'
import { unwrapErrorBody, type ProxyErrorShape } from '~~/composables/useQuery'

/**
 * Mark CRUD state for the current chapter (Slice 1 reader).
 *
 * `marks` holds the marks for whatever chapter was last loaded via
 * `loadForChapter`. `create` / `update` / `remove` write through the proxy
 * then reload the current chapter's marks so the reader stays in sync.
 * Component-local refs, no Pinia.
 */
export interface ChapterScope {
  corpus: string
  book: string
  chapter: number
  version: string
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

export const useMarks = () => {
  const marks = ref<MarkOut[]>([])
  const pending = ref(false)
  const error = ref<ProxyErrorShape | null>(null)
  const scope = ref<ChapterScope | null>(null)

  const loadForChapter = async (s: ChapterScope): Promise<void> => {
    scope.value = s
    pending.value = true
    error.value = null
    try {
      const res = await $fetch<MarksResponse>('/api/sp/marks', {
        query: {
          corpus: s.corpus,
          book: s.book,
          chapter: s.chapter,
          version: s.version,
        },
      })
      marks.value = res.marks
    } catch (err) {
      error.value = toProxyError(err)
    } finally {
      pending.value = false
    }
  }

  const reload = async (): Promise<void> => {
    if (scope.value) await loadForChapter(scope.value)
  }

  const create = async (req: MarkCreateRequest): Promise<MarkOut | null> => {
    error.value = null
    try {
      const created = await $fetch<MarkOut>('/api/sp/marks', {
        method: 'POST',
        body: req,
      })
      await reload()
      return created
    } catch (err) {
      error.value = toProxyError(err)
      return null
    }
  }

  const update = async (
    id: number,
    req: MarkUpdateRequest,
  ): Promise<MarkOut | null> => {
    error.value = null
    try {
      const updated = await $fetch<MarkOut>(`/api/sp/marks/${id}`, {
        method: 'PATCH',
        body: req,
      })
      await reload()
      return updated
    } catch (err) {
      error.value = toProxyError(err)
      return null
    }
  }

  const remove = async (id: number): Promise<boolean> => {
    error.value = null
    try {
      await $fetch(`/api/sp/marks/${id}`, { method: 'DELETE' })
      await reload()
      return true
    } catch (err) {
      error.value = toProxyError(err)
      return false
    }
  }

  return { marks, pending, error, scope, loadForChapter, reload, create, update, remove }
}
