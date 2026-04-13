# Node Ontology

## Purpose
Define the type system for query nodes in the Scripture Pattern Lab DSL. Every node in a query graph has a type that determines what it matches, how it relates to other nodes, and what operations are valid on it. This document is the authoritative specification for node types, their semantics, and their relationships. [CONV-002][DEC-009][DEC-010]

## Design Principles
- Node types must be explicit and unambiguous — no implicit type coercion
- The ontology must support polarity at the node level, not only at the query level
- Relationships between node types (e.g., lemma realizes concept) must be declared, not inferred at runtime
- The ontology must be extensible through versioned additions without breaking existing queries
- Every node type must have a clear matching rule against corpus data [DEC-008][DEC-011]

## Node Types

<!-- REQ:04.node-lemma -->
### 1. Lemma
A dictionary headword in a specific language.

- **Syntax**: `lemma:pistis`, `lemma:אמן`
- **Matches**: All tokens in the corpus whose lemma matches the specified form
- **Language**: Inherited from the lemma itself or constrained by `lang:` scope
- **Granularity**: Exact lexical identity
- **Example**: `lemma:pistis` matches every inflected form of πίστις in a Greek corpus

<!-- REQ:04.node-root -->
### 2. Root
A consonantal or morphological root underlying one or more lemmas.

- **Syntax**: `root:אמן`, `root:πιστ`
- **Matches**: All tokens whose lemma derives from the specified root
- **Scope**: Broader than lemma — a single root may underlie multiple lemmas
- **Example**: `root:אמן` matches forms derived from the root א-מ-ן including אֱמוּנָה, אָמֵן, נֶאֱמָן

<!-- REQ:04.node-concept -->
### 3. Concept
A language-independent semantic concept that may be realized by multiple lemmas across languages.

- **Syntax**: `concept:faith`, `concept:trust`, `concept:hope`
- **Matches**: All tokens whose lemma is mapped to the specified concept in the concept registry
- **Resolution**: Requires a maintained concept-to-lemma mapping table
- **Example**: `concept:faith` might resolve to `lemma:pistis` (Greek), `lemma:אֱמוּנָה` (Hebrew), and others depending on the mapping

<!-- REQ:04.node-domain -->
### 4. Domain
A broader semantic field grouping multiple related concepts.

- **Syntax**: `domain:trust`, `domain:covenant`, `domain:eschatology`
- **Matches**: All tokens whose lemma maps to any concept within the specified domain
- **Resolution**: Requires a domain-to-concept mapping layer above the concept registry
- **Scope**: Broader than concept — `domain:trust` might include concepts like faith, faithfulness, reliability, belief
- **Example**: `domain:trust` expands to `{concept:faith, concept:faithfulness, concept:reliability, concept:belief, ...}`

<!-- REQ:04.node-morph -->
### 5. Morphology
A morphological feature or category.

- **Syntax**: `morph:NOUN`, `morph:VERB`, `morph:IMPERATIVE`, `morph:PARTICIPLE`
- **Matches**: All tokens whose morphological parse includes the specified feature
- **Combinable**: Can be combined with other node types as a filter (see Compound Nodes below)
- **Example**: `morph:IMPERATIVE` matches all imperative verb forms in scope

<!-- REQ:04.node-token -->
### 6. Token
A specific surface form as it appears in the text.

- **Syntax**: `token:πίστει`, `token:באמונה`
- **Matches**: Exact surface-form match in the corpus
- **Granularity**: Most specific — matches only the exact inflected/pointed form
- **Use case**: When the user wants to search for a precise textual form rather than a lemma or concept

<!-- REQ:04.node-wildcard -->
### 7. Wildcard
A placeholder node that matches any single token position.

- **Syntax**: `*`
- **Matches**: Any one token
- **Use case**: Structural pattern matching where specific content at a position is unknown
- **Example**: `faith > * > love` matches any three-token sequence where faith and love bookend an arbitrary middle token

<!-- REQ:04.node-hierarchy -->
## Node Type Hierarchy

The node types form a specificity hierarchy from narrow to broad:

```
token           (exact surface form)
  └─ lemma      (dictionary headword)
      └─ root   (morphological root family)
      └─ concept (semantic equivalence class)
          └─ domain (semantic field)

morph           (orthogonal feature axis — filters, not containers)
wildcard        (structural placeholder)
```

