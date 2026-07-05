<script setup lang="ts">
import type { ConceptSummary } from '~~/types/api'

/**
 * The concept library / search sub-view. Search-as-you-type filters the list
 * by name; each row shows the authored color swatch (USER DATA — sanctioned
 * inline color), the name, a polarity chip, and the verification state. A
 * "New concept" action and per-row pick/open round it out.
 *
 * Doubles as the "associate concept" search when `contextLabel` is set (the
 * marking flow): same list, but picking emits `pick` to attach the concept to
 * the pending mark, and the create button carries the typed name forward.
 *
 * Chrome uses semantic tokens; the swatch is the only raw-color render.
 */
const props = defineProps<{
  concepts: ConceptSummary[]
  /** When set, render in "associate" mode with this context line shown. */
  contextLabel?: string | null
  /** Names of concepts currently highlighted (multi-select; library mode). */
  selected?: string[]
}>()

const emit = defineEmits<{
  /** Toggle a concept in/out of the highlight set (library mode). */
  toggle: [name: string]
  /** Pick a concept to associate (associate mode). */
  pick: [name: string]
  /** Start creating a new concept; carries the current search text. */
  create: [prefillName: string]
  /** Delete a concept — emitted only after the are-you-sure dialog confirms. */
  remove: [name: string]
  /** Switch the panel to the connections view. */
  'open-connections': []
}>()

const query = ref('')

// Delete flow: the trash affordance opens a confirm dialog (deliberate
// friction — deletion must never be one tap). The component owns the dialog
// as pure UI state and emits `remove` only on explicit confirmation; the
// page owns the actual delete call.
const deleteTarget = ref<string | null>(null)

function askDelete(name: string): void {
  deleteTarget.value = name
}

function confirmDelete(): void {
  if (deleteTarget.value) emit('remove', deleteTarget.value)
  deleteTarget.value = null
}

const filtered = computed<ConceptSummary[]>(() => {
  const f = query.value.trim().toLowerCase()
  if (!f) return props.concepts
  return props.concepts.filter((c) => c.name.toLowerCase().includes(f))
})

const isAssociate = computed(() => props.contextLabel != null)
const selectedSet = computed(() => new Set(props.selected ?? []))

const POLARITY_LABEL: Record<string, string> = {
  '+': 'Positive',
  '-': 'Negative',
  '±': 'Neutral',
}

function stateLabel(state: string): string {
  return state.replace(/_/g, ' ')
}

function onRow(name: string): void {
  if (isAssociate.value) emit('pick', name)
  else emit('toggle', name)
}
</script>

<template>
  <div data-testid="concept-library">
    <p
      v-if="contextLabel"
      class="text-body-2 text-medium-emphasis mb-3"
      data-testid="associate-context"
    >
      {{ contextLabel }}
    </p>

    <v-text-field
      v-model="query"
      :label="isAssociate ? 'Type to find a concept' : 'Search concepts'"
      prepend-inner-icon="mdi-magnify"
      density="comfortable"
      hide-details
      clearable
      class="mb-3"
      data-testid="concept-search"
    />

    <v-list lines="one" density="compact" class="bg-transparent py-0">
      <v-list-item
        v-for="c in filtered"
        :key="c.name"
        class="px-2 rounded concept-row"
        :class="{ 'concept-row--sel': !isAssociate && selectedSet.has(c.name) }"
        :active="!isAssociate && selectedSet.has(c.name)"
        :data-concept="c.name"
        :data-selected="!isAssociate && selectedSet.has(c.name) ? 'true' : 'false'"
        data-testid="concept-row"
        @click="onRow(c.name)"
      >
        <template #prepend>
          <span
            class="library-swatch mr-2"
            :style="{ backgroundColor: c.authored_color || 'rgb(var(--v-theme-secondary))' }"
            aria-hidden="true"
          />
        </template>
        <v-list-item-title class="d-flex align-center ga-2">
          <span class="text-truncate">{{ c.name }}</span>
          <v-chip
            v-if="c.authored_polarity"
            size="x-small"
            variant="outlined"
            :data-polarity="c.authored_polarity"
          >
            {{ POLARITY_LABEL[c.authored_polarity] ?? c.authored_polarity }}
          </v-chip>
          <span class="text-caption text-medium-emphasis text-no-wrap">{{
            stateLabel(c.verification_state)
          }}</span>
        </v-list-item-title>
        <template v-if="!isAssociate" #append>
          <v-btn
            icon="mdi-delete-outline"
            size="x-small"
            variant="text"
            class="concept-delete"
            :aria-label="`Delete ${c.name}`"
            data-testid="concept-delete"
            @click.stop="askDelete(c.name)"
          />
        </template>
      </v-list-item>

      <v-list-item v-if="!filtered.length" data-testid="concept-empty">
        <v-list-item-subtitle class="text-medium-emphasis">
          No concept matches “{{ query }}”.
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-dialog
      :model-value="deleteTarget !== null"
      max-width="22rem"
      data-testid="concept-delete-dialog"
      @update:model-value="deleteTarget = null"
    >
      <v-card v-if="deleteTarget">
        <v-card-title class="text-h6">Delete “{{ deleteTarget }}”?</v-card-title>
        <v-card-text class="text-body-2">
          This removes the concept from your library. Passages you marked with
          it keep their highlight but lose the concept.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" data-testid="concept-delete-cancel" @click="deleteTarget = null">
            Cancel
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            data-testid="concept-delete-confirm"
            @click="confirmDelete"
          >
            Yes, delete it
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-btn
      variant="outlined"
      color="primary"
      block
      prepend-icon="mdi-plus"
      class="mt-3"
      data-testid="concept-new"
      @click="emit('create', query.trim())"
    >
      {{ query.trim() ? `Create “${query.trim()}”` : 'New concept' }}
    </v-btn>

    <v-btn
      v-if="!isAssociate"
      variant="text"
      block
      prepend-icon="mdi-vector-polyline"
      class="mt-2"
      data-testid="open-connections"
      @click="emit('open-connections')"
    >
      Connections
    </v-btn>
  </div>
</template>

<style scoped>
.library-swatch {
  display: inline-block;
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 5px;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.12);
}
.concept-row {
  min-height: 2.25rem;
}
/* Quiet by default so the list stays calm; full strength on row hover. */
.concept-delete {
  opacity: 0.55;
}
.concept-row:hover .concept-delete,
.concept-delete:focus-visible {
  opacity: 1;
}
</style>
