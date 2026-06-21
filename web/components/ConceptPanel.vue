<script setup lang="ts">
import { useDisplay } from 'vuetify'
import type {
  ConceptCreateRequest,
  ConceptSummary,
  ConceptUpdateRequest,
  MarkOut,
} from '~~/types/api'

/**
 * The right-hand workbench panel. On a wide viewport it's a persistent aside;
 * on a narrow / touch viewport it's a slide-over `v-navigation-drawer` with a
 * scrim (useDisplay() picks). It routes between four sub-views driven by the
 * `view` prop: library, search (associate-concept), edit (concept form), and
 * mark-detail.
 *
 * The panel is presentational glue — it owns no data, only forwards events up
 * to the page (which owns reader/concept/mark state). Chrome only.
 */
type PanelView = 'library' | 'search' | 'edit' | 'mark'

const drawer = defineModel<boolean>('drawer', { default: false })

const props = defineProps<{
  view: PanelView
  concepts: ConceptSummary[]
  /** The mark shown in mark-detail / targeted by search-associate. */
  activeMark: MarkOut | null
  /** Resolved text of the active mark, for mark-detail. */
  activeMarkPhrase: string
  /** The concept open in the edit form (null = create mode). */
  editingConcept: ConceptSummary | null
  /** Prefill for the create form name. */
  createPrefill: string
  /** Context line for the associate-concept search. */
  associateLabel: string | null
  /** Names of concepts currently highlighted (multi-select; library mode). */
  selectedConcepts: string[]
}>()

const emit = defineEmits<{
  // library
  'toggle-concept': [name: string]
  'new-concept': [prefillName: string]
  // clear the multi-select highlight
  'clear-highlight': []
  // search / associate
  'pick-concept': [name: string]
  // edit form
  'save-concept': [
    payload:
      | { mode: 'create'; req: ConceptCreateRequest }
      | { mode: 'update'; name: string; req: ConceptUpdateRequest },
  ]
  'cancel-edit': []
  // mark detail
  'mark-back': []
  'mark-change': []
  'mark-add': []
  'mark-remove': []
  'mark-edit': [name: string]
}>()

const { mobile } = useDisplay()

const hasSelection = computed(() => props.selectedConcepts.length > 0)
/** The Clear affordance shows in the library/search header when concepts are
 * highlighted (spec .clearbtn). */
const showClear = computed(
  () => hasSelection.value && (props.view === 'library' || props.view === 'search'),
)

const title = computed(() => {
  switch (props.view) {
    case 'search':
      return 'Associate concept'
    case 'edit':
      return props.editingConcept ? 'Edit concept' : 'New concept'
    case 'mark':
      return 'Mark'
    default:
      return 'Concepts'
  }
})
</script>

<template>
  <!-- Narrow / touch: slide-over drawer -->
  <v-navigation-drawer
    v-if="mobile"
    v-model="drawer"
    location="right"
    temporary
    width="380"
    data-testid="concept-panel-drawer"
  >
    <div class="pa-4">
      <div class="d-flex align-center justify-space-between mb-4">
        <span class="text-overline text-medium-emphasis">{{ title }}</span>
        <div class="d-flex align-center ga-1">
          <v-btn
            v-if="showClear"
            variant="outlined"
            size="x-small"
            rounded="pill"
            data-testid="concept-clear"
            @click="emit('clear-highlight')"
          >
            Clear
          </v-btn>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            aria-label="Close panel"
            data-testid="concept-panel-close"
            @click="drawer = false"
          />
        </div>
      </div>
      <ConceptPanelBody
        :view="view"
        :concepts="concepts"
        :active-mark="activeMark"
        :active-mark-phrase="activeMarkPhrase"
        :editing-concept="editingConcept"
        :create-prefill="createPrefill"
        :associate-label="associateLabel"
        :selected-concepts="selectedConcepts"
        @toggle-concept="emit('toggle-concept', $event)"
        @new-concept="emit('new-concept', $event)"
        @pick-concept="emit('pick-concept', $event)"
        @save-concept="emit('save-concept', $event)"
        @cancel-edit="emit('cancel-edit')"
        @mark-back="emit('mark-back')"
        @mark-change="emit('mark-change')"
        @mark-add="emit('mark-add')"
        @mark-remove="emit('mark-remove')"
        @mark-edit="emit('mark-edit', $event)"
      />
    </div>
  </v-navigation-drawer>

  <!-- Wide: persistent aside -->
  <aside v-else class="concept-aside pa-4" data-testid="concept-panel-aside">
    <div class="d-flex align-center justify-space-between mb-4">
      <span class="text-overline text-medium-emphasis">{{ title }}</span>
      <v-btn
        v-if="showClear"
        variant="outlined"
        size="x-small"
        rounded="pill"
        data-testid="concept-clear"
        @click="emit('clear-highlight')"
      >
        Clear
      </v-btn>
    </div>
    <ConceptPanelBody
      :view="view"
      :concepts="concepts"
      :active-mark="activeMark"
      :active-mark-phrase="activeMarkPhrase"
      :editing-concept="editingConcept"
      :create-prefill="createPrefill"
      :associate-label="associateLabel"
      :selected-concepts="selectedConcepts"
      @toggle-concept="emit('toggle-concept', $event)"
      @new-concept="emit('new-concept', $event)"
      @pick-concept="emit('pick-concept', $event)"
      @save-concept="emit('save-concept', $event)"
      @cancel-edit="emit('cancel-edit')"
      @mark-back="emit('mark-back')"
      @mark-change="emit('mark-change')"
      @mark-add="emit('mark-add')"
      @mark-remove="emit('mark-remove')"
      @mark-edit="emit('mark-edit', $event)"
    />
  </aside>
</template>

<style scoped>
.concept-aside {
  position: sticky;
  top: 0;
  max-height: 100vh;
  overflow: auto;
  border-left: 1px solid rgb(var(--v-border-color));
  background: rgb(var(--v-theme-surface));
}
</style>
