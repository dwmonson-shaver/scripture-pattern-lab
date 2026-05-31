import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import AutoCreatedConceptNote from '~~/components/AutoCreatedConceptNote.vue'
import type { AutoCreatedConceptNote as Note } from '~~/types/api'

const BASE: Note = {
  concept_name: 'humility',
  lemmas: ['ταπεινοφροσύνη', 'ταπεινός'],
  summary:
    'auto-created from lexicon data — machine/lexicon-sourced, unverified, starting prior pending corpus + curator review',
  document_available: true,
}

describe('AutoCreatedConceptNote', () => {
  it('renders the concept name', () => {
    const wrapper = mountWithVuetify(AutoCreatedConceptNote, { props: { note: BASE } })
    expect(wrapper.find('[data-testid="auto-created-concept-name"]').text()).toBe('humility')
  })

  it('renders the backend summary verbatim (no paraphrase)', () => {
    const wrapper = mountWithVuetify(AutoCreatedConceptNote, { props: { note: BASE } })
    expect(wrapper.find('[data-testid="auto-created-summary"]').text()).toBe(BASE.summary)
  })

  it('renders the unverified-starting-prior epistemic chip', () => {
    const wrapper = mountWithVuetify(AutoCreatedConceptNote, { props: { note: BASE } })
    expect(wrapper.text()).toContain('unverified — starting prior')
  })

  it('renders every lemma as a Greek chip', () => {
    const wrapper = mountWithVuetify(AutoCreatedConceptNote, { props: { note: BASE } })
    const chips = wrapper.findAll('[data-testid="auto-created-lemma"]')
    expect(chips).toHaveLength(2)
    const text = chips.map((c) => c.text()).join(' ')
    expect(text).toContain('ταπεινοφροσύνη')
    expect(text).toContain('ταπεινός')
  })

  it('shows the document link when document_available=true', () => {
    const wrapper = mountWithVuetify(AutoCreatedConceptNote, { props: { note: BASE } })
    const link = wrapper.find('[data-testid="auto-created-document-link"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toContain('/concept/humility')
  })

  it('hides the document link when document_available=false', () => {
    const wrapper = mountWithVuetify(AutoCreatedConceptNote, {
      props: { note: { ...BASE, document_available: false } },
    })
    expect(wrapper.find('[data-testid="auto-created-document-link"]').exists()).toBe(false)
  })

  it('handles an empty lemmas list without rendering an empty chip row', () => {
    const wrapper = mountWithVuetify(AutoCreatedConceptNote, {
      props: { note: { ...BASE, lemmas: [] } },
    })
    expect(wrapper.findAll('[data-testid="auto-created-lemma"]')).toHaveLength(0)
    // The card still renders the name + summary
    expect(wrapper.find('[data-testid="auto-created-concept-name"]').text()).toBe('humility')
  })

  it('URL-encodes concept names with spaces in the document link', () => {
    const wrapper = mountWithVuetify(AutoCreatedConceptNote, {
      props: { note: { ...BASE, concept_name: 'fear of the lord' } },
    })
    const link = wrapper.find('[data-testid="auto-created-document-link"]')
    expect(link.attributes('href')).toBe('/concept/fear%20of%20the%20lord')
  })
})
