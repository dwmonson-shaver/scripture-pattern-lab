<script setup lang="ts">
import type { QueryNLResponse, ValidationStatus } from '~~/types/api'

/**
 * Caller contract: this component renders the **executed** shape of
 * `QueryNLResponse` (Slice L Decision #6 — the four pipeline fields
 * populated). The clarification shape (all four null) is the parent's
 * job to surface; not this component's concern.
 */
type ExecutedQueryNLResponse = QueryNLResponse & {
  validation: NonNullable<QueryNLResponse['validation']>
  result: NonNullable<QueryNLResponse['result']>
  explanation: NonNullable<QueryNLResponse['explanation']>
  translation: NonNullable<QueryNLResponse['translation']>
}

const props = defineProps<{ response: ExecutedQueryNLResponse }>()

const statusColor = computed(() => {
  const s = props.response.validation.status as ValidationStatus
  if (s === 'supported') return 'success'
  if (s === 'partial') return 'warning'
  return 'error'
})

const groundingLabel = computed(() => {
  const g = props.response.validation.grounding
  if (!g) return null
  // "evidence-grounded" → "Evidence-Grounded"
  return g
    .split('-')
    .map((p: string) => p[0].toUpperCase() + p.slice(1))
    .join('-')
})

const confidencePct = computed(() =>
  Math.round((props.response.translation.confidence ?? 0) * 100),
)

const contextualization = computed(() => props.response.result.contextualization)

const observedAlt = computed(() =>
  contextualization.value?.alternative_orderings.find((a) => a.is_observed) ?? null,
)
</script>

<template>
  <div data-testid="result-envelope">
    <!-- Compiled DSL -->
    <v-card class="pa-6 mb-4" data-testid="compiled-dsl">
      <div class="d-flex align-center mb-2">
        <v-chip size="small" color="info" prepend-icon="mdi-translate" class="mr-2">
          Compiled DSL
        </v-chip>
        <v-chip
          size="small"
          color="secondary"
          variant="outlined"
          :prepend-icon="confidencePct >= 80 ? 'mdi-check' : 'mdi-help-circle-outline'"
        >
          {{ confidencePct }}% confidence
        </v-chip>
      </div>
      <code class="text-body-1 d-block py-2" style="font-family: monospace">{{
        response.query
      }}</code>
      <p
        v-if="response.translation.explanation"
        class="text-caption text-medium-emphasis mt-2 mb-0"
      >
        {{ response.translation.explanation }}
      </p>
      <div v-if="response.translation.alternatives.length > 0" class="mt-3">
        <p class="text-caption text-medium-emphasis mb-1">Alternatives the translator considered:</p>
        <code
          v-for="(alt, i) in response.translation.alternatives"
          :key="i"
          class="d-block text-caption pl-3 text-medium-emphasis"
          style="font-family: monospace"
        >
          {{ alt }}
        </code>
      </div>
    </v-card>

    <!-- Validation status -->
    <v-card class="pa-4 mb-4" data-testid="validation-card">
      <div class="d-flex align-center ga-3 flex-wrap">
        <v-chip
          size="small"
          :color="statusColor"
          prepend-icon="mdi-shield-check-outline"
          data-testid="validation-status"
        >
          {{ response.validation.status }}
        </v-chip>
        <v-chip v-if="groundingLabel" size="small" variant="outlined">
          {{ groundingLabel }}
        </v-chip>
        <v-chip
          v-if="response.validation.findings.length > 0"
          size="small"
          color="warning"
          variant="tonal"
        >
          {{ response.validation.findings.length }} finding{{
            response.validation.findings.length === 1 ? '' : 's'
          }}
        </v-chip>
      </div>
    </v-card>

    <!-- Results -->
    <v-card class="pa-6 mb-4" data-testid="results-card">
      <v-card-title class="text-h6 px-0 pt-0">
        Matches
        <v-chip size="small" class="ml-2">
          {{ response.result.candidates.length }}
        </v-chip>
      </v-card-title>
      <div v-if="response.explanation.results.length === 0" class="text-medium-emphasis">
        No matches.
      </div>
      <div
        v-for="(r, i) in response.explanation.results"
        :key="i"
        class="mb-4"
        data-testid="result-row"
      >
        <div class="d-flex align-center ga-2 flex-wrap mb-1">
          <span class="font-weight-bold">{{ r.reference }}</span>
          <v-chip size="x-small" variant="tonal">{{ r.match_type }}</v-chip>
        </div>
        <GreekText class="text-body-1 d-block">{{ r.text_display }}</GreekText>
        <p class="text-caption text-medium-emphasis mt-1 mb-0">{{ r.explanation }}</p>
      </div>
    </v-card>

    <!-- Contextualization -->
    <v-card v-if="contextualization" class="pa-6 mb-4" data-testid="contextualization-card">
      <v-card-title class="text-h6 px-0 pt-0">Context</v-card-title>
      <p class="text-body-2 mb-3">
        Observed
        <span class="font-weight-bold">{{ contextualization.observed_count }}</span>
        match{{ contextualization.observed_count === 1 ? '' : 'es' }} in the corpus.
      </p>
      <p class="text-body-2 mb-2">Each node's standalone frequency:</p>
      <ul class="mb-4">
        <li v-for="(b, i) in contextualization.node_baselines" :key="i">
          <GreekText>{{ b.resolved_lemmas.join(', ') }}</GreekText>
          — <strong>{{ b.count }}</strong> occurrences
          <span class="text-caption text-medium-emphasis">({{ b.node_value }})</span>
        </li>
      </ul>
      <p v-if="contextualization.alternative_orderings_capped" class="text-caption text-medium-emphasis mb-2">
        Alternative orderings list is capped (only the first
        {{ contextualization.alternative_orderings.length }} shown of all possible permutations).
      </p>
      <p class="text-body-2 mb-2">
        {{ contextualization.alternative_orderings.length }} possible orderings of the nodes:
      </p>
      <ul>
        <li
          v-for="(a, i) in contextualization.alternative_orderings"
          :key="i"
          :class="{ 'font-weight-bold': a.is_observed }"
        >
          {{ a.sequence_label }} — {{ a.count }} occurrence{{ a.count === 1 ? '' : 's' }}
          <v-chip v-if="a.is_observed" size="x-small" color="success" class="ml-1">
            observed
          </v-chip>
        </li>
      </ul>
      <p v-if="observedAlt" class="text-caption text-medium-emphasis mt-3 mb-0">
        The observed ordering accounts for
        {{ observedAlt.count }} of
        {{
          contextualization.alternative_orderings.reduce((sum: number, a) => sum + a.count, 0)
        }}
        total occurrences across all orderings.
      </p>
    </v-card>

    <!-- Explanation summary -->
    <v-card class="pa-6" data-testid="explanation-card">
      <v-card-title class="text-h6 px-0 pt-0">Explanation</v-card-title>
      <p
        class="text-body-1 mb-0"
        style="white-space: pre-wrap"
        data-testid="explanation-summary"
      >{{ response.explanation.summary }}</p>
    </v-card>
  </div>
</template>
