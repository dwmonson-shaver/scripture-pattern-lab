<script setup lang="ts">
import type { ComparativeLexiconSection } from '~~/types/api'

/**
 * Part 1 §1 of the Conceptual Document — pure deterministic comparative
 * lexicon data (DEC-106). NO LLM. NO opinion.
 *
 * The visual treatment (outlined card, green "Lexicon data" chip,
 * `mdi-database-check-outline` icon) is intentional and load-bearing per
 * DEC-111: a reader who skims must immediately register this as
 * ground-truth lexicon data rather than LLM commentary.
 */
defineProps<{ section: ComparativeLexiconSection }>()
</script>

<template>
  <v-card
    variant="outlined"
    class="pa-6 mb-4"
    data-testid="comparative-lexicon-section"
  >
    <div class="d-flex align-center ga-2 mb-3 flex-wrap">
      <v-chip
        size="small"
        color="success"
        variant="flat"
        prepend-icon="mdi-database-check-outline"
        data-testid="comparative-lexicon-badge"
      >
        Lexicon data
      </v-chip>
      <v-chip size="small" variant="outlined">deterministic</v-chip>
    </div>

    <p class="text-h6 mb-1">
      Comparative lexicon analysis — {{ section.english_term }}
    </p>
    <p class="text-caption text-medium-emphasis mb-4">
      Lemmas and verse references pulled directly from open-licensed lexicon
      data. No LLM, no opinion.
    </p>

    <v-table density="comfortable" data-testid="comparative-lexicon-table">
      <thead>
        <tr>
          <th class="text-left">Lemma</th>
          <th class="text-left">Strong's</th>
          <th class="text-left">Usual renderings</th>
          <th class="text-left">Corpus verses</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in section.rows" :key="row.lemma" data-testid="comparative-lexicon-row">
          <td><GreekText>{{ row.lemma }}</GreekText></td>
          <td>{{ row.strongs.length > 0 ? row.strongs.join(', ') : '—' }}</td>
          <td>
            <span v-if="row.usual_renderings.length === 0">—</span>
            <span v-else>{{ row.usual_renderings.join(', ') }}</span>
          </td>
          <td>
            <span v-if="row.corpus_verse_refs.length === 0" class="text-medium-emphasis">
              none in corpus
            </span>
            <span v-else>{{ row.corpus_verse_refs.join('; ') }}</span>
          </td>
        </tr>
      </tbody>
    </v-table>

    <p
      v-if="section.generated_from.length > 0"
      class="text-caption text-medium-emphasis mt-3 mb-0"
      data-testid="comparative-lexicon-provenance"
    >
      Generated from: {{ section.generated_from.join(', ') }}
    </p>
  </v-card>
</template>
