<script setup lang="ts">
/**
 * Design-exploration page: prototype renderings of how typed connections could
 * be shown in/around the reading column, drawn from
 * docs/design/research-connection-annotation-methodologies-2026-07-05.md.
 * Each option is a live mock over one sample passage (Romans 5:1-5, which
 * carries a real produces/sequence chain plus an interchange), with commentary
 * and a recommendation. Static/presentational — no data layer.
 */
// Fixed line geometry so the SVG/CSS overlays can anchor to line centers.
const LINE_H = 40

// Sample passage. Each line is HTML with concept words wrapped in <mark> (a
// neutral gilt highlight); the OVERLAYS carry the connection-type color/label.
const lines: string[] = [
  'Therefore being justified by <mark>faith</mark>, we have <mark>peace</mark> with God',
  'through our Lord Jesus Christ:',
  'And we glory in <mark>tribulations</mark> also: knowing that tribulation',
  'worketh <mark>patience</mark>; and patience, experience;',
  'and experience, <mark>hope</mark>: and hope maketh not ashamed;',
  'because the <mark>love</mark> of God is shed abroad in our hearts.',
]

interface ConnType {
  key: string
  label: string
  color: string
  directional: boolean
}
// Data palette (like a concept's authored_color) — legible on parchment + dark.
const TYPES: Record<string, ConnType> = {
  produces: { key: 'produces', label: 'produces', color: '#2E8C6A', directional: true },
  sequence: { key: 'sequence', label: 'sequence', color: '#3B6FB0', directional: true },
  interchange: { key: 'interchange', label: 'interchange', color: '#7A5BA6', directional: false },
}

// Connections anchored to line indices (macro/line-level, matching the
// "step back and see the pattern" view).
interface Conn {
  from: number
  to: number
  type: keyof typeof TYPES
  note: string
}
const connections: Conn[] = [
  { from: 2, to: 3, type: 'produces', note: 'tribulation worketh patience' },
  { from: 3, to: 4, type: 'sequence', note: 'patience → experience → hope' },
  { from: 0, to: 4, type: 'sequence', note: 'faith … hope (the arc of the passage)' },
]
// The interchange lives within line 5 (divine love → human hearts).
const interchangeLine = 5

const readerHeight = computed(() => lines.length * LINE_H)
const lineCenter = (i: number) => i * LINE_H + LINE_H / 2

// For each line, which connection types touch it (for the gutter mock).
function typesOnLine(i: number): ConnType[] {
  const keys = new Set<string>()
  for (const c of connections) if (c.from === i || c.to === i) keys.add(c.type)
  if (i === interchangeLine) keys.add('interchange')
  return [...keys].map((k) => TYPES[k])
}

// Arc path between two line centers, bulging into the right band.
function arcPath(from: number, to: number, bandWidth: number): string {
  const y1 = lineCenter(from)
  const y2 = lineCenter(to)
  const reach = Math.min(bandWidth - 6, 14 + Math.abs(to - from) * 16)
  return `M 2 ${y1} C ${reach} ${y1}, ${reach} ${y2}, 2 ${y2}`
}
</script>

