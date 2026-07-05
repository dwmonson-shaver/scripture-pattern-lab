<script setup lang="ts">
// Reader layout (Slice 1 reader-alignment): a full-height shell with NO
// v-container padding, so the reader page can own the app-shell (spec #screen)
// where only the text column + panel scroll. The theme toggle lives in the
// reader's own masthead area; this layout keeps just the <v-app> root that
// Vuetify needs for theming + the navigation-drawer layout context.
const { isDark, toggle } = useThemeToggle()
const { toast } = useToast()
</script>

<template>
  <v-app>
    <v-main class="reader-main-shell">
      <NuxtLink
        to="/docs"
        class="masthead-link"
        aria-label="Project docs"
        data-testid="reader-docs-link"
      >
        <v-icon icon="mdi-file-document-multiple-outline" size="small" />
      </NuxtLink>
      <button
        class="theme-toggle"
        type="button"
        :aria-label="isDark ? 'Switch to parchment mode' : 'Switch to dark mode'"
        data-testid="reader-theme-toggle"
        @click="toggle"
      >
        <v-icon :icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'" size="small" />
      </button>
      <slot />
      <v-snackbar
        v-model="toast.show"
        :color="toast.color"
        :timeout="2600"
        location="bottom right"
        data-testid="app-toast"
      >
        {{ toast.text }}
      </v-snackbar>
    </v-main>
  </v-app>
</template>

<style scoped>
.reader-main-shell {
  height: 100vh;
  min-height: 0;
}
/* Override Vuetify's default v-main padding so the shell owns the full height. */
.reader-main-shell :deep(.v-main__wrap),
.reader-main-shell.v-main {
  --v-layout-top: 0;
  padding: 0 !important;
  height: 100vh;
}
/* A small, unobtrusive theme toggle pinned to the masthead corner — the reader
 * identity is parchment, but the dark toggle stays reachable. */
.theme-toggle {
  position: fixed;
  top: 0.55rem;
  right: 0.75rem;
  z-index: 20;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  border: 1px solid rgb(var(--v-border-color));
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
}
.theme-toggle:hover {
  border-color: rgb(var(--v-theme-secondary));
}
/* Docs link — same pill treatment as the theme toggle, sat just left of it. */
.masthead-link {
  position: fixed;
  top: 0.55rem;
  right: 3.05rem;
  z-index: 20;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  border: 1px solid rgb(var(--v-border-color));
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  text-decoration: none;
}
.masthead-link:hover {
  border-color: rgb(var(--v-theme-secondary));
}
</style>
