/**
 * Project docs types + pure helpers. The content is rendered to HTML at build
 * time by scripts/collect-docs.mjs and served as the static asset
 * `/docs.json` (fetched by `useDocs`) — no Markdown renderer or doc content
 * ships in the JS bundle. These helpers are pure so they're trivially testable.
 */
export interface DocEntry {
  slug: string
  title: string
  category: string
  categoryLabel: string
  order: number
  path: string
  html: string
}

export interface DocGroup {
  key: string
  label: string
  order: number
  docs: DocEntry[]
}

/** Group docs by category (category order; titles sorted within a group). */
export function groupDocs(docs: DocEntry[]): DocGroup[] {
  const groups = new Map<string, DocGroup>()
  for (const doc of docs) {
    let g = groups.get(doc.category)
    if (!g) {
      g = { key: doc.category, label: doc.categoryLabel, order: doc.order, docs: [] }
      groups.set(doc.category, g)
    }
    g.docs.push(doc)
  }
  const out = [...groups.values()]
  out.sort((a, b) => a.order - b.order)
  for (const g of out) g.docs.sort((a, b) => a.title.localeCompare(b.title))
  return out
}

export function findDoc(docs: DocEntry[], slug: string | undefined): DocEntry | undefined {
  if (!slug) return undefined
  return docs.find((d) => d.slug === slug)
}