<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-2">
      <h1 class="text-h5 font-weight-bold">Connection visualizations — design options</h1>
      <v-btn to="/docs" variant="text" size="small" prepend-icon="mdi-chevron-left"> Docs </v-btn>
    </div>
    <p class="text-body-2 text-medium-emphasis mb-6" style="max-width: 60ch">
      Prototype renderings of how typed connections could appear in the reading column, drawn from
      the
      <NuxtLink to="/docs/design-research-connection-annotation-methodologies-2026-07-05"
        >margin-annotation research</NuxtLink
      >. Every mock uses the same passage — Romans 5:1–5, which carries a real
      <em>produces</em>/<em>sequence</em> chain (tribulation → patience → hope) plus an
      <em>interchange</em> (the love of God shed abroad in human hearts). Colors encode connection
      <em>type</em>.
    </p>

    <!-- Legend -->
    <div class="d-flex flex-wrap ga-4 mb-8">
      <span v-for="t in TYPES" :key="t.key" class="d-flex align-center ga-2 text-body-2">
        <span class="legend-dot" :style="{ background: t.color }" />
        {{ t.label }}
      </span>
    </div>

    <!-- OPTION A — colored gutter bars -->
    <section class="mb-10">
      <h2 class="text-h6 font-weight-bold mb-1">A · Colored gutter bars <span class="opt-tag">reading state</span></h2>
      <p class="opt-blurb">
        A quiet colored rule in the left margin beside any line that takes part in a connection,
        colored by type. Always on, near-zero clutter — it says “something is here” without drawing
        the relationship. This is the resting state a reader lives in.
      </p>
      <div class="proto">
        <div class="reader gutter-reader" :style="{ height: `${readerHeight}px` }">
          <div class="gutter">
            <div v-for="(l, i) in lines" :key="i" class="gutter-cell" :style="{ height: `${LINE_H}px` }">
              <span
                v-for="t in typesOnLine(i)"
                :key="t.key"
                class="gutter-bar"
                :style="{ background: t.color }"
              />
            </div>
          </div>
          <div class="text-col">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-for="(l, i) in lines" :key="i" class="rline" :style="{ height: `${LINE_H}px` }" v-html="l" />
          </div>
        </div>
      </div>
      <p class="opt-note">
        <strong>Good at:</strong> staying out of the way; scanning “where is there anything” at a
        glance. <strong>Weak at:</strong> showing <em>what</em> connects to what, or direction. Best
        as the default layer beneath a reveal-on-demand option.
      </p>
    </section>

    <!-- OPTION B — margin brackets + typed labels (bracketing / arcing) -->
    <section class="mb-10">
      <h2 class="text-h6 font-weight-bold mb-1">
        B · Margin brackets + typed labels <span class="opt-tag rec">recommended structure</span>
      </h2>
      <p class="opt-blurb">
        The idiom from scripture <em>bracketing</em>/<em>arcing</em>: a bracket in the margin spans
        the lines a connection covers, tagged with its type. This is the closest field-tested prior
        art — decades of exegetical practice draw typed, labeled relationships exactly this way.
        Directional types point (▸); symmetric ones don’t.
      </p>
      <div class="proto">
        <div class="reader" :style="{ height: `${readerHeight}px` }">
          <div class="text-col">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-for="(l, i) in lines" :key="i" class="rline" :style="{ height: `${LINE_H}px` }" v-html="l" />
          </div>
          <svg class="bracket-band" :height="readerHeight" width="150" :viewBox="`0 0 150 ${readerHeight}`">
            <g v-for="(c, idx) in connections" :key="idx" :style="{ color: TYPES[c.type].color }">
              <path
                :d="`M 4 ${lineCenter(c.from)} L ${12 + idx * 16} ${lineCenter(c.from)} L ${12 + idx * 16} ${lineCenter(c.to)} L 4 ${lineCenter(c.to)}`"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              />
              <circle v-if="TYPES[c.type].directional" :cx="4" :cy="lineCenter(c.to)" r="3.5" fill="currentColor" />
              <text
                :x="18 + idx * 16"
                :y="(lineCenter(c.from) + lineCenter(c.to)) / 2 + 4"
                font-size="11.5"
                fill="currentColor"
              >
                {{ TYPES[c.type].label }}
              </text>
            </g>
          </svg>
        </div>
      </div>
      <p class="opt-note">
        <strong>Good at:</strong> showing typed, hierarchical, directional relationships in the exact
        idiom scholars already read; nesting brackets communicates depth for free. <strong>Weak
        at:</strong> many overlapping brackets crowd the margin — needs the toggle/filter discipline
        below. Maps cleanly onto our types (sequence, produces, prerequisite, interchange…).
      </p>
    </section>

    <!-- OPTION C — arc band -->
    <section class="mb-10">
      <h2 class="text-h6 font-weight-bold mb-1">C · Arc band <span class="opt-tag">“show all” state</span></h2>
      <p class="opt-blurb">
        The Harrison/Römhild cross-reference idiom, scoped to one chapter: each connection is an arc
        from source to target in a side band, colored by type. Beautiful for seeing the whole
        chapter’s structure at once; the field’s lesson is to filter to the visible scope and draw
        the full tie-line only on hover, or it becomes a spaghetti.
      </p>
      <div class="proto">
        <div class="reader" :style="{ height: `${readerHeight}px` }">
          <div class="text-col">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-for="(l, i) in lines" :key="i" class="rline" :style="{ height: `${LINE_H}px` }" v-html="l" />
          </div>
          <svg class="arc-band" :height="readerHeight" width="120" :viewBox="`0 0 120 ${readerHeight}`">
            <path
              v-for="(c, idx) in connections"
              :key="idx"
              :d="arcPath(c.from, c.to, 110)"
              fill="none"
              :stroke="TYPES[c.type].color"
              stroke-width="2.5"
              opacity="0.85"
            />
            <circle
              v-for="(c, idx) in connections"
              :key="'d' + idx"
              cx="2"
              :cy="lineCenter(c.to)"
              r="3"
              :fill="TYPES[c.type].color"
            />
          </svg>
        </div>
      </div>
      <p class="opt-note">
        <strong>Good at:</strong> the “step back and see the pattern” view you described — macro
        structure across a chapter. <strong>Weak at:</strong> reading precise endpoints; degrades
        badly at scale without filtering. Best as a toggled overview, not the default.
      </p>
    </section>

    <!-- OPTION D — Tufte sidenotes -->
    <section class="mb-10">
      <h2 class="text-h6 font-weight-bold mb-1">D · Anchored sidenotes <span class="opt-tag">annotation state</span></h2>
      <p class="opt-blurb">
        Tufte-style: the connection’s note sits in the margin at the vertical position of its source
        line. Carries the most <em>meaning</em> per connection (you read the claim, not just a
        color), and collapses gracefully into the iPad slide-over. Trades density for legibility.
      </p>
      <div class="proto">
        <div class="reader" :style="{ height: `${readerHeight}px` }">
          <div class="text-col">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-for="(l, i) in lines" :key="i" class="rline" :style="{ height: `${LINE_H}px` }" v-html="l" />
          </div>
          <div class="sidenotes" :style="{ height: `${readerHeight}px` }">
            <div
              v-for="(c, idx) in connections"
              :key="idx"
              class="sidenote"
              :style="{ top: `${lineCenter(c.from) - 10}px`, borderColor: TYPES[c.type].color }"
            >
              <span class="sidenote-type" :style="{ color: TYPES[c.type].color }">{{ TYPES[c.type].label }}</span>
              {{ c.note }}
            </div>
          </div>
        </div>
      </div>
      <p class="opt-note">
        <strong>Good at:</strong> conveying the actual relationship and its evidence; least
        ambiguous. <strong>Weak at:</strong> vertical space — only a few fit before they collide;
        can’t show many connections at once. Best paired with a gutter/bracket for the dense cases.
      </p>
    </section>

    <!-- Recommendation -->
    <section class="rec-card pa-4 mb-6">
      <h2 class="text-h6 font-weight-bold mb-2">Recommendation — one layered surface</h2>
      <p class="opt-blurb mb-2">
        None of these wins outright; they’re <em>states of the same margin</em>, revealed as the
        reader asks for more:
      </p>
      <ol class="rec-list">
        <li>
          <strong>Rest (A):</strong> quiet colored gutter bars — always on, tells you where
          connections exist without noise.
        </li>
        <li>
          <strong>“Show connections in this chapter” (B + C):</strong> reveal margin brackets with
          typed labels (the exegetical idiom, our primary surface), with an optional arc overlay for
          the macro pattern.
        </li>
        <li>
          <strong>Focus (D):</strong> tapping one connection promotes it to an anchored sidenote
          with its note/evidence, and draws its full tie-line; everything else dims.
        </li>
      </ol>
      <p class="opt-note mt-3">
        Why this order: it honors the research’s central tension — dense typed structure
        (bracketing) versus legibility (Tufte) — by making density the default-collapsed state and
        meaning the on-demand state. It also fits the app we already have: the gutter/brackets live
        in the reading column; the focused sidenote reuses the existing iPad slide-over. And it maps
        onto the connection types we just built — including <em>interchange</em>, which has no
        equivalent in the classic arcing vocabulary and so earns a distinct color as a genuinely new
        relationship. My suggestion is to build <strong>A + B first</strong> (gutter + toggled
        brackets), since those cover the everyday case, and add C/D once you’ve mapped enough
        connections to feel the density.
      </p>
    </section>
  </div>
