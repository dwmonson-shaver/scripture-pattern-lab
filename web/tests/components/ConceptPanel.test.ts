import { describe, expect, it } from 'vitest'
import { h } from 'vue'
import { VApp } from 'vuetify/components'
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
    connections: [],
    activeMark: null,
    activeMarkPhrase: '',
    editingConcept: null,
    createPrefill: '',
    associateLabel: null,
    selectedConcepts: [],
    ...overrides,
  }
}

// The panel's drawer branch requires a Vuetify layout ancestor (the app
// supplies it via the default layout's <v-app>). Mount inside <v-app> so the
// component has the same context it has in the running app, regardless of the
// viewport useDisplay() reports under jsdom.
function mountPanel(overrides: Record<string, unknown> = {}) {
  return mountWithVuetify(VApp, {
    global: { components: panelComponents },
    // baseProps is a loose record (test fixture); ConceptPanel's props are
    // strongly typed, so cast at the render-fn boundary.
    slots: {
      default: () =>
        h(ConceptPanel, baseProps(overrides) as InstanceType<typeof ConceptPanel>['$props']),
    },
  })
}

describe('ConceptPanel host', () => {
  it('renders the panel host', () => {
    const wrapper = mountPanel()
    const aside = wrapper.find('[data-testid="concept-panel-aside"]').exists()
    const drawer = wrapper.find('[data-testid="concept-panel-drawer"]').exists()
    expect(aside || drawer).toBe(true)
  })

  it('hosts the panel body (which renders the library in library view)', () => {
    const wrapper = mountPanel()
    expect(wrapper.find('[data-testid="concept-panel-body"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="concept-library"]').exists()).toBe(true)
  })
})
