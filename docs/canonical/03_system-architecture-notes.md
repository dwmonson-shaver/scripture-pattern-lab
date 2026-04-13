# System Architecture Notes

## Architectural Thesis
The product should use symbolic retrieval as the core engine, embeddings and semantic retrieval as supporting layers, and an LLM as translator, explainer, and assistant rather than sole source of truth. [CONV-002][EXT-001][EXT-002][DEC-012]

## Core Layers
<!-- REQ:03.text-layer -->
### 1. Text and language layer
Canonical structured corpus with tokens, lemmas, roots, morphology, semantic labels, scope boundaries, and alignment metadata. [CONV-001][DEC-013]

<!-- REQ:03.pattern-engine -->
### 2. Pattern engine
Deterministic search over ordered sequences, variants, gaps, polarity, and extension logic. [CONV-001][CONV-003][DEC-014]

### 3. AI layer
Use AI for:
- natural-language-to-DSL translation
- query expansion suggestions
- result explanation
- counter-evidence generation
- clustering and memo generation [CONV-002][DEC-015]

<!-- REQ:03.capability-validator -->
### 4. Capability validator
This is a first-class component, not just a prompt. It checks whether generated queries are executable under current DSL and engine support. [CONV-004][DEC-006]

### 5. Exploration UI
Hypothesis builder, results explorer, evidence inspector, and comparison workspace. [CONV-001][DEC-016]

<!-- REQ:03.retrieval-strategy -->
## Retrieval Strategy
Use multi-stage retrieval:
1. symbolic/structured retrieval for exactness,
2. lexical retrieval for phrase relevance,
3. semantic retrieval for concept expansion,
4. reranking for confidence ordering,
5. LLM explanation for user-facing synthesis. [CONV-002][EXT-002][DEC-017]

## Recommended Early Stack
- Frontend: Next.js
- Backend: FastAPI
- Canonical DB: Postgres
- Vector support: pgvector first
- Search engine: Postgres initially, optional Elastic/OpenSearch later
- Worker jobs: background queue
- LLM integration: model API for structured generation and explanation [CONV-002][EXT-001][EXT-002][ASM-003]

## Why Not “Just RAG”
Naive RAG over scripture text is insufficient because sequence hypotheses depend on order, morphology, scope, polarity, and explicit interpretability. RAG is useful for concept expansion and explanation, but not as the primary pattern engine. [CONV-002][DEC-018]

<!-- REQ:03.scoring-philosophy -->
## Scoring Philosophy
Ranking should be transparent and weighted across factors such as:
- lexical sequence alignment
- morphology alignment
- semantic overlap
- polarity fidelity
- rarity/distinctiveness
- contextual coherence [CONV-002][DEC-019]

## MVP Boundary
Start with a narrow but sharp product:
- one corpus family first
- lemma and concept nodes
- ordered sequence search with gaps
- basic polarity support
- NL-to-DSL translation and validation
- transparent result explanations [CONV-002][DEC-020]

## Confidence and Volatility
- Confidence: High
- Volatility: Medium

## References
- Decisions: DEC-006, DEC-012, DEC-013, DEC-014, DEC-015, DEC-016, DEC-017, DEC-018, DEC-019, DEC-020
- Evidence: CONV-001, CONV-002, CONV-003, CONV-004
- External: EXT-001, EXT-002
- Assumptions: ASM-003
