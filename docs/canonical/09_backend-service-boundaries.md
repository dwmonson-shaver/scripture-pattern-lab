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

**Response envelope (POST /api/v1/query/dsl)**: composes existing
project models verbatim — no wrapping, no re-derivation. All four
fields are always emitted:

```python
class QueryDSLResponse(BaseModel):
    query: str                         # echo of the request DSL
    validation: ValidationResult        # status, findings, grounding
    result: RetrievalResult             # candidates, stages_used, contextualization
    explanation: ExplainedResultSet     # deterministic prose summary
```

**Null-field policy**: nullable fields emit as `null` in JSON, not
omitted. The codebase calls `model_dump`/`model_dump_json` without
`exclude_none=True` so `Contextualization.null_distribution`,
`ExplainedResultSet.contextualization`, `ValidationResult.grounding`,
etc., all surface as keys with value `null` when their value is
`None`. [DEC-G8 / DEC-057]

**Error envelope**: error responses use `HTTPException(detail=ErrorResponse(...).model_dump())`:

```python
class ErrorResponse(BaseModel):
    error: str                  # stable machine code, e.g. "parse_error"
    message: str                # human-readable description
    details: dict | None = None # error-type-specific fields
```

**HTTP status code mapping** for the DSL pipeline. Each pipeline
exception maps to one row; the route handler's `try/except` chain
must cover all of them. Unmapped exceptions fall through to 500.

