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
