import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ConceptDocumentView from '~~/components/ConceptDocumentView.vue'
import ComparativeLexiconSection from '~~/components/ComparativeLexiconSection.vue'
import EducationalArticleSection from '~~/components/EducationalArticleSection.vue'
import Tier2GroupingSection from '~~/components/Tier2GroupingSection.vue'
import type { ConceptDocument } from '~~/types/api'

// Auto-imports don't resolve under Vitest, so register the child
// components explicitly. Same pattern as `GreekText` in `test-utils.ts`.
const globalComponents = {
  ComparativeLexiconSection,
  EducationalArticleSection,
  Tier2GroupingSection,
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
  part2_grouping: null,
  part2_grouping_pointer: null,
}

const DOC_WITHOUT_ARTICLE: ConceptDocument = {
  ...DOC_WITH_ARTICLE,
  part1_educational: null,
}

const DOC_WITH_GROUPING: ConceptDocument = {
  ...DOC_WITH_ARTICLE,
  part2_grouping: {
    anchor_name: 'humility',
    members: [
      { concept_name: 'humility', confidence: 0.95, note: null },
      { concept_name: 'meekness', confidence: 0.85, note: null },
      { concept_name: 'lowliness', confidence: 0.75, note: null },
    ],
    rationale: 'Humility cluster: ταπεινός / πραΰς family',
    origin: 'curated',
    verification_state: 'unverified',
    created_at: '2026-05-31T00:00:00Z',
  },
}

const DOC_WITH_POINTER: ConceptDocument = {
  ...DOC_WITH_ARTICLE,
  concept_name: 'meekness',
  part2_grouping_pointer: { grouping_anchors: ['humility'] },
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

  it('renders the Tier-2 placeholder when concept is not yet in any grouping', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_ARTICLE },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="tier2-grouping-placeholder"]').exists()).toBe(true)
  })

  it('renders the full Tier-2 grouping when the document is an anchor (Slice O)', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_GROUPING },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="tier2-grouping-section"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tier2-grouping-placeholder"]').exists()).toBe(false)
  })

  it('renders the pointer card when the document is a member (Slice O)', () => {
    const wrapper = mountWithVuetify(ConceptDocumentView, {
      props: { document: DOC_WITH_POINTER },
      global: { components: globalComponents },
    })
    expect(wrapper.find('[data-testid="tier2-grouping-pointer"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tier2-grouping-section"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="tier2-grouping-placeholder"]').exists()).toBe(false)
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
