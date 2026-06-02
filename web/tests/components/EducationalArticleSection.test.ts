import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import EducationalArticleSection from '~~/components/EducationalArticleSection.vue'
import type { EducationalArticleSection as Section } from '~~/types/api'

const SAMPLE: Section = {
  prose:
    'Humility in the Pauline corpus carries a distinctive social register.\n\nThe term ταπεινοφροσύνη was used in classical Greek pejoratively.',
  cited_sources: ['Strong G5012', 'Thayer ταπεινοφροσύνη', 'BDAG ταπεινός'],
  generated: true,
  model_label: 'claude-opus-4-7-20251201',
}

describe('EducationalArticleSection', () => {
  it('renders the LLM-commentary badge so a skimming reader knows it is opinion not data', () => {
    const wrapper = mountWithVuetify(EducationalArticleSection, { props: { section: SAMPLE } })
    const badge = wrapper.find('[data-testid="educational-article-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('LLM-generated commentary')
  })

  it('renders the starting-prior disclaimer', () => {
    const wrapper = mountWithVuetify(EducationalArticleSection, { props: { section: SAMPLE } })
    const disclaimer = wrapper.find('[data-testid="educational-article-disclaimer"]')
    expect(disclaimer.exists()).toBe(true)
    expect(disclaimer.text()).toContain('starting prior')
    expect(disclaimer.text()).toContain('ground truth')
  })

  it('renders the prose preserving line breaks', () => {
    const wrapper = mountWithVuetify(EducationalArticleSection, { props: { section: SAMPLE } })
    const prose = wrapper.find('[data-testid="educational-article-prose"]')
    expect(prose.text()).toContain('Humility in the Pauline corpus')
    expect(prose.text()).toContain('classical Greek pejoratively')
    // white-space: pre-wrap is what preserves the blank line — assert the
    // style is set rather than counting visible newlines.
    expect(prose.attributes('style')).toContain('pre-wrap')
  })

  it('renders the model label so the user knows which model generated the prose', () => {
    const wrapper = mountWithVuetify(EducationalArticleSection, { props: { section: SAMPLE } })
    const model = wrapper.find('[data-testid="educational-article-model"]')
    expect(model.exists()).toBe(true)
    expect(model.text()).toContain('claude-opus-4-7-20251201')
  })

  it('renders every cited source under the Cited sources list', () => {
    const wrapper = mountWithVuetify(EducationalArticleSection, { props: { section: SAMPLE } })
    const sources = wrapper.find('[data-testid="educational-article-sources"]')
    expect(sources.exists()).toBe(true)
    expect(sources.text()).toContain('Strong G5012')
    expect(sources.text()).toContain('Thayer ταπεινοφροσύνη')
    expect(sources.text()).toContain('BDAG ταπεινός')
  })

  it('omits the Cited sources block when cited_sources is empty', () => {
    const wrapper = mountWithVuetify(EducationalArticleSection, {
      props: { section: { ...SAMPLE, cited_sources: [] } },
    })
    expect(wrapper.find('[data-testid="educational-article-sources"]').exists()).toBe(false)
  })

  it('uses a semantic theme color visibly distinct from the deterministic §1 (DEC-111)', () => {
    // DEC-111 / "visibly distinct" rule: the §2 card must NOT share the
    // §1 color treatment. We assert the semantic theme token (`accent` —
    // purple in the project palette) rather than the literal palette name
    // so the theme remains the single source of truth for the visual
    // distinction (Codex Slice-NP1 P3-002 / DEC-118 follow-up).
    const wrapper = mountWithVuetify(EducationalArticleSection, { props: { section: SAMPLE } })
    const html = wrapper.html()
    expect(html).toContain('accent')
    // Negative: must not regress to the hardcoded palette literal.
    expect(html).not.toContain('color="purple"')
  })
})
