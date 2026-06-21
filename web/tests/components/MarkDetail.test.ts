import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import MarkDetail from '~~/components/MarkDetail.vue'
import type { ConceptSummary, MarkOut } from '~~/types/api'

const concepts: ConceptSummary[] = [
  {
    name: 'Hope',
    description: null,
    verification_state: 'unverified',
    lemma_count: 0,
    lemmas: [],
    authored_color: '#E0A12E',
    authored_polarity: '+',
    authored_opposite_name: null,
  },
]

function mark(conceptNames: string[]): MarkOut {
  return {
    id: 5,
    corpus_id: 'nt',
    book: 'rom',
    chapter: 8,
    verse_start: 24,
    verse_end: 24,
    char_start: 0,
    char_end: 18,
    version_code: 'kjv',
    actor: 'user',
    concept_names: conceptNames,
  }
}

describe('MarkDetail', () => {
  it('shows the marked phrase', () => {
    const wrapper = mountWithVuetify(MarkDetail, {
      props: { mark: mark(['Hope']), phrase: 'we are saved by hope', concepts },
    })
    expect(wrapper.get('[data-testid="mark-phrase"]').text()).toContain('we are saved by hope')
  })

  it('a concepted mark offers Change / Add / Remove', () => {
    const wrapper = mountWithVuetify(MarkDetail, {
      props: { mark: mark(['Hope']), phrase: 'x', concepts },
    })
    expect(wrapper.find('[data-testid="mark-change"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="mark-add"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="mark-remove"]').exists()).toBe(true)
  })

  it('an unconcepted (Just highlight) mark shows the unassigned note and no Change button', () => {
    const wrapper = mountWithVuetify(MarkDetail, {
      props: { mark: mark([]), phrase: 'x', concepts },
    })
    expect(wrapper.find('[data-testid="mark-unassigned"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="mark-change"]').exists()).toBe(false)
  })

  it('emits remove', async () => {
    const wrapper = mountWithVuetify(MarkDetail, {
      props: { mark: mark(['Hope']), phrase: 'x', concepts },
    })
    await wrapper.get('[data-testid="mark-remove"]').trigger('click')
    expect(wrapper.emitted('remove')).toBeTruthy()
  })

  it('emits change and add', async () => {
    const wrapper = mountWithVuetify(MarkDetail, {
      props: { mark: mark(['Hope']), phrase: 'x', concepts },
    })
    await wrapper.get('[data-testid="mark-change"]').trigger('click')
    await wrapper.get('[data-testid="mark-add"]').trigger('click')
    expect(wrapper.emitted('change')).toBeTruthy()
    expect(wrapper.emitted('add')).toBeTruthy()
  })

  it('notes that handles adjust the span (single-verse)', () => {
    const wrapper = mountWithVuetify(MarkDetail, {
      props: { mark: mark(['Hope']), phrase: 'x', concepts },
    })
    expect(wrapper.get('[data-testid="mark-handles-note"]').text().toLowerCase()).toContain(
      'handles',
    )
  })

  it('emits edit with the concept name (the in-reader concept-update entry)', async () => {
    const wrapper = mountWithVuetify(MarkDetail, {
      props: { mark: mark(['Hope']), phrase: 'x', concepts },
    })
    await wrapper.get('[data-testid="mark-edit"]').trigger('click')
    expect(wrapper.emitted('edit')?.[0]).toEqual(['Hope'])
  })

  it('flags cross-verse marks instead of showing the single-verse resize note', () => {
    const crossVerse = { ...mark(['Hope']), verse_start: 24, verse_end: 26 }
    const wrapper = mountWithVuetify(MarkDetail, {
      props: { mark: crossVerse, phrase: 'x', concepts },
    })
    expect(wrapper.find('[data-testid="mark-handles-note"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="mark-crossverse-note"]').text()).toContain('24')
  })
})
