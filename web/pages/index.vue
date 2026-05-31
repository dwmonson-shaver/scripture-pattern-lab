<script setup lang="ts">
definePageMeta({ title: 'Scripture Pattern Lab' })

const { nlQuery, pending, response, error, run } = useQuery()

/**
 * The NL response has two shapes (Slice L Decision #6): executed (four
 * pipeline fields populated) vs. clarification (all four null). Narrow
 * here so `<ResultEnvelope>` gets the executed shape it expects. The
 * clarification UI is out of scope for this slice — when it lands it
 * will branch off `response.value?.clarification` independently.
 */
const executedResponse = computed(() => {
  const r = response.value
  if (!r) return null
  if (!r.validation || !r.result || !r.explanation || !r.translation) return null
  return {
    ...r,
    validation: r.validation,
    result: r.result,
    explanation: r.explanation,
    translation: r.translation,
  }
})

const autoCreatedNote = computed(() => response.value?.auto_created_concept ?? null)
</script>

<template>
  <v-row justify="center">
    <v-col cols="12" md="10" lg="8" xl="7">
      <div class="mb-6">
        <p class="text-body-2 text-medium-emphasis mb-1">Scripture Pattern Lab</p>
        <p class="text-h6">
          Symbolic pattern queries over the original-language corpus, with AI assisting at the
          natural-language boundary only.
        </p>
      </div>

      <QueryForm v-model="nlQuery" :pending="pending" @run="run" />

      <ErrorPanel v-if="error" :error="error" />

      <AutoCreatedConceptNote v-if="autoCreatedNote" :note="autoCreatedNote" />

      <ResultEnvelope v-if="executedResponse" :response="executedResponse" />
    </v-col>
  </v-row>
</template>
