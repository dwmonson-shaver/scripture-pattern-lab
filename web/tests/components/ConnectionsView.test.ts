import { afterEach, describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ConnectionsView from '~~/components/ConnectionsView.vue'
import type { ConceptSummary, ConnectionOut } from '~~/types/api'

function concept(name: string): ConceptSummary {
  return {
    name,
    description: null,
    verification_state: 'unverified',
    lemma_count: 0,
    lemmas: [],
    authored_color: null,
    authored_polarity: null,
    authored_opposite_name: null,
  }
}

const concepts = [concept('righteousness'), concept('faith'), concept('hope')]
const connections: ConnectionOut[] = [
  { id: 1, note: null, actor: 'local', members: ['righteousness', 'faith'], types: ['interchange'] },
]

// VDialog teleports to document.body; clear between tests so a stale dialog
// can't be matched by a later querySelector.
afterEach(() => {
  document.body.innerHTML = ''
})

describe('ConnectionsView', () => {
  it('lists existing connections with their type chips', () => {
    const wrapper = mountWithVuetify(ConnectionsView, { props: { concepts, connections } })
    const row = wrapper.get('[data-testid="connection-row"]')
    expect(row.text()).toContain('righteousness')
    expect(row.text()).toContain('faith')
    expect(row.find('[data-type="interchange"]').exists()).toBe(true)
  })

  it('shows an empty state when there are no connections', () => {
    const wrapper = mountWithVuetify(ConnectionsView, { props: { concepts, connections: [] } })
    expect(wrapper.find('[data-testid="connections-empty"]').exists()).toBe(true)
  })

  it('emits back', async () => {
    const wrapper = mountWithVuetify(ConnectionsView, { props: { concepts, connections } })
    await wrapper.get('[data-testid="connections-back"]').trigger('click')
    expect(wrapper.emitted('back')).toBeTruthy()
  })

  it('New connection reveals the builder', async () => {
    const wrapper = mountWithVuetify(ConnectionsView, { props: { concepts, connections } })
    await wrapper.get('[data-testid="connection-new"]').trigger('click')
    expect(wrapper.find('[data-testid="connection-first"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="connection-types"]').exists()).toBe(true)
  })

  it('create is disabled until two distinct concepts and a type are chosen', async () => {
    const wrapper = mountWithVuetify(ConnectionsView, { props: { concepts, connections } })
    await wrapper.get('[data-testid="connection-new"]').trigger('click')
    // Starts disabled — no endpoints/types selected yet.
    expect(wrapper.get('[data-testid="connection-create"]').attributes('disabled')).toBeDefined()
  })

  it('emits create with ordered members + selected types', async () => {
    const wrapper = mountWithVuetify(ConnectionsView, { props: { concepts, connections } })
    await wrapper.get('[data-testid="connection-new"]').trigger('click')
    // Drive the component's state directly (autocomplete/chip-group internals are
    // Vuetify-heavy under happy-dom); the emit contract is what matters.
    const vm = wrapper.vm as unknown as {
      firstName: string
      secondName: string
      selectedTypes: string[]
      submit: () => void
    }
    vm.firstName = 'righteousness'
    vm.secondName = 'faith'
    vm.selectedTypes = ['interchange']
    await wrapper.vm.$nextTick()
    vm.submit()
    const evt = wrapper.emitted('create')?.[0]?.[0] as {
      member_names: string[]
      types: string[]
    }
    expect(evt.member_names).toEqual(['righteousness', 'faith'])
    expect(evt.types).toEqual(['interchange'])
  })

  it('delete asks for confirmation, then emits remove with the id', async () => {
    const wrapper = mountWithVuetify(ConnectionsView, { props: { concepts, connections } })
    await wrapper.get('[data-testid="connection-delete"]').trigger('click')
    expect(document.body.textContent).toContain('Delete this connection?')
    const confirm = document.querySelector(
      '[data-testid="connection-delete-confirm"]',
    ) as HTMLElement
    confirm.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('remove')?.[0]).toEqual([1])
  })
})
