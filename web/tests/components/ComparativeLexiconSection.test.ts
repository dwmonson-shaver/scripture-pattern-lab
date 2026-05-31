import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ComparativeLexiconSection from '~~/components/ComparativeLexiconSection.vue'
import type { ComparativeLexiconSection as Section } from '~~/types/api'

const SAMPLE: Section = {
  english_term: 'humility',
  rows: [
    {
      lemma: 'ταπεινοφροσύνη',
      strongs: ['G5012'],
      usual_renderings: ['humility', 'lowliness of mind'],
      corpus_verse_refs: ['Acts 20:19', 'Eph 4:2'],
    },
    {
      lemma: 'ταπεινός',
      strongs: ['G5011'],
      usual_renderings: ['lowly', 'humble'],
      corpus_verse_refs: [],
    },
  ],
  generated_from: ['Strong + Thayer (open-licensed)'],
}

describe('ComparativeLexiconSection', () => {
  it('renders the deterministic badge so a skimming reader knows it is ground truth', () => {
    const wrapper = mountWithVuetify(ComparativeLexiconSection, { props: { section: SAMPLE } })
    const badge = wrapper.find('[data-testid="comparative-lexicon-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('Lexicon data')
    expect(wrapper.text()).toContain('deterministic')
  })

  it('renders the english term in the section header', () => {
    const wrapper = mountWithVuetify(ComparativeLexiconSection, { props: { section: SAMPLE } })
    expect(wrapper.text()).toContain('humility')
  })

  it('renders one row per lemma', () => {
    const wrapper = mountWithVuetify(ComparativeLexiconSection, { props: { section: SAMPLE } })
    expect(wrapper.findAll('[data-testid="comparative-lexicon-row"]')).toHaveLength(2)
  })

  it('renders lemmas via GreekText so they get the polytonic font', () => {
    const wrapper = mountWithVuetify(ComparativeLexiconSection, { props: { section: SAMPLE } })
    const greekSpans = wrapper.findAll('[data-testid="greek-text"]')
    const text = greekSpans.map((s) => s.text()).join(' ')
    expect(text).toContain('ταπεινοφροσύνη')
    expect(text).toContain('ταπεινός')
  })

  it('renders verse refs joined with semicolons', () => {
    const wrapper = mountWithVuetify(ComparativeLexiconSection, { props: { section: SAMPLE } })
    expect(wrapper.text()).toContain('Acts 20:19; Eph 4:2')
  })

  it('renders an empty corpus_verse_refs row with the none-in-corpus marker', () => {
    const wrapper = mountWithVuetify(ComparativeLexiconSection, { props: { section: SAMPLE } })
    expect(wrapper.text()).toContain('none in corpus')
  })

  it('renders the generated_from provenance line', () => {
    const wrapper = mountWithVuetify(ComparativeLexiconSection, { props: { section: SAMPLE } })
    const prov = wrapper.find('[data-testid="comparative-lexicon-provenance"]')
    expect(prov.exists()).toBe(true)
    expect(prov.text()).toContain('Strong + Thayer (open-licensed)')
  })

  it('omits the provenance line when generated_from is empty', () => {
    const wrapper = mountWithVuetify(ComparativeLexiconSection, {
      props: { section: { ...SAMPLE, generated_from: [] } },
    })
    expect(wrapper.find('[data-testid="comparative-lexicon-provenance"]').exists()).toBe(false)
  })
})
