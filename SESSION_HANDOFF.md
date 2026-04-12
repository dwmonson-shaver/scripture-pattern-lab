# Session Handoff

## Where to begin

Start implementing. The canonical documentation (9 docs) is complete. Begin with the code.

## What's ready

All design specs are written and committed:
- **01-03**: Product foundation, query language draft, system architecture notes
- **04**: Node ontology — type system for query nodes
- **05**: DSL AST — internal representation for compiled queries
- **06**: Capability validator — validation rules and contract
- **07**: Query-to-AST examples — 8 worked examples with validation outcomes
- **08**: MVP corpus scope — Greek NT (SBLGNT/MorphGNT), concept registry, DB schema
- **09**: Backend service boundaries — component topology, interfaces, directory mapping

## Implementation priorities

1. **AST types** (`src/engine/models.py`) — Define the Python dataclasses/Pydantic models for QueryPlan, SequenceExpr, NodeRef, etc. from doc 05.
2. **DSL parser** (`src/engine/parser.py`) — Recursive descent parser that produces QueryPlan from DSL text.
3. **Capability validator** (`src/validation/`) — Implement the 12 validation rules from doc 06.
4. **Corpus ingestion** (`scripts/ingest/`) — Download MorphGNT, parse, load into Postgres per doc 08.
5. **Pattern engine** (`src/engine/executor.py`) — SQL-based sequence search against tokens table.
6. **API routes** (`src/app/`) — FastAPI endpoints per doc 09.
7. **NL-to-DSL translator** (`src/nlp/translator.py`) — LLM-based translation.

## Key constraints to carry forward
- Natural language compiles to DSL, never bypasses it
- The system must say when it cannot do something yet
- Symbolic retrieval is the core engine
- Polarity-aware and inverse-pattern analysis are foundational
- Results must distinguish match types (exact, conceptual, inverse, expanded, intertwined)
- MVP is monolith-first — all components in one FastAPI process
