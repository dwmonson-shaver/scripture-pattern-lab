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

<!-- REQ:09.api-gateway -->
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

<!-- REQ:09.nl-to-dsl -->
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

<!-- REQ:09.dsl-parser -->
### 3. DSL Parser
**Location**: `src/engine/parser.py`
**Responsibility**: Parse DSL text into a QueryPlan AST (as defined in `05_dsl-ast.md`).

**Interface**:
```python
def parse(dsl: str) -> QueryPlan

# Raises ParseError with line/column info on invalid syntax
```

**MVP implementation**: Hand-written recursive descent parser. The grammar is small enough that a parser generator is unnecessary overhead.

<!-- REQ:09.capability-validator -->
### 4. Capability Validator
**Location**: `src/validation/`
**Responsibility**: Validate a QueryPlan against the current capability registry. Produce structured validation results. (Full contract in `06_capability-validator.md`.)

**Interface**:
```python
def validate(plan: QueryPlan, registry: CapabilityRegistry) -> ValidationResult
```

**MVP implementation**: Sequential rule checks as specified in the validator contract. The capability registry is loaded from a versioned config file.

<!-- REQ:09.pattern-engine -->
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

<!-- REQ:09.retrieval-pipeline -->
### 6. Retrieval Pipeline
**Location**: `src/retrieval/`
**Responsibility**: Orchestrate multi-stage retrieval. In MVP, this is a thin wrapper around the pattern engine. In later versions, it coordinates symbolic, lexical, and semantic retrieval stages. [DEC-017]

**Interface**:
```python
def retrieve(plan: QueryPlan, *, contextualize: bool = False) -> RetrievalResult

class RetrievalResult:
    candidates: list[MatchCandidate]
    stages_used: list[str]                       # Which retrieval stages contributed
    contextualization: Contextualization | None  # Populated when contextualize=True; None otherwise
```

**MVP implementation**: Single-stage symbolic retrieval only (calls the pattern engine). The pipeline interface exists so that semantic retrieval can be added later without changing the API surface. The `contextualize` flag is engine-layer default-`False` (test-friendly, deterministic, cost-bounded); API-layer / CLI consumers pass `True` so users see calibrated counts by default. [DEC-024]

<!-- REQ:09.scoring-ranking -->
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

**Boundary**: scoring ranks **within** a result set; it does not calibrate the result set against alternatives. That second concern is the contextualization layer (§8) — see DEC-024 for the epistemic split.

<!-- REQ:09.contextualization -->
### 8. Result Contextualization
**Location**: `src/retrieval/contextualization.py`
**Responsibility**: Calibrate the result count of a query against (a) the constituent nodes' baseline frequencies in the corpus, (b) the alternative orderings of the same node-set, and (c) a null-distribution baseline (when feasible). Produces a `Contextualization` envelope attached to the result set; does not modify per-match scoring. The corpus-is-ground-truth principle [DEC-024] makes this an output-side counterpart to the registry-epistemics input-side: raw match counts presented without baseline context invite confirmation bias the same way unverified registry entries do.

**Interface**:
```python
def contextualize(
    plan: QueryPlan,
    scope: ScopeConstraint,
    candidates: list[MatchCandidate],
    engine: Engine,
    registry: ConceptRegistry,
) -> Contextualization

class NodeBaseline:
    node_index: int             # Index of the node in the original sequence
    node_type: str              # "lemma", "concept", etc.
    node_value: str             # The lemma name or concept name
    resolved_lemmas: list[str]  # The actual lemmas matched (after registry resolution)
    count: int                  # COUNT(*) against tokens for this node alone, scope-filtered

class AlternativeOrderingCount:
    permutation: list[int]      # Permutation of step indices, e.g. [1,0,2] for "hope > faith > love"
    sequence_label: str         # Human-readable label, e.g. "hope > faith > love"
    count: int                  # Result count for this ordering (0 if no matches)
    is_observed: bool           # True for the original ordering; False otherwise

class NullDistribution:
    sample_size: int            # Number of random comparable-frequency sequences sampled
    mean: float
    std: float
    seed: int                   # Fixed seed for sampling reproducibility

class Contextualization:
    observed_count: int                              # The original query's match count
    node_baselines: list[NodeBaseline]               # One per node in the sequence
    alternative_orderings: list[AlternativeOrderingCount]
    alternative_orderings_capped: bool               # True if the permutation set was truncated
    null_distribution: NullDistribution | None       # MVP: always None; schema slot for future slices
```

