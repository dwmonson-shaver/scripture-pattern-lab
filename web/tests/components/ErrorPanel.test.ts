import { describe, expect, it } from 'vitest'
import { mountWithVuetify } from '../test-utils'
import ErrorPanel from '~~/components/ErrorPanel.vue'
import type { ProxyErrorShape } from '~~/composables/useQuery'

const makeError = (over: Partial<ProxyErrorShape> = {}): ProxyErrorShape => ({
  status: 422,
  body: {
    detail: {
      error: 'validation_unsupported',
      message: 'inverse not supported',
      details: { findings: [{ code: 'UNSUPPORTED_INVERSE' }] },
    },
  },
  ...over,
})

describe('ErrorPanel', () => {
  it('renders the error code as title case', () => {
    const wrapper = mountWithVuetify(ErrorPanel, { props: { error: makeError() } })
    expect(wrapper.text()).toContain('Validation Unsupported')
  })

  it('renders the message', () => {
    const wrapper = mountWithVuetify(ErrorPanel, { props: { error: makeError() } })
    expect(wrapper.text()).toContain('inverse not supported')
  })

  it('uses error severity for 5xx', () => {
    const wrapper = mountWithVuetify(ErrorPanel, {
      props: {
        error: makeError({
          status: 503,
          body: { detail: { error: 'engine_unavailable', message: 'db down', details: null } },
        }),
      },
    })
    // v-alert with type="error" gets a "v-alert--variant-tonal" + theme class.
    const alert = wrapper.find('[data-testid="error-panel"]')
    expect(alert.exists()).toBe(true)
    expect(alert.classes().some((c) => c.includes('error'))).toBe(true)
  })

  it('uses warning severity for 4xx', () => {
    const wrapper = mountWithVuetify(ErrorPanel, { props: { error: makeError() } })
    const alert = wrapper.find('[data-testid="error-panel"]')
    expect(alert.exists()).toBe(true)
    expect(alert.classes().some((c) => c.includes('warning'))).toBe(true)
  })

  it('uses info severity for network errors (status 0)', () => {
    const wrapper = mountWithVuetify(ErrorPanel, {
      props: {
        error: makeError({
          status: 0,
          body: { detail: { error: 'network_error', message: 'down', details: null } },
        }),
      },
    })
    const alert = wrapper.find('[data-testid="error-panel"]')
    expect(alert.classes().some((c) => c.includes('info'))).toBe(true)
  })

  it('shows HTTP status code in the body when status > 0', () => {
    const wrapper = mountWithVuetify(ErrorPanel, { props: { error: makeError() } })
    expect(wrapper.text()).toContain('HTTP 422')
  })

  it('does not show HTTP status when status == 0', () => {
    const wrapper = mountWithVuetify(ErrorPanel, {
      props: {
        error: makeError({
          status: 0,
          body: { detail: { error: 'network_error', message: 'x', details: null } },
        }),
      },
    })
    expect(wrapper.text()).not.toContain('HTTP 0')
  })
})
