<script setup lang="ts">
definePageMeta({ title: 'Scripture Pattern Lab' })

const { nlQuery, pending, response, error, run } = useQuery()
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

      <ResultEnvelope v-if="response" :response="response" />
    </v-col>
  </v-row>
</template>
