# Backend Service Boundaries

## Purpose
Define the service topology for the Scripture Pattern Lab backend: what components exist, what each is responsible for, how they communicate, and how the MVP simplifies this into a practical starting architecture. [DEC-012][DEC-014][DEC-015]

## Architectural Principle
The backend is decomposed into logical components with clear boundaries, but the MVP deploys them as a single process (monolith-first). Service boundaries are defined now so that extraction into separate services is straightforward later, but premature distribution is avoided. [DEC-020]

## Component Overview

```
┌──────────────────────────────────────────────────────────┐
│                      API Gateway                         │
│                    (FastAPI routes)                       │
└──────────┬───────────────────────────────┬───────────────┘
           │                               │
           ▼                               ▼
┌─────────────────────┐        ┌─────────────────────────┐
│  NL-to-DSL Service  │        │    Query Endpoint       │
│    (AI translator)  │        │  (accepts DSL directly) │
└──────────┬──────────┘        └──────────┬──────────────┘
           │                               │
           └───────────┬───────────────────┘
                       ▼
              ┌─────────────────┐
              │   DSL Parser    │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │   Capability    │
              │   Validator     │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Pattern Engine │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │   Retrieval     │
              │   Pipeline      │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │   Scoring &     │
              │   Ranking       │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Result Builder │
              │  & Explainer    │
              └────────┬────────┘
                       ▼
                   Response
```

## Component Specifications

### 1. API Gateway
**Location**: `src/app/`
**Responsibility**: HTTP routing, request validation, authentication (future), rate limiting (future).

**MVP routes**:
- `POST /api/v1/query/nl` — Accept natural language, translate to DSL, validate, execute
- `POST /api/v1/query/dsl` — Accept raw DSL, validate, execute
- `POST /api/v1/query/validate` — Accept DSL, return validation result without executing
- `GET /api/v1/capabilities` — Return current capability registry
- `GET /api/v1/concepts` — Return concept registry (for UI autocomplete)
- `GET /api/v1/health` — Health check

**Input/output format**: JSON. Requests and responses use typed schemas.

### 2. NL-to-DSL Service
**Location**: `src/nlp/`
**Responsibility**: Translate natural language queries into DSL syntax using an LLM.

**Interface**:
```python
def translate(nl_query: str, context: TranslationContext) -> TranslationResult

class TranslationResult:
    dsl: str                    # Generated DSL string
    confidence: float           # Model's confidence in the translation
    alternatives: list[str]     # Alternative DSL interpretations if ambiguous
    explanation: str            # Why the model chose this translation
```

**Constraints**:
- Must produce valid DSL syntax (parseable by the DSL parser)
- Must not invent DSL features that don't exist
- Must surface ambiguity rather than silently resolve it
- The LLM receives the current capability registry as context [DEC-003][DEC-006]

**MVP implementation**: Single LLM call with a system prompt containing DSL grammar, capability registry, and concept registry. No fine-tuning, no multi-turn refinement.

### 3. DSL Parser
**Location**: `src/engine/parser.py`
**Responsibility**: Parse DSL text into a QueryPlan AST (as defined in `05_dsl-ast.md`).

**Interface**:
```python
def parse(dsl: str) -> QueryPlan

# Raises ParseError with line/column info on invalid syntax
```

**MVP implementation**: Hand-written recursive descent parser. The grammar is small enough that a parser generator is unnecessary overhead.

### 4. Capability Validator
**Location**: `src/validation/`
**Responsibility**: Validate a QueryPlan against the current capability registry. Produce structured validation results. (Full contract in `06_capability-validator.md`.)

**Interface**:
```python
def validate(plan: QueryPlan, registry: CapabilityRegistry) -> ValidationResult
```

**MVP implementation**: Sequential rule checks as specified in the validator contract. The capability registry is loaded from a versioned config file.

### 5. Pattern Engine
**Location**: `src/engine/`
**Responsibility**: Execute a validated QueryPlan against the corpus. This is the core deterministic search component.

**Interface**:
```python
def execute(plan: QueryPlan, scope: ScopeConstraint) -> list[MatchCandidate]

class MatchCandidate:
    tokens: list[Token]         # The matched token sequence
    reference: str              # e.g., "1Cor 13:13"
    match_type: str             # "exact", "variant", "conceptual"
    alignment: list[StepMatch]  # How each query step mapped to corpus tokens
```

**MVP implementation**: SQL-based sequence search against the tokens table. For each step in the sequence, generate candidate token positions, then verify ordering and gap constraints. This is not elegant at scale but is correct and sufficient for 138K tokens.

**Future**: For larger corpora, replace SQL scans with indexed sequence search (inverted index + position lists).

### 6. Retrieval Pipeline
**Location**: `src/retrieval/`
**Responsibility**: Orchestrate multi-stage retrieval. In MVP, this is a thin wrapper around the pattern engine. In later versions, it coordinates symbolic, lexical, and semantic retrieval stages. [DEC-017]

**Interface**:
```python
def retrieve(plan: QueryPlan) -> RetrievalResult

class RetrievalResult:
    candidates: list[MatchCandidate]
    stages_used: list[str]      # Which retrieval stages contributed
```

**MVP implementation**: Single-stage symbolic retrieval only (calls the pattern engine). The pipeline interface exists so that semantic retrieval can be added later without changing the API surface.

### 7. Scoring & Ranking
**Location**: `src/scoring/`
**Responsibility**: Score and rank match candidates according to configurable weights. [DEC-019]

