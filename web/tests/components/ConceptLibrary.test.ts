import { afterEach, describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ConceptLibrary from '~~/components/ConceptLibrary.vue'
import type { ConceptSummary } from '~~/types/api'

function concept(name: string): ConceptSummary {
  return {
    name,
    description: null,
    verification_state: 'unverified',
    lemma_count: 0,
    lemmas: [],
    authored_color: '#E0A12E',
    authored_polarity: '+',
    authored_opposite_name: null,
  }
}

const concepts = [concept('Hope'), concept('Patience'), concept('Love')]

// VDialog teleports its content to document.body and does not clean it up on
// unmount within a test file; clear it so a later test's querySelector cannot
// match a stale (unmounted) dialog from an earlier test.
afterEach(() => {
  document.body.innerHTML = ''
})

describe('ConceptLibrary', () => {
  it('lists all concepts in library mode', () => {
    const wrapper = mountWithVuetify(ConceptLibrary, { props: { concepts } })
    expect(wrapper.findAll('[data-testid="concept-row"]')).toHaveLength(3)
  })

  it('emits toggle with the concept name in library mode', async () => {
    const wrapper = mountWithVuetify(ConceptLibrary, { props: { concepts } })
    await wrapper.get('[data-concept="Hope"]').trigger('click')
    expect(wrapper.emitted('toggle')?.[0]).toEqual(['Hope'])
  })

  it('marks selected rows in library mode', () => {
    const wrapper = mountWithVuetify(ConceptLibrary, {
      props: { concepts, selected: ['Patience'] },
    })
    expect(wrapper.get('[data-concept="Patience"]').attributes('data-selected')).toBe('true')
    expect(wrapper.get('[data-concept="Hope"]').attributes('data-selected')).toBe('false')
  })

  it('emits pick (not toggle) in associate mode', async () => {
    const wrapper = mountWithVuetify(ConceptLibrary, {
      props: { concepts, contextLabel: 'Mark “the love of Christ” as:' },
    })
    await wrapper.get('[data-concept="Love"]').trigger('click')
    expect(wrapper.emitted('pick')?.[0]).toEqual(['Love'])
    expect(wrapper.emitted('toggle')).toBeFalsy()
  })

  it('shows the associate context label', () => {
    const wrapper = mountWithVuetify(ConceptLibrary, {
      props: { concepts, contextLabel: 'Mark “x” as:' },
    })
    expect(wrapper.get('[data-testid="associate-context"]').text()).toContain('Mark')
  })

  it('emits create carrying the search text', async () => {
    const wrapper = mountWithVuetify(ConceptLibrary, { props: { concepts } })
    const input = wrapper.get('[data-testid="concept-search"]').get('input')
    await input.setValue('Glory')
    await wrapper.get('[data-testid="concept-new"]').trigger('click')
    expect(wrapper.emitted('create')?.[0]).toEqual(['Glory'])
  })

  describe('delete flow', () => {
    it('trash button opens the confirm dialog without toggling the row', async () => {
      const wrapper = mountWithVuetify(ConceptLibrary, { props: { concepts } })
      await wrapper
        .get('[data-concept="Hope"]')
        .get('[data-testid="concept-delete"]')
        .trigger('click')
      expect(wrapper.emitted('toggle')).toBeFalsy()
      expect(wrapper.emitted('remove')).toBeFalsy()
      // The dialog teleports to the overlay container — search the document.
      expect(document.body.textContent).toContain('Delete “Hope”?')
    })

    async function openDialogAndClick(testid: string): Promise<ReturnType<typeof mountWithVuetify>> {
      const wrapper = mountWithVuetify(ConceptLibrary, { props: { concepts } })
      await wrapper
        .get('[data-concept="Hope"]')
        .get('[data-testid="concept-delete"]')
        .trigger('click')
      const matches = document.querySelectorAll(`[data-testid="${testid}"]`)
      const btn = matches[matches.length - 1] as HTMLElement
      // The dialog is teleported outside the wrapper; a bubbling MouseEvent
      // drives Vuetify's click listener (bare .click() does not in happy-dom).
      btn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))
      await wrapper.vm.$nextTick()
      return wrapper
    }

    it('confirm emits remove with the concept name', async () => {
      const wrapper = await openDialogAndClick('concept-delete-confirm')
      expect(wrapper.emitted('remove')?.[0]).toEqual(['Hope'])
    })

    it('cancel closes without emitting remove', async () => {
      const wrapper = await openDialogAndClick('concept-delete-cancel')
      expect(wrapper.emitted('remove')).toBeFalsy()
    })

    it('hides the delete affordance in associate mode', () => {
      const wrapper = mountWithVuetify(ConceptLibrary, {
        props: { concepts, contextLabel: 'Mark “x” as:' },
      })
      expect(wrapper.find('[data-testid="concept-delete"]').exists()).toBe(false)
    })
  })
})
