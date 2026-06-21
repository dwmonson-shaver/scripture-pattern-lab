# Structure Outline — Slice 1 Reader Alignment (study-edition parchment)

**Goal:** Align the existing Nuxt `web/` reader (built code-complete, UNVERIFIED, on the
dark Vuetify theme at `b823065`) to the approved v8 design spec
`docs/design/reader-reference.html` + DEC-150/151/152. This is a **refactor toward the
spec**, not a rewrite. The interaction grammar already largely exists; the dominant gap is
the **study-edition parchment theme** (DEC-152) plus a handful of spec interactions the
current reader lacks (Versed/Continuous toggle, illuminated opening, scroll-spy chapter
dropdown, multi-select concept highlight with dim-others, three-state dismissal).

**Reference precedence:** `reader-reference.html` is the visual + interaction spec. The
project Vuetify theme is REDEFINED to parchment (DEC-152) — semantic tokens stay; only their
values change. Concept colors remain content (`authored_color`, inline). No raw hex in
chrome, no `text-white`/`text-black`.

**Out of scope (Slices 2–5):** connections engine, axes, evidence dossiers, citations/OKF,
AI explainer, discovery, lens. Cross-verse resize is implemented within-verse and **flagged**
(known open hard case) — not faked.

**Baseline note:** at `c24fa43`, `npm test` has **4 pre-existing failures** in files this
slice reworks: `SpanHandles.test.ts` x2 (`onBeforeUnmount is not defined` — missing explicit
import in the vitest env) and `ConceptPanel.test.ts` x2 (`v-navigation-drawer` needs an
injected `v-layout` the test doesn't provide). Both get fixed in their owning phase. Typecheck
+ no-llm-sdk are green at baseline. Each phase runs typecheck + vitest + check:no-llm-sdk.

---

## Phase 1 — Parchment theme tokens + THEME.md (DEC-152 foundation)

Redefine the reader's identity. Because the existing components already style via
`rgb(var(--v-theme-*))`, swapping the Vuetify token values flips most chrome to parchment for
free; this phase establishes the palette + the literary-serif / sans split + the grain ground,
and rewrites the canonical theme doc.

- **`web/vuetify.config.ts`** — redefine the **light** theme (make it the parchment study
  edition) and set it as the **default** theme. Map spec → tokens:
  - `background` ← `#EBE1CE` (ground), `surface` ← `#FBF6EA` (card), `surface-variant` ←
    `#F3ECDB` (panel), `surface-bright` ← `#E2D6BD` (ground-2)
  - `on-background` / `on-surface` ← `#2B2722` (oak-gall ink)
  - `primary` ← `#9C2A23` (rubric red — the manuscript accent used for verse numbers, book
    label, primary actions), `on-primary` ← `#FBF6EA`
  - `secondary` ← `#A07E2A` (gilt), `on-secondary` ← `#2B2722`
  - `error` ← `#9C2A23` (rubric doubles as danger), keep `success`/`info`/`warning` as muted
    parchment-compatible values
  - add a custom `--v-border-color` hairline ← `#C9BC9F` (via theme `variables`)
  - Keep a `dark` theme defined (parchment-night or the prior dark) so the toggle still works,
    but the reader's identity + default is parchment.
- **`web/assets/styles/globals.css`** — add the study-edition foundation that tokens can't
  express: the parchment **grain** background (the spec's radial-gradient + feTurbulence SVG
  data-URI on `body`), and CSS custom properties for the **two display families** the spec
  uses beyond Vuetify's sans: `--font-read` (literary serif: Iowan Old Style/Palatino/Georgia
  stack) and `--font-display` (Hoefler Text/Big Caslon stack) and `--font-grc` (Palatino for
  Greek beside SBL). These are plain CSS vars (not LLM, not theme-toggle-dependent — the
  scripture serif identity is constant across light/dark).
- **`web/THEME.md`** — rewrite to the study-edition palette as canonical: parchment ground,
  oak-gall ink, rubric, gilt, hairline; the serif-for-scripture / sans-for-chrome rule; the
  rule that concept colors are content; the multiply-blend marker-stroke convention; keep the
  no-raw-hex-in-chrome / no-`text-white` discipline. Note the reader is parchment-identity
  (DEC-152) and the dark theme is retained for the rest of the app / accessibility toggle.
- **`web/components/CLAUDE.md`** / **`web/CLAUDE.md`** — note the theme redefinition where they
  reference the dark Vuetify theme.

**Checkpoint:** typecheck green; vitest green except the 4 known baseline fails (untouched this
phase); `check:no-llm-sdk` green. Visual verification is deferred to the user's last-mile
(no headless render this session); commit flags theme UNVERIFIED-visually per DEC-149.

---

## Phase 2 — Illuminated chapter opening + scripture typography in ChapterView

Make the reader page itself look like the spec's study edition.

