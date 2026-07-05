<script setup lang="ts">
import type {
  ConceptCreateRequest,
  ConceptSummary,
  ConceptUpdateRequest,
  ConnectionOut,
  ConnectionType,
  MarkOut,
} from '~~/types/api'

/**
 * The view-router body shared by `ConceptPanel`'s drawer and aside hosts.
 * Pulled out so the switch (library / search / edit / mark / connections) is
 * written once. Pure presentational glue — forwards every event up.
 */
type PanelView = 'library' | 'search' | 'edit' | 'mark' | 'connections'

defineProps<{
  view: PanelView
  concepts: ConceptSummary[]
  connections: ConnectionOut[]
  activeMark: MarkOut | null
  activeMarkPhrase: string
  editingConcept: ConceptSummary | null
  createPrefill: string
  associateLabel: string | null
  /** Names of concepts currently highlighted (multi-select; library mode). */
  selectedConcepts: string[]
}>()

const emit = defineEmits<{
  'toggle-concept': [name: string]
  'new-concept': [prefillName: string]
  'pick-concept': [name: string]
  'remove-concept': [name: string]
  'open-connections': []
  'connections-back': []
  'create-connection': [
    req: { member_names: string[]; types: ConnectionType[]; note: string | null },
  ]
  'remove-connection': [id: number]
  'save-concept': [
    payload:
      | { mode: 'create'; req: ConceptCreateRequest }
      | { mode: 'update'; name: string; req: ConceptUpdateRequest },
  ]
  'cancel-edit': []
  'mark-back': []
  'mark-change': []
  'mark-add': []
  'mark-remove': []
  'mark-edit': [name: string]
}>()
</script>

<template>
  <div data-testid="concept-panel-body">
    <ConceptEditForm
      v-if="view === 'edit'"
      :concept="editingConcept"
      :prefill-name="createPrefill"
      @save="emit('save-concept', $event)"
      @cancel="emit('cancel-edit')"
    />

    <MarkDetail
      v-else-if="view === 'mark' && activeMark"
      :mark="activeMark"
      :phrase="activeMarkPhrase"
      :concepts="concepts"
      @back="emit('mark-back')"
      @change="emit('mark-change')"
      @add="emit('mark-add')"
      @remove="emit('mark-remove')"
      @edit="emit('mark-edit', $event)"
    />

    <ConnectionsView
      v-else-if="view === 'connections'"
      :concepts="concepts"
      :connections="connections"
      @back="emit('connections-back')"
      @create="emit('create-connection', $event)"
      @remove="emit('remove-connection', $event)"
    />

    <ConceptLibrary
      v-else
      :concepts="concepts"
      :context-label="view === 'search' ? associateLabel : null"
      :selected="selectedConcepts"
      @toggle="emit('toggle-concept', $event)"
      @pick="emit('pick-concept', $event)"
      @create="emit('new-concept', $event)"
      @remove="emit('remove-concept', $event)"
      @open-connections="emit('open-connections')"
    />
  </div>
</template>
