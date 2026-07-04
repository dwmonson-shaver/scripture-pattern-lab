<script setup lang="ts">
import type { VersionInfoOut } from '~~/types/api'

/**
 * Top navigation bar for the reader: canon / book / chapter selectors, the
 * version switcher, and the interlinear (original-language) toggle.
 *
 * The interlinear toggle is hidden when the selected corpus has no original
 * language (e.g. an English-original corpus). Slice 1 ships NT only, whose
 * original language is Greek; the per-corpus capability map mirrors the
 * prototype's CORPUS_META so adding OT (Hebrew) / others later is a data edit.
 *
 * v-model:* on each control; the page owns the reader state and reloads on
 * change. Chrome only — semantic tokens, no raw color.
 */
const corpus = defineModel<string>('corpus', { required: true })
const book = defineModel<string>('book', { required: true })
const chapter = defineModel<number>('chapter', { required: true })
const version = defineModel<string>('version', { required: true })
const greekOn = defineModel<boolean>('greekOn', { required: true })
// Layout mode (spec): Versed (default) lays verses out as blocks with
// interlinear rows under each; Continuous flows the verses as prose with ruby
// Greek above the aligned word.
const mode = defineModel<'versed' | 'continuous'>('mode', { required: true })

defineProps<{
  versions: VersionInfoOut[]
  pending?: boolean
}>()

const emit = defineEmits<{
  prev: []
  next: []
}>()

// Per-corpus capabilities. `origLang` null => no interlinear toggle.
// Slice 1 seeds NT only; the rest are chrome for the canon dropdown.
const CORPUS_META: Record<string, { label: string; origLang: string | null }> = {
  nt: { label: 'New Testament', origLang: 'Greek' },
  ot: { label: 'Old Testament', origLang: 'Hebrew' },
  bom: { label: 'Book of Mormon', origLang: null },
}

const corpusItems = computed(() =>
  Object.entries(CORPUS_META).map(([value, meta]) => ({
    value,
    title: meta.label,
  })),
)

// NT book abbreviations → display names. Mirrors the reader's default anchor
// (rom = Romans). Kept small for Slice 1; expands as the corpus grows.
const NT_BOOKS: { value: string; title: string }[] = [
  { value: 'mat', title: 'Matthew' },
  { value: 'mrk', title: 'Mark' },
  { value: 'luk', title: 'Luke' },
  { value: 'jhn', title: 'John' },
  { value: 'act', title: 'Acts' },
  { value: 'rom', title: 'Romans' },
  { value: '1co', title: '1 Corinthians' },
  { value: 'gal', title: 'Galatians' },
  { value: 'eph', title: 'Ephesians' },
  { value: 'php', title: 'Philippians' },
  { value: 'heb', title: 'Hebrews' },
  { value: 'jas', title: 'James' },
  { value: 'rev', title: 'Revelation' },
]

const bookItems = computed(() => NT_BOOKS)

const chapterItems = computed(() => Array.from({ length: 40 }, (_, i) => i + 1))

const origLang = computed(() => CORPUS_META[corpus.value]?.origLang ?? null)
</script>

<template>
  <v-toolbar flat density="comfortable" color="surface" class="reader-bar" data-testid="reader-bar">
    <v-container class="d-flex align-center ga-2 flex-wrap py-0">
      <v-select
        v-model="corpus"
        :items="corpusItems"
        density="compact"
        hide-details
        variant="outlined"
        style="max-width: 13rem"
        data-testid="reader-corpus"
        label="Collection"
      />

      <v-select
        v-model="book"
        :items="bookItems"
        density="compact"
        hide-details
        variant="outlined"
        style="max-width: 11rem"
        data-testid="reader-book"
        label="Book"
      />

      <v-btn
        icon="mdi-chevron-left"
        variant="text"
        :disabled="pending"
        aria-label="Previous chapter"
        data-testid="reader-prev"
        @click="emit('prev')"
      />

      <v-select
        v-model="chapter"
        :items="chapterItems"
        density="compact"
        hide-details
        variant="outlined"
        style="max-width: 6rem"
        data-testid="reader-chapter"
        label="Ch."
      />

      <v-btn
        icon="mdi-chevron-right"
        variant="text"
        :disabled="pending"
        aria-label="Next chapter"
        data-testid="reader-next"
        @click="emit('next')"
      />

      <v-spacer />

      <v-btn-toggle
        v-model="mode"
        mandatory
        density="compact"
        variant="outlined"
        divided
        class="mode-toggle"
        data-testid="reader-mode"
      >
        <v-btn value="versed" size="small" data-testid="reader-mode-versed">Versed</v-btn>
        <v-btn value="continuous" size="small" data-testid="reader-mode-continuous">
          Continuous
        </v-btn>
      </v-btn-toggle>

      <v-select
        v-model="version"
        :items="versions"
        item-title="name"
        item-value="code"
        density="compact"
        hide-details
        variant="outlined"
        style="max-width: 16rem"
        data-testid="reader-version"
        label="Version"
      />

      <v-switch
        v-if="origLang"
        v-model="greekOn"
        :label="origLang"
        color="primary"
        hide-details
        density="compact"
        class="ml-2"
        data-testid="reader-interlinear"
      />
    </v-container>
  </v-toolbar>
</template>

<style scoped>
.reader-bar {
  position: sticky;
  top: 0;
  z-index: 5;
  border-bottom: 1px solid rgb(var(--v-border-color));
  /* Vuetify pins the toolbar to a fixed height (inline style on __content).
   * The controls flex-wrap at narrower widths; without these overrides the
   * wrapped second row is clipped and overlapped by the reading pane. */
  height: auto !important;
}
.reader-bar :deep(.v-toolbar__content) {
  height: auto !important;
  min-height: 56px;
  padding-block: 6px;
}
.mode-toggle {
  margin-right: 0.5rem;
}
</style>
