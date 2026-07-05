import { describe, expect, it } from 'vitest'
import { groupDocs, findDoc, type DocEntry } from '~~/utils/docs'

function doc(over: Partial<DocEntry>): DocEntry {
  return {
    slug: 'x',
    title: 'X',
    category: 'plan',
    categoryLabel: 'Plan',
    order: 2,
    path: 'X.md',
    html: '<p>x</p>',
    ...over,
  }
}

describe('docs helpers', () => {
  it('groups by category in category order, titles sorted within', () => {
    const docs = [
      doc({ slug: 'b', title: 'Beta', category: 'plan', categoryLabel: 'Plan', order: 2 }),
      doc({ slug: 'a', title: 'Alpha', category: 'plan', categoryLabel: 'Plan', order: 2 }),
      doc({ slug: 'c', title: 'Spec', category: 'canonical', categoryLabel: 'Specs', order: 1 }),
    ]
    const groups = groupDocs(docs)
    expect(groups.map((g) => g.key)).toEqual(['canonical', 'plan']) // order 1 before 2
    expect(groups[1].docs.map((d) => d.title)).toEqual(['Alpha', 'Beta']) // sorted
  })

  it('every doc lands in exactly one group', () => {
    const docs = [doc({ slug: 'a', category: 'x' }), doc({ slug: 'b', category: 'y' })]
    const total = groupDocs(docs).reduce((n, g) => n + g.docs.length, 0)
    expect(total).toBe(2)
  })

  it('findDoc matches by slug and is safe on undefined/miss', () => {
    const docs = [doc({ slug: 'a' }), doc({ slug: 'b' })]
    expect(findDoc(docs, 'b')?.slug).toBe('b')
    expect(findDoc(docs, 'nope')).toBeUndefined()
    expect(findDoc(docs, undefined)).toBeUndefined()
  })
})