- **`web/components/ChapterView.vue`**:
  - Page column: serif (`var(--font-read)`), justified, `--measure` ~34rem, generous
    line-height; reader scrolls, header/panel fixed (app-shell — see Phase 6).
  - **Illuminated opening** (`.opening`): rubric book label (letter-spaced uppercase, rubric
    color), large display chapter numeral + italic chapter label, the gilt-gradient `.rule`.
  - **Gilt versal**: first letter of verse 1 rendered as the spec's `.versal` (display serif,
    gilt gradient fill, inset highlight) — implemented as a leading `<span class="versal">`.
  - Verse numbers (`.vn`): small sans, rubric, superscript.
  - Keep mark rendering (`<mark class="concept-mark">`) but restyle to the spec's `.cm`:
    `mix-blend-mode: multiply`, `color-mix` tint of the concept color, 2.5px underline in the
    concept color, `box-decoration-break: clone`. The concept color stays inline
    (`--c: <authored_color>`); the blend/underline are class CSS.
  - `prefers-reduced-motion` guard on the opening's rise/wipe/gild animations.

**Checkpoint:** typecheck + vitest (ChapterView.test.ts still green or updated for new markup)
+ no-llm-sdk green.

---

## Phase 3 — Versed / Continuous mode toggle + interlinear placement

The spec offers a Versed (default) ↔ Continuous segmented toggle that changes verse layout AND
where Greek appears (Versed → interlinear rows under the verse; Continuous → ruby above the
aligned word).

- **`web/components/ReaderBar.vue`**: add a `mode` `defineModel<'versed'|'continuous'>`
  rendered as the spec's segmented control (`.seg`) styled with tokens. Keep the existing Greek
  `v-switch`. Keep version + chapter selects.
- **`web/components/ChapterView.vue`**: accept a `mode` prop. Versed → `display:block` verses
  with interlinear chip rows under each verse when `greekOn` (existing chips, restyled to spec
  `.gk`). Continuous → verses flow inline; when `greekOn`, render the spec's `.ruby` (Greek +
  transliteration) above the aligned English word. **Transliteration is ALWAYS shown beside the
  Greek** in both modes (spec rule).
- **`web/pages/reader.vue`**: hold `mode` ref, wire `v-model` to ReaderBar, pass to ChapterView.

**Alignment-data honesty (DEC charter):** the backend read endpoint returns **verse-level**
`greek_tokens` only — there is **no word-level Greek↔English alignment** (`src/retrieval/reader.py`
docstring confirms Slice-1 surfaces verse-whole tokens, not per-word mapping). So:
  - Render the Greek tokens the corpus provides (transliteration shown).
  - The spec's "tap a Greek word → flash the exact English word it translates" is implemented as
    the existing **approximate stem-match** (`flashGloss`) and **explicitly flagged** with a
    `TODO(DEC-align)` comment + a code note that true per-word alignment awaits the BSB
    alignment slice. **Do not fabricate per-word alignments.**

**Checkpoint:** typecheck + vitest + no-llm-sdk green; ReaderBar.test updated for the mode
control.

---

## Phase 4 — Selection → popup three-state dismissal grammar

Tighten the select/mark/highlight grammar to the spec's three states.

- **`web/components/SelectionPopup.vue`**: add the spec's third button — **Cancel (✕)** —
  alongside "Mark as concept" (primary, rubric) and "Just highlight" (with swatch dot). Emit a
  `cancel` event.
- **`web/pages/reader.vue`** — implement the **three-state dismissal**:
  1. **live selection** — popup shows while a selection is active; Esc / click-off / ✕ dismiss
     it (clear `pendingSelection`, `popupOpen`, native selection).
  2. **committed mark** — persists; clicking it sets `activeMarkId`, highlights its concept,
     shows handles + the MarkDetail (Change/Edit/Remove).
  3. **concept highlight** — clicking the concept again / clicking empty space / Clear turns it
     off.
  - Add the global keydown (Esc) + click-off handlers (guarded to ignore clicks inside popup /
    panel / masthead / handles), mirroring the spec's `mousedown`/`click`/`keydown` logic but
    in Vue idiom (composable or page-level listeners registered in `onMounted`, removed in
    `onBeforeUnmount`).
- **`web/components/MarkDetail.vue`**: ensure the action set is **Change / Edit concept /
  Remove** with the "drag the gold handles" hint (spec `.hnote`).

**Checkpoint:** typecheck + vitest (SelectionPopup.test updated for the ✕/cancel) + no-llm-sdk.

---

## Phase 5 — Multi-select concept highlight (dim-others-keep-underline) + library polish + span handles fix

The spec lets multiple concepts be highlighted at once; non-selected marks dim but **keep their
underline** (`body.has-sel .cm:not(.on)` lightens the fill only). The current reader tracks a
single active concept.

