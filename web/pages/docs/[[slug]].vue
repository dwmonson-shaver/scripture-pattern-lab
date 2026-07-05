<script setup lang="ts">
/**
 * Project docs viewer — the plan / design / governance Markdown, rendered to
 * HTML at build time and served as the static /docs.json asset (fetched by
 * useDocs), shown in a two-pane reader: a grouped nav on the left, the selected
 * doc on the right. Uses the default layout (app bar + theme toggle). Reachable
 * from the reader's masthead.
 */
const route = useRoute()
const { all, groups, bySlug, pending } = useDocs()

const slug = computed(() => {
  const s = route.params.slug
  return Array.isArray(s) ? s[0] : s
})

const current = computed(() => bySlug(slug.value))
</script>

<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-4">
      <h1 class="text-h5 font-weight-bold">Project docs</h1>
      <v-btn
        to="/reader"
        variant="text"
        size="small"
        prepend-icon="mdi-book-open-page-variant-outline"
        data-testid="docs-to-reader"
      >
        Reader
      </v-btn>
    </div>

    <v-row>
      <!-- Nav -->
      <v-col cols="12" md="4" lg="3">
        <v-card variant="outlined" data-testid="docs-nav">
          <v-list density="compact" nav>
            <template v-for="group in groups" :key="group.key">
              <v-list-subheader class="text-overline">{{ group.label }}</v-list-subheader>
              <v-list-item
                v-for="doc in group.docs"
                :key="doc.slug"
                :to="`/docs/${doc.slug}`"
                :active="doc.slug === slug"
                :title="doc.title"
                data-testid="docs-nav-item"
                :data-slug="doc.slug"
              />
            </template>
          </v-list>
        </v-card>
      </v-col>

      <!-- Content -->
      <v-col cols="12" md="8" lg="9">
        <v-card variant="flat" class="doc-content pa-2 pa-sm-4" data-testid="docs-content">
          <div v-if="pending" class="text-medium-emphasis" data-testid="docs-loading">Loading…</div>
          <template v-else-if="current">
            <p class="text-caption text-medium-emphasis mb-2">{{ current.path }}</p>
            <!-- Trusted, build-time-rendered repo docs (not user input). -->
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="doc-prose" v-html="current.html" />
          </template>
          <template v-else>
            <p class="text-body-1 mb-2">
              {{ all.length }} documents — the plan, design, and governance behind Scripture Pattern
              Lab. Pick one from the list to read it.
            </p>
            <p class="text-medium-emphasis text-body-2">
              These are the same Markdown files that live in the repo, rendered here so they travel
              with the app.
            </p>
          </template>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<style scoped>
/* Readable prose that adapts to both themes via semantic tokens. Tables matter
 * (governance docs are table-heavy), so they get explicit borders + padding. */
.doc-prose {
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.doc-prose :deep(h1),
.doc-prose :deep(h2),
.doc-prose :deep(h3),
.doc-prose :deep(h4) {
  font-weight: 700;
  line-height: 1.25;
  margin: 1.6em 0 0.6em;
}
.doc-prose :deep(h1) {
  font-size: 1.6rem;
}
.doc-prose :deep(h2) {
  font-size: 1.3rem;
}
.doc-prose :deep(h3) {
  font-size: 1.1rem;
}
.doc-prose :deep(p),
.doc-prose :deep(ul),
.doc-prose :deep(ol),
.doc-prose :deep(blockquote) {
  margin: 0.7em 0;
}
.doc-prose :deep(ul),
.doc-prose :deep(ol) {
  padding-left: 1.4em;
}
.doc-prose :deep(a) {
  color: rgb(var(--v-theme-primary));
}
.doc-prose :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.88em;
  background: rgba(var(--v-theme-on-surface), 0.07);
  padding: 0.1em 0.35em;
  border-radius: 4px;
}
.doc-prose :deep(pre) {
  background: rgba(var(--v-theme-on-surface), 0.07);
  padding: 0.9em 1em;
  border-radius: 6px;
  overflow-x: auto;
}
.doc-prose :deep(pre code) {
  background: none;
  padding: 0;
}
.doc-prose :deep(blockquote) {
  border-left: 3px solid rgba(var(--v-theme-on-surface), 0.2);
  padding-left: 1em;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.85;
}
.doc-prose :deep(table) {
  border-collapse: collapse;
  display: block;
  overflow-x: auto;
  max-width: 100%;
  margin: 0.9em 0;
}
.doc-prose :deep(th),
.doc-prose :deep(td) {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  padding: 0.4em 0.7em;
  text-align: left;
  vertical-align: top;
}
.doc-prose :deep(th) {
  background: rgba(var(--v-theme-on-surface), 0.05);
  font-weight: 700;
}
.doc-prose :deep(hr) {
  border: none;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.15);
  margin: 1.5em 0;
}
</style>
