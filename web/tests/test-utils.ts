/**
 * Vuetify-aware mount helper. Every component test composes a fresh
 * Vuetify instance so tests don't share theme state.
 *
 * Nuxt auto-imports our `components/` at runtime. In Vitest there's no
 * Nuxt component resolver, so any `<GreekText>` (or other auto-imported
 * component) referenced inside a SUT would render as an unknown element
 * — silently passing text assertions but stripping the `data-testid`
 * attribute that the wrapping component sets. We register them
 * explicitly here so component tests see the real DOM the user sees.
 */

import { mount } from '@vue/test-utils'
import type { Component } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import GreekText from '../components/GreekText.vue'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyMountOpts = Record<string, any>

export function mountWithVuetify<T extends Component>(
  component: T,
  options: AnyMountOpts = {},
) {
  const vuetify = createVuetify({ components, directives })
  const existingPlugins = (options.global?.plugins ?? []) as unknown[]
  const existingComponents = (options.global?.components ?? {}) as Record<string, Component>
  return mount(component, {
    ...options,
    global: {
      ...(options.global ?? {}),
      plugins: [...existingPlugins, vuetify],
      components: {
        ...existingComponents,
        GreekText,
      },
    },
  })
}
