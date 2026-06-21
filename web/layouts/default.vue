<script setup lang="ts">
const config = useRuntimeConfig()
const APP_NAME = (config.public?.appName as string | undefined) || 'Scripture Pattern Lab'
const { isDark, toggle } = useThemeToggle()
</script>

<template>
  <v-app>
    <v-app-bar elevation="1" color="surface" density="comfortable">
      <v-app-bar-title class="font-weight-bold">{{ APP_NAME }}</v-app-bar-title>
      <template #append>
        <v-btn
          variant="text"
          :icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
          :aria-label="isDark ? 'Switch to parchment mode' : 'Switch to dark mode'"
          @click="toggle"
        />
      </template>
    </v-app-bar>
    <v-main>
      <v-container class="pa-6">
        <slot />
      </v-container>
    </v-main>
  </v-app>
</template>
