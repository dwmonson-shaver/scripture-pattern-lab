import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ConceptPanelBody from '~~/components/ConceptPanelBody.vue'
import ConceptLibrary from '~~/components/ConceptLibrary.vue'
import ConceptEditForm from '~~/components/ConceptEditForm.vue'
import MarkDetail from '~~/components/MarkDetail.vue'
import type { ConceptSummary, MarkOut } from '~~/types/api'

// ConceptPanelBody routes to these auto-imported sub-views; register them so
// the rendered DOM (and their testids) match the app.
const subViews = { ConceptLibrary, ConceptEditForm, MarkDetail }

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

const mark: MarkOut = {
  id: 1,
  corpus_id: 'nt',
  book: 'rom',
  chapter: 8,
  verse_start: 24,
  verse_end: 24,
  char_start: 0,
  char_end: 5,
  version_code: 'kjv',
  actor: 'user',
  concept_names: ['Hope'],
}

function props(view: string, extra: Record<string, unknown> = {}) {
  return {
    view,
    concepts,
    activeMark: null,
    activeMarkPhrase: '',
    editingConcept: null,
    createPrefill: '',
    associateLabel: null,
    ...extra,
  }
}

function mountBody(view: string, extra: Record<string, unknown> = {}) {
  return mountWithVuetify(ConceptPanelBody, {
    props: props(view, extra),
    global: { components: subViews },
  })
}

describe('ConceptPanelBody routing', () => {
  it('library view renders the concept library', () => {
    expect(mountBody('library').find('[data-testid="concept-library"]').exists()).toBe(true)
  })

  it('edit view renders the concept edit form', () => {
    expect(mountBody('edit').find('[data-testid="concept-edit-form"]').exists()).toBe(true)
  })

  it('mark view renders the mark detail', () => {
    const wrapper = mountBody('mark', { activeMark: mark, activeMarkPhrase: 'hope' })
    expect(wrapper.find('[data-testid="mark-detail"]').exists()).toBe(true)
  })

  it('search view renders the library in associate mode with a context label', () => {
    const wrapper = mountBody('search', { associateLabel: 'Mark “hope” as:' })
    expect(wrapper.find('[data-testid="associate-context"]').exists()).toBe(true)
  })

  it('forwards a pick event from the associate search', async () => {
    const wrapper = mountBody('search', { associateLabel: 'Mark “hope” as:' })
    await wrapper.get('[data-concept="Hope"]').trigger('click')
    expect(wrapper.emitted('pick-concept')?.[0]).toEqual(['Hope'])
  })
})
