<script setup lang="ts">
import { useDisplay } from 'vuetify'
import type {
  ConceptCreateRequest,
  ConceptUpdateRequest,
  GreekTokenOut,
  MarkCreateRequest,
} from '~~/types/api'

/**
 * The concept-identification reader workbench (Slice 1, DEC-149).
 *
 * Wires ReaderBar + ChapterView + ConceptPanel + SelectionPopup + SpanHandles.
 * The page owns the cross-component state (reader nav, concepts, marks, and the
 * panel's current sub-view); the composables own the fetch/CRUD. Default anchor
 * is the prototype's: nt / rom / 8 / kjv.
 *
 * Scope is concept identification only — no connections, axes, patterns, AI
 * explainer. A "Just highlight" (mark with no concept) is in scope.
 */
definePageMeta({ title: 'Reader' })

const { mobile } = useDisplay()

const {
  corpus,
  book,
  chapter,
  version,
  greekOn,
  chapterData,
  versions,
  pending: readerPending,
  error: readerError,
  loadChapter,
  loadVersions,
  nextChapter,
  prevChapter,
} = useReader({ corpus: 'nt', book: 'rom', chapter: 8, version: 'kjv' })

const conceptStore = useConcepts()
const markStore = useMarks()

const chapterScope = computed(() => ({
  corpus: corpus.value,
  book: book.value,
  chapter: chapter.value,
  version: version.value,
}))

async function reloadAll(): Promise<void> {
  await loadChapter()
  await markStore.loadForChapter(chapterScope.value)
}

// Initial load — useAsyncData so it runs once under SSR and on the client.
await useAsyncData('reader-init', async () => {
  await Promise.all([loadVersions(), conceptStore.load()])
  await reloadAll()
  return true
})

// Reload chapter + marks when the navigation target changes.
watch(
  () => [corpus.value, book.value, chapter.value, version.value],
  () => {
    resetPanel()
    void reloadAll()
  },
)

// --- panel state ------------------------------------------------------------
type PanelView = 'library' | 'search' | 'edit' | 'mark'
const panelView = ref<PanelView>('library')
const drawer = ref(false)
const activeMarkId = ref<number | null>(null)
const editingConceptName = ref<string | null>(null)
const createPrefill = ref('')
// Drives whether search-associate targets a pending (new) selection or an
// existing mark, and whether picking replaces or adds.
const associate = ref<
  | { kind: 'pending'; req: MarkCreateRequest }
  | { kind: 'mark'; id: number; mode: 'replace' | 'add' }
  | null
>(null)

// Selection popup state — declared here so `associateLabel` can reference
// `pendingPhrase` without a use-before-define.
const popupOpen = ref(false)
const popupAnchor = ref<{ left: number; top: number; bottom: number } | null>(null)
const pendingSelection = ref<MarkCreateRequest | null>(null)
const pendingPhrase = ref('')

const activeMark = computed(
  () => markStore.marks.value.find((m) => m.id === activeMarkId.value) ?? null,
)

const editingConcept = computed(() =>
  editingConceptName.value
    ? (conceptStore.concepts.value.find((c) => c.name === editingConceptName.value) ?? null)
    : null,
)

/** Resolve a mark's text from the loaded chapter + its char offsets. */
function markPhrase(): string {
  const m = activeMark.value
  const doc = chapterData.value
  if (!m || !doc) return ''
  const parts: string[] = []
  for (const v of doc.verses) {
    if (v.verse < m.verse_start || v.verse > m.verse_end) continue
    const isFirst = v.verse === m.verse_start
    const isLast = v.verse === m.verse_end
    const start = isFirst ? Math.max(0, m.char_start) : 0
    const end = isLast ? Math.min(v.english_text.length, m.char_end) : v.english_text.length
    parts.push(v.english_text.slice(start, end))
  }
  return parts.join(' ')
}
const activeMarkPhrase = computed(markPhrase)

const associateLabel = computed(() => {
  if (!associate.value) return null
  if (associate.value.kind === 'pending') {
    return `Mark “${pendingPhrase.value}” as:`
  }
  const verb = associate.value.mode === 'add' ? 'Add another concept to' : 'Change the concept on'
  return `${verb} “${activeMarkPhrase.value}”`
})

function resetPanel(): void {
  panelView.value = 'library'
  activeMarkId.value = null
  editingConceptName.value = null
  createPrefill.value = ''
  associate.value = null
}