- Moving down the hierarchy broadens the match set
- `token` is a specific inflection of a `lemma`
- A `lemma` may belong to a `root` family AND realize one or more `concept`s
- A `concept` may belong to one or more `domain`s
- `morph` is orthogonal: it constrains by grammatical feature, not by meaning
- `wildcard` is maximally broad within structural constraints

<!-- REQ:04.compound-nodes -->
## Compound Nodes

Nodes can be combined to create intersection constraints:

- **Syntax**: `lemma:pistis+morph:NOUN` — match πίστις only in noun forms
- **Syntax**: `concept:faith+morph:VERB` — match any faith-concept lemma only in verb forms
- **Semantics**: Compound nodes are conjunctions — all constraints must be satisfied simultaneously
- **Restriction**: Compounds combine a content node (token, lemma, root, concept, domain) with one or more morph filters. Two content nodes in a compound is invalid (use alternatives `|` instead).

<!-- REQ:04.polarity -->
## Polarity at the Node Level

Each content node can carry a polarity marker: [DEC-005][DEC-011]

- `+concept:faith` — positive pole (faith, trust, belief)
- `-concept:faith` — negative pole (inverse: unbelief, distrust, doubt)
- `±concept:faith` — either pole (matches both positive and negative realizations)
- No marker — polarity-unaware (matches without regard to polarity classification)

### Polarity Resolution
Polarity is resolved through the concept registry. Each concept entry declares:
- its default polarity (positive or negative)
- its inverse concept(s), if any
- its polarity-group membership

Example registry entries:
```
concept:faith       polarity:+  inverse:[concept:unbelief, concept:doubt]  group:trust-polarity
concept:unbelief    polarity:-  inverse:[concept:faith]                    group:trust-polarity
concept:doubt       polarity:-  inverse:[concept:faith, concept:certainty] group:trust-polarity
```

When the query contains `-concept:faith`, the engine resolves it to the set of inverse concepts: `{concept:unbelief, concept:doubt}`.

When the query contains `±concept:faith`, the engine matches both `concept:faith` and its inverses.

### Polarity and Domains
Domains inherit polarity behavior from their constituent concepts. `+domain:trust` matches all positive-pole concepts in the trust domain. `-domain:trust` matches all negative-pole concepts.

<!-- REQ:04.matching-rules -->
## Node Matching Rules

| Node Type | Corpus Field Matched | Resolution Layer |
|-----------|---------------------|-----------------|
| token     | surface form        | direct          |
| lemma     | lemma annotation    | direct          |
| root      | root annotation     | root-to-lemma index |
| concept   | lemma annotation    | concept-to-lemma registry |
| domain    | lemma annotation    | domain-to-concept-to-lemma registry |
| morph     | morphology parse    | direct          |
| wildcard  | (any)               | structural      |

## Data Requirements

This ontology depends on the following data layers existing in the corpus:

1. **Token-level annotations**: surface form, lemma, root, morphological parse
2. **Concept registry**: concept-to-lemma mappings with polarity metadata
3. **Domain registry**: domain-to-concept groupings
4. **Root index**: root-to-lemma derivation mappings

For MVP, the concept and domain registries will be manually curated for the initial corpus scope, with AI-assisted expansion as a later capability. [DEC-020]

## Versioning

- **v0.1** (MVP): token, lemma, concept, morph, wildcard. Basic polarity on concept nodes.
- **v0.2**: root nodes. Domain nodes. Compound nodes. Full polarity with inverse resolution.
- **v0.3**: Discourse-role nodes (e.g., `role:subject`, `role:predicate`). Structural template nodes.
- **v0.4**: Cross-lingual mediation nodes for MT/LXX/NT alignment.

## Open Questions
1. Should concept-to-lemma mappings be versioned independently of the DSL version?
2. How should ambiguous polarity be handled (lemmas that can carry either pole depending on context)?
3. Should domain membership be exclusive or overlapping (can a concept belong to multiple domains)?
4. What is the minimum viable concept registry size for a useful MVP?

## Confidence and Volatility
- Confidence: Medium-High
- Volatility: Medium

## References
- Decisions: DEC-005, DEC-008, DEC-009, DEC-010, DEC-011, DEC-020
- Evidence: CONV-001, CONV-002, CONV-003
- Prior docs: 01_product-foundation.md, 02_query-language-draft.md, 03_system-architecture-notes.md
