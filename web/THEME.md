# Theme + color guide

This project uses Vuetify 3's theme system. Every UI **must** work in both light and dark mode without manual styling per theme. This file is the canonical reference for the color classes / props / CSS variables to use.

The short version lives in `CLAUDE.md`. This doc has the worked examples.

---

## How Vuetify theming works (~30s read)

- Two named themes (`light` + `dark`) are defined in `vuetify.config.ts`.
- Each theme defines named colors: `primary`, `secondary`, `surface`, `surface-variant`, `error`, `success`, `warning`, `info`, plus auto-computed `on-X` colors (the contrasting text/icon color for each background).
- Vuetify exposes those as:
  - **Props on Vuetify components**: `<v-card color="primary">`, `<v-btn color="success">`
  - **Utility classes**: `bg-primary`, `text-primary`, `text-on-primary`, `bg-surface-variant`, etc.
  - **CSS variables**: `--v-theme-primary`, `--v-theme-on-primary`, etc.
- The runtime active theme is picked by `useTheme().global.name.value` (toggled via the `useThemeToggle()` composable that's wired into the app's default layout).

---

## Picking the right text color

### Rule 1: Plain text on the default page background

Use no class. The default text color is theme-aware (`on-surface`).

```vue
<v-container>
  <h2>Heading</h2>
  <p>Paragraph text.</p>
</v-container>
```

For lower-emphasis text:

```vue
<p class="text-medium-emphasis">Subtle helper text</p>
<p class="text-disabled">Disabled text</p>
```

### Rule 2: Text inside a colored container

When the container has an explicit `color` prop, use the matching `text-on-X` class for any *manually-classed* text inside:

```vue
<v-card color="primary" class="pa-4">
  <h3 class="text-on-primary">Title</h3>
  <p class="text-on-primary">Body — contrasts with primary in BOTH themes.</p>
</v-card>
```

Vuetify already applies `on-primary` as the default text color for content inside `<v-card color="primary">`, so usually you can skip the class:

```vue
<v-card color="primary" class="pa-4">
  <h3>Title</h3>
  <p>Body</p>
</v-card>
```

The `text-on-primary` class is needed when:
- You're styling a child manually via `class` or `style`
- The child is a non-Vuetify element (`<div>`, `<span>`, custom component) that doesn't inherit the colorized context

### Rule 3: Backgrounds on plain elements

If you must use a `<div>` (no Vuetify component fits), pair `bg-X` with `text-on-X`:

```vue
<div class="bg-surface-variant text-on-surface-variant pa-3 rounded">
  This div looks right in both themes.
</div>
```

| Use case | Background class | Text class |
|---|---|---|
| Default content panel | `bg-surface` | `text-on-surface` |
| Elevated / secondary panel | `bg-surface-variant` | `text-on-surface-variant` |
| Brand / call-to-action | `bg-primary` | `text-on-primary` |
| Success state | `bg-success` | `text-on-success` |
| Error state | `bg-error` | `text-on-error` |
| Warning / caution | `bg-warning` | `text-on-warning` |
| Info / neutral | `bg-info` | `text-on-info` |

### Rule 4: Custom CSS (scoped styles)

Use Vuetify's CSS variables. They update reactively when the theme changes.

```vue
<style scoped>
.my-callout {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-on-surface-variant));
  border: 1px solid rgb(var(--v-border-color));
  border-radius: 8px;
  padding: 16px;
}
.my-callout--primary {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}
</style>
```

Available variables:

| Variable | Purpose |
|---|---|
| `--v-theme-primary` / `--v-theme-on-primary` | Brand color + contrasting text |
| `--v-theme-secondary` / `--v-theme-on-secondary` | Secondary accent |
| `--v-theme-surface` / `--v-theme-on-surface` | Default page background + text |
| `--v-theme-surface-variant` / `--v-theme-on-surface-variant` | Elevated panel + text |
| `--v-theme-success` / `--v-theme-on-success` | Success state |
| `--v-theme-error` / `--v-theme-on-error` | Error state |
| `--v-theme-warning` / `--v-theme-on-warning` | Warning state |
| `--v-theme-info` / `--v-theme-on-info` | Info / neutral state |
| `--v-border-color` | Hairline borders, dividers (semi-transparent) |

For alpha-modulated colors: use the comma form so you can layer opacity:

```css
.muted-overlay { background: rgba(var(--v-theme-primary), 0.1); }
```

---

## Anti-patterns — DO NOT USE

### `text-white` / `text-black`

These render the same color in BOTH themes — they don't adapt. White text on a light background = invisible.

### Hardcoded colors in inline styles

```vue
<!-- WRONG: doesn't adapt -->
<div style="background: white; color: black;">

<!-- RIGHT -->
<v-card>...</v-card>
<!-- or -->
<div class="bg-surface text-on-surface" style="border: 1px solid rgb(var(--v-border-color))">
```

### Hex colors in scoped CSS

```css
/* WRONG */
.banner { background: #f3f4f6; color: #1f2937; }

/* RIGHT */
.banner {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-on-surface-variant));
}
```

### Tailwind-style classes

Vuetify does NOT ship Tailwind. `text-gray-500`, `bg-red-100`, etc. resolve to nothing.

### Setting `bg-X` without `text-on-X`

```vue
<!-- WRONG: text color drift in some theme -->
<div class="bg-primary"><span>Hello</span></div>

<!-- RIGHT -->
<div class="bg-primary text-on-primary"><span>Hello</span></div>
```

---

## Source-language text

Polytonic Greek text in citations uses the `.text-grc` class, which applies the self-hosted `SBL Greek` font:

```vue
<p>The flagship sequence is <span class="text-grc">πίστις > ἐλπίς > ἀγάπη</span>.</p>
```

The `<GreekText>` component wraps this idiom — prefer it for consistency:

```vue
<p>The flagship sequence is <GreekText>πίστις > ἐλπίς > ἀγάπη</GreekText>.</p>
```

A `.text-heb` class is declared in `assets/styles/globals.css` with `direction: rtl` and a system-font fallback. No Hebrew font ships in S1 (NT-only corpus); the hook exists so a future slice can drop in `SBLHebrew.woff2` without restructuring.

---

## Definition of done

Before considering a UI change complete:

1. **Toggle the theme.** Click the light/dark toggle in the app header.
2. **Scan every piece of text.** Check that contrast is adequate.
3. **Scan every border / divider.** Should be visible but not loud.
4. **Look for hard-coded colors** in the diff: `text-white`, `text-black`, `#hex`, `rgb()` literals, `bg-white`, named CSS colors. Replace them with the theme-aware equivalents above.

If any test fails, the change isn't done — the fix is always one of the patterns in "Rule 1–4" above.
