#!/usr/bin/env node
// DEC-081 structural enforcement: the deployed Worker bundle must NOT
// contain any LLM SDK. The backend (FastAPI on Render) owns all LLM calls.
//
// Fails the build if any output chunk references:
// - `@ai-sdk/anthropic` or `@anthropic-ai/sdk` (Anthropic SDKs)
// - `openai` (the OpenAI SDK package)
// - `google-generative-ai` (Gemini SDK)
//
// Each is a discrete add-back path that would erode DEC-081 if it ever
// shipped. The check runs after `nuxt build` writes .output/.
//
// This is a SECOND-LINE defense. The first line is that the SDK never
// enters package.json. Dynamic imports with variable specifiers
// (e.g., `await import(someVar)`) could bypass this grep; review every
// new dependency addition substantively against DEC-081 rather than
// relying on this script alone.

import { readFile, readdir } from 'node:fs/promises'
import { join } from 'node:path'

const OUTPUT_DIR = '.output'
const FORBIDDEN_PATTERNS = [
  '@ai-sdk/anthropic',
  '@anthropic-ai/sdk',
  'google-generative-ai',
]
// 'openai' would false-positive on the word "openai" in any other context.
// Match it only as an import / require.
const FORBIDDEN_REGEXPS = [
  /from\s+['"]openai['"]/i,
  /require\(\s*['"]openai['"]\s*\)/i,
]

async function* walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) yield* walk(path)
    else yield path
  }
}

let violations = []
for await (const path of walk(OUTPUT_DIR)) {
  if (!path.endsWith('.js') && !path.endsWith('.mjs') && !path.endsWith('.cjs')) continue
  const content = await readFile(path, 'utf8')
  for (const pattern of FORBIDDEN_PATTERNS) {
    if (content.includes(pattern)) {
      violations.push({ path, pattern })
    }
  }
  for (const regex of FORBIDDEN_REGEXPS) {
    const match = content.match(regex)
    if (match) {
      violations.push({ path, pattern: match[0] })
    }
  }
}

if (violations.length > 0) {
  console.error('DEC-081 violation: LLM SDK detected in deployed bundle.')
  for (const v of violations) {
    console.error(`  ${v.path}: ${v.pattern}`)
  }
  console.error('')
  console.error('All LLM calls must go through the backend (POST /api/v1/query/nl).')
  console.error('Remove the offending dependency from package.json or via grep.')
  process.exit(1)
}

console.log('DEC-081 check passed: no LLM SDK in output.')
