<script setup lang="ts">
import type {
  ChapterReadResponse,
  ConceptSummary,
  GreekTokenOut,
  MarkOut,
  VerseRead,
} from '~~/types/api'

/**
 * The reading pane: serif chapter text with concept-highlighted spans, the
 * verse-number rubric, and (when `greekOn`) per-verse interlinear chips.
 *
 * Highlighted spans tint with the concept's `authored_color` — this is the
 * ONE place a raw color renders, because it's USER DATA (the concept's color),
 * not chrome. It's applied via inline :style only. Everything else is semantic
 * tokens. An unconcepted ("Just highlight") mark uses a neutral theme tint.
 *
 * Emits:
 *  - `select`  — a phrase was selected. Carries verse_start/verse_end + char
 *                offsets into the rendered English text (DEC-143: cross-verse
 *                allowed), plus the selection's viewport rect for popup anchor.
 *  - `mark-click` — a rendered mark span was clicked (its id).
 *  - `chip-tap`   — an interlinear chip was tapped (verse + token).
 */
const props = defineProps<{
  chapter: ChapterReadResponse | null
  marks: MarkOut[]
  concepts: ConceptSummary[]
  greekOn: boolean
  activeMarkId: number | null
}>()

const emit = defineEmits<{
  select: [
    payload: {
      verseStart: number
      verseEnd: number
      charStart: number
      charEnd: number
      rect: { left: number; top: number; bottom: number }
    },
  ]
  'mark-click': [id: number]
  'chip-tap': [payload: { verse: number; token: GreekTokenOut }]
}>()

const conceptByName = computed<Record<string, ConceptSummary>>(() => {
  const map: Record<string, ConceptSummary> = {}
  for (const c of props.concepts) map[c.name] = c
  return map
})

/** Neutral tint for marks with no concept (theme-aware, not a raw color). */
const NEUTRAL_TINT = 'rgba(var(--v-theme-on-surface), 0.10)'
const NEUTRAL_RULE = 'rgba(var(--v-theme-on-surface), 0.45)'

/**
 * Split one verse's text into plain runs and mark runs. A mark applies to this
 * verse when the verse number is within [verse_start, verse_end]; char offsets
 * are clamped to this verse's text for the single-verse case. For a multi-verse
 * mark the whole verse text is covered on the interior verses (DEC-143).
 */
interface Segment {
  text: string
  mark: MarkOut | null
}

function segmentsForVerse(verse: VerseRead): Segment[] {
  const plain = verse.english_text
  const applicable = props.marks
    .filter((m) => verse.verse >= m.verse_start && verse.verse <= m.verse_end)
    .map((m) => {
      // Resolve this mark's [start,end) within THIS verse's text.
      const isFirst = verse.verse === m.verse_start
      const isLast = verse.verse === m.verse_end
      const start = isFirst ? Math.max(0, Math.min(plain.length, m.char_start)) : 0
      const end = isLast ? Math.max(0, Math.min(plain.length, m.char_end)) : plain.length
      return { mark: m, start, end }
    })
    .filter((r) => r.end > r.start)
    .sort((a, b) => a.start - b.start)

  const segs: Segment[] = []
  let cur = 0
  for (const r of applicable) {
    if (r.start < cur) continue // skip overlaps, prototype parity
    if (r.start > cur) segs.push({ text: plain.slice(cur, r.start), mark: null })
    segs.push({ text: plain.slice(r.start, r.end), mark: r.mark })
    cur = r.end
  }
  if (cur < plain.length) segs.push({ text: plain.slice(cur), mark: null })
  return segs
}

function markStyle(mark: MarkOut): Record<string, string> {
  const primaryName = mark.concept_names[0]
  const concept = primaryName ? conceptByName.value[primaryName] : undefined
  const color = concept?.authored_color
  if (color) {
    // USER DATA — the concept's authored color. The sole sanctioned raw-color
    // render (see component doc). Tint the background, underline with the hue.
    return {
      'background-color': hexToTint(color),
      'border-bottom': `2.5px solid ${color}`,
    }
  }
  return {
    'background-color': NEUTRAL_TINT,
    'border-bottom': `2.5px solid ${NEUTRAL_RULE}`,
  }
}

