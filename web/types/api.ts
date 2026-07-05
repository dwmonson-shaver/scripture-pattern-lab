/**
 * Hand-written API type aliases that bridge the generated
 * `openapi-typescript` shape (`components["schemas"][...]`) to the
 * named types frontend code reads.
 *
 * Two responsibilities:
 *
 * 1) **Name aliases for backend response models.** Re-export the
 *    components.schemas entries under the readable names consumers use
 *    (`QueryNLResponse`, `ConceptDocument`, `AutoCreatedConceptNote`,
 *    ...). Without this, callers would write
 *    `components['schemas']['QueryNLResponse']` everywhere.
 *
 * 2) **Hand-written types that aren't in the backend's OpenAPI surface.**
 *    The project's error envelope (`{ detail: ErrorResponse }`) is
 *    documented in canonical-09 but FastAPI doesn't include it in the
 *    OpenAPI components (response_model covers 200 only). Hand-write it
 *    here, matching `src/app/schemas.py:ErrorResponse` shape.
 *
 * DEC-081: the regenerated `backend.ts` is the structural seam for
 * response shapes. This file deliberately stays thin — only aliases
 * over the generated file plus the few hand-written pieces.
 */

import type { components } from './backend'

export type AutoCreatedConceptNote = components['schemas']['AutoCreatedConceptNote']
export type ConceptDocument = components['schemas']['ConceptDocument']
export type ComparativeLexiconSection = components['schemas']['ComparativeLexiconSection']
export type EducationalArticleSection = components['schemas']['EducationalArticleSection']
export type LexiconComparisonRow = components['schemas']['LexiconComparisonRow']
export type Tier2Grouping = components['schemas']['Tier2Grouping']
export type GroupingMember = components['schemas']['GroupingMember']
export type GroupingPointer = components['schemas']['GroupingPointer']
export type QueryDSLResponse = components['schemas']['QueryDSLResponse']
export type QueryNLResponse = components['schemas']['QueryNLResponse']
export type TranslationMetadata = components['schemas']['TranslationMetadata']
export type ValidationResult = components['schemas']['ValidationResult']
export type ValidationFinding = components['schemas']['ValidationFinding']

/**
 * `ValidationResult.status` enum values. Re-stated as a named union
 * because the generated type inlines them and downstream code (e.g.,
 * `statusColor` computed) wants a single name to switch on.
 */
export type ValidationStatus = ValidationResult['status']

/**
 * Project error envelope: every backend error response body is
 * `{ detail: { error, message, details } }`. Hand-written because
 * FastAPI doesn't surface this in the OpenAPI components. Shape
 * matches `src/app/schemas.py:ErrorResponse`.
 */
export interface BackendErrorDetail {
  error: string
  message: string
  details: Record<string, unknown> | null
}

export interface BackendErrorBody {
  detail: BackendErrorDetail
}

/**
 * Slice 1 — interim hand-written types for the concept-identification reader
 * (DEC-149 / DEC-125 precedent). The reader/marks/concept-write endpoints are
 * NOT yet in the deployed backend's OpenAPI surface, so `gen:types` cannot
 * regenerate them. These mirror src/app/schemas.py exactly; replace with
 * `components['schemas'][...]` aliases once the backend is redeployed and
 * `npm run gen:types` runs.
 */

// --- Chapter read (GET /api/v1/read/{corpus}/{book}/{chapter}) -------------
export interface GreekTokenOut {
  position: number
  surface_form: string
  normalized_form: string
  lemma: string
  morph_code: string
  pos: string
}

export interface VerseRead {
  verse: number
  reference: string
  english_text: string
  greek_tokens: GreekTokenOut[]
}

export interface ChapterReadResponse {
  corpus_id: string
  book: string
  book_display: string
  chapter: number
  version_code: string
  verses: VerseRead[]
}

export interface VersionInfoOut {
  code: string
  name: string
  is_public_domain: boolean
}

export interface VersionsResponse {
  versions: VersionInfoOut[]
}

// --- Concepts (GET/POST/PATCH /api/v1/concepts) ----------------------------
export type AuthoredPolarity = '+' | '-' | '±'

export interface ConceptSummary {
  name: string
  description: string | null
  verification_state: string
  lemma_count: number
  lemmas: string[]
  authored_color: string | null
  authored_polarity: AuthoredPolarity | null
  authored_opposite_name: string | null
}

export interface ConceptsResponse {
  concepts: ConceptSummary[]
}

export interface ConceptCreateRequest {
  name: string
  description?: string | null
  authored_color?: string | null
  authored_polarity?: AuthoredPolarity | null
  authored_opposite_name?: string | null
}

export interface ConceptUpdateRequest {
  description?: string | null
  authored_color?: string | null
  authored_polarity?: AuthoredPolarity | null
  authored_opposite_name?: string | null
}

export interface ConceptWriteResponse {
  name: string
  description: string | null
  origin: string
  verification_state: string
  authored_color: string | null
  authored_polarity: string | null
  authored_opposite_name: string | null
}

// --- Marks (CRUD /api/v1/marks) --------------------------------------------
export interface MarkOut {
  id: number
  corpus_id: string
  book: string
  chapter: number
  verse_start: number
  verse_end: number
  char_start: number
  char_end: number
  version_code: string
  actor: string
  concept_names: string[]
}

export interface MarksResponse {
  marks: MarkOut[]
}

export interface MarkCreateRequest {
  corpus_id?: string
  book: string
  chapter: number
  verse_start: number
  verse_end: number
  char_start: number
  char_end: number
  version_code?: string
  concept_names?: string[]
}

export interface MarkUpdateRequest {
  verse_start?: number | null
  verse_end?: number | null
  char_start?: number | null
  char_end?: number | null
  concept_names?: string[] | null
}

// Slice 2 — typed connections between concepts (2026-07-05). Interim
// hand-written until gen:types picks the backend schema up on next redeploy.

/** The connection claim-type vocabulary; mirrors 08_connections.sql CHECK. */
export type ConnectionType =
  | 'opposite'
  | 'prerequisite'
  | 'produces'
  | 'sequence'
  | 'compound'
  | 'association'
  | 'interchange'
  | 'unknown'

export interface ConnectionOut {
  id: number
  note: string | null
  actor: string
  members: string[] // concept names, in position order
  types: ConnectionType[]
}

export interface ConnectionsResponse {
  connections: ConnectionOut[]
}

export interface ConnectionCreateRequest {
  member_names: string[]
  types: ConnectionType[]
  note?: string | null
}
