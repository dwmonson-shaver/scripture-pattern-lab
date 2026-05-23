<script setup lang="ts">
definePageMeta({ title: 'Home' })
</script>

<template>
  <v-row justify="center">
    <v-col cols="12" md="8" lg="6">
      <v-card class="pa-8 text-center">
        <v-icon size="64" color="primary" class="mb-4">mdi-book-open-page-variant</v-icon>
        <h1 class="text-h4 font-weight-bold mb-2">Scripture Pattern Lab</h1>
        <p class="text-body-1 text-medium-emphasis mb-6">
          AI-assisted original-language hypothesis exploration for Judeo-Christian scripture.
        </p>
        <p class="text-body-2 text-medium-emphasis mb-6">
          Query surface lands in Phase J1.3. This is the deploy-infrastructure placeholder.
        </p>
        <v-chip color="success" variant="tonal" prepend-icon="mdi-check-circle">
          Deployed via Cloudflare Workers
        </v-chip>
      </v-card>
    </v-col>
  </v-row>
</template>
