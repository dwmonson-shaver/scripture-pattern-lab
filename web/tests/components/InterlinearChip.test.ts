import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import InterlinearChip from '~~/components/InterlinearChip.vue'
import type { GreekTokenOut } from '~~/types/api'

const token: GreekTokenOut = {
  position: 3,
  surface_form: 'ἐλπίδι',
  normalized_form: 'ελπιδι',
  lemma: 'ἐλπίς',
  morph_code: 'N-DSF',
  pos: 'noun',
}

describe('InterlinearChip', () => {
  it('renders the lemma via GreekText', () => {
    const wrapper = mountWithVuetify(InterlinearChip, { props: { token } })
    const greek = wrapper.get('[data-testid="greek-text"]')
    expect(greek.text()).toContain('ἐλπίς')
  })

  it('emits tap with the token on click', async () => {
    const wrapper = mountWithVuetify(InterlinearChip, { props: { token } })
    await wrapper.get('[data-testid="interlinear-chip"]').trigger('click')
    expect(wrapper.emitted('tap')?.[0]).toEqual([token])
  })
})
