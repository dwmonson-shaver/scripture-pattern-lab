import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ConceptEditForm from '~~/components/ConceptEditForm.vue'
import type { ConceptSummary } from '~~/types/api'

const existing: ConceptSummary = {
  name: 'Hope',
  description: 'expectation of good',
  verification_state: 'corpus_observed',
  lemma_count: 3,
  lemmas: [],
  authored_color: '#E0A12E',
  authored_polarity: '+',
  authored_opposite_name: 'Despair',
}

describe('ConceptEditForm', () => {
  it('emits a create payload with the typed name in create mode', async () => {
    const wrapper = mountWithVuetify(ConceptEditForm, {
      props: { concept: null, prefillName: 'Glory' },
    })
    await wrapper.get('[data-testid="concept-save"]').trigger('click')
    const ev = wrapper.emitted('save')
    expect(ev).toBeTruthy()
    const payload = ev?.[0]?.[0] as { mode: string; req: { name: string } }
    expect(payload.mode).toBe('create')
    expect(payload.req.name).toBe('Glory')
  })

  it('does not save with an empty name', async () => {
    const wrapper = mountWithVuetify(ConceptEditForm, {
      props: { concept: null, prefillName: '' },
    })
    await wrapper.get('[data-testid="concept-save"]').trigger('click')
    expect(wrapper.emitted('save')).toBeFalsy()
  })

  it('emits an update payload keyed by the existing name in edit mode', async () => {
    const wrapper = mountWithVuetify(ConceptEditForm, {
      props: { concept: existing },
    })
    await wrapper.get('[data-testid="concept-save"]').trigger('click')
    const payload = wrapper.emitted('save')?.[0]?.[0] as {
      mode: string
      name: string
      req: { authored_polarity: string }
    }
    expect(payload.mode).toBe('update')
    expect(payload.name).toBe('Hope')
    expect(payload.req.authored_polarity).toBe('+')
  })

  it('selecting a palette swatch updates the saved color', async () => {
    const wrapper = mountWithVuetify(ConceptEditForm, {
      props: { concept: null, prefillName: 'Victory' },
    })
    const swatch = wrapper.get('[data-color="#3F6FB5"]')
    await swatch.trigger('click')
    await wrapper.get('[data-testid="concept-save"]').trigger('click')
    const payload = wrapper.emitted('save')?.[0]?.[0] as { req: { authored_color: string } }
    expect(payload.req.authored_color).toBe('#3F6FB5')
  })

  it('emits cancel', async () => {
    const wrapper = mountWithVuetify(ConceptEditForm, {
      props: { concept: null },
    })
    await wrapper.get('[data-testid="concept-edit-cancel"]').trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })
})