| Pipeline exception / state                   | HTTP status                      | `error` code              | `details` keys              |
|----------------------------------------------|----------------------------------|---------------------------|-----------------------------|
| Pydantic body validation (FastAPI default)   | 422 Unprocessable Content        | (FastAPI default shape)   | (FastAPI default)           |
| `ParseError` from `src/engine/parser.py`     | 422 Unprocessable Content        | `parse_error`             | `position`, `source`        |
| Validator returns `status="unsupported"`     | 422 Unprocessable Content        | `validation_unsupported`  | `findings: [...]`           |
| `UnsupportedPlanShape` from executor         | 422 Unprocessable Content        | `unsupported_plan_shape`  | `path`                      |
| `ConceptNotMapped` from executor             | 422 Unprocessable Content        | `concept_not_mapped`      | `concept_name`              |
| `RegistryRequired` from executor             | 503 Service Unavailable          | `registry_required`       | `concept_name`              |
| Engine missing (lifespan didn't construct)   | 503 Service Unavailable          | `engine_unavailable`      | (none)                      |
| Registry missing (lifespan didn't construct) | 503 Service Unavailable          | `registry_unavailable`    | (none)                      |
| `LLMUnavailable` from `src/nlp/llm_client.py` (network, auth, rate-limit, 5xx server) | 503 Service Unavailable | `llm_unavailable` | `reason` |
| LLM client missing (lifespan didn't construct, ANTHROPIC_API_KEY unset) | 503 Service Unavailable | `llm_unavailable` | (none) |
| Translation context missing (lifespan didn't construct) | 503 Service Unavailable | `translation_context_unavailable` | (none) |
| `NLCompileError` from `src/nlp/translator.py` (LLM output couldn't be parsed as DSL) | 422 Unprocessable Content | `nl_compile_error` | `nl_query`, `attempted_output`, `reason` |
| Any uncaught exception                       | 500 Internal Server Error        | `internal_error`          | (none — message is generic; full traceback logged server-side. Includes 4xx anthropic.* errors that propagate raw — DEC-070 distinguishes "LLM unavailable" from "we wrote a bad request to the LLM API.") |

`partial` and `supported` validation statuses both return HTTP 200
with `validation.findings` carrying any reduction warnings; the
client renders them but the response is not an error.

**Dependency injection**: `Engine` and `ConceptRegistry` are
process-scoped resources constructed once during the FastAPI
`lifespan` async context manager and stashed on `app.state`. Route
handlers obtain them via `Depends(get_engine)` /
`Depends(get_concept_registry)` providers in
`src/app/dependencies.py`. The CLI's "one engine per invocation"
pattern generalizes to "one engine per FastAPI process." Tests
bypass the providers via `app.dependency_overrides` so unit-shape
HTTP tests don't require `DATABASE_URL`. [DEC-G2]

**Concurrency**: handlers are sync `def` (not `async def`) because
all upstream code is sync (`engine.connect()`, `validate()`,
`retrieve()`, `explain()`); FastAPI offloads sync handlers to a
thread pool, which is correct here. SQLAlchemy `Engine` is
thread-safe across `connect()` calls.

<!-- REQ:09.nl-to-dsl -->
### 2. NL-to-DSL Service
**Location**: `src/nlp/translator.py` (compile logic) + `src/nlp/llm_client.py`
(LLMClient seam) + `src/nlp/prompts/system_prompt.py` (cached system prompt).
**Responsibility**: Translate natural language queries into DSL syntax using an LLM.

**Interface**:
```python
def translate(
    nl_query: str,
    context: TranslationContext,
    llm_client: LLMClient,
) -> TranslationResult

class TranslationResult(BaseModel):  # frozen Pydantic v2
    dsl: str                    # Generated DSL string (load-bearing field)
    confidence: float = 1.0     # Self-assessed translation fidelity (DEC-072)
    alternatives: list[str] = []  # Alternative DSL interpretations if ambiguous
    explanation: str = ""       # Translator's prose justification

class TranslationContext(BaseModel):  # frozen Pydantic v2
    capability_registry_summary: str
    concept_registry_summary: str
```

**LLMClient seam** (DEC-067): `LLMClient` is a concrete base class (not
`typing.Protocol`) with one method, `complete(system_prompt: str,
user_message: str) -> str`. The sole concrete child for MVP is
`AnthropicLLMClient`. Adding another provider means subclassing — no
architectural change. Tests stub the seam via `monkeypatch.setattr` on
the import-binding in the module under test, matching the project's
existing IoC pattern.

**Failure-mode wrapping** (DEC-070, H-H1H2-001): `AnthropicLLMClient.complete`
catches and wraps as `LLMUnavailable` only the *availability* + *auth* +
*5xx-server* exceptions: `APIConnectionError`, `APITimeoutError`,
`RateLimitError`, `AuthenticationError`, `PermissionDeniedError`,
`InternalServerError`. Other `anthropic.APIError` subclasses
(`BadRequestError`, `NotFoundError`, `UnprocessableEntityError`,
`ConflictError`) are translator-side request bugs, not availability
issues; they propagate raw and the route returns 500 `internal_error`.

**Constraints**:
- Must produce valid DSL syntax (parseable by the DSL parser).
- Must not invent DSL features that don't exist (the system prompt embeds
  `docs/agent/dsl-cookbook.md` which documents the full executable surface
  + the unsupported "Coming Soon" forms).
- Must surface ambiguity via `alternatives` rather than silently resolve
  it. (Verified by `test_nl_query_for_unsupported_form_surfaces_alternatives`.)
- The LLM receives the current capability registry + concept registry as
  context [DEC-003][DEC-006].
- No confidence-threshold gate (DEC-072): `confidence` is surfaced; the
  caller decides whether to execute. Filtering by confidence pre-empts
  user judgment without corpus-grounded basis (corpus-is-ground-truth
  charter, DEC-024).

**MVP implementation**: Single LLM call with a static system prompt
assembled at module import time from `docs/agent/dsl-cookbook.md` plus a
compile-only translator framing (DEC-071). No fine-tuning, no multi-turn
refinement. LLM provider: Anthropic Claude (DEC-067 confirms the MVP
technology stack pin).

**Output format protocol**: The system prompt instructs the LLM to emit
a structured response:
```
DSL: <one DSL string on a single line>
Confidence: <float in [0.0, 1.0]>
Alternatives:
- <optional alt 1>
- <optional alt 2>
Explanation: <one short sentence>
```
The translator extracts these fields with line-anchored regex. Missing
or empty `DSL:` line raises `NLCompileError`; missing optional fields
default to `confidence=1.0`, `alternatives=[]`, `explanation=""`. (Note:
the "default to 1.0 on missing" choice is recorded as an open question
for slice review — see thoughts/design-slice-h-nl-translator-2026-05-09.md
OQ-H4.)

**Dependency injection**: `LLMClient` and `TranslationContext` are
process-scoped resources constructed once during the FastAPI `lifespan`
async context manager (DEC-074). Lifespan reads `ANTHROPIC_API_KEY` and
`DATABASE_URL` independently — missing `ANTHROPIC_API_KEY` only disables
the NL route; the DSL route stays serviceable. Construction errors are
fail-fast (deployment problems should not be masked behind runtime 503).
Route handlers obtain the resources via `Depends(get_llm_client)` /
`Depends(get_translation_context)`.

**Concurrency**: same as §1 — sync `def` route handler, FastAPI offloads
to a thread pool. The Anthropic SDK has a sync interface that works
inside the thread pool offload.

**Testing**: unit tests mock `anthropic.Anthropic` at the SDK seam
(`unittest.mock.patch("src.nlp.llm_client.anthropic.Anthropic")`); they
do not consume API tokens. The slice exit gate
`tests/integration/test_app_nl_route_live_llm.py` runs against the live
LLM and is gated by both `integration` and `live_llm` markers, plus
runtime env-var assertions for `DATABASE_URL` and `ANTHROPIC_API_KEY`.
Default `pytest` excludes both markers.

**Response envelope**: `POST /api/v1/query/nl` returns `QueryNLResponse`
which subclasses `QueryDSLResponse` (DEC-069) and adds one field:
```python
class QueryNLResponse(QueryDSLResponse):
    translation: TranslationMetadata  # confidence, alternatives, explanation

class TranslationMetadata(BaseModel):  # frozen
    confidence: float
    alternatives: list[str]
    explanation: str
```
The `query` field carries the *compiled* DSL (what the corpus actually
saw), not the original NL — original NL is in the request body
(transparency rule, REQ:01).

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
def retrieve(
    plan: QueryPlan,
    scope: ScopeConstraint,
    engine: Engine,
    *,
    contextualize: bool = False,
    registry: ConceptRegistry | None = None,
) -> RetrievalResult

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
    registry: ConceptRegistry | None = None,
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
- (b) Every result set carries alternative-ordering counts for the same node-set, capped at `min(N!, 24)` permutations; for N ≥ 5, the cap-fallback is identity + reverse + (N − 1) adjacent pairwise swaps, truncated at 24.
- (c) A null-distribution slot is reserved on the envelope; MVP always sets it to `None` (sampling protocol pending future `/research` and `/design`).
- (d) The explainer (§9) must surface contextualization in user-facing output, not just the raw observed count.

**MVP implementation**: Direct SQL `COUNT(*)` against `tokens` for each node baseline (lemma direct; concept resolved via `ConceptRegistry.get_lemmas_for_concept` per `REQ:04.matching-rules`). Re-enters the pattern engine for each non-original permutation. Scope filters (`corpus_id`, `language`, `books`) carry into every baseline and alt-ordering query. Opt-in via the retrieval pipeline's `contextualize` flag (engine-layer default `False`; API/CLI consumer default `True`).

**Future**: Null-distribution sampling protocol (separate `/research` and `/design`); concept-baseline caching; cross-corpus baseline comparison.

<!-- REQ:09.result-explainer -->
### 9. Result Builder & Explainer
**Location**: `src/nlp/explainer.py`
**Responsibility**: Transform a `RetrievalResult` into user-facing results with deterministic prose explanations grounded in the actual corpus counts. The explainer is the contract realization for canonical-09 §8 invariant (d) — it surfaces contextualization in user-facing output. [DEC-015, DEC-061]

**Interface**:
```python
def explain(
    result: RetrievalResult,
    plan: QueryPlan,
    validation: ValidationResult,
) -> ExplainedResultSet

class ExplainedResultSet:
    query_shown: str                              # The DSL that was executed
    nl_source: str | None = None                  # Original NL if applicable
    validation_notes: list[str]                   # Validator findings as raw strings; empty when status=supported
    results: list[ExplainedResult]                # One entry per MatchCandidate in result.candidates
    contextualization: Contextualization | None = None  # Mirrors result.contextualization
    summary: str                                  # Slice-level prose (≤ 5 lines; see MVP implementation note below)

class ExplainedResult:
    reference: str                                # e.g., "1Cor 13:13"
    text_display: str                             # Comma-joined matched lemmas in corpus order
    match_type: Literal["exact", "variant", "conceptual"]
    score: float | None = None                    # Populated when scoring lands; None in MVP
    explanation: str                              # One-paragraph deterministic prose
```

**MVP implementation (DEC-061)**: Template-based explanation for ALL match types — including conceptual. The earlier canonical sentence "LLM explanation for conceptual matches or when results need qualification" is deferred. The deferral is tracked in a named bucket; trigger is "Slice H ships an LLM dependency for translation OR the deterministic explainer prose is judged inadequate against a real research question." Rationale: adding an LLM client solely for prose generation is overkill — the user has not yet seen a deterministic baseline against which to evaluate LLM upside, and Slice H (NL→DSL translator) is the natural owner of "first LLM dep in the project."

**Invariants**:
- (a) The signature consumes a `RetrievalResult` (not the canonical-pre-Slice-F `list[ScoredMatch]`). `ScoredMatch` is reserved for a future scoring slice; until then, `ExplainedResult.score` is `None`.
- (b) Every prose claim derives from fields on `result`, `plan`, or `validation` — never invented (DEC-024 corpus-is-ground-truth). Caller contract: `result.contextualization.observed_count` MUST equal `len(result.candidates)`; the explainer reads both fields and a divergence will produce internally-contradictory prose.
- (c) The explainer is purely deterministic and synchronous — no I/O, no LLM client, no environment-variable reads, no async (per DEC-061; verifiable via `grep -L "anthropic\|openai\|httpx\|asyncio" src/nlp/explainer.py`).
- (d) `validation_notes` is populated from `ValidationResult.findings` formatted as raw `"severity: code at path: message"` strings — same form `_print_findings` emits.
- (e) **Cap policy** (Bucket 4 closure): the explainer caps resolved-lemma display at 5 items with `"+N more"` suffix and sequence labels at 64 chars with ellipsis. The structured `_print_contextualization` block in `scripts/query.py` remains unbounded — that block is the data-fidelity view; the prose layer is where presentation discipline applies.

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
7. Retrieval pipeline assembles RetrievalResult (candidates + stages_used)
8. Contextualization computes per-node baselines, alternative-ordering counts,
   and reserved null-distribution slot; embeds Contextualization on
   RetrievalResult (skipped when retrieve() was called with contextualize=False)
9. Scoring ranks candidates within the result set
10. Explainer surfaces both per-match scores and the result-set Contextualization
    in user-facing output
11. API returns ExplainedResultSet as JSON
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
│   ├── pipeline.py           # Multi-stage retrieval orchestration (retrieve())
│   └── contextualization.py  # Per-node baselines + alternative-ordering counts
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