/**
 * Soften an authored hex color into a readable highlight tint. Falls back to
 * a low-alpha wrap of the raw color string for non-hex inputs (e.g. named).
 */
function hexToTint(color: string): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(color.trim())
  if (m) {
    const n = parseInt(m[1], 16)
    const r = (n >> 16) & 255
    const g = (n >> 8) & 255
    const b = n & 255
    return `rgba(${r}, ${g}, ${b}, 0.32)`
  }
  return color
}

// --- selection → emit -------------------------------------------------------
const rootEl = ref<HTMLElement | null>(null)

/** Compute the char offset of a node+offset within a verse's .verse-text. */
function globalOffset(vtext: Element, node: Node, offset: number): number {
  const walker = document.createTreeWalker(vtext, NodeFilter.SHOW_TEXT, null)
  let total = 0
  let tn: Node | null
  while ((tn = walker.nextNode())) {
    if (tn === node) return total + offset
    total += (tn.nodeValue ?? '').length
  }
  return total
}

function verseOf(node: Node | null): HTMLElement | null {
  if (!node) return null
  const el = node.nodeType === 3 ? node.parentElement : (node as HTMLElement)
  return el?.closest?.('.verse') ?? null
}

function onMouseUp(): void {
  // Defer so the selection settles (prototype parity).
  setTimeout(() => {
    if (!import.meta.client) return
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed) return
    const text = sel.toString()
    if (text.trim().length < 2) return
    const range = sel.getRangeAt(0)
    const startVerseEl = verseOf(range.startContainer)
    const endVerseEl = verseOf(range.endContainer)
    if (!startVerseEl || !endVerseEl) return

    const startVerse = Number(startVerseEl.dataset.verse)
    const endVerse = Number(endVerseEl.dataset.verse)
    const startVtext = startVerseEl.querySelector('.verse-text')
    const endVtext = endVerseEl.querySelector('.verse-text')
    if (!startVtext || !endVtext) return

    let charStart = globalOffset(startVtext, range.startContainer, range.startOffset)
    let charEnd = globalOffset(endVtext, range.endContainer, range.endOffset)
    let vStart = startVerse
    let vEnd = endVerse
    // Normalize direction (DEC-143: cross-verse allowed).
    if (vEnd < vStart || (vEnd === vStart && charEnd < charStart)) {
      ;[vStart, vEnd] = [vEnd, vStart]
      ;[charStart, charEnd] = [charEnd, charStart]
    }
    const rect = range.getBoundingClientRect()
    emit('select', {
      verseStart: vStart,
      verseEnd: vEnd,
      charStart,
      charEnd,
      rect: { left: rect.left, top: rect.top, bottom: rect.bottom },
    })
  }, 1)
}

// --- interlinear flashGloss -------------------------------------------------
function onChipTap(verse: number, token: GreekTokenOut): void {
  emit('chip-tap', { verse, token })
  flashGloss(verse, token)
}

/**
 * Briefly highlight the English word(s) under a Greek token's gloss. Mirrors
 * the prototype's flashGloss: stem-match the surface/normalized form against
 * the rendered verse text, wrap the hit in a transient `.gloss-flash` span,
 * then unwrap after a beat. Client-only; no-op under SSR / tests without DOM.
 */
function flashGloss(verse: number, token: GreekTokenOut): void {
  if (!import.meta.client || !rootEl.value) return
  const vtext = rootEl.value.querySelector(
    `.verse[data-verse="${verse}"] .verse-text`,
  )
  if (!vtext) return
  // Use the normalized form's leading latin-ish stem if present, else skip —
  // Greek surface forms won't substring-match English. The English alignment
  // is approximate in Slice 1 (the live interlinear resolves every word).
  const stem = (token.normalized_form || token.surface_form || '')
    .toLowerCase()
    .replace(/[^a-z]/g, '')
    .slice(0, 4)
  if (stem.length < 3) return
  const walker = document.createTreeWalker(vtext, NodeFilter.SHOW_TEXT, null)
  let tn: Node | null
  while ((tn = walker.nextNode())) {
    const value = tn.nodeValue ?? ''
    const idx = value.toLowerCase().indexOf(stem)
    if (idx < 0) continue
    let s = idx
    while (s > 0 && /\S/.test(value[s - 1])) s--
    let e = idx + stem.length
    while (e < value.length && /\S/.test(value[e])) e++
    const r = document.createRange()
    r.setStart(tn, s)
    r.setEnd(tn, e)
    const span = document.createElement('span')
    span.className = 'gloss-flash'
    try {
      r.surroundContents(span)
    } catch {
      return
    }
    span.scrollIntoView?.({ block: 'center', behavior: 'smooth' })
    setTimeout(() => {
      const parent = span.parentNode
      if (!parent) return
      while (span.firstChild) parent.insertBefore(span.firstChild, span)
      parent.removeChild(span)
      parent.normalize?.()
    }, 1600)
    return
  }
}

