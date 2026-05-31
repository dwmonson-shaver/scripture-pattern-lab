import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import Tier2GroupingSection from '~~/components/Tier2GroupingSection.vue'
import type { Tier2Grouping, GroupingPointer } from '~~/types/api'

const HUMILITY_GROUPING: Tier2Grouping = {
  anchor_name: 'humility',
  members: [
    { concept_name: 'humility', confidence: 0.95, note: null },
    { concept_name: 'meekness', confidence: 0.85, note: 'πραΰς family' },
    { concept_name: 'lowliness', confidence: 0.75, note: null },
  ],
  rationale:
    'Humility-cluster: lexically close Greek roots (ταπεινός / πραΰς).',
  origin: 'curated',
  verification_state: 'unverified',
  created_at: '2026-05-31T00:00:00Z',
}

const POINTER: GroupingPointer = {
  grouping_anchors: ['humility'],
}

describe('Tier2GroupingSection — anchor view', () => {
  it('renders the section card when grouping is provided', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: HUMILITY_GROUPING, pointer: null },
    })
    expect(wrapper.find('[data-testid="tier2-grouping-section"]').exists()).toBe(true)
  })

  it('renders all members in the list', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: HUMILITY_GROUPING, pointer: null },
    })
    expect(wrapper.find('[data-testid="tier2-member-humility"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tier2-member-meekness"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tier2-member-lowliness"]').exists()).toBe(true)
  })

  it('formats confidence as a percent', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: HUMILITY_GROUPING, pointer: null },
    })
    expect(wrapper.find('[data-testid="tier2-confidence-humility"]').text()).toBe('95%')
    expect(wrapper.find('[data-testid="tier2-confidence-meekness"]').text()).toBe('85%')
    expect(wrapper.find('[data-testid="tier2-confidence-lowliness"]').text()).toBe('75%')
  })

  it('renders the per-member note when provided', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: HUMILITY_GROUPING, pointer: null },
    })
    const meeknessItem = wrapper.find('[data-testid="tier2-member-meekness"]')
    expect(meeknessItem.text()).toContain('πραΰς family')
  })

  it('renders the rationale verbatim', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: HUMILITY_GROUPING, pointer: null },
    })
    expect(wrapper.find('[data-testid="tier2-rationale"]').text()).toContain(
      'Humility-cluster: lexically close Greek roots',
    )
  })

  it('renders the unverified epistemic chip (DEC-081 / DEC-115 line)', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: HUMILITY_GROUPING, pointer: null },
    })
    expect(wrapper.find('[data-testid="tier2-vstate-chip"]').text()).toContain(
      'unverified — human review required',
    )
  })
})

describe('Tier2GroupingSection — pointer view', () => {
  it('renders the pointer card when pointer (not grouping) is provided', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: null, pointer: POINTER },
    })
    expect(wrapper.find('[data-testid="tier2-grouping-pointer"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tier2-grouping-section"]').exists()).toBe(false)
  })

  it('renders a link back to the anchor concept', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: null, pointer: POINTER },
    })
    expect(wrapper.find('[data-testid="tier2-pointer-humility"]').exists()).toBe(true)
  })

  it('renders multiple anchors when the concept belongs to multiple groupings', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: {
        grouping: null,
        pointer: { grouping_anchors: ['humility', 'patience'] },
      },
    })
    expect(wrapper.find('[data-testid="tier2-pointer-humility"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tier2-pointer-patience"]').exists()).toBe(true)
  })
})

describe('Tier2GroupingSection — placeholder view', () => {
  it('renders the placeholder when neither grouping nor pointer is set', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: null, pointer: null },
    })
    expect(wrapper.find('[data-testid="tier2-grouping-placeholder"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tier2-grouping-section"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="tier2-grouping-pointer"]').exists()).toBe(false)
  })

  it('placeholder mentions Tier-2 explicitly so users understand the section', () => {
    const wrapper = mountWithVuetify(Tier2GroupingSection, {
      props: { grouping: null, pointer: null },
    })
    expect(wrapper.find('[data-testid="tier2-grouping-placeholder"]').text()).toContain(
      'Tier-2',
    )
  })
})
