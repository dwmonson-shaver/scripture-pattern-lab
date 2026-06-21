<script setup lang="ts">
definePageMeta({ title: 'Conceptual Document' })

const route = useRoute()

/**
 * Route param `name`. Nuxt decodes URL params, so a concept named
 * `fear of the lord` arrives as `fear of the lord` (not the encoded
 * form). The composable re-encodes when building the proxy URL.
 */
const conceptName = computed(() => {
  const raw = route.params.name
  if (Array.isArray(raw)) return raw[0] ?? ''
  return raw ?? ''
})

const { document, pending, error } = useConceptDocument(conceptName)

useHead(() => ({
  title: conceptName.value ? `${conceptName.value} — Conceptual Document` : 'Conceptual Document',
}))
</script>

<template>
  <v-row justify="center">
    <v-col cols="12" md="10" lg="8" xl="7">
      <div class="mb-4 d-flex align-center ga-3">
        <v-btn
          to="/"
          variant="text"
          size="small"
          prepend-icon="mdi-arrow-left"
          data-testid="concept-back-link"
        >
          Back to query
        </v-btn>
      </div>

      <div v-if="pending" data-testid="concept-loading">
        <v-skeleton-loader type="article, table, paragraph" />
      </div>

      <ErrorPanel v-else-if="error" :error="error" />

      <ConceptDocumentView v-else-if="document" :document="document" />
    </v-col>
  </v-row>
</template>
