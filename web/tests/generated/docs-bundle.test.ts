import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import type { DocEntry } from '~~/utils/docs'

// Verifies the real output of scripts/collect-docs.mjs (run by the `pretest`
// hook). Guards the build-time contract: REQ comment markers stripped, HTML
// rendered (not raw markdown), every entry well-formed.
const bundlePath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../public/docs.json',
)
const docs = JSON.parse(readFileSync(bundlePath, 'utf8')) as DocEntry[]

describe('generated docs bundle', () => {
  it('contains a well-formed, non-empty set', () => {
    expect(docs.length).toBeGreaterThan(0)
    for (const d of docs) {
      expect(d.slug).toBeTruthy()
      expect(d.title).toBeTruthy()
      expect(d.category).toBeTruthy()
      expect(typeof d.html).toBe('string')
    }
  })

  it('has unique slugs', () => {
    const slugs = docs.map((d) => d.slug)
    expect(new Set(slugs).size).toBe(slugs.length)
  })

  it('renders HTML and strips REQ / HTML comment markers', () => {
    expect(docs.some((d) => d.html.includes('<'))).toBe(true)
    for (const d of docs) {
      expect(d.html).not.toContain('<!--')
    }
  })
})
