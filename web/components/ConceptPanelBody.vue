<script setup lang="ts">
import type {
  ConceptCreateRequest,
  ConceptSummary,
  ConceptUpdateRequest,
  MarkOut,
} from '~~/types/api'

/**
 * The view-router body shared by `ConceptPanel`'s drawer and aside hosts.
 * Pulled out so the four-way switch (library / search / edit / mark) is
 * written once. Pure presentational glue — forwards every event up.
 */
type PanelView = 'library' | 'search' | 'edit' | 'mark'

defineProps<{
  view: PanelView
  concepts: ConceptSummary[]
  activeMark: MarkOut | null
  activeMarkPhrase: string
  editingConcept: ConceptSummary | null
  createPrefill: string
  associateLabel: string | null
}>()

const emit = defineEmits<{
  'open-concept': [name: string]
  'new-concept': [prefillName: string]
  'pick-concept': [name: string]
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
    />

    <ConceptLibrary
      v-else
      :concepts="concepts"
      :context-label="view === 'search' ? associateLabel : null"
      @open="emit('open-concept', $event)"
      @pick="emit('pick-concept', $event)"
      @create="emit('new-concept', $event)"
    />
  </div>
</template>
