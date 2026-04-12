# Roadmap — Next Steps

## Immediate Priorities

### 1. Define node ontology
Specify the type system for query nodes: how concept, domain, lexical realization, inverse candidates, and morphological categories relate to each other. This is the foundation for the DSL and the pattern engine.

### 2. Define internal AST for the DSL
Design the abstract syntax tree that the DSL compiles into. This is what the pattern engine actually executes against — the bridge between human-readable query syntax and deterministic search.

### 3. Define capability validator contract
Specify the interface and rules for the capability validator: what it checks, what outcomes it produces (full support, partial support, unsupported, developer-mode extension suggestion), and how it integrates with the NL-to-DSL pipeline.

### 4. Define example query-to-AST transformations
Work through concrete examples showing how DSL queries map to AST structures. This validates the AST design and surfaces edge cases before implementation.

### 5. Choose MVP corpus scope
Decide whether to start with Greek NT, Hebrew Bible, or a narrower slice. This affects data modeling, ingestion, and what queries are testable early.

### 6. Sketch backend service boundaries
Define the service topology: what runs where, what talks to what, and where the boundaries are between the pattern engine, retrieval pipeline, AI layer, and API surface.

## DSL Version Roadmap
- **v0.1**: concepts, lemmas, ordered sequence, gaps, scope, polarity basics
- **v0.2**: inverse search, expansion, alternate orders
- **v0.3**: intertwined sequences, contrast pairs, structural templates
- **v0.4**: parallelism, discourse roles, cross-lingual mediation
