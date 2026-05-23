import { defineVuetifyConfiguration } from 'vuetify-nuxt-module/custom-configuration'

// Dark-default palette derived from pattern-mapping template. Slice J1 keeps
// this as-is; a scripture-research-appropriate rebrand is deferred to a
// follow-on polish slice (tracked in design-slice-j1 OQ-J1-5).
export default defineVuetifyConfiguration({
  theme: {
    defaultTheme: 'dark',
    themes: {
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
      light: {
        dark: false,
        colors: {
          background: '#fafafa',
          surface: '#ffffff',
          'surface-bright': '#f4f6fb',
          'surface-light': '#f4f6fb',
          'surface-variant': '#e6ecf5',
          primary: '#1d6dff',
          secondary: '#5b6b85',
          accent: '#8b5cf6',
          error: '#dc2626',
          info: '#3b82f6',
          success: '#16a34a',
          warning: '#d97706',
          'on-background': '#0a1628',
          'on-surface': '#0a1628',
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
