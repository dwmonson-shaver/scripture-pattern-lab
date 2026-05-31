import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ConceptDocumentView from '~~/components/ConceptDocumentView.vue'
import ComparativeLexiconSection from '~~/components/ComparativeLexiconSection.vue'
import EducationalArticleSection from '~~/components/EducationalArticleSection.vue'
import Tier2GroupingPlaceholder from '~~/components/Tier2GroupingPlaceholder.vue'
import type { ConceptDocument } from '~~/types/api'

// Auto-imports don't resolve under Vitest, so register the child
// components explicitly. Same pattern as `GreekText` in `test-utils.ts`.
const globalComponents = {
  ComparativeLexiconSection,
  EducationalArticleSection,
  Tier2GroupingPlaceholder,
}

const DOC_WITH_ARTICLE: ConceptDocument = {
  concept_name: 'humility',
  short_summary: 'auto-created Tier-1 prior pending corpus + curator review',
  part1_comparative: {
    english_term: 'humility',
    rows: [
      {
        lemma: 'ταπεινοφροσύνη',
        strongs: ['G5012'],
        usual_renderings: ['humility'],
        corpus_verse_refs: ['Acts 20:19'],
      },
    ],
    generated_from: ['Strong + Thayer'],
  },
  part1_educational: {
    prose: 'Humility in the Pauline corpus carries a distinctive register.',
    cited_sources: ['Strong G5012'],
    generated: true,
    model_label: 'claude-opus-4-7',
  },
  part2_grouping_placeholder: null,
}

const DOC_WITHOUT_ARTICLE: ConceptDocument = {
  ...DOC_WITH_ARTICLE,
  part1_educational: null,
}

describe('ConceptDocumentView', () => {
  it('renders the concept name in the header', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_ARTICLE },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="concept-document-name"]').text()).toBe('humility')
  })

  it('renders the short_summary in the header', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_ARTICLE },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="concept-document-header"]').text()).toContain(
      'auto-created Tier-1 prior',
    )
  })

  it('renders the unverified-starting-prior epistemic chip in the header', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_ARTICLE },
      global: { components: globalComponents },
    })
    const header = wrapper.find('[data-testid="concept-document-header"]')
    expect(header.text()).toContain('unverified — starting prior')
  })

  it('renders the deterministic comparative lexicon section', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_ARTICLE },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="comparative-lexicon-section"]').exists()).toBe(true)
  })

  it('renders the LLM educational article section when part1_educational is present', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_ARTICLE },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="educational-article-section"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="educational-article-absent"]').exists()).toBe(false)
  })

  it('renders the "no article" placeholder when part1_educational is null (DEC-107)', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITHOUT_ARTICLE },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="educational-article-section"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="educational-article-absent"]').exists()).toBe(true)
  })

  it('always renders the Tier-2 grouping placeholder', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_ARTICLE },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="tier2-grouping-placeholder"]').exists()).toBe(true)
  })

  it('renders sections in document order: comparative before educational before tier2', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_ARTICLE },
      global: { components: globalComponents },
    })
    const html = wrapper.html()
    const idxComparative = html.indexOf('data-testid="comparative-lexicon-section"')
    const idxEducational = html.indexOf('data-testid="educational-article-section"')
    const idxTier2 = html.indexOf('data-testid="tier2-grouping-placeholder"')
    expect(idxComparative).toBeGreaterThan(-1)
    expect(idxEducational).toBeGreaterThan(idxComparative)
    expect(idxTier2).toBeGreaterThan(idxEducational)
  })
})
