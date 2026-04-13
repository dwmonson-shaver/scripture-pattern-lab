# Product Foundation

## Purpose
Build an AI-assisted original-language hypothesis exploration platform for Judeo-Christian ancient scripture. The product should help users test lexical, conceptual, structural, and polarity-aware sequence hypotheses across Hebrew, Aramaic, Greek, and aligned textual traditions. [CONV-001][CONV-002][DEC-001]

## Core Product Thesis
The core value is not a chatbot over scripture. The core value is a hypothesis exploration engine that combines deterministic symbolic search with AI-assisted query translation, explanation, and expansion. [CONV-001][CONV-002][DEC-002]

<!-- REQ:01.job-to-be-done -->
## Primary Job To Be Done
Given a user’s natural-language question about a word, concept, sequence, pattern, or inverse-pattern, the system should:
1. translate the request into formal query syntax,
2. validate whether the requested analysis is actually supported,
3. run the supported portion of the analysis,
4. explain the results and their limitations clearly. [CONV-004][DEC-003]

## Core User Types
- scholars and researchers
- seminarians and advanced students
- pastors and teachers
- technically curious readers working with original languages

## Defining Use Cases
### 1. Sequence hypothesis testing
Example: determine whether faith > hope > love recurs elsewhere exactly, approximately, conceptually, or as part of a larger sequence. [CONV-001]

### 2. Sequence expansion analysis
Determine what concepts commonly precede or follow a target sequence. [CONV-001][DEC-004]

### 3. Polarity-aware inverse analysis
Determine whether a positive sequence has negative-pole analogues, such as possible inverse-domain candidates related to unbelief > despair > hatred. [CONV-003][DEC-005]

### 4. Intertwined pattern analysis
Detect passages where positive and negative sequence families are mixed, interrupted, or braided together. [CONV-003]

### 5. Cross-lingual conceptual migration
Eventually trace patterns across MT, LXX, and NT traditions, with explicit limitations when the engine does not yet support a requested level of alignment. [CONV-002][ASM-005]

## Non-Negotiable Product Behaviors
<!-- REQ:01.nl-compiles-to-dsl -->
### Natural language compiles to DSL
Natural language is the primary entry point, but the engine runs formal query syntax underneath. The AI must translate user requests into DSL rather than bypassing it. [CONV-004][DEC-003]

<!-- REQ:01.capability-boundary -->
### Capability boundary must be explicit
If a natural-language request exceeds current query-language or engine capability, the system must not improvise unsupported analysis. It must clearly say it cannot do that yet, or in developer mode propose a roadmap-aligned syntax extension. [CONV-004][DEC-006]

<!-- REQ:01.transparent-evidence -->
### Transparent evidence over opaque magic
The product should show the generated query, explain why results matched, and label exact, approximate, conceptual, extended, inverse, and intertwined matches distinctly. [CONV-001][CONV-002][DEC-007]

## Product Positioning
Recommended positioning: an original-language hypothesis exploration platform for textual sequence, conceptual recurrence, and intertextual analysis. [CONV-001]

## Confidence and Volatility
- Confidence: High
- Volatility: Medium

## References
- Decisions: DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007
- Evidence: CONV-001, CONV-002, CONV-003, CONV-004
- Assumptions: ASM-005
