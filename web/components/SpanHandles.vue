<script setup lang="ts">
// Lifecycle + reactivity primitives are auto-imported in the Nuxt app, but the
// Vitest unit environment does not resolve the lifecycle hooks the same way, so
// import them explicitly to keep the component mountable under test.
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * Two draggable handles that adjust the active mark's span, word-snapping as
 * they move. Ports the prototype's pointer logic to Vue: large touch targets
 * (`touch-action: none`, pointer capture) so a finger / Pencil can drag them.
 *
 * The component is purely the dragging surface — it does not own the mark.
 * Given the verse element + the mark's current char offsets, it positions the
 * handles over the mark's rendered rects and, on drag, emits `span-change`
 * with the new (word-snapped) char offsets for the parent to persist.
 *
 * Single-verse spans only for handle dragging (the prototype's constraint);
 * the parent still supports cross-verse marks for selection (DEC-143), it just
 * doesn't expose handle-dragging across a verse boundary.
 */
const props = defineProps<{
  /** Show the handles. */
  active: boolean
  /** The rendered text of the verse the active mark sits in. */
  verseText: string
  /** Current char offsets of the active mark within that verse. */
  charStart: number
  charEnd: number
  /** The `.verse-text` element of the active mark's verse, for hit-testing. */
  verseTextEl: HTMLElement | null
  /** The `<mark>` element of the active mark, for positioning. */
  markEl: HTMLElement | null
}>()

const emit = defineEmits<{
  'span-change': [payload: { charStart: number; charEnd: number }]
}>()

const startStyle = ref<Record<string, string>>({ display: 'none' })
const endStyle = ref<Record<string, string>>({ display: 'none' })

function position(): void {
  if (!props.active || !props.markEl || !import.meta.client) {
    startStyle.value = { display: 'none' }
    endStyle.value = { display: 'none' }
    return
  }
  const rects = props.markEl.getClientRects()
  if (!rects.length) {
    startStyle.value = { display: 'none' }
    endStyle.value = { display: 'none' }
    return
  }
  const first = rects[0]
  const last = rects[rects.length - 1]
  startStyle.value = {
    display: 'block',
    left: `${first.left}px`,
    top: `${first.top}px`,
    height: `${first.height}px`,
  }
  endStyle.value = {
    display: 'block',
    left: `${last.right}px`,
    top: `${last.top}px`,
    height: `${last.height}px`,
  }
}

watch(
  () => [props.active, props.markEl, props.charStart, props.charEnd],
  () => nextTick(position),
)

onMounted(() => {
  position()
  window.addEventListener('scroll', position, true)
  window.addEventListener('resize', position)
})

onBeforeUnmount(() => {
  if (!import.meta.client) return
  window.removeEventListener('scroll', position, true)
  window.removeEventListener('resize', position)
})

/** Snap an offset to a word boundary; isStart pulls left, else pushes right. */
function snapWord(plain: string, off: number, isStart: boolean): number {
  let o = Math.max(0, Math.min(plain.length, off))
  if (isStart) {
    while (o > 0 && /\S/.test(plain[o - 1])) o--
  } else {
    while (o < plain.length && /\S/.test(plain[o])) o++
  }
  return o
}

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

function caretOffsetFromPoint(vtext: Element, x: number, y: number): number | null {
  type CaretDoc = Document & {
    caretRangeFromPoint?: (x: number, y: number) => Range | null
    caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node; offset: number } | null
  }
  const doc = document as CaretDoc
  let node: Node | null = null
  let off = 0
  if (doc.caretRangeFromPoint) {
    const r = doc.caretRangeFromPoint(x, y)
    if (!r) return null
    node = r.startContainer
    off = r.startOffset
  } else if (doc.caretPositionFromPoint) {
    const p = doc.caretPositionFromPoint(x, y)
    if (!p) return null
    node = p.offsetNode
    off = p.offset
  } else {
    return null
  }
  if (!node || !vtext.contains(node)) return null
  return globalOffset(vtext, node, off)
}

function drag(which: 'start' | 'end', clientX: number, clientY: number): void {
  if (!props.verseTextEl) return
  const pos = caretOffsetFromPoint(props.verseTextEl, clientX, clientY)
  if (pos == null) return
  const plain = props.verseText
  if (which === 'start') {
    const ns = snapWord(plain, pos, true)
    if (ns < props.charEnd) emit('span-change', { charStart: ns, charEnd: props.charEnd })
  } else {
    const ne = snapWord(plain, pos, false)
    if (ne > props.charStart) emit('span-change', { charStart: props.charStart, charEnd: ne })
  }
}

function onPointerDown(which: 'start' | 'end', e: PointerEvent): void {
  e.preventDefault()
  const target = e.currentTarget as HTMLElement
  target.setPointerCapture(e.pointerId)
  const move = (ev: PointerEvent): void => drag(which, ev.clientX, ev.clientY)
  const up = (): void => {
    target.releasePointerCapture(e.pointerId)
    document.removeEventListener('pointermove', move)
    document.removeEventListener('pointerup', up)
  }
  document.addEventListener('pointermove', move)
  document.addEventListener('pointerup', up)
}
</script>

<template>
  <div v-if="active">
    <div
      class="span-handle span-handle--start"
      :style="startStyle"
      data-testid="span-handle-start"
      @pointerdown="onPointerDown('start', $event)"
    />
    <div
      class="span-handle span-handle--end"
      :style="endStyle"
      data-testid="span-handle-end"
      @pointerdown="onPointerDown('end', $event)"
    />
  </div>
</template>

<style scoped>
.span-handle {
  position: fixed;
  width: 34px;
  z-index: 55;
  touch-action: none;
  cursor: ew-resize;
  transform: translateX(-50%);
  background: linear-gradient(
    to right,
    transparent calc(50% - 1.25px),
    rgb(var(--v-theme-secondary)) calc(50% - 1.25px),
    rgb(var(--v-theme-secondary)) calc(50% + 1.25px),
    transparent calc(50% + 1.25px)
  );
}
.span-handle::before {
  content: '';
  position: absolute;
  left: 50%;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgb(var(--v-theme-secondary)); /* gilt — spec gold knob */
  transform: translateX(-50%);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.35);
  border: 2px solid rgb(var(--v-theme-surface));
}
.span-handle--start::before {
  top: -20px;
}
.span-handle--end::before {
  bottom: -20px;
}
</style>
