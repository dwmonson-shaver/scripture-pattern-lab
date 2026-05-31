<script setup lang="ts">
/**
 * Part 2 of the Conceptual Document — Tier-2 grouping placeholder.
 *
 * Slice N delivered Part 1 (lexicon section + LLM commentary) only.
 * Part 2 — the Tier-2 conceptual grouping artifact (claims that
 * different expressions "hang together", e.g. hope ↔ patience) — is
 * the explicit scope of a later slice (DEC-102 Tier-2 charter). This
 * placeholder renders as a stub so the document layout makes the
 * structural shape visible from day one.
 */
</script>

<template>
  <v-card
    variant="outlined"
    class="pa-6 mb-4"
    data-testid="tier2-grouping-placeholder"
  >
    <div class="d-flex align-center ga-2 mb-3 flex-wrap">
      <v-chip
        size="small"
        variant="outlined"
        prepend-icon="mdi-graph-outline"
      >
        Tier-2 grouping
      </v-chip>
      <v-chip
        size="small"
        color="warning"
        variant="tonal"
        prepend-icon="mdi-clock-outline"
      >
        not yet built
      </v-chip>
    </div>

    <p class="text-h6 mb-1">Conceptual groupings</p>
    <p class="text-body-2 text-medium-emphasis mb-0">
      The Tier-2 layer — claims that different expressions "hang
      together" beyond their lexicon mapping — is the explicit scope of
      a later curator slice (DEC-102). Once it ships, this section will
      render the corpus-evidenced groupings + their human-validation
      state.
    </p>
  </v-card>
</template>
