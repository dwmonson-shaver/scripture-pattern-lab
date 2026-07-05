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
  /** The selected/marked text — enables Copy when non-empty. */
  selectedText?: string
  /** True when the popup targets a committed mark (enables Remove). */
  canRemove?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  concept: []
  highlight: []
  copy: []
  remove: []
  cancel: []
}>()

const canCopy = computed(() => !!props.selectedText && props.selectedText.trim().length > 0)

// Clamp the popup into the viewport horizontally; prefer below the selection,
// flip above if it would overflow the bottom. Width/height are approximate
// (the popup is small) — mirrors the prototype's openPop math.
const style = computed(() => {
  const a = props.anchor
  if (!a) return { display: 'none' }
  const pw = 340
  const ph = 104
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
    <!-- Concept/highlight actions apply to a fresh selection; on a committed
         mark (canRemove) the detail panel owns concept editing, so this row
         is hidden and only the quick actions below remain. -->
    <div v-if="!canRemove" class="popup-row">
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
      <v-btn variant="text" size="large" data-testid="popup-highlight" @click="emit('highlight')">
        <span class="highlight-dot mr-2" aria-hidden="true" />
        Just highlight
      </v-btn>
    </div>
    <div class="popup-row">
      <v-btn
        variant="text"
        size="small"
        prepend-icon="mdi-content-copy"
        :disabled="!canCopy"
        data-testid="popup-copy"
        @click="emit('copy')"
      >
        Copy
      </v-btn>
      <v-btn
        variant="text"
        size="small"
        color="error"
        prepend-icon="mdi-delete-outline"
        :disabled="!canRemove"
        data-testid="popup-remove"
        @click="emit('remove')"
      >
        Remove
      </v-btn>
      <v-btn
        variant="text"
        icon="mdi-close"
        size="small"
        aria-label="Cancel selection"
        data-testid="popup-cancel"
        @click="emit('cancel')"
      />
    </div>
  </v-card>
</template>

<style scoped>
.selection-popup {
  position: fixed;
  z-index: 60;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  max-width: min(24rem, 94vw);
}
.popup-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
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
