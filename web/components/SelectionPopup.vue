<script setup lang="ts">
/**
 * Floating popup shown while a phrase is selected (dismissal state ①). The
 * spec's action set: "Mark as concept" (primary → opens the concept search),
 * "Just highlight" (a mark with no concept — still in scope) with a swatch
 * dot, and "✕" Cancel (dismiss the live selection).
 *
 * The prototype's "Tell me about this" (the AI explainer) is deliberately
 * OMITTED — out of scope for concept identification.
 *
 * Positioned at a viewport rect supplied by the parent (the selection's
 * bounding rect). Chrome only — semantic tokens, no raw color.
 */
const props = defineProps<{
  /** Show/hide. */
  modelValue: boolean
  /** Viewport-space anchor rect of the current selection. */
  anchor: { left: number; bottom: number; top: number } | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  concept: []
  highlight: []
  cancel: []
}>()

// Clamp the popup into the viewport horizontally; prefer below the selection,
// flip above if it would overflow the bottom. Width/height are approximate
// (the popup is small) — mirrors the prototype's openPop math.
const style = computed(() => {
  const a = props.anchor
  if (!a) return { display: 'none' }
  const pw = 320
  const ph = 56
  let left = a.left
  let top = a.bottom + 8
  if (import.meta.client) {
    if (left + pw > window.innerWidth - 12) left = window.innerWidth - pw - 12
    if (left < 12) left = 12
    if (top + ph > window.innerHeight - 12) top = Math.max(12, a.top - ph - 8)
  }
  return { left: `${left}px`, top: `${top}px` }
})
</script>

<template>
  <v-card
    v-if="modelValue"
    class="selection-popup pa-1"
    elevation="8"
    :style="style"
    data-testid="selection-popup"
  >
    <v-btn
      color="primary"
      variant="text"
      prepend-icon="mdi-pencil"
      size="large"
      data-testid="popup-concept"
      @click="emit('concept')"
    >
      Mark as concept
    </v-btn>
    <v-btn
      variant="text"
      size="large"
      data-testid="popup-highlight"
      @click="emit('highlight')"
    >
      <span class="highlight-dot mr-2" aria-hidden="true" />
      Just highlight
    </v-btn>
    <v-btn
      variant="text"
      icon="mdi-close"
      size="large"
      aria-label="Cancel selection"
      data-testid="popup-cancel"
      @click="emit('cancel')"
    />
  </v-card>
</template>

<style scoped>
.selection-popup {
  position: fixed;
  z-index: 60;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  max-width: min(22rem, 92vw);
}
.highlight-dot {
  display: inline-block;
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 50%;
  background: rgb(var(--v-theme-secondary)); /* gilt — neutral highlight swatch */
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.15);
}
</style>
