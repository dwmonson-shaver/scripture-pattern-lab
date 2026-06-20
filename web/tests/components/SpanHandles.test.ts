import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import SpanHandles from '~~/components/SpanHandles.vue'

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    active: true,
    verseText: 'For we are saved by hope',
    charStart: 11,
    charEnd: 24,
    verseTextEl: null,
    markEl: null,
    ...overrides,
  }
}

describe('SpanHandles', () => {
  it('renders both handles when active', () => {
    const wrapper = mountWithVuetify(SpanHandles, { props: baseProps() })
    expect(wrapper.find('[data-testid="span-handle-start"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="span-handle-end"]').exists()).toBe(true)
  })

  it('renders nothing when inactive', () => {
    const wrapper = mountWithVuetify(SpanHandles, { props: baseProps({ active: false }) })
    expect(wrapper.find('[data-testid="span-handle-start"]').exists()).toBe(false)
  })
})