</template>

<style scoped>
.legend-dot {
  display: inline-block;
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 3px;
}
.opt-tag {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.1em 0.5em;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  color: rgb(var(--v-theme-on-surface));
  vertical-align: middle;
  margin-left: 0.4rem;
}
.opt-tag.rec {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}
.opt-blurb {
  max-width: 62ch;
  margin: 0.4rem 0 1rem;
  line-height: 1.6;
}
.opt-note {
  max-width: 62ch;
  margin-top: 0.9rem;
  font-size: 0.9rem;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.85;
  line-height: 1.55;
}
.proto {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.15);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  background: rgba(var(--v-theme-on-surface), 0.02);
  overflow-x: auto;
}
.reader {
  display: flex;
  align-items: flex-start;
  min-width: 520px;
  font-family: var(--font-read, Georgia, 'Times New Roman', serif);
}
.text-col {
  flex: 1;
  min-width: 320px;
}
.rline {
  /* NOT flex — a flex container drops the whitespace between the text runs and
   * the <mark> items ("by faith" → "byfaith"). Block + line-height centers the
   * single line within the fixed row height while preserving inline spacing. */
  display: block;
  line-height: 40px;
  font-size: 1.02rem;
  white-space: nowrap;
}
.rline :deep(mark) {
  background: rgba(var(--v-theme-secondary), 0.22);
  color: inherit;
  padding: 0 0.1em;
  border-radius: 2px;
}
/* A · gutter */
.gutter-reader {
  gap: 0;
}
.gutter {
  width: 22px;
  flex: none;
  margin-right: 0.75rem;
}
.gutter-cell {
  display: flex;
  align-items: center;
  gap: 2px;
}
.gutter-bar {
  width: 4px;
  height: 62%;
  border-radius: 2px;
}
/* B · brackets, C · arcs */
.bracket-band,
.arc-band {
  flex: none;
  margin-left: 0.5rem;
  overflow: visible;
}
/* D · sidenotes */
.sidenotes {
  position: relative;
  width: 220px;
  flex: none;
  margin-left: 0.75rem;
}
.sidenote {
  position: absolute;
  left: 0;
  right: 0;
  font-size: 0.8rem;
  line-height: 1.35;
  padding-left: 0.6rem;
  border-left: 3px solid;
  font-family: system-ui, sans-serif;
  color: rgb(var(--v-theme-on-surface));
}
.sidenote-type {
  display: block;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.66rem;
  letter-spacing: 0.04em;
}
.rec-card {
  border: 1px solid rgb(var(--v-theme-primary));
  border-radius: 10px;
  background: rgba(var(--v-theme-primary), 0.05);
}
.rec-list {
  padding-left: 1.3rem;
  line-height: 1.6;
  max-width: 62ch;
}
.rec-list li {
  margin: 0.35rem 0;
}
</style>