// --- selection popup --------------------------------------------------------
function onSelect(payload: {
  verseStart: number
  verseEnd: number
  charStart: number
  charEnd: number
  rect: { left: number; top: number; bottom: number }
}): void {
  pendingSelection.value = {
    book: book.value,
    chapter: chapter.value,
    corpus_id: corpus.value,
    version_code: version.value,
    verse_start: payload.verseStart,
    verse_end: payload.verseEnd,
    char_start: payload.charStart,
    char_end: payload.charEnd,
  }
  pendingPhrase.value = resolvePhrase(payload)
  popupAnchor.value = payload.rect
  popupOpen.value = true
}

function resolvePhrase(payload: {
  verseStart: number
  verseEnd: number
  charStart: number
  charEnd: number
}): string {
  const doc = chapterData.value
  if (!doc) return ''
  const parts: string[] = []
  for (const v of doc.verses) {
    if (v.verse < payload.verseStart || v.verse > payload.verseEnd) continue
    const isFirst = v.verse === payload.verseStart
    const isLast = v.verse === payload.verseEnd
    const start = isFirst ? payload.charStart : 0
    const end = isLast ? payload.charEnd : v.english_text.length
    parts.push(v.english_text.slice(start, end))
  }
  return parts.join(' ')
}

function closePopup(): void {
  popupOpen.value = false
  popupAnchor.value = null
}

// "Mark as concept" → open associate-search for the pending selection.
function onPopupConcept(): void {
  if (!pendingSelection.value) return
  associate.value = { kind: 'pending', req: pendingSelection.value }
  panelView.value = 'search'
  closePopup()
  if (mobile.value) drawer.value = true
}

// "Just highlight" → create a mark with no concept immediately.
async function onPopupHighlight(): Promise<void> {
  if (!pendingSelection.value) return
  const created = await markStore.create({ ...pendingSelection.value, concept_names: [] })
  closePopup()
  if (created) {
    activeMarkId.value = created.id
    panelView.value = 'mark'
    if (mobile.value) drawer.value = true
  }
}

// --- panel actions ----------------------------------------------------------
function onMarkClick(id: number): void {
  activeMarkId.value = id
  editingConceptName.value = null
  associate.value = null
  panelView.value = 'mark'
  if (mobile.value) drawer.value = true
}

function onOpenConcept(name: string): void {
  // Slice 1: no full concept-detail view in scope; opening jumps to edit so
  // the reader can adjust the authored fields. (Detail/pattern view is later.)
  editingConceptName.value = name
  panelView.value = 'edit'
}

function onNewConcept(prefill: string): void {
  editingConceptName.value = null
  createPrefill.value = prefill
  panelView.value = 'edit'
}

async function onSaveConcept(
  payload:
    | { mode: 'create'; req: ConceptCreateRequest }
    | { mode: 'update'; name: string; req: ConceptUpdateRequest },
): Promise<void> {
  const result =
    payload.mode === 'create'
      ? await conceptStore.create(payload.req)
      : await conceptStore.update(payload.name, payload.req)
  if (!result) return
  // If we were in the middle of associating a concept to a selection/mark,
  // finish that association with the just-created/edited concept.
  if (associate.value) {
    await applyAssociation(result.name)
    return
  }
  panelView.value = 'library'
  editingConceptName.value = null
}

function onCancelEdit(): void {
  panelView.value = associate.value ? 'search' : 'library'
  editingConceptName.value = null
}

// pick a concept in associate-search
async function onPickConcept(name: string): Promise<void> {
  await applyAssociation(name)
}

async function applyAssociation(name: string): Promise<void> {
  const ctx = associate.value
  if (!ctx) return
  if (ctx.kind === 'pending') {
    const created = await markStore.create({ ...ctx.req, concept_names: [name] })
    associate.value = null
    if (created) {
      activeMarkId.value = created.id
      panelView.value = 'mark'
    }
  } else {
    const mark = markStore.marks.value.find((m) => m.id === ctx.id)
    if (!mark) {
      associate.value = null
      return
    }
    const names =
      ctx.mode === 'add'
        ? Array.from(new Set([...mark.concept_names, name]))
        : [name]
    await markStore.update(ctx.id, { concept_names: names })
    associate.value = null
    activeMarkId.value = ctx.id
    panelView.value = 'mark'
  }
}

// mark-detail actions
function onMarkBack(): void {
  resetPanel()
}
function onMarkChange(): void {
  if (!activeMark.value) return
  associate.value = { kind: 'mark', id: activeMark.value.id, mode: 'replace' }
  panelView.value = 'search'
}
function onMarkAdd(): void {
  if (!activeMark.value) return
  associate.value = { kind: 'mark', id: activeMark.value.id, mode: 'add' }
  panelView.value = 'search'
}
async function onMarkRemove(): Promise<void> {
  if (!activeMark.value) return
  await markStore.remove(activeMark.value.id)
  resetPanel()
}

