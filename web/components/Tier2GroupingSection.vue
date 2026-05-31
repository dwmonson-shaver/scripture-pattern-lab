<script setup lang="ts">
import type { Tier2Grouping, GroupingPointer } from '~~/types/api'

/**
 * Part 2 of the Conceptual Document — Tier-2 conceptual grouping.
 *
 * Replaces the prior `Tier2GroupingPlaceholder` (Slice O).
 * Renders one of three shapes depending on the document being viewed:
 *
 *   1. Anchor concept — `grouping` is set: full Tier-2 grouping card with
 *      members + per-edge confidence + epistemic chip + rationale.
 *   2. Member concept — `pointer` is set: lightweight pointer card linking
 *      back to the anchor concept(s).
 *   3. Neither — the concept is not yet a member of any grouping; renders
 *      the original "not yet built" placeholder so the layout stays stable.
 *
 * DEC-081 / DEC-115 epistemic line: every grouping is unverified. The chip
 * says exactly that. NO LLM SDK in this component (check:no-llm-sdk
 * verified at build time).
 */
defineProps<{
  grouping?: Tier2Grouping | null
  pointer?: GroupingPointer | null
}>()

function confidencePct(c: number): string {
  return `${Math.round(c * 100)}%`
}
</script>

<template>
  <!-- Anchor view: full Tier-2 grouping -->
  <v-card
    v-if="grouping"
    variant="outlined"
    class="pa-6 mb-4"
    data-testid="tier2-grouping-section"
  >
    <div class="d-flex align-center ga-2 mb-3 flex-wrap">
      <v-chip
        size="small"
        color="info"
        variant="tonal"
        prepend-icon="mdi-graph-outline"
      >
        Tier-2 grouping
      </v-chip>
      <v-chip
        size="small"
        variant="outlined"
        prepend-icon="mdi-flask-outline"
        data-testid="tier2-vstate-chip"
      >
        unverified — human review required
      </v-chip>
    </div>

    <p class="text-h6 mb-1">Conceptual grouping</p>
    <p class="text-caption text-medium-emphasis mb-3">
      Anchor: {{ grouping.anchor_name }}
    </p>

    <v-list density="compact" class="mb-3" data-testid="tier2-member-list">
      <v-list-item
        v-for="m in grouping.members"
        :key="m.concept_name"
        :data-testid="`tier2-member-${m.concept_name}`"
      >
        <v-list-item-title class="d-flex align-center ga-2 flex-wrap">
          <span>{{ m.concept_name }}</span>
          <v-chip
            size="x-small"
            variant="tonal"
            color="primary"
            :data-testid="`tier2-confidence-${m.concept_name}`"
          >
            {{ confidencePct(m.confidence) }}
          </v-chip>
          <span v-if="m.note" class="text-caption text-medium-emphasis">
            — {{ m.note }}
          </span>
        </v-list-item-title>
      </v-list-item>
    </v-list>

    <p class="text-body-2 text-medium-emphasis mb-0" data-testid="tier2-rationale">
      {{ grouping.rationale }}
    </p>
  </v-card>

  <!-- Member view: pointer back to anchor(s) -->
  <v-card
    v-else-if="pointer"
    variant="outlined"
    class="pa-6 mb-4"
    data-testid="tier2-grouping-pointer"
  >
    <div class="d-flex align-center ga-2 mb-3 flex-wrap">
      <v-chip
        size="small"
        variant="outlined"
        prepend-icon="mdi-link-variant"
      >
        Tier-2 member
      </v-chip>
      <v-chip
        size="small"
        variant="outlined"
        prepend-icon="mdi-flask-outline"
      >
        unverified — human review required
      </v-chip>
    </div>

    <p class="text-h6 mb-1">Member of conceptual grouping</p>
    <p class="text-body-2 text-medium-emphasis mb-0">
      This concept belongs to a Tier-2 grouping anchored on:
      <NuxtLink
        v-for="(anchor, i) in pointer.grouping_anchors"
        :key="anchor"
        :to="`/concept/${encodeURIComponent(anchor)}`"
        :data-testid="`tier2-pointer-${anchor}`"
        class="text-decoration-none"
      >
        <span v-if="i > 0">, </span>
        <strong>{{ anchor }}</strong>
      </NuxtLink>
      .
    </p>
  </v-card>

  <!-- Neither: placeholder for concepts not yet in any grouping -->
  <v-card
    v-else
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
        not yet a member
      </v-chip>
    </div>

    <p class="text-h6 mb-1">Conceptual groupings</p>
    <p class="text-body-2 text-medium-emphasis mb-0">
      This concept is not yet part of a Tier-2 grouping. The Tier-2 layer
      surfaces claims that different expressions "hang together" beyond
      their lexicon mapping; groupings are written by the curator workflow
      and the system's worked-example seed (DEC-116).
    </p>
  </v-card>
</template>