**Interface**:
```python
def score(candidates: list[MatchCandidate], prefs: RankingPrefs | None) -> list[ScoredMatch]

class ScoredMatch:
    candidate: MatchCandidate
    total_score: float
    factor_scores: dict[str, float]  # Score per ranking factor
```

**MVP implementation**: Simple weighted scoring with default weights. Factors: lexical alignment (do lemmas match exactly?), sequence fidelity (are positions in order with acceptable gaps?), scope precision (verse-level vs. cross-verse). More factors (morphology, semantic, polarity, rarity) added as retrieval stages expand.

### 8. Result Builder & Explainer
**Location**: `src/nlp/explainer.py`
**Responsibility**: Transform scored matches into user-facing results with explanations. Uses an LLM to generate natural-language explanations of why each result matched and what its limitations are. [DEC-015]

**Interface**:
```python
def explain(matches: list[ScoredMatch], plan: QueryPlan, validation: ValidationResult) -> ExplainedResultSet

class ExplainedResultSet:
    query_shown: str            # The DSL that was executed
    nl_source: str | None       # Original NL if applicable
    validation_notes: list[str] # Any capability limitations
    results: list[ExplainedResult]

class ExplainedResult:
    reference: str
    text_display: str           # Highlighted passage text
    match_type: str
    score: float
    explanation: str            # Why this matched
```

**MVP implementation**: Template-based explanation for exact/variant matches. LLM explanation for conceptual matches or when results need qualification.

## Communication Model

### MVP: In-Process
All components run in a single FastAPI process. Components call each other as Python functions. No message queues, no HTTP between services, no containers.

```
FastAPI process
├── routes (src/app/)
├── NL translator (src/nlp/) → calls LLM API externally
├── parser (src/engine/parser.py)
├── validator (src/validation/)
├── pattern engine (src/engine/)
├── retrieval pipeline (src/retrieval/)
├── scoring (src/scoring/)
├── explainer (src/nlp/explainer.py)
└── Postgres connection pool
```

### Future: Extraction Points
When scale or team structure demands it, the natural extraction boundaries are:

1. **NL-to-DSL** → separate service (it has the only external LLM dependency for input)
2. **Pattern engine + retrieval** → separate service (compute-heavy, can scale independently)
3. **Explainer** → separate service (second external LLM dependency, for output)
4. **Background jobs** (corpus ingestion, concept registry updates) → worker queue

### External Dependencies
- **Postgres**: Token storage, concept registry, query logging
- **LLM API**: NL-to-DSL translation, result explanation (Claude or similar)
- No other external services for MVP

## Request Lifecycle — MVP

```
1. User submits NL query via POST /api/v1/query/nl
2. API gateway validates request shape
3. NL-to-DSL translator calls LLM, returns DSL string + explanation
4. DSL parser produces QueryPlan AST
5. Capability validator checks QueryPlan → returns ValidationResult
   a. If unsupported → return error response with explanation
   b. If partial → reduce plan, include warnings in response
   c. If supported → continue
6. Pattern engine executes the (possibly reduced) QueryPlan against Postgres
7. Retrieval pipeline returns MatchCandidates
8. Scoring ranks candidates
9. Explainer produces user-facing results with explanations
10. API returns ExplainedResultSet as JSON
```

For `POST /api/v1/query/dsl`, steps 3 is skipped (DSL is provided directly).

## MVP Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| API framework | FastAPI | Async, typed, good for prototyping |
| Database | PostgreSQL | Structured queries, reliable, pgvector-ready |
| ORM/query | SQLAlchemy + raw SQL | ORM for CRUD, raw SQL for pattern engine queries |
| LLM integration | Anthropic SDK (Claude) | Structured generation, large context for DSL grammar |
| Config | YAML/JSON files | Capability registry, concept registry |
| Testing | pytest | Standard Python testing |
| Dependency management | uv or poetry | Modern Python dependency management |

## Directory Mapping

```
src/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── routes/
│   │   ├── query.py          # /api/v1/query/* routes
│   │   ├── capabilities.py   # /api/v1/capabilities
│   │   └── concepts.py       # /api/v1/concepts
│   └── schemas/              # Pydantic request/response models
├── engine/
│   ├── parser.py             # DSL parser → QueryPlan
│   ├── executor.py           # Pattern engine
│   └── models.py             # AST node types (QueryPlan, SequenceExpr, etc.)
├── nlp/
│   ├── translator.py         # NL-to-DSL translation
│   └── explainer.py          # Result explanation
├── ontology/
│   └── registry.py           # Concept and domain registry access
├── retrieval/
│   └── pipeline.py           # Multi-stage retrieval orchestration
├── scoring/
│   └── ranker.py             # Scoring and ranking
└── validation/
    ├── validator.py           # Capability validator
    └── registry.py            # Capability registry loader
```

## Open Questions
1. Should the LLM translation and explanation share a session/context, or be fully independent calls?
2. Should query logging be synchronous (part of the request) or async (background write)?
3. Should the concept registry support hot-reload, or is a restart acceptable for MVP?
4. What is the target response time budget for an end-to-end NL query?

## Confidence and Volatility
- Confidence: Medium-High
- Volatility: Medium (component boundaries are stable; implementation details will evolve)

## References
- Decisions: DEC-003, DEC-006, DEC-012, DEC-014, DEC-015, DEC-017, DEC-019, DEC-020
- Assumptions: ASM-003
- Prior docs: 05_dsl-ast.md, 06_capability-validator.md, 08_mvp-corpus-scope.md
