/**
 * Vuetify-aware mount helper. Every component test composes a fresh
 * Vuetify instance so tests don't share theme state.
 */

import { mount, type MountingOptions } from '@vue/test-utils'
import type { Component } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export function mountWithVuetify<T extends Component>(
  component: T,
  options: MountingOptions<unknown> = {},
) {
  const vuetify = createVuetify({ components, directives })
  return mount(component, {
    ...options,
    global: {
      ...(options.global ?? {}),
      plugins: [...((options.global?.plugins as unknown[]) ?? []), vuetify],
    },
  })
}
