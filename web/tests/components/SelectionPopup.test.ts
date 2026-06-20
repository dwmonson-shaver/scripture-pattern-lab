import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import SelectionPopup from '~~/components/SelectionPopup.vue'

const anchor = { left: 100, top: 200, bottom: 220 }

describe('SelectionPopup', () => {
  it('renders both choices when open', () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor },
    })
    expect(wrapper.find('[data-testid="popup-concept"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="popup-highlight"]').exists()).toBe(true)
  })

  it('does NOT render the AI explainer (out of scope)', () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor },
    })
    expect(wrapper.text().toLowerCase()).not.toContain('tell me about this')
  })

  it('emits concept when "Mark as concept" is clicked', async () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor },
    })
    await wrapper.get('[data-testid="popup-concept"]').trigger('click')
    expect(wrapper.emitted('concept')).toBeTruthy()
  })

  it('emits highlight when "Just highlight" is clicked', async () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor },
    })
    await wrapper.get('[data-testid="popup-highlight"]').trigger('click')
    expect(wrapper.emitted('highlight')).toBeTruthy()
  })

  it('renders nothing when closed', () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: false, anchor },
    })
    expect(wrapper.find('[data-testid="selection-popup"]').exists()).toBe(false)
  })
})
