import type { DocEntry } from '~~/utils/docs'
import { groupDocs, findDoc } from '~~/utils/docs'

/**
 * Loads the project docs from the static `/docs.json` asset (built by
 * scripts/collect-docs.mjs) and exposes grouped + by-slug views. Client-only
 * fetch (server:false) — the docs are a big, static, non-critical payload, so
 * there's no reason to block SSR on them. Shared via a keyed useAsyncData so
 * every /docs navigation reuses the one fetch.
 */
export const useDocs = () => {
  const { data, pending, error } = useAsyncData<DocEntry[]>(
    'project-docs',
    () => $fetch<DocEntry[]>('/docs.json'),
    { server: false, default: () => [] },
  )

  const all = computed<DocEntry[]>(() => data.value ?? [])
  const groups = computed(() => groupDocs(all.value))
  const bySlug = (slug: string | undefined) => findDoc(all.value, slug)

  return { all, groups, bySlug, pending, error }
}
