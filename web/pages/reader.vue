<script setup lang="ts">
import { useDisplay } from 'vuetify'
import type {
  ConceptCreateRequest,
  ConceptUpdateRequest,
  ConnectionType,
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
definePageMeta({ title: 'Reader', layout: 'reader' })

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
const connectionStore = useConnections()
const { notify } = useToast()

// Layout mode (spec): Versed (default) ↔ Continuous. Page-local; no reload.
const mode = ref<'versed' | 'continuous'>('versed')

// Multi-select concept highlight (spec: dim-others-keep-underline).
const conceptHighlight = useConceptSelection()
const selectedConcepts = computed(() => Array.from(conceptHighlight.selected.value))

const chapterScope = computed(() => ({
  corpus: corpus.value,
  book: book.value,
  chapter: chapter.value,
  version: version.value,
}))

// Track the last actually-loaded scope so the spy-suppression check can tell a
// pure chapter scroll-spy from a real book/version/corpus nav (F5).
const lastLoaded = reactive({ corpus: corpus.value, book: book.value, version: version.value })

async function reloadAll(): Promise<void> {
  await loadChapter()
  await markStore.loadForChapter(chapterScope.value)
  // Record the scope that is now loaded so the scroll-spy suppression check can
  // distinguish a pure chapter spy-update from a real book/version/corpus nav.
  lastLoaded.corpus = corpus.value
  lastLoaded.book = book.value
  lastLoaded.version = version.value
}

// Initial load — client-only (`server: false`). The reader's state lives in
// composable refs, which do NOT transfer from SSR to the client; letting this
// run on the server renders a full chapter into the HTML, then the client
// hydrates against empty refs — a hydration mismatch that breaks the chrome
// and strands the page on "No chapter loaded" (prod bug, 2026-07-03). With
// server:false both sides start empty and the client fetches after mount.
await useAsyncData(
  'reader-init',
  async () => {
    await Promise.all([loadVersions(), conceptStore.load(), connectionStore.load()])
    await reloadAll()
    return true
  },
  { server: false },
)

// Sentinel: the chapter value that a scroll-spy event set (already loaded) —
// suppress its reload, but ONLY when the change is purely that chapter (a real
// book/version/corpus nav in the same tick must still reload). A boolean flag
// could be consumed by a coalesced real nav; the sentinel is specific (F5).
const spyTarget = ref<number | null>(null)

// Reload chapter + marks when the navigation target changes.
watch(
  () => [corpus.value, book.value, chapter.value, version.value],
  () => {
    const target = spyTarget.value
    spyTarget.value = null
    // Suppress only when the change is exactly the spy-driven chapter and
    // nothing else (book/version/corpus) moved with it.
    if (
      target !== null &&
      chapter.value === target &&
      book.value === lastLoaded.book &&
      version.value === lastLoaded.version &&
      corpus.value === lastLoaded.corpus
    ) {
      return
    }
    resetPanel()
    void reloadAll()
  },
)

/** Scroll-spy: a chapter opening scrolled into view → reflect in the dropdown. */
function onChapterInView(ch: number): void {
  if (ch === chapter.value) return
  spyTarget.value = ch
  chapter.value = ch
}

// --- panel state ------------------------------------------------------------
type PanelView = 'library' | 'search' | 'edit' | 'mark' | 'connections'
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

// The popup serves two states: a live selection (pendingSelection set) and a
// committed mark (activeMarkId set, no pending). Copy uses whichever text is
// current; Remove is enabled only for a committed mark (LDS: greyed on a fresh
// selection, active on a mark).
const popupSelectedText = computed(() =>
  pendingSelection.value ? pendingPhrase.value : activeMarkPhrase.value,
)
const popupCanRemove = computed(() => !pendingSelection.value && activeMarkId.value !== null)

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
  conceptHighlight.clear()
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

/**
 * Three-state dismissal (spec):
 *  ① live selection — popup shows while a selection is active; Esc / click-off
 *    / ✕ dismiss it (clear pending + native selection).
 *  ② committed mark — persists; clicking it activates it (onMarkClick).
 *  ③ concept highlight — clicking empty space / Esc / Clear turns it off.
 */
function dismissLiveSelection(): void {
  pendingSelection.value = null
  pendingPhrase.value = ''
  closePopup()
  if (import.meta.client) window.getSelection()?.removeAllRanges()
}

/** State ③ + active mark off: clear the highlighted concept(s) + active mark. */
function clearHighlight(): void {
  activeMarkId.value = null
  conceptHighlight.clear()
  if (panelView.value === 'mark') panelView.value = 'library'
}

/** Library row → toggle the concept in/out of the multi-select highlight. */
function onToggleConcept(name: string): void {
  conceptHighlight.toggle(name)
}

function onReaderKeydown(e: KeyboardEvent): void {
  if (e.key !== 'Escape') return
  if (popupOpen.value || pendingSelection.value) {
    dismissLiveSelection()
  } else if (activeMarkId.value !== null) {
    clearHighlight()
  }
}

/** A click outside the popup / panel / toolbar / handles / a mark dismisses. */
function onReaderClickAway(e: MouseEvent): void {
  if (!import.meta.client) return
  const t = e.target as HTMLElement | null
  if (
    t?.closest?.(
      '[data-testid="selection-popup"], .concept-aside, .v-navigation-drawer, .reader-bar, .span-handle, .concept-mark',
    )
  ) {
    return
  }
  // Clicking empty space (including inside the reader gutter) dismisses the
  // live selection first, else clears the concept highlight / active mark.
  if (popupOpen.value || pendingSelection.value) {
    // Only dismiss if the click is NOT (re)starting a selection in the text.
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed) dismissLiveSelection()
  } else if (activeMarkId.value !== null) {
    clearHighlight()
  }
}

