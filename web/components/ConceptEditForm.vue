<script setup lang="ts">
import type {
  AuthoredPolarity,
  ConceptCreateRequest,
  ConceptSummary,
  ConceptUpdateRequest,
} from '~~/types/api'

/**
 * Create / edit form for a concept's authored display fields: title, color,
 * polarity, opposite name.
 *
 * The color swatches + custom picker render USER DATA (the chosen color), so
 * inline color is sanctioned here exactly as in the reader. The polarity
 * segmented control uses semantic-token chrome. The form never sets
 * verification_state / origin — those are backend-owned (DEC-102).
 *
 * `concept` null => create mode; otherwise edit mode (name is the immutable
 * key and is shown read-only when editing). Emits `save` with the right
 * request shape for the mode, and `cancel`.
 */
const props = defineProps<{
  concept: ConceptSummary | null
  /** Prefill the name field in create mode (from the search box). */
  prefillName?: string
}>()

const emit = defineEmits<{
  save: [
    payload:
      | { mode: 'create'; req: ConceptCreateRequest }
      | { mode: 'update'; name: string; req: ConceptUpdateRequest },
  ]
  cancel: []
}>()

const isNew = computed(() => props.concept === null)

const PALETTE = [
  '#E0A12E',
  '#2E8C99',
  '#C44A63',
  '#7B5EA7',
  '#B98A1E',
  '#3F6FB5',
  '#557A46',
  '#B5603A',
  '#5A6B8C',
  '#8A8D3F',
]

const name = ref(props.concept?.name ?? props.prefillName ?? '')
const description = ref(props.concept?.description ?? '')
const color = ref(props.concept?.authored_color ?? PALETTE[0])
const polarity = ref<AuthoredPolarity>(props.concept?.authored_polarity ?? '+')
const opposite = ref(props.concept?.authored_opposite_name ?? '')

const POLARITY_ITEMS: { value: AuthoredPolarity; label: string }[] = [
  { value: '+', label: 'Positive' },
  { value: '-', label: 'Negative' },
  { value: '±', label: 'Neutral' },
]

const canSave = computed(() => name.value.trim().length > 0)

function onSave(): void {
  if (!canSave.value) return
  const common = {
    description: description.value.trim() || null,
    authored_color: color.value || null,
    authored_polarity: polarity.value,
    authored_opposite_name: opposite.value.trim() || null,
  }
  if (props.concept) {
    emit('save', { mode: 'update', name: props.concept.name, req: common })
  } else {
    emit('save', { mode: 'create', req: { name: name.value.trim(), ...common } })
  }
}
</script>

<template>
  <div data-testid="concept-edit-form">
    <div class="d-flex align-center justify-space-between mb-3">
      <span class="text-overline text-medium-emphasis">{{
        isNew ? 'New concept' : 'Edit concept'
      }}</span>
      <v-btn
        size="small"
        variant="text"
        data-testid="concept-edit-cancel"
        @click="emit('cancel')"
        >Cancel</v-btn
      >
    </div>

    <v-text-field
      v-model="name"
      label="Title"
      :readonly="!isNew"
      :hint="isNew ? '' : 'The name is the concept key and cannot be changed here'"
      persistent-hint
      density="comfortable"
      data-testid="concept-name"
    />

    <v-textarea
      v-model="description"
      label="Description (optional)"
      rows="2"
      auto-grow
      density="comfortable"
      data-testid="concept-description"
    />

    <div class="text-caption text-medium-emphasis mt-2 mb-1">Color</div>
    <div class="d-flex flex-wrap align-center ga-2 mb-2" data-testid="concept-swatches">
      <button
        v-for="c in PALETTE"
        :key="c"
        type="button"
        class="swatch"
        :class="{ 'swatch--sel': c.toLowerCase() === color.toLowerCase() }"
        :style="{ backgroundColor: c }"
        :aria-label="`Color ${c}`"
        :data-color="c"
        @click="color = c"
      />
      <input
        v-model="color"
        type="color"
        class="swatch-pick"
        aria-label="Custom color"
        data-testid="concept-color-custom"
      />
    </div>

    <div class="text-caption text-medium-emphasis mt-2 mb-1">Polarity</div>
    <v-btn-toggle
      v-model="polarity"
      mandatory
      density="comfortable"
      variant="outlined"
      class="mb-3"
      data-testid="concept-polarity"
    >
      <v-btn
        v-for="p in POLARITY_ITEMS"
        :key="p.value"
        :value="p.value"
        size="small"
        :data-polarity="p.value"
      >
        {{ p.label }}
      </v-btn>
    </v-btn-toggle>

    <v-text-field
      v-model="opposite"
      label="Opposite of (optional)"
      density="comfortable"
      data-testid="concept-opposite"
    />

    <v-btn
      color="primary"
      block
      :disabled="!canSave"
      class="mt-2"
      data-testid="concept-save"
      @click="onSave"
    >
      {{ isNew ? 'Create concept' : 'Save changes' }}
    </v-btn>
  </div>
</template>

<style scoped>
.swatch {
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 50%;
  border: 2px solid transparent;
  padding: 0;
  cursor: pointer;
}
.swatch--sel {
  border-color: rgb(var(--v-theme-on-surface));
}
.swatch-pick {
  width: 2.2rem;
  height: 1.9rem;
  border: 1px solid rgb(var(--v-border-color));
  border-radius: 6px;
  background: transparent;
  padding: 0;
  cursor: pointer;
}
</style>
