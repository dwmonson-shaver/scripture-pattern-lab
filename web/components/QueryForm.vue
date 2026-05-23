<script setup lang="ts">
const props = defineProps<{
  modelValue: string
  pending: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  run: []
}>()

const queryValue = computed({
  get: () => props.modelValue,
  set: (v: string) => emit('update:modelValue', v),
})

const canRun = computed(() => !!queryValue.value.trim() && !props.pending)

const onRun = () => {
  if (canRun.value) emit('run')
}
</script>

<template>
  <v-card class="pa-6 mb-6" data-testid="query-form">
    <v-card-title class="text-h6 px-0 pt-0">Ask a question</v-card-title>
    <v-card-subtitle class="px-0 mb-4 text-medium-emphasis">
      Natural language compiles to DSL; the corpus is the ground truth.
    </v-card-subtitle>
    <v-textarea
      v-model="queryValue"
      label="Question"
      placeholder="Where do faith, hope, and love appear together in proximity with precedence?"
      :counter="2000"
      maxlength="2000"
      rows="3"
      auto-grow
      data-testid="query-input"
      :disabled="pending"
      @keydown.ctrl.enter.prevent="onRun"
      @keydown.meta.enter.prevent="onRun"
    />
    <div class="d-flex align-center justify-space-between mt-2">
      <span class="text-caption text-medium-emphasis">Cmd/Ctrl + Enter to run</span>
      <v-btn
        color="primary"
        size="large"
        :disabled="!canRun"
        :loading="pending"
        prepend-icon="mdi-magnify"
        data-testid="query-run"
        @click="onRun"
      >
        Run
      </v-btn>
    </div>
  </v-card>
</template>