onMounted(() => {
  document.addEventListener('keydown', onReaderKeydown)
  document.addEventListener('click', onReaderClickAway)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onReaderKeydown)
  document.removeEventListener('click', onReaderClickAway)
})

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
function onMarkClick(payload: {
  id: number
  rect: { left: number; top: number; bottom: number }
}): void {
  const { id, rect } = payload
  activeMarkId.value = id
  editingConceptName.value = null
  associate.value = null
  pendingSelection.value = null
  panelView.value = 'mark'
  // Activating a mark highlights its concept(s) (spec state ②→③ link).
  const m = markStore.marks.value.find((mk) => mk.id === id)
  for (const name of m?.concept_names ?? []) conceptHighlight.add(name)
  // LDS-style: show the quick-action popup anchored on the mark (Copy / Remove
  // enabled) alongside the detail panel; single-verse marks also get handles.
  popupAnchor.value = rect
  popupOpen.value = true
  if (mobile.value) drawer.value = true
}

async function onPopupCopy(): Promise<void> {
  const text = popupSelectedText.value
  if (!text || !import.meta.client) return
  try {
    await navigator.clipboard.writeText(text)
    notify('Copied')
  } catch {
    notify('Could not copy to the clipboard.', 'error')
  }
}

async function onPopupRemove(): Promise<void> {
  const m = activeMark.value
  if (!m) return
  const ok = await markStore.remove(m.id)
  closePopup()
  if (!ok) {
    notify(markStore.error.value?.body.detail.message ?? 'Could not remove the mark.', 'error')
    return
  }
  activeMarkId.value = null
  conceptHighlight.clear()
  if (panelView.value === 'mark') panelView.value = 'library'
  notify('Mark removed')
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
  if (!result) {
    // Surface the failure instead of silently doing nothing — the common case
    // is a duplicate name (409) when a concept by that name already exists.
    const msg = conceptStore.error.value?.body.detail.message
    notify(msg ?? 'Could not save the concept.', 'error')
    return
  }
  notify(payload.mode === 'create' ? `Created “${result.name}”` : `Saved “${result.name}”`)
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

// Delete a concept (the library's are-you-sure dialog already confirmed).
// Marks keep their highlight but lose the association (backend cascade), so
// the chapter's marks are reloaded to reflect that; the deleted name also
// leaves the multi-select highlight set.
async function onRemoveConcept(name: string): Promise<void> {
  const ok = await conceptStore.remove(name)
  if (!ok) {
    notify(conceptStore.error.value?.body.detail.message ?? 'Could not delete the concept.', 'error')
    return
  }
  if (conceptHighlight.isSelected(name)) conceptHighlight.toggle(name)
  await markStore.loadForChapter(chapterScope.value)
  notify(`Deleted “${name}”`)
}

// --- connections ------------------------------------------------------------
function onOpenConnections(): void {
  panelView.value = 'connections'
}

function onConnectionsBack(): void {
  panelView.value = 'library'
}

async function onCreateConnection(req: {
  member_names: string[]
  types: ConnectionType[]
  note: string | null
}): Promise<void> {
  const created = await connectionStore.create(req)
  if (!created) {
    notify(connectionStore.error.value?.body.detail.message ?? 'Could not create the connection.', 'error')
    return
  }
  notify(`Connected ${created.members.join(' → ')}`)
}

async function onRemoveConnection(id: number): Promise<void> {
  const ok = await connectionStore.remove(id)
  notify(ok ? 'Connection deleted' : (connectionStore.error.value?.body.detail.message ?? 'Could not delete the connection.'), ok ? 'success' : 'error')
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
    const names = ctx.mode === 'add' ? Array.from(new Set([...mark.concept_names, name])) : [name]
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
/** Edit the concept attached to the active mark → open the concept edit form.
 * This is the in-reader entry to the concept-update path (F9). */
function onMarkEdit(name: string): void {
  editingConceptName.value = name
  panelView.value = 'edit'
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
  <!-- App-shell (spec): the screen fills the viewport and does not scroll; only
       the reader text column (and the panel) scroll independently. -->
  <div class="reader-screen">
    <ReaderBar
      v-model:corpus="corpus"
      v-model:book="book"
      v-model:chapter="chapter"
      v-model:version="version"
      v-model:greek-on="greekOn"
      v-model:mode="mode"
      :versions="versions"
      :pending="readerPending"
      @prev="prevChapter()"
      @next="nextChapter()"
    />

    <ErrorPanel v-if="readerError" :error="readerError" class="ma-4 flex-none" />

    <div class="reader-stage">
      <main class="reader-main" data-testid="reader-main">
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
          :mode="mode"
          :selected-concepts="selectedConcepts"
          @select="onSelect"
          @mark-click="onMarkClick"
          @chip-tap="onChipTap"
          @chapter-in-view="onChapterInView"
        />
      </main>

      <ConceptPanel
        v-model:drawer="drawer"
        :view="panelView"
        :concepts="conceptStore.concepts.value"
        :connections="connectionStore.connections.value"
        :active-mark="activeMark"
        :active-mark-phrase="activeMarkPhrase"
        :editing-concept="editingConcept"
        :create-prefill="createPrefill"
        :associate-label="associateLabel"
        :selected-concepts="selectedConcepts"
        @toggle-concept="onToggleConcept"
        @clear-highlight="clearHighlight"
        @new-concept="onNewConcept"
        @pick-concept="onPickConcept"
        @remove-concept="onRemoveConcept"
        @open-connections="onOpenConnections"
        @connections-back="onConnectionsBack"
        @create-connection="onCreateConnection"
        @remove-connection="onRemoveConnection"
        @save-concept="onSaveConcept"
        @cancel-edit="onCancelEdit"
        @mark-back="onMarkBack"
        @mark-change="onMarkChange"
        @mark-add="onMarkAdd"
        @mark-remove="onMarkRemove"
        @mark-edit="onMarkEdit"
      />
    </div>

    <SelectionPopup
      v-model="popupOpen"
      :anchor="popupAnchor"
      :selected-text="popupSelectedText"
      :can-remove="popupCanRemove"
      @concept="onPopupConcept"
      @highlight="onPopupHighlight"
      @copy="onPopupCopy"
      @remove="onPopupRemove"
      @cancel="dismissLiveSelection"
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
/* App-shell: the screen fills the page-content area and does not itself
 * scroll; the reader column + panel scroll independently (spec #screen). The
 * reader uses the `reader` layout, which strips the default v-container padding
 * so this shell can own the full height. */
.reader-screen {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
.flex-none {
  flex: none;
}
.reader-stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 21rem;
  flex: 1;
  min-height: 0;
}
.reader-main {
  overflow-y: auto;
  min-height: 0;
}
@media (max-width: 1280px) {
  .reader-stage {
    grid-template-columns: 1fr;
  }
}
</style>
