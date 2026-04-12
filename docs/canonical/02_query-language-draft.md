# Query Language Draft

## Goal
Create a readable but formal domain-specific language for expressing sequence hypotheses across lexical, conceptual, structural, and polarity dimensions. [CONV-002][CONV-004][DEC-008]

## Design Principles
- readable for non-programmers
- layered from simple to advanced
- deterministic and validated before execution
- extensible through versioned roadmap growth
- inspectable through visible generated queries and execution plans [CONV-002][CONV-004]

## Core Model
The DSL represents sequence graphs, not bag-of-words search. A query declares:
- nodes
- order relations
- alternatives or optional elements
- gaps or windows
- scope
- polarity
- exploration directives
- ranking preferences [CONV-002][DEC-009]

## MVP Syntax Surface
### Simple sequence
`faith > hope > love`

### Typed nodes
- `lemma:pistis`
- `concept:faith`
- `root:אמן`
- `morph:NOUN`
- `domain:trust`

### Operators
- `>` ordered precedence
- `>>` immediate adjacency or minimal gap
- `~` unordered nearby co-occurrence
- `|` alternatives
- `[]` optional node
- `!` exclusion
- `()` grouping [CONV-002]

### Constraints
- `>{0,5}` gap constraints
- `within:verse`
- `within:clause`
- `lang:grc`
- `corpus:nt`
- `book:1cor`
- `mode:exact|variant|conceptual|hybrid` [CONV-002][DEC-010]

### Polarity features
- `+faith > +hope > +love`
- `-faith > -hope > -love`
- `inverse(faith > hope > love)`
- `±faith > ±hope > ±love` [CONV-003][DEC-011]

### Expansion features
- `faith > hope > love => forward:2`
- `faith > hope > love => backward:2`
- `faith > hope > love => expand:2`
- `supersequence(faith > hope > love)` [CONV-001][DEC-004]

## Natural Language Translation Requirement
The AI should accept natural language and compile it into formal DSL. The generated DSL should be visible and editable. The engine should never silently exceed current DSL support. [CONV-004][DEC-003][DEC-006]

## Validation Behavior
Every generated query must be checked by a capability validator against:
- supported node types
- supported operators
- supported scopes
- supported polarity logic
- supported analysis modes
- supported corpora/languages [CONV-004][DEC-006]

### Supported outcomes
- full support: run query
- partial support: run supported subset and explain missing capability
- unsupported: state inability clearly
- developer mode: optionally recommend next syntax extension [CONV-004]

## Versioning Guidance
- DSL v0.1: concepts, lemmas, ordered sequence, gaps, scope, polarity basics
- DSL v0.2: inverse search, expansion, alternate orders
- DSL v0.3: intertwined sequences, contrast pairs, structural templates
- DSL v0.4: parallelism, discourse roles, cross-lingual mediation [CONV-004][ASM-004]

## Open Edges
- how to represent structural templates cleanly
- how to expose ranking weights without harming usability
- how to balance simple-mode UI with advanced-mode power
- how to represent braided or intertwined sequences in a readable way

## Confidence and Volatility
- Confidence: High
- Volatility: High

## References
- Decisions: DEC-003, DEC-004, DEC-006, DEC-008, DEC-009, DEC-010, DEC-011
- Evidence: CONV-001, CONV-002, CONV-003, CONV-004
- Assumptions: ASM-004