// --- span handles -----------------------------------------------------------
const chapterViewRef = ref<{ $el: HTMLElement } | null>(null)

const activeMarkSingleVerse = computed(
  () => !!activeMark.value && activeMark.value.verse_start === activeMark.value.verse_end,
)

const activeMarkEl = computed<HTMLElement | null>(() => {
  if (!import.meta.client || !activeMark.value || !chapterViewRef.value) return null
  const root = chapterViewRef.value.$el as HTMLElement
  return root?.querySelector?.(`mark[data-mark="${activeMark.value.id}"]`) ?? null
})

const activeVerseTextEl = computed<HTMLElement | null>(() => {
  if (!import.meta.client || !activeMark.value || !chapterViewRef.value) return null
  const root = chapterViewRef.value.$el as HTMLElement
  return (
    root?.querySelector?.(`.verse[data-verse="${activeMark.value.verse_start}"] .verse-text`) ??
    null
  )
})

const activeVerseText = computed(() => {
  const m = activeMark.value
  const doc = chapterData.value
  if (!m || !doc) return ''
  return doc.verses.find((v) => v.verse === m.verse_start)?.english_text ?? ''
})

async function onSpanChange(payload: { charStart: number; charEnd: number }): Promise<void> {
  if (!activeMark.value) return
  await markStore.update(activeMark.value.id, {
    char_start: payload.charStart,
    char_end: payload.charEnd,
  })
}

// chip tap is handled inside ChapterView (flashGloss); nothing to do here yet.
function onChipTap(_payload: { verse: number; token: GreekTokenOut }): void {
  // no-op: the visual flash lives in ChapterView. Hook kept for future
  // interlinear-driven selection.
}
</script>

<template>
  <div>
    <ReaderBar
      v-model:corpus="corpus"
      v-model:book="book"
      v-model:chapter="chapter"
      v-model:version="version"
      v-model:greek-on="greekOn"
      :versions="versions"
      :pending="readerPending"
      @prev="prevChapter()"
      @next="nextChapter()"
    />

    <ErrorPanel v-if="readerError" :error="readerError" class="ma-4" />

    <div class="reader-stage">
      <main>
        <v-btn
          v-if="mobile"
          variant="outlined"
          prepend-icon="mdi-format-list-bulleted"
          class="ma-3"
          data-testid="open-panel"
          @click="drawer = true"
        >
          Concepts
        </v-btn>

        <ChapterView
          ref="chapterViewRef"
          :chapter="chapterData"
          :marks="markStore.marks.value"
          :concepts="conceptStore.concepts.value"
          :greek-on="greekOn"
          :active-mark-id="activeMarkId"
          @select="onSelect"
          @mark-click="onMarkClick"
          @chip-tap="onChipTap"
        />
      </main>

      <ConceptPanel
        v-model:drawer="drawer"
        :view="panelView"
        :concepts="conceptStore.concepts.value"
        :active-mark="activeMark"
        :active-mark-phrase="activeMarkPhrase"
        :editing-concept="editingConcept"
        :create-prefill="createPrefill"
        :associate-label="associateLabel"
        @open-concept="onOpenConcept"
        @new-concept="onNewConcept"
        @pick-concept="onPickConcept"
        @save-concept="onSaveConcept"
        @cancel-edit="onCancelEdit"
        @mark-back="onMarkBack"
        @mark-change="onMarkChange"
        @mark-add="onMarkAdd"
        @mark-remove="onMarkRemove"
      />
    </div>

    <SelectionPopup
      v-model="popupOpen"
      :anchor="popupAnchor"
      @concept="onPopupConcept"
      @highlight="onPopupHighlight"
    />

    <SpanHandles
      :active="!!activeMark && activeMarkSingleVerse"
      :verse-text="activeVerseText"
      :char-start="activeMark?.char_start ?? 0"
      :char-end="activeMark?.char_end ?? 0"
      :verse-text-el="activeVerseTextEl"
      :mark-el="activeMarkEl"
      @span-change="onSpanChange"
    />
  </div>
</template>

<style scoped>
.reader-stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 25rem;
  align-items: start;
}
@media (max-width: 1280px) {
  .reader-stage {
    grid-template-columns: 1fr;
  }
}
</style>
