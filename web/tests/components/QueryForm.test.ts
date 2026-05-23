import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import QueryForm from '~~/components/QueryForm.vue'

describe('QueryForm', () => {
  it('emits @run when the button is clicked with non-empty query', async () => {
    const wrapper = mountWithVuetify(QueryForm, {
      props: { modelValue: 'where do faith and hope appear', pending: false },
    })
    const btn = wrapper.get('[data-testid="query-run"]')
    await btn.trigger('click')
    expect(wrapper.emitted('run')).toBeTruthy()
    expect(wrapper.emitted('run')).toHaveLength(1)
  })

  it('does NOT emit @run when modelValue is empty', async () => {
    const wrapper = mountWithVuetify(QueryForm, {
      props: { modelValue: '', pending: false },
    })
    const btn = wrapper.get('[data-testid="query-run"]')
    await btn.trigger('click')
    expect(wrapper.emitted('run')).toBeFalsy()
  })

  it('does NOT emit @run when modelValue is whitespace', async () => {
    const wrapper = mountWithVuetify(QueryForm, {
      props: { modelValue: '   \n  ', pending: false },
    })
    await wrapper.get('[data-testid="query-run"]').trigger('click')
    expect(wrapper.emitted('run')).toBeFalsy()
  })

  it('does NOT emit @run while pending', async () => {
    const wrapper = mountWithVuetify(QueryForm, {
      props: { modelValue: 'real query', pending: true },
    })
    await wrapper.get('[data-testid="query-run"]').trigger('click')
    expect(wrapper.emitted('run')).toBeFalsy()
  })

  it('emits update:modelValue when the textarea changes', async () => {
    const wrapper = mountWithVuetify(QueryForm, {
      props: { modelValue: 'initial', pending: false },
    })
    const textarea = wrapper.get('textarea')
    await textarea.setValue('updated')
    const emits = wrapper.emitted('update:modelValue')
    expect(emits).toBeTruthy()
    expect(emits?.[emits.length - 1]).toEqual(['updated'])
  })
})