function onMarkClick(id: number): void {
  emit('mark-click', id)
}
</script>

<template>
  <div ref="rootEl" class="reader-page" data-testid="chapter-view" @mouseup="onMouseUp">
    <template v-if="chapter">
      <header class="chap-head text-center mb-8">
        <div
          class="text-overline text-primary"
          data-testid="chapter-book"
          style="letter-spacing: 0.3em"
        >
          {{ chapter.book_display }}
        </div>
        <div class="chap-num text-primary">{{ chapter.chapter }}</div>
        <v-divider class="mx-auto mt-3" style="max-width: 42px" />
      </header>

      <template v-for="verse in chapter.verses" :key="verse.verse">
        <p class="verse" :data-verse="verse.verse" data-testid="verse">
          <span class="verse-num text-primary">{{ verse.verse }}</span>
          <span class="verse-text">
            <template v-for="(seg, i) in segmentsForVerse(verse)" :key="i">
              <mark
                v-if="seg.mark"
                class="concept-mark"
                :class="{ 'concept-mark--active': seg.mark.id === activeMarkId }"
                :style="markStyle(seg.mark)"
                :data-mark="seg.mark.id"
                data-testid="concept-mark"
                tabindex="0"
                @click.stop="onMarkClick(seg.mark.id)"
                @keydown.enter.stop="onMarkClick(seg.mark.id)"
                >{{ seg.text
                }}<sup
                  v-if="seg.mark.concept_names.length > 1"
                  class="mark-multi text-primary"
                  >{{ seg.mark.concept_names.length }}</sup
                ></mark
              >
              <template v-else>{{ seg.text }}</template>
            </template>
          </span>
        </p>

        <div
          v-if="greekOn && verse.greek_tokens.length"
          class="interlinear d-flex flex-wrap mb-4"
          data-testid="interlinear-row"
        >
          <InterlinearChip
            v-for="token in verse.greek_tokens"
            :key="token.position"
            :token="token"
            @tap="onChipTap(verse.verse, $event)"
          />
        </div>
      </template>
    </template>

    <div v-else class="text-center text-medium-emphasis py-12" data-testid="chapter-empty">
      No chapter loaded.
    </div>
  </div>
</template>

<style scoped>
.reader-page {
  max-width: 38rem;
  margin: 0 auto;
  padding: 1rem 1rem 6rem;
  font-family: 'Iowan Old Style', Palatino, 'Palatino Linotype', Georgia, serif;
}
.chap-num {
  font-size: 4rem;
  line-height: 0.9;
  font-weight: 600;
}
.verse {
  margin: 0 0 0.15rem;
  font-size: 1.18rem;
  line-height: 1.9;
  text-align: justify;
  hyphens: auto;
}
.verse-num {
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.62rem;
  font-weight: 700;
  vertical-align: 0.55em;
  margin-right: 0.28em;
  user-select: none;
}
.verse-text::selection,
.verse-text *::selection {
  background: rgba(var(--v-theme-primary), 0.28);
}
.concept-mark {
  border-radius: 2px;
  padding: 0.04em 0.06em;
  cursor: pointer;
  color: inherit;
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
  transition: filter 0.15s;
}
.concept-mark:hover {
  filter: saturate(1.25);
}
.concept-mark--active {
  outline: 2px dashed rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
.mark-multi {
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.5rem;
  font-weight: 700;
  vertical-align: 0.5em;
  margin-left: 0.12em;
}
:deep(.gloss-flash) {
  background: rgba(var(--v-theme-warning), 0.4);
  border-radius: 3px;
  box-shadow: 0 0 0 3px rgba(var(--v-theme-warning), 0.3);
}
</style>
