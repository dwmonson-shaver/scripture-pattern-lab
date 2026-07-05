#!/usr/bin/env node
/**
 * Build-time docs collector.
 *
 * Reads a curated set of the project's plan/design/governance Markdown files
 * from the repo, strips HTML comments (e.g. the canonical docs' `<!-- REQ:… -->`
 * markers), renders each to HTML with markdown-it, and writes a single
 * `web/generated/docs.json` the in-app /docs viewer imports. markdown-it is a
 * build-time (dev) dependency only — the client receives pre-rendered HTML, so
 * no Markdown renderer ships to the browser (keeps the bundle lean + CSP-safe).
 *
 * Output goes to `public/docs.json` — a STATIC ASSET fetched at runtime, not
 * imported into a JS chunk. That keeps the docs (which quote LLM-SDK names in
 * prose, e.g. the DEC-081 rule) out of the scanned bundle, keeps the main
 * bundle lean, and lazy-loads the content only when /docs is visited. Regen'd
 * by the `predev`/`prebuild` hooks and manually via `npm run generate:docs`.
 */
import { fileURLToPath } from 'node:url'
import { dirname, resolve, basename, join } from 'node:path'
import { readFileSync, readdirSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import MarkdownIt from 'markdown-it'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const webRoot = resolve(scriptDir, '..')
const repoRoot = resolve(webRoot, '..')

// Category → { label, order, source }. `source` is either a directory (all its
// top-level .md files) or an explicit list of repo-relative files.
const CATEGORIES = [
  {
    key: 'canonical',
    label: 'Canonical specs',
    order: 1,
    dir: 'docs/canonical',
  },
  {
    key: 'design',
    label: 'Design',
    order: 2,
    dir: 'docs/design',
    files: [
      'design-concepts-connections-evidence.md',
      'design-slice-1-concept-identification-2026-06-20.md',
      'structure-reader-alignment.md',
      'structure-slice-1-concept-identification-2026-06-20.md',
    ],
  },
  {
    key: 'governance',
    label: 'Governance',
    order: 3,
    dir: 'docs/governance',
  },
  {
    key: 'vision',
    label: 'Vision',
    order: 4,
    dir: 'docs/vision',
  },
  {
    key: 'plan',
    label: 'Plan & status',
    order: 5,
    files: [
      'README.md',
      'FEATURE-INVENTORY.md',
      'ROADMAP_NEXT_STEPS.md',
      'CHANGELOG.md',
    ],
  },
]

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

function slugify(category, name) {
  const base = basename(name, '.md')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return `${category}-${base}`
}

function titleOf(raw, fallbackName) {
  const m = raw.match(/^#\s+(.+?)\s*$/m)
  return m ? m[1].replace(/[`*_]/g, '').trim() : basename(fallbackName, '.md')
}

function render(raw) {
  // Drop HTML comments (REQ markers, notes) so they don't render as stray text.
  const cleaned = raw.replace(/<!--[\s\S]*?-->/g, '')
  return md.render(cleaned)
}

function collectFiles(cat) {
  const out = []
  const seen = new Set()
  const add = (relPath) => {
    const abs = join(repoRoot, relPath)
    if (seen.has(abs) || !existsSync(abs) || !relPath.endsWith('.md')) return
    seen.add(abs)
    const raw = readFileSync(abs, 'utf8')
    if (!raw.trim()) return
    out.push({
      slug: slugify(cat.key, relPath),
      title: titleOf(raw, relPath),
      category: cat.key,
      categoryLabel: cat.label,
      order: cat.order,
      path: relPath,
      html: render(raw),
    })
  }
  if (cat.dir && existsSync(join(repoRoot, cat.dir))) {
    for (const f of readdirSync(join(repoRoot, cat.dir)).sort()) {
      if (f.endsWith('.md')) add(join(cat.dir, f))
    }
  }
  for (const f of cat.files ?? []) add(f)
  return out
}

const docs = CATEGORIES.flatMap(collectFiles)
// Stable order: by category order, then title.
docs.sort((a, b) => a.order - b.order || a.title.localeCompare(b.title))

const outDir = join(webRoot, 'public')
mkdirSync(outDir, { recursive: true })
writeFileSync(join(outDir, 'docs.json'), JSON.stringify(docs) + '\n', 'utf8')
console.log(`collect-docs: wrote ${docs.length} docs to public/docs.json`)
