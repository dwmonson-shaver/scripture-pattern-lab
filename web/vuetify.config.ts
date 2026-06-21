import { defineVuetifyConfiguration } from 'vuetify-nuxt-module/custom-configuration'

// Study-edition parchment identity (DEC-152). The reader's visual spec is
// docs/design/reader-reference.html (v8, approved). Semantic tokens are kept;
// their VALUES are redefined to the parchment palette:
//   ground  #EBE1CE  · ground-2 #E2D6BD · panel #F3ECDB · card #FBF6EA
//   ink     #2B2722  · rubric   #9C2A23 · gilt  #A07E2A · hairline #C9BC9F
// Concept colors stay CONTENT (authored_color, inline) — never theme tokens.
// The dark theme is retained for the accessibility toggle / the rest of the
// app, but parchment is the default and the reader's identity.
export default defineVuetifyConfiguration({
  theme: {
    defaultTheme: 'parchment',
    themes: {
      // --- Reader identity: warm rag-paper study edition (default) ---
      parchment: {
        dark: false,
        colors: {
          background: '#EBE1CE', // rag-paper ground
          surface: '#FBF6EA', // card / illuminated leaf
          'surface-bright': '#FBF6EA',
          'surface-light': '#F3ECDB',
          'surface-variant': '#F3ECDB', // apparatus panel
          primary: '#9C2A23', // manuscript rubric red — verse nums, book label, primary actions
          secondary: '#A07E2A', // gilt — rules, handles, accents
          accent: '#A07E2A',
          error: '#9C2A23', // rubric doubles as danger
          info: '#557A8C',
          success: '#5E9A45',
          warning: '#A07E2A',
          'on-background': '#2B2722', // oak-gall ink
          'on-surface': '#2B2722',
          'on-surface-variant': '#6B6152', // soft ink for secondary text
          'on-primary': '#FBF6EA',
          'on-secondary': '#2B2722',
        },
        variables: {
          'border-color': '#C9BC9F', // hairline
          'border-opacity': 1,
          'high-emphasis-opacity': 1,
          'medium-emphasis-opacity': 0.74,
        },
      },
      // --- Retained dark theme for the toggle / rest of the app ---
      dark: {
        dark: true,
        colors: {
          background: '#0a1628',
          surface: '#13213a',
          'surface-bright': '#1d3a5e',
          'surface-light': '#1d3a5e',
          'surface-variant': '#243960',
          primary: '#3b82f6',
          secondary: '#8b9bb5',
          accent: '#8b5cf6',
          error: '#ef4444',
          info: '#3b82f6',
          success: '#22c55e',
          warning: '#f59e0b',
          'on-background': '#e8edf5',
          'on-surface': '#e8edf5',
          'on-primary': '#ffffff',
          'on-secondary': '#0a1628',
        },
      },
    },
  },
  defaults: {
    global: {
      ripple: true,
    },
    VBtn: {
      variant: 'flat',
      rounded: 'lg',
      class: 'text-none font-weight-bold',
    },
    VCard: {
      variant: 'flat',
      rounded: 'lg',
    },
    VTextField: {
      variant: 'outlined',
      rounded: 'lg',
      density: 'comfortable',
      color: 'primary',
    },
    VTextarea: {
      variant: 'outlined',
      rounded: 'lg',
      color: 'primary',
    },
    VSelect: {
      variant: 'outlined',
      rounded: 'lg',
      density: 'comfortable',
      color: 'primary',
    },
    VChip: {
      rounded: 'md',
    },
    VAlert: {
      rounded: 'lg',
      variant: 'tonal',
    },
    VDialog: {
      rounded: 'lg',
    },
    VList: {
      rounded: 'lg',
    },
    VAvatar: {
      rounded: 'circle',
    },
  },
  icons: {
    defaultSet: 'mdi',
  },
})
