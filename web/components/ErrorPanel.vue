<script setup lang="ts">
import type { ProxyErrorShape } from '~~/composables/useQuery'

const props = defineProps<{ error: ProxyErrorShape }>()

// Severity-by-status: 5xx is system fault, 4xx is request fault.
const severity = computed<'error' | 'warning' | 'info'>(() => {
  if (props.error.status === 0) return 'info'
  if (props.error.status >= 500) return 'error'
  if (props.error.status >= 400) return 'warning'
  return 'info'
})

const detail = computed(() => props.error.body.detail)

const titleCase = (s: string): string =>
  s
    .split(/[_\s]+/)
    .map((p) => (p.length > 0 ? p[0].toUpperCase() + p.slice(1) : p))
    .join(' ')

const codeLabel = computed(() => {
  const code = detail.value?.error ?? 'unknown_error'
  return titleCase(code)
})

const showDetails = ref(false)
const hasDetails = computed(() => {
  const d = detail.value?.details
  if (d === null || d === undefined) return false
  if (typeof d !== 'object') return false
  return Object.keys(d as Record<string, unknown>).length > 0
})
</script>

<template>
  <v-alert :type="severity" :title="codeLabel" class="mb-6" data-testid="error-panel" closable>
    <p class="mb-2">{{ detail?.message ?? 'no message' }}</p>
    <p v-if="error.status !== 0" class="text-caption text-medium-emphasis">
      HTTP {{ error.status }} · code <code>{{ detail?.error ?? 'unknown' }}</code>
    </p>
    <v-expand-transition>
      <div v-if="showDetails && hasDetails" class="mt-3">
        <pre
          class="text-caption pa-3 rounded"
          style="
            background: rgba(var(--v-theme-on-surface), 0.05);
            white-space: pre-wrap;
            word-break: break-word;
          "
          data-testid="error-details"
          >{{ JSON.stringify(detail?.details, null, 2) }}</pre
        >
      </div>
    </v-expand-transition>
    <template v-if="hasDetails" #append>
      <v-btn
        variant="text"
        size="small"
        :prepend-icon="showDetails ? 'mdi-chevron-up' : 'mdi-chevron-down'"
        @click="showDetails = !showDetails"
      >
        Details
      </v-btn>
    </template>
  </v-alert>
</template>
