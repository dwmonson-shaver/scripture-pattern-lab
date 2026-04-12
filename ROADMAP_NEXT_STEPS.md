# Roadmap — Next Steps

## Documentation Phase (Complete)

- [x] Define node ontology → `docs/canonical/04_node-ontology.md`
- [x] Define internal AST for the DSL → `docs/canonical/05_dsl-ast.md`
- [x] Define capability validator contract → `docs/canonical/06_capability-validator.md`
- [x] Define example query-to-AST transformations → `docs/canonical/07_query-to-ast-examples.md`
- [x] Choose MVP corpus scope → `docs/canonical/08_mvp-corpus-scope.md`
- [x] Sketch backend service boundaries → `docs/canonical/09_backend-service-boundaries.md`

## Implementation Phase (Next)

### 1. AST types and DSL parser
Define Python types for the AST (QueryPlan, SequenceExpr, NodeRef, etc.) and implement a recursive descent parser that compiles DSL text into these types. See docs 05 and 07.

### 2. Capability validator
Implement the 12 validation rules and partial plan reduction. See doc 06.

### 3. Corpus ingestion
Download MorphGNT data, parse it, load into Postgres. Seed the concept registry. See doc 08.

### 4. Pattern engine
SQL-based sequence search: given a validated QueryPlan and a Postgres token table, find matching sequences. See doc 09.

### 5. API layer
FastAPI routes for NL query, DSL query, validation, capabilities, and concept registry. See doc 09.

### 6. NL-to-DSL translation
LLM-based translation with DSL grammar and capability registry as context.

### 7. Result explanation
Template-based and LLM-assisted explanation of search results.

## DSL Version Roadmap
- **v0.1**: concepts, lemmas, ordered sequence, gaps, scope, polarity basics
- **v0.2**: inverse search, expansion, alternate orders, root and domain nodes
- **v0.3**: intertwined sequences, contrast pairs, structural templates
- **v0.4**: parallelism, discourse roles, cross-lingual mediation
