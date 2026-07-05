import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import SelectionPopup from '~~/components/SelectionPopup.vue'

const anchor = { left: 100, top: 200, bottom: 220 }

describe('SelectionPopup', () => {
  it('renders the three actions when open', () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor },
    })
    expect(wrapper.find('[data-testid="popup-concept"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="popup-highlight"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="popup-cancel"]').exists()).toBe(true)
  })

  it('emits cancel when the ✕ is clicked', async () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor },
    })
    await wrapper.get('[data-testid="popup-cancel"]').trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
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

  it('enables Copy only when there is selected text, and emits copy', async () => {
    const noText = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor, selectedText: '' },
    })
    expect(noText.get('[data-testid="popup-copy"]').attributes('disabled')).toBeDefined()

    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor, selectedText: 'When thou hast' },
    })
    const copy = wrapper.get('[data-testid="popup-copy"]')
    expect(copy.attributes('disabled')).toBeUndefined()
    await copy.trigger('click')
    expect(wrapper.emitted('copy')).toBeTruthy()
  })

  it('disables Remove on a fresh selection (LDS: greyed until marked)', () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor, selectedText: 'x', canRemove: false },
    })
    expect(wrapper.get('[data-testid="popup-remove"]').attributes('disabled')).toBeDefined()
  })

  it('committed-mark mode: hides Mark/Highlight, enables Remove, emits remove', async () => {
    const wrapper = mountWithVuetify(SelectionPopup, {
      props: { modelValue: true, anchor, selectedText: 'When thou hast', canRemove: true },
    })
    // Concept/highlight actions are hidden for a committed mark.
    expect(wrapper.find('[data-testid="popup-concept"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="popup-highlight"]').exists()).toBe(false)
    const remove = wrapper.get('[data-testid="popup-remove"]')
    expect(remove.attributes('disabled')).toBeUndefined()
    await remove.trigger('click')
    expect(wrapper.emitted('remove')).toBeTruthy()
  })
})
