# Theme + color guide

This project uses Vuetify 3's theme system. Two named themes ship:

- **`parchment`** — the reader's study-edition identity and the **default** theme
  (DEC-152). Warm rag-paper ground, oak-gall ink, manuscript rubric + gilt accents,
  a literary serif for scripture and a sans for chrome.
- **`dark`** — the retained alternate (accessibility toggle / the rest of the app).

Every UI **must** work in both themes without manual styling per theme. This file is the
canonical reference for the color classes / props / CSS variables to use. The short
version lives in `CLAUDE.md`. This doc has the worked examples.

---

## The study-edition palette (DEC-152)

The approved visual spec is `docs/design/reader-reference.html` (v8). The reader's identity
is the **parchment** theme. Its semantic tokens map to the manuscript palette:

| Token | Parchment value | Meaning |
|---|---|---|
| `background` | `#EBE1CE` | rag-paper ground |
| `surface` | `#FBF6EA` | card / illuminated leaf |
| `surface-variant` | `#F3ECDB` | apparatus panel |
| `surface-light` | `#F3ECDB` | secondary panel |
| `on-surface` / `on-background` | `#2B2722` | oak-gall ink (body text) |
| `on-surface-variant` | `#6B6152` | soft ink (secondary text) |
| `primary` | `#9C2A23` | manuscript **rubric** red — verse numbers, book label, primary actions, danger |
| `secondary` / `accent` | `#A07E2A` | **gilt** — the gilt rule, resize handles, accents |
| `border-color` (variable) | `#C9BC9F` | hairline rules / dividers |

**Rule of thumb:** in the reader, `primary` = rubric red and `secondary` = gilt. Use the
semantic token, never the hex.

### Typography: serif for scripture, sans for chrome

Scripture text is set in a **literary serif**; all chrome (toolbar, panel labels, buttons)
stays in the Vuetify **sans**. Three CSS custom properties are declared in
`assets/styles/globals.css` (constant across both themes — the scripture face does not
change with the accessibility toggle):

```css
font-family: var(--font-read);     /* scripture body — Iowan Old Style / Palatino / Georgia */
font-family: var(--font-display);  /* chapter numeral, versal — Hoefler Text / Big Caslon */
font-family: var(--font-grc);      /* Greek beside the SBL face — Palatino */
```

Polytonic Greek still uses `.text-grc` / `<GreekText>` (SBL Greek woff2). Use the
`var(--font-grc)` stack only where SBL is paired with a Palatino fallback in the interlinear.

### The grain ground

`.v-theme--parchment` carries the paper texture (a radial highlight + a monochrome
turbulence SVG, `background-attachment: fixed`). It is keyed off the theme class so the
`dark` theme stays flat. Do not re-declare it per component.

---

## Concept colors are CONTENT, not chrome (DEC-146 / DEC-150 / DEC-152)

A concept's `authored_color` is **user data**, not a theme token. It is the ONE place a raw
hex renders — applied inline (`:style="{ '--c': c.authored_color }"` or
`backgroundColor`), with a semantic-token fallback (`rgb(var(--v-theme-secondary))`) when a
concept has no color. Concept marks blend over the parchment with **multiply**:

```css
.concept-mark {
  background: color-mix(in srgb, var(--c) 38%, #fff);
  mix-blend-mode: multiply;
  border-bottom: 2.5px solid var(--c);
}
```

Never promote `authored_color` to a theme token; never read it as evidence (DEC-146).

---

## Picking the right text color

### Rule 1: Plain text on the page background

Use no class. The default text color is theme-aware (`on-surface` = oak-gall ink under
parchment). For lower-emphasis text use `text-medium-emphasis`; for disabled, `text-disabled`.

### Rule 2: Text inside a colored container

When a container has an explicit `color` prop, use the matching `text-on-X` class for any
manually-classed text inside (`text-on-primary` inside `<v-card color="primary">`). Vuetify
applies `on-primary` as the default content color, so you can usually skip the class.

### Rule 3: Backgrounds on plain elements

Pair `bg-X` with `text-on-X`:

| Use case | Background class | Text class |
|---|---|---|
| Default content panel | `bg-surface` | `text-on-surface` |
| Elevated / secondary panel | `bg-surface-variant` | `text-on-surface-variant` |
| Rubric / call-to-action | `bg-primary` | `text-on-primary` |

### Rule 4: Custom CSS (scoped styles)

Use Vuetify's CSS variables — they update reactively with the theme:

```css
.my-rule {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  border: 1px solid rgb(var(--v-border-color));
}
.gilt-rule { background: rgb(var(--v-theme-secondary)); }   /* gilt */
.rubric    { color: rgb(var(--v-theme-primary)); }          /* rubric red */
```

For alpha, use the comma form: `rgba(var(--v-theme-primary), 0.1)`.

---

## Anti-patterns — DO NOT USE

- **`text-white` / `text-black`** — render the same in both themes; they don't adapt.
- **Hardcoded hex in chrome** (inline styles or scoped CSS) — the ONLY sanctioned raw hex is
  a concept's `authored_color` (content) and the parchment grain data-URI in `globals.css`.
- **Tailwind classes** (`text-gray-500`, `bg-red-100`) — Vuetify ships no Tailwind.
- **`bg-X` without `text-on-X`**.

---

## Source-language text

Polytonic Greek uses the `.text-grc` class (self-hosted SBL Greek), wrapped by `<GreekText>`:

```vue
<p>The flagship sequence is <GreekText>πίστις > ἐλπίς > ἀγάπη</GreekText>.</p>
```

`.text-heb` is declared with `direction: rtl` and a system fallback; no Hebrew font ships at
S1 (NT-only corpus) — the hook lets a future slice drop in `SBLHebrew.woff2` without
restructuring.

---

## Definition of done

Before considering a UI change complete:

1. **Toggle the theme** (sun/moon button in the header) — verify the change reads correctly
   under both `parchment` and `dark`.
2. **Scan every piece of text** for adequate contrast.
3. **Scan every border / divider** — visible but not loud (hairline `--v-border-color`).
4. **Grep the diff for hard-coded colors** — `text-white`, `text-black`, `#hex`, `rgb()`
   literals, Tailwind classes. The only allowed raw color is concept `authored_color`
   (content). Everything else uses the patterns in Rules 1–4.
