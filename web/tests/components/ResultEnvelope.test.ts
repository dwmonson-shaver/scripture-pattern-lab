import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ResultEnvelope from '~~/components/ResultEnvelope.vue'
import type { QueryNLResponse } from '~~/types/backend'

const SAMPLE: QueryNLResponse = {
  query: 'faith > hope > love',
  validation: {
    status: 'supported',
    executable_plan: {},
    findings: [],
    engine_version: '0.1',
    grounding: 'prior-grounded',
  },
  result: {
    candidates: [
      {
        tokens: [],
        reference: '1Cor 13:13',
        match_type: 'conceptual',
        alignment: [],
      },
      {
        tokens: [],
        reference: '1Cor 13:13',
        match_type: 'conceptual',
        alignment: [],
      },
    ],
    stages_used: ['concept'],
    contextualization: {
      observed_count: 2,
      node_baselines: [
        { node_index: 0, value: 'faith', resolved_lemmas: ['πίστις'], count: 483, match_type: 'conceptual', sample_size: 137554 },
        { node_index: 1, value: 'hope', resolved_lemmas: ['ἐλπίς'], count: 84, match_type: 'conceptual', sample_size: 137554 },
        { node_index: 2, value: 'love', resolved_lemmas: ['ἀγάπη'], count: 259, match_type: 'conceptual', sample_size: 137554 },
      ],
      alternative_orderings: [
        { sequence_label: 'faith > hope > love', count: 2, is_observed: true },
        { sequence_label: 'faith > love > hope', count: 0, is_observed: false },
        { sequence_label: 'hope > faith > love', count: 0, is_observed: false },
        { sequence_label: 'hope > love > faith', count: 0, is_observed: false },
        { sequence_label: 'love > faith > hope', count: 0, is_observed: false },
        { sequence_label: 'love > hope > faith', count: 0, is_observed: false },
      ],
      null_distribution: null,
    },
  },
  explanation: {
    query_shown: 'faith > hope > love',
    nl_source: 'where do faith hope love appear together',
    validation_notes: [],
    results: [
      {
        reference: '1Cor 13:13',
        text_display: 'πίστις, ἐλπίς, ἀγάπη',
        match_type: 'conceptual',
        score: null,
        explanation: 'matched the flagship sequence',
      },
      {
        reference: '1Cor 13:13',
        text_display: 'πίστις, ἐλπίς, ἀγάπη',
        match_type: 'conceptual',
        score: null,
        explanation: 'matched a second chain through the same verse',
      },
    ],
    contextualization: null,
    summary: 'Two matches at 1Cor 13:13.\nThe ordering is unique.',
  },
  translation: {
    confidence: 0.95,
    alternatives: ['hope < faith > love'],
    explanation: 'compiled to the conceptual sequence',
  },
}

describe('ResultEnvelope', () => {
  it('renders the compiled DSL', () => {
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: SAMPLE } })
    expect(wrapper.text()).toContain('faith > hope > love')
  })

  it('renders the validation status chip', () => {
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: SAMPLE } })
    expect(wrapper.find('[data-testid="validation-status"]').text()).toContain('supported')
  })

  it('renders all result rows', () => {
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: SAMPLE } })
    const rows = wrapper.findAll('[data-testid="result-row"]')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('1Cor 13:13')
    expect(rows[0].text()).toContain('conceptual')
  })

  it('renders Greek text in result rows via .text-grc wrapper', () => {
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: SAMPLE } })
    const greekSpans = wrapper.findAll('[data-testid="greek-text"]')
    expect(greekSpans.length).toBeGreaterThan(0)
    // At least one of them contains the flagship lemmas.
    const text = greekSpans.map((s) => s.text()).join(' ')
    expect(text).toContain('πίστις')
  })

  it('renders all three node baselines', () => {
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: SAMPLE } })
    const ctxCard = wrapper.find('[data-testid="contextualization-card"]')
    expect(ctxCard.text()).toContain('483')
    expect(ctxCard.text()).toContain('84')
    expect(ctxCard.text()).toContain('259')
  })

  it('renders all six alternative orderings with the observed one highlighted', () => {
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: SAMPLE } })
    const ctx = wrapper.find('[data-testid="contextualization-card"]')
    expect(ctx.text()).toContain('faith > hope > love')
    expect(ctx.text()).toContain('faith > love > hope')
    expect(ctx.text()).toContain('hope > faith > love')
    expect(ctx.text()).toContain('hope > love > faith')
    expect(ctx.text()).toContain('love > faith > hope')
    expect(ctx.text()).toContain('love > hope > faith')
    expect(ctx.text()).toContain('observed')
  })

  it('renders the explanation summary preserving line breaks', () => {
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: SAMPLE } })
    const summary = wrapper.find('[data-testid="explanation-summary"]')
    expect(summary.text()).toContain('Two matches at 1Cor 13:13')
    expect(summary.text()).toContain('The ordering is unique')
  })

  it('renders translation confidence as a percentage', () => {
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: SAMPLE } })
    expect(wrapper.text()).toContain('95% confidence')
  })

  it('does not crash on empty alternatives list', () => {
    const noAlts: QueryNLResponse = {
      ...SAMPLE,
      translation: { ...SAMPLE.translation, alternatives: [] },
    }
    const wrapper = mountWithVuetify(ResultEnvelope, { props: { response: noAlts } })
    expect(wrapper.exists()).toBe(true)
  })
})
