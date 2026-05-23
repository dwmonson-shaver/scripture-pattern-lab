import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import GreekText from '~~/components/GreekText.vue'

describe('GreekText', () => {
  it('renders slot content', () => {
    const wrapper = mountWithVuetify(GreekText, {
      slots: { default: 'πίστις, ἐλπίς, ἀγάπη' },
    })
    expect(wrapper.text()).toBe('πίστις, ἐλπίς, ἀγάπη')
  })

  it('applies the .text-grc class for SBL Greek font', () => {
    const wrapper = mountWithVuetify(GreekText, {
      slots: { default: 'πίστις' },
    })
    expect(wrapper.classes()).toContain('text-grc')
  })

  it('passes ariaLabel prop to the element', () => {
    const wrapper = mountWithVuetify(GreekText, {
      props: { ariaLabel: 'faith' },
      slots: { default: 'πίστις' },
    })
    expect(wrapper.attributes('aria-label')).toBe('faith')
  })
})
