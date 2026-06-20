import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ConceptPanel from '~~/components/ConceptPanel.vue'
import ConceptPanelBody from '~~/components/ConceptPanelBody.vue'
import ConceptLibrary from '~~/components/ConceptLibrary.vue'
import ConceptEditForm from '~~/components/ConceptEditForm.vue'
import MarkDetail from '~~/components/MarkDetail.vue'
import type { ConceptSummary } from '~~/types/api'

// The panel host delegates to ConceptPanelBody, which routes to one of the
// sub-views. Register the full chain so the rendered DOM matches the app.
const panelComponents = { ConceptPanelBody, ConceptLibrary, ConceptEditForm, MarkDetail }

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

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    drawer: false,
    view: 'library',
    concepts,
    activeMark: null,
    activeMarkPhrase: '',
    editingConcept: null,
    createPrefill: '',
    associateLabel: null,
    ...overrides,
  }
}

describe('ConceptPanel host', () => {
  // jsdom reports a wide viewport, so useDisplay().mobile is false → aside.
  it('renders the persistent aside on a wide viewport', () => {
    const wrapper = mountWithVuetify(ConceptPanel, {
      props: baseProps(),
      global: { components: panelComponents },
    })
    expect(wrapper.find('[data-testid="concept-panel-aside"]').exists()).toBe(true)
  })

  it('hosts the panel body (which renders the library in library view)', () => {
    const wrapper = mountWithVuetify(ConceptPanel, {
      props: baseProps(),
      global: { components: panelComponents },
    })
    expect(wrapper.find('[data-testid="concept-panel-body"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="concept-library"]').exists()).toBe(true)
  })
})
