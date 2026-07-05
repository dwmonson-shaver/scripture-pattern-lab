<script setup lang="ts">
import type { ConceptSummary, ConnectionOut, ConnectionType } from '~~/types/api'

/**
 * Connections panel view (Slice 2). Two modes:
 *  - list: existing connections (A → B with type chips) + delete (are-you-sure).
 *  - build: pick a first concept, a second concept (order matters for
 *    directional types), choose one or more types, optional note, create.
 *
 * A connection is a corrigible human-authored prior — the backend never
 * auto-promotes it. Chrome uses semantic tokens; no raw color.
 */
const props = defineProps<{
  concepts: ConceptSummary[]
  connections: ConnectionOut[]
}>()

const emit = defineEmits<{
  back: []
  create: [req: { member_names: string[]; types: ConnectionType[]; note: string | null }]
  remove: [id: number]
}>()

// type value → { label, directional }. Directional types read member order
// (A → B); symmetric ones ignore it (shown as A ↔ B).
const TYPE_META: Record<ConnectionType, { label: string; directional: boolean }> = {
  interchange: { label: 'Interchange (God ↔ man)', directional: false },
  sequence: { label: 'Sequence', directional: true },
  prerequisite: { label: 'Prerequisite', directional: true },
  produces: { label: 'Produces', directional: true },
  compound: { label: 'Compound', directional: true },
  opposite: { label: 'Opposite', directional: false },
  association: { label: 'Association', directional: false },
  unknown: { label: 'Unknown', directional: false },
}
const TYPE_ORDER = Object.keys(TYPE_META) as ConnectionType[]

const conceptNames = computed(() => props.concepts.map((c) => c.name))

const mode = ref<'list' | 'build'>('list')
const firstName = ref<string | null>(null)
const secondName = ref<string | null>(null)
const selectedTypes = ref<ConnectionType[]>([])
const note = ref('')

const canCreate = computed(
  () =>
    !!firstName.value &&
    !!secondName.value &&
    firstName.value !== secondName.value &&
    selectedTypes.value.length > 0,
)

// A connection reads directional if ANY of its types is directional.
function arrowFor(types: ConnectionType[]): string {
  return types.some((t) => TYPE_META[t]?.directional) ? '→' : '↔'
}

function startBuild(): void {
  firstName.value = null
  secondName.value = null
  selectedTypes.value = []
  note.value = ''
  mode.value = 'build'
}

function submit(): void {
  if (!canCreate.value || !firstName.value || !secondName.value) return
  emit('create', {
    member_names: [firstName.value, secondName.value],
    types: [...selectedTypes.value],
    note: note.value.trim() ? note.value.trim() : null,
  })
  // Optimistic return to the list; the reader reloads and toasts the result.
  mode.value = 'list'
}

// Delete confirm (deliberate friction, mirrors the concept library).
const deleteTarget = ref<ConnectionOut | null>(null)
function confirmDelete(): void {
  if (deleteTarget.value) emit('remove', deleteTarget.value.id)
  deleteTarget.value = null
}
function labelFor(c: ConnectionOut): string {
  return `${c.members.join(` ${arrowFor(c.types)} `)}`
}
</script>

<template>
  <div data-testid="connections-view">
    <div class="d-flex align-center justify-space-between mb-3">
      <v-btn
        variant="text"
        size="small"
        prepend-icon="mdi-chevron-left"
        data-testid="connections-back"
        @click="emit('back')"
      >
        Concepts
      </v-btn>
      <span class="text-overline text-medium-emphasis">Connections</span>
    </div>

    <!-- LIST MODE -->
    <template v-if="mode === 'list'">
      <v-list lines="two" density="compact" class="bg-transparent py-0">
        <v-list-item
          v-for="c in connections"
          :key="c.id"
          class="px-2 rounded"
          data-testid="connection-row"
          :data-connection-id="c.id"
        >
          <v-list-item-title class="font-weight-medium">{{ labelFor(c) }}</v-list-item-title>
          <v-list-item-subtitle class="d-flex align-center flex-wrap ga-1 mt-1">
            <v-chip
              v-for="t in c.types"
              :key="t"
              size="x-small"
              variant="tonal"
              :data-type="t"
            >
              {{ TYPE_META[t]?.label ?? t }}
            </v-chip>
          </v-list-item-subtitle>
          <template #append>
            <v-btn
              icon="mdi-delete-outline"
              size="x-small"
              variant="text"
              :aria-label="`Delete connection ${labelFor(c)}`"
              data-testid="connection-delete"
              @click="deleteTarget = c"
            />
          </template>
        </v-list-item>

        <v-list-item v-if="!connections.length" data-testid="connections-empty">
          <v-list-item-subtitle class="text-medium-emphasis">
            No connections yet. Map one to start gathering evidence.
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <v-btn
        variant="outlined"
        color="primary"
        block
        prepend-icon="mdi-vector-polyline-plus"
        class="mt-3"
        data-testid="connection-new"
        @click="startBuild"
      >
        New connection
      </v-btn>
    </template>

    <!-- BUILD MODE -->
    <template v-else>
      <p class="text-body-2 text-medium-emphasis mb-3">
        Pick two concepts. Order matters for directional types (first → second).
      </p>

      <v-autocomplete
        v-model="firstName"
        :items="conceptNames"
        label="First concept"
        density="comfortable"
        variant="outlined"
        hide-details
        class="mb-3"
        data-testid="connection-first"
      />
      <v-autocomplete
        v-model="secondName"
        :items="conceptNames"
        label="Second concept"
        density="comfortable"
        variant="outlined"
        hide-details
        class="mb-1"
        data-testid="connection-second"
      />
      <p
        v-if="firstName && secondName && firstName === secondName"
        class="text-caption text-error mb-2"
        data-testid="connection-same-warning"
      >
        Pick two different concepts.
      </p>

      <p class="text-body-2 text-medium-emphasis mt-3 mb-2">Type(s) — choose one or more:</p>
      <v-chip-group v-model="selectedTypes" multiple column data-testid="connection-types">
        <v-chip
          v-for="t in TYPE_ORDER"
          :key="t"
          :value="t"
          filter
          variant="outlined"
          size="small"
          :data-type="t"
        >
          {{ TYPE_META[t].label }}
        </v-chip>
      </v-chip-group>

      <v-textarea
        v-model="note"
        label="Note (optional)"
        density="comfortable"
        variant="outlined"
        rows="2"
        auto-grow
        hide-details
        class="mt-3"
        data-testid="connection-note"
      />

      <div class="d-flex justify-end ga-2 mt-4">
        <v-btn variant="text" data-testid="connection-cancel" @click="mode = 'list'">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :disabled="!canCreate"
          data-testid="connection-create"
          @click="submit"
        >
          Create connection
        </v-btn>
      </div>
    </template>

    <v-dialog
      :model-value="deleteTarget !== null"
      max-width="24rem"
      data-testid="connection-delete-dialog"
      @update:model-value="deleteTarget = null"
    >
      <v-card v-if="deleteTarget">
        <v-card-title class="text-h6">Delete this connection?</v-card-title>
        <v-card-text class="text-body-2">
          {{ labelFor(deleteTarget) }} — this removes the connection and its
          types. The concepts themselves are untouched.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" data-testid="connection-delete-cancel" @click="deleteTarget = null">
            Cancel
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            data-testid="connection-delete-confirm"
            @click="confirmDelete"
          >
            Yes, delete it
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
