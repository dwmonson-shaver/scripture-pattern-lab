import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ChapterView from '~~/components/ChapterView.vue'
import InterlinearChip from '~~/components/InterlinearChip.vue'
import type { ChapterReadResponse, ConceptSummary, MarkOut } from '~~/types/api'

// ChapterView renders <InterlinearChip> (auto-imported in the app). Register
// it so the greek-on test sees the real chip DOM, not an unresolved element.
const childComponents = { InterlinearChip }

const chapter: ChapterReadResponse = {
  corpus_id: 'nt',
  book: 'rom',
  book_display: 'Romans',
  chapter: 8,
  version_code: 'kjv',
  verses: [
    {
      verse: 24,
      reference: 'Romans 8:24',
      english_text: 'For we are saved by hope',
      greek_tokens: [
        {
          position: 1,
          surface_form: 'ἐλπίδι',
          normalized_form: 'elpidi',
          lemma: 'ἐλπίς',
          morph_code: 'N-DSF',
          pos: 'noun',
        },
      ],
    },
    {
      verse: 25,
      reference: 'Romans 8:25',
      english_text: 'But if we hope for that we see not',
      greek_tokens: [],
    },
  ],
}

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
  id: 11,
  corpus_id: 'nt',
  book: 'rom',
  chapter: 8,
  verse_start: 24,
  verse_end: 24,
  char_start: 11,
  char_end: 24, // "saved by hope"
  version_code: 'kjv',
  actor: 'user',
  concept_names: ['Hope'],
}

describe('ChapterView', () => {
  it('renders each verse with its number', () => {
    const wrapper = mountWithVuetify(ChapterView, {
      props: { chapter, marks: [], concepts, greekOn: false, activeMarkId: null },
    })
    expect(wrapper.findAll('[data-testid="verse"]')).toHaveLength(2)
    expect(wrapper.get('[data-testid="chapter-book"]').text()).toBe('Romans')
  })

  it('renders a concept mark tinted with the authored color', () => {
    const wrapper = mountWithVuetify(ChapterView, {
      props: { chapter, marks: [mark], concepts, greekOn: false, activeMarkId: null },
    })
    const m = wrapper.get('[data-testid="concept-mark"]')
    expect(m.text()).toContain('saved by hope')
    // Authored color (user data) renders inline as the `--c` custom property —
    // the sanctioned raw-color exception. The CSS does the multiply-blend tint
    // + underline off `--c` (study-edition .cm, DEC-152).
    const style = m.attributes('style') ?? ''
    expect(style).toContain('--c: #E0A12E')
  })

  it('emits mark-click with the mark id', async () => {
    const wrapper = mountWithVuetify(ChapterView, {
      props: { chapter, marks: [mark], concepts, greekOn: false, activeMarkId: null },
    })
    await wrapper.get('[data-testid="concept-mark"]').trigger('click')
    expect(wrapper.emitted('mark-click')?.[0]).toEqual([11])
  })

  it('hides interlinear chips when greekOn is false', () => {
    const wrapper = mountWithVuetify(ChapterView, {
      props: { chapter, marks: [], concepts, greekOn: false, activeMarkId: null },
    })
    expect(wrapper.find('[data-testid="interlinear-row"]').exists()).toBe(false)
  })

  it('shows interlinear chips when greekOn is true', () => {
    const wrapper = mountWithVuetify(ChapterView, {
      props: { chapter, marks: [], concepts, greekOn: true, activeMarkId: null },
      global: { components: childComponents },
    })
    expect(wrapper.findAll('[data-testid="interlinear-chip"]')).toHaveLength(1)
  })

  it('renders an empty state when no chapter is loaded', () => {
    const wrapper = mountWithVuetify(ChapterView, {
      props: { chapter: null, marks: [], concepts, greekOn: false, activeMarkId: null },
    })
    expect(wrapper.find('[data-testid="chapter-empty"]').exists()).toBe(true)
  })
})
