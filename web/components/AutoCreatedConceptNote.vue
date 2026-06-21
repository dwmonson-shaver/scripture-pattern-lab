<script setup lang="ts">
import type { AutoCreatedConceptNote } from '~~/types/api'

/**
 * Slice N (DEC-102 / DEC-104 / DEC-105): when a query references a term
 * with no registry mapping, the backend auto-generates a machine /
 * lexicon-sourced concept and re-runs the query. This component is the
 * first-class UI surface for that event so the user never has to inspect
 * raw JSON to know it happened.
 *
 * Design rules:
 * - `note.summary` is the backend's authoritative
 *   "machine/lexicon-sourced — unverified — starting prior" wording.
 *   Render it verbatim. Do NOT paraphrase. Do NOT add adjectives the
 *   backend didn't sign off on.
 * - Visually distinct (info-toned, prominent header) so it reads as a
 *   pipeline event, not a search result.
 * - When `document_available=true`, surface a link to the persisted
 *   two-part Conceptual Document view (route: /concept/:name).
 */
const props = defineProps<{ note: AutoCreatedConceptNote }>()

const documentHref = computed(() => `/concept/${encodeURIComponent(props.note.concept_name)}`)
</script>

<template>
  <v-card class="pa-6 mb-4" color="info" variant="tonal" data-testid="auto-created-concept-note">
    <div class="d-flex align-center ga-2 mb-3 flex-wrap">
      <v-chip
        size="small"
        color="info"
        prepend-icon="mdi-auto-fix"
        data-testid="auto-created-badge"
      >
        Auto-created concept
      </v-chip>
      <v-chip size="small" variant="outlined" prepend-icon="mdi-flask-outline">
        unverified — starting prior
      </v-chip>
    </div>

    <p class="text-h6 mb-1" data-testid="auto-created-concept-name">
      {{ note.concept_name }}
    </p>

    <p class="text-body-2 mb-3" data-testid="auto-created-summary">
      {{ note.summary }}
    </p>

    <div v-if="note.lemmas.length > 0" class="mb-3">
      <p class="text-caption text-medium-emphasis mb-1">Lemmas pulled in from the lexicon:</p>
      <div class="d-flex flex-wrap ga-2">
        <v-chip
          v-for="lemma in note.lemmas"
          :key="lemma"
          size="small"
          variant="outlined"
          data-testid="auto-created-lemma"
        >
          <GreekText>{{ lemma }}</GreekText>
        </v-chip>
      </div>
    </div>

    <div v-if="note.document_available" class="mt-2">
      <v-btn
        :href="documentHref"
        color="info"
        variant="flat"
        size="small"
        prepend-icon="mdi-file-document-outline"
        data-testid="auto-created-document-link"
      >
        Open the Conceptual Document
      </v-btn>
    </div>
  </v-card>
</template>
