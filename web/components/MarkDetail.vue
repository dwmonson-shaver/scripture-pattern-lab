<script setup lang="ts">
import type { ConceptSummary, MarkOut } from '~~/types/api'

/**
 * Detail view for a selected mark: the marked phrase, the concept(s) attached
 * (with authored-color swatches — USER DATA), and the edit actions. For a
 * "Just highlight" mark (no concept) it offers to associate one.
 *
 * Actions (Slice 1 scope): Change concept, Add concept, Remove mark. A note
 * reminds the reader that the gold handles in the text adjust the span. The
 * prototype's "Tell me about this" and pattern view are OUT of scope.
 */
const props = defineProps<{
  mark: MarkOut
  /** The marked text, resolved by the parent from the chapter + offsets. */
  phrase: string
  concepts: ConceptSummary[]
}>()

const emit = defineEmits<{
  back: []
  change: []
  add: []
  remove: []
}>()

const conceptByName = computed<Record<string, ConceptSummary>>(() => {
  const map: Record<string, ConceptSummary> = {}
  for (const c of props.concepts) map[c.name] = c
  return map
})

const attached = computed(() =>
  props.mark.concept_names.map((n) => conceptByName.value[n]).filter(Boolean),
)

const hasConcept = computed(() => props.mark.concept_names.length > 0)
</script>

<template>
  <div data-testid="mark-detail">
    <div class="d-flex align-center justify-space-between mb-3">
      <v-btn
        size="small"
        variant="text"
        prepend-icon="mdi-chevron-left"
        data-testid="mark-back"
        @click="emit('back')"
        >Concepts</v-btn
      >
    </div>

    <v-card variant="outlined" class="pa-3 mb-3">
      <p class="text-body-1 font-italic mb-3" data-testid="mark-phrase">“{{ phrase }}”</p>

      <div v-if="hasConcept" class="d-flex flex-wrap ga-2 mb-3" data-testid="mark-concepts">
        <v-chip
          v-for="c in attached"
          :key="c.name"
          size="small"
          variant="outlined"
        >
          <span
            class="mark-swatch mr-2"
            :style="{ backgroundColor: c.authored_color || 'rgb(var(--v-theme-secondary))' }"
            aria-hidden="true"
          />
          {{ c.name }}
        </v-chip>
      </div>
      <p v-else class="text-body-2 text-medium-emphasis mb-3" data-testid="mark-unassigned">
        Plain highlight — not yet tied to a concept.
      </p>

      <div class="d-flex flex-wrap ga-2">
        <v-btn
          v-if="hasConcept"
          size="small"
          variant="outlined"
          data-testid="mark-change"
          @click="emit('change')"
          >Change concept</v-btn
        >
        <v-btn
          size="small"
          variant="outlined"
          :prepend-icon="hasConcept ? 'mdi-plus' : undefined"
          data-testid="mark-add"
          @click="emit('add')"
        >
          {{ hasConcept ? 'Add concept' : 'Associate a concept' }}
        </v-btn>
        <v-btn
          size="small"
          variant="outlined"
          color="error"
          data-testid="mark-remove"
          @click="emit('remove')"
          >Remove mark</v-btn
        >
      </div>

      <p class="text-caption text-medium-emphasis mt-3" data-testid="mark-handles-note">
        Drag the handles in the text to adjust the span.
      </p>
    </v-card>
  </div>
</template>

<style scoped>
.mark-swatch {
  display: inline-block;
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 3px;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.12);
}
</style>
