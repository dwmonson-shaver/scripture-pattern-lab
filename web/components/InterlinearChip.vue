<script setup lang="ts">
import type { GreekTokenOut } from '~~/types/api'

/**
 * One Greek interlinear token chip. Shows the lemma in the SBL Greek font
 * (via <GreekText>) plus the normalized/surface form as a transliteration-ish
 * sub-label. Tapping emits `tap` with the token so the parent can flash the
 * matching word in the rendered English verse (the prototype's flashGloss).
 *
 * Chrome uses semantic tokens only; no raw color renders here.
 */
const props = defineProps<{ token: GreekTokenOut }>()

const emit = defineEmits<{ tap: [token: GreekTokenOut] }>()

const subLabel = computed(() => {
  const t = props.token
  // surface_form differs from lemma when the word is inflected; show it as the
  // contextual form. Fall back to the part-of-speech tag when they match.
  if (t.surface_form && t.surface_form !== t.lemma) return t.surface_form
  return t.pos
})
</script>

<template>
  <v-chip
    size="small"
    variant="outlined"
    class="ma-1"
    data-testid="interlinear-chip"
    :data-position="token.position"
    @click="emit('tap', token)"
  >
    <GreekText class="mr-1">{{ token.lemma }}</GreekText>
    <span class="text-medium-emphasis text-caption">{{ subLabel }}</span>
  </v-chip>
</template>