**Invariants**:
- (a) Every result set produced with `contextualize=True` carries node-level baseline counts for every constituent node.
- (b) Every result set carries alternative-ordering counts for the same node-set, capped at `min(N!, 24)` permutations; for N ≥ 5, the cap-fallback is identity + reverse + N pairwise swaps.
- (c) A null-distribution slot is reserved on the envelope; MVP always sets it to `None` (sampling protocol pending future `/research` and `/design`).
- (d) The explainer (§9) must surface contextualization in user-facing output, not just the raw observed count.

**MVP implementation**: Direct SQL `COUNT(*)` against `tokens` for each node baseline (lemma direct; concept resolved via `ConceptRegistry.get_lemmas_for_concept` per `REQ:04.matching-rules`). Re-enters the pattern engine for each non-original permutation. Scope filters (`corpus_id`, `language`, `books`) carry into every baseline and alt-ordering query. Opt-in via the retrieval pipeline's `contextualize` flag (engine-layer default `False`; API/CLI consumer default `True`).

**Future**: Null-distribution sampling protocol (separate `/research` and `/design`); concept-baseline caching; cross-corpus baseline comparison.

<!-- REQ:09.result-explainer -->
### 9. Result Builder & Explainer
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
    contextualization: Contextualization | None  # Populated when retrieve() ran with contextualize=True; None otherwise

class ExplainedResult:
    reference: str
    text_display: str           # Highlighted passage text
    match_type: str
    score: float
    explanation: str            # Why this matched
```

**MVP implementation**: Template-based explanation for exact/variant matches. LLM explanation for conceptual matches or when results need qualification.

<!-- REQ:09.ingestion -->
### 10. Corpus Ingestion (non-request-path)
**Location**: `src/ingestion/`
**Responsibility**: Parse corpus source files (MorphGNT today, future corpora later), bulk-load tokens into Postgres, manage schema apply. Invoked from scripts or workers — never from a query route. [DEC-025]

**Interface**:
```python
def parse_corpus_file(path: Path, *, start_global_position: int = 1) -> Iterator[CorpusToken]
def parse_corpus_directory(directory: Path) -> Iterator[CorpusToken]
def load_tokens(
    engine: Engine,
    tokens: Iterable[CorpusToken],
    *,
    progress_callback: ProgressCallback | None = None,
) -> int
def truncate_tokens(engine: Engine) -> None
def get_engine() -> Engine
```

`progress_callback` is an opt-in observability hook (DEC-034) — `load_tokens` stays I/O-pure and emits `ProgressEvent`s on batch flush, file boundary, and post-commit `done`; no internal logger. The script wires the callback to a stderr printer; library callers (e.g. tests) leave it as `None` and behavior is unchanged. `truncate_tokens` (DEC-038) is the destructive primitive used by the script's `--truncate` gate; it does not self-gate.

**Dependency direction**: Query-side packages (`src/app/`, `src/engine/`, `src/nlp/`, `src/ontology/`, `src/retrieval/`, `src/scoring/`, `src/validation/`) **must not import** `src/ingestion/`. They consume persisted corpus and registry data through stable read interfaces (the `tokens` table; future read-only ontology helpers). Ingestion is the only component that issues bulk writes to corpus tables and applies schema files.

**MVP implementation**: SQLAlchemy 2.0 Core, 1000-row batches in a single global `engine.begin()` transaction (DEC-044). Schema apply is a shell entrypoint (`scripts/db/apply_schemas.sh`), not a Python migration tool. Corpus load is a Python CLI entrypoint (`scripts/db/ingest_corpus.py`) — see DEC-039 for the two-factor `--truncate` + `SPL_INGEST_CONFIRM_TRUNCATE=1` destructive-op gate, DEC-040 for the 0/1/2/3 exit-code taxonomy, DEC-042 for the `sys.path` bootstrap pattern that keeps `scripts/` non-package, DEC-048 for the "extras tolerated on default path" filename-guard semantics. [DEC-021] [DEC-028]

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

`src/ingestion/` is in the codebase but runs outside this process — invoked via a script or worker (see component §10). Query-side modules above must not import from it.

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

<!-- REQ:09.request-lifecycle -->
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
├── ingestion/                 # Non-request-path; not imported by query-side packages
│   ├── corpus_parser.py      # MorphGNT parser → CorpusToken iterator
│   ├── db.py                  # SQLAlchemy 2.0 Core engine + tokens_table mirror
│   └── loader.py              # Bulk loader (1000-row batches, single transaction)
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
- Decisions: DEC-003, DEC-006, DEC-012, DEC-014, DEC-015, DEC-017, DEC-019, DEC-020, DEC-021, DEC-025, DEC-028
- Assumptions: ASM-003
- Prior docs: 05_dsl-ast.md, 06_capability-validator.md, 08_mvp-corpus-scope.md
