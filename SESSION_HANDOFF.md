# Session Handoff

## Where to begin

Start with `docs/canonical/04_node-ontology.md`.

The product foundation, query language draft, and system architecture notes are established in docs 01-03. The next intellectual work is defining the node ontology: how the system represents and distinguishes concept, domain, lexical realization, morphological category, and inverse candidates.

## Context

The node ontology is the type system that underpins everything else. The DSL's typed nodes (`lemma:pistis`, `concept:faith`, `root:AMN`, `domain:trust`) need a formal model that defines:
- what each node type means
- how node types relate to each other
- what operations are valid on each type
- how polarity and inverse relationships are modeled at the node level

This feeds directly into the AST design, the capability validator, and the pattern engine.

## Key constraints to carry forward
- Natural language compiles to DSL, never bypasses it
- The system must say when it cannot do something yet
- Symbolic retrieval is the core engine
- Polarity-aware and inverse-pattern analysis are foundational
- Results must distinguish match types (exact, conceptual, inverse, expanded, intertwined)
