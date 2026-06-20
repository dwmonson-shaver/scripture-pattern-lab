import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ReaderBar from '~~/components/ReaderBar.vue'
import type { VersionInfoOut } from '~~/types/api'

const versions: VersionInfoOut[] = [
  { code: 'kjv', name: 'King James Version', is_public_domain: true },
  { code: 'web', name: 'World English Bible', is_public_domain: true },
]

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    corpus: 'nt',
    book: 'rom',
    chapter: 8,
    version: 'kjv',
    greekOn: false,
    versions,
    ...overrides,
  }
}

describe('ReaderBar', () => {
  it('shows the interlinear toggle labeled Greek for the NT corpus', () => {
    const wrapper = mountWithVuetify(ReaderBar, { props: baseProps() })
    const toggle = wrapper.find('[data-testid="reader-interlinear"]')
    expect(toggle.exists()).toBe(true)
    expect(toggle.text()).toContain('Greek')
  })

  it('hides the interlinear toggle for an original-language-less corpus', () => {
    const wrapper = mountWithVuetify(ReaderBar, { props: baseProps({ corpus: 'bom' }) })
    expect(wrapper.find('[data-testid="reader-interlinear"]').exists()).toBe(false)
  })

  it('emits prev / next on the chapter arrows', async () => {
    const wrapper = mountWithVuetify(ReaderBar, { props: baseProps() })
    await wrapper.get('[data-testid="reader-prev"]').trigger('click')
    await wrapper.get('[data-testid="reader-next"]').trigger('click')
    expect(wrapper.emitted('prev')).toBeTruthy()
    expect(wrapper.emitted('next')).toBeTruthy()
  })
})
