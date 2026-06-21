<script setup lang="ts">
import type { ConceptDocument } from '~~/types/api'

/**
 * Top-level renderer for the persisted Conceptual Document (DEC-106).
 *
 * Renders four sections in order:
 *   1. Header (concept name + short summary + epistemic chip)
 *   2. Part 1 §1 — Comparative lexicon (deterministic)
 *   3. Part 1 §2 — LLM-generated educational article (clearly labeled)
 *      (omitted when `part1_educational` is null — store-once means an
 *       early-version document may exist without §2)
 *   4. Part 2 — Tier-2 grouping section (anchor view / member-pointer
 *      view / not-yet-a-member placeholder, decided by Tier2GroupingSection
 *      from `document.part2_grouping` and `document.part2_grouping_pointer`)
 *
 * The §1 / §2 visual distinction (different colors, different chips,
 * different surface treatments) is intentional and load-bearing per
 * DEC-111.
 */
defineProps<{ document: ConceptDocument }>()
</script>

<template>
  <div data-testid="concept-document-view">
    <!-- Header -->
    <v-card class="pa-6 mb-4" data-testid="concept-document-header">
      <div class="d-flex align-center ga-2 mb-2 flex-wrap">
        <v-chip size="small" color="info" prepend-icon="mdi-file-document-outline">
          Conceptual Document
        </v-chip>
        <v-chip size="small" variant="outlined" prepend-icon="mdi-flask-outline">
          unverified — starting prior
        </v-chip>
      </div>
      <p class="text-h5 mb-2" data-testid="concept-document-name">
        {{ document.concept_name }}
      </p>
      <p class="text-body-2 text-medium-emphasis mb-0">
        {{ document.short_summary }}
      </p>
    </v-card>

    <!-- Part 1 §1 — Deterministic comparative lexicon -->
    <ComparativeLexiconSection :section="document.part1_comparative" />

    <!-- Part 1 §2 — LLM commentary (optional) -->
    <EducationalArticleSection
      v-if="document.part1_educational"
      :section="document.part1_educational"
    />
    <v-alert
      v-else
      type="info"
      variant="outlined"
      density="compact"
      class="mb-4"
      data-testid="educational-article-absent"
    >
      No LLM-generated educational commentary is attached to this document. (The article generator
      is opt-in per DEC-107 and the document is stored once on first creation.)
    </v-alert>

    <!-- Part 2 — Tier-2 grouping section (anchor / member / placeholder) -->
    <Tier2GroupingSection
      :grouping="document.part2_grouping ?? null"
      :pointer="document.part2_grouping_pointer ?? null"
    />
  </div>
</template>