- **`web/pages/reader.vue`** (or a small `useConceptSelection` composable): track a
  `Set<string>` of selected concept names + `lastActive`; toggle on library-row click; apply
  `.on` to matching marks and a `has-sel` body/stage class so `:not(.on)` marks dim. Clear via
  the panel's **Clear** button / empty-space click / Esc.
- **`web/components/ConceptLibrary.vue`**: reflect multi-select (`.sel` state on rows); show
  the per-concept mark count; keep live search; the "+ New concept" dashed-gilt button (spec
  `.addc`); add the **Clear** affordance in the panel header (spec `.clearbtn`) when any
  concept is selected or a mark is active.
- **`web/components/ChapterView.vue`**: apply the dim-others CSS keyed off the selected set.
- **Fix the baseline `SpanHandles.vue` bug**: add the missing explicit `import { onBeforeUnmount,
  ... } from 'vue'` (or move the listener teardown so the auto-import resolves in the vitest
  env) so `SpanHandles.test.ts` x2 pass. Restyle the handles to the spec's gilt circular
  finger/Pencil targets (34px hit area, `touch-action:none`, gold line + gilt knob) — **keep
  the within-verse word-snapping resize working across wrapped lines**.
- **Cross-verse resize**: keep it **flagged** — handles operate within the active verse;
  cross-verse resize shows a clear "cross-verse resize coming" affordance / is disabled, with a
  `TODO(DEC-143)` note. Do not fake it.

**Checkpoint:** typecheck + vitest (SpanHandles x2 now PASS; ConceptLibrary updated) +
no-llm-sdk. Net: the 2 SpanHandles baseline fails close here.

---

## Phase 6 — App-shell (fixed header + panel, only text scrolls) + iPad slide-over + ConceptPanel test fix

Final assembly to the spec's shell + the iPad target (DEC-142).

- **`web/pages/reader.vue`**: the spec's `#screen` shell — `height:100vh; overflow:hidden`;
  masthead `flex:none`; `.stage` is a grid `minmax(0,1fr) 21rem`; **only the reader column
  scrolls** (`overflow-y:auto`), the apparatus panel scrolls independently, the header is
  fixed. Restyle the existing two-column grid to this.
- **Scroll-spy chapter dropdown + continuous book scroll** (spec): the chapter `<select>`
  updates as chapters scroll into view, and selecting a chapter scrolls to it. In Slice-1 the
  read endpoint loads one chapter at a time, so:
  - Implement the **dropdown → load+scroll** behavior (selecting a chapter calls
    `loadChapter`).
  - Implement **scroll-spy** structurally (IntersectionObserver / scroll handler updating the
    select) against whatever chapter blocks are present; if only one chapter is loaded, the spy
    is a no-op but the wiring is present. Flag multi-chapter continuous-scroll-load as a
    follow-up `TODO` (the read API is per-chapter; loading the whole book is a later
    enhancement). Do not fake multi-chapter data.
- **`web/components/ConceptPanel.vue`**: keep the `v-navigation-drawer` slide-over for
  `mobile` (DEC-142) and the sticky aside for wide. **Fix the baseline `ConceptPanel.test.ts`
  bug**: the test fails because `v-navigation-drawer` needs an injected `v-layout`; either wrap
  the drawer in the component's own `v-layout`/`v-main` context or adjust the test to provide
  the layout stub. Net: the 2 ConceptPanel baseline fails close here.
- Large tap targets throughout (min-height ≥ 2.4rem on actionable controls), `touch-action`
  correct on handles.

**Checkpoint:** typecheck + vitest **fully green (0 fails)** + no-llm-sdk green. This is the
slice's exit gate for the toolchain DoD.

---

## Slice close

- Run the full web DoD (lint:check / typecheck / vitest / check:no-llm-sdk). `gen:types`
  stays interim (no deployed backend — DEC-149).
- Independent review (Codex via `/codex:rescue`, or Claude-fallback if Codex still blocked by
  the `~/.codex` perms class — Bucket-P-Codex precedent) over the cumulative alignment diff.
  Save `docs/reviews/review-{flavor}-reader-alignment-2026-06-21.md`; add a `reviews-log.md`
  row; triage findings (fixed / bucketed-with-trigger / rejected).
- Record DECs for any load-bearing alignment decisions (theme token mapping, scroll-spy
  partial, alignment-TODO honesty).
- Carry-over: **web visual verification** (parchment render on iPad), **gen:types** regen after
  redeploy, **cross-verse resize** (flagged), **multi-chapter continuous scroll** (flagged).

## Phase independence

Each phase is independently checkable via the web toolchain (typecheck + vitest + no-llm-sdk)
and leaves the reader runnable. Visual fidelity to the parchment spec is verified by the user
on-device at last-mile (no headless render available this session) — every phase commit that
changes appearance flags it UNVERIFIED-visually per DEC-149.
