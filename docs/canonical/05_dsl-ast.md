# DSL Abstract Syntax Tree

## Purpose
Define the internal representation that DSL query strings compile into. The AST is the contract between the parser (which reads DSL syntax) and the pattern engine (which executes searches). No query reaches the engine except through this structure. [DEC-003][DEC-009]

## Design Principles
- The AST must be a complete, unambiguous representation of any valid DSL query
- It must be serializable (for logging, caching, and debugging)
- It must be validatable by the capability validator before execution
- It must be composable — subqueries and expansions build on the same node types
- The AST is the single source of truth for what a query means; the surface syntax is sugar [DEC-006][DEC-008]

## Top-Level Structure

<!-- REQ:05.query-plan -->
Every compiled query produces a `QueryPlan`:

```
QueryPlan
├── version: string              # DSL version (e.g., "0.1")
├── source: string               # Original DSL text
├── sequence: SequenceExpr       # The core pattern expression
├── scope: ScopeConstraint       # Corpus, book, language, structural unit
├── mode: MatchMode              # exact | variant | conceptual | hybrid
├── expansion: ExpansionDirective | null
├── ranking: RankingPrefs | null
└── metadata: QueryMetadata      # parse timestamp, NL source if applicable
```

## Expression Nodes

<!-- REQ:05.sequence-expr -->
### SequenceExpr
An ordered list of steps with order operators between them.

```
SequenceExpr
├── steps: StepExpr[]            # Ordered list of pattern steps
└── operators: OrderOperator[]   # Operators between adjacent steps (length = steps.length - 1)
```

<!-- REQ:05.step-expr -->
### StepExpr
A single position in the sequence. One of:

- **NodeRef** — a typed node reference
- **GroupExpr** — a parenthesized sub-expression
- **AlternativeExpr** — a choice between options
- **OptionalExpr** — an optional step

<!-- REQ:05.node-ref -->
### NodeRef
A reference to a node in the ontology, optionally with polarity and morph filters.

```
NodeRef
├── type: "token" | "lemma" | "root" | "concept" | "domain" | "morph" | "wildcard"
├── value: string                # The node value (e.g., "pistis", "faith", "אמן")
├── polarity: "+" | "-" | "±" | null
├── morphFilters: MorphFilter[]  # Compound constraints (e.g., morph:NOUN)
└── negated: boolean             # True if preceded by ! (exclusion)
```

<!-- REQ:05.group-expr -->
### GroupExpr
A parenthesized sub-sequence, treated as a single step.

```
GroupExpr
├── sequence: SequenceExpr       # The grouped sub-expression
└── negated: boolean
```

<!-- REQ:05.alternative-expr -->
### AlternativeExpr
A choice between two or more options at a single step position.

```
AlternativeExpr
├── options: StepExpr[]          # Two or more alternatives
└── negated: boolean
```

<!-- REQ:05.optional-expr -->
### OptionalExpr
A step that may or may not be present in a match.

```
OptionalExpr
├── inner: StepExpr              # The optional content
```

## Operators

<!-- REQ:05.order-operator -->
### OrderOperator
Defines the relationship between adjacent steps.

```
OrderOperator
├── type: "precedence" | "adjacency" | "cooccurrence"
├── gap: GapConstraint | null    # Only for precedence
```

Mapping from DSL surface syntax:
- `>` → `precedence` (ordered, with optional gap)
- `>>` → `adjacency` (immediate or minimal gap)
- `~` → `cooccurrence` (unordered nearby)

<!-- REQ:05.gap-constraint -->
### GapConstraint
Limits the distance between two steps.

```
GapConstraint
├── min: integer                 # Minimum tokens between steps (default 0)
├── max: integer | null          # Maximum tokens between steps (null = unbounded)
```

DSL syntax `>{0,5}` compiles to `GapConstraint { min: 0, max: 5 }`.

## Scope

<!-- REQ:05.scope-constraint -->
### ScopeConstraint
Defines the search boundaries.

```
ScopeConstraint
├── corpus: string | null        # e.g., "nt", "ot", "lxx"
├── language: string | null      # e.g., "grc", "heb", "arc"
├── books: string[] | null       # e.g., ["1cor", "rom"]
├── unit: ScopeUnit | null       # discriminated union — see below
```

### ScopeUnit (Slice L)

`ScopeUnit` is a discriminated union (Pydantic v2; tag field `kind`). Two
siblings ship today; future slices add the rest:

```
ScopeUnit = ScopeUnitVerse | ScopeUnitWindow

ScopeUnitVerse
└── kind: "verse"                # single-verse boundary (legacy MVP unit)

ScopeUnitWindow
├── kind: "window"
└── n: int                       # 1 ≤ n ≤ CapabilityRegistry.window_max_tokens
                                 # window of n tokens, anchored on first match
```

Surface syntax:

- `within:verse` → `ScopeUnitVerse()`
- `within:window(N)` → `ScopeUnitWindow(n=N)`. `window(0)` is rejected at
  parse time; `n > window_max_tokens` is rejected by validator rule 10
  (`WINDOW_EXCEEDS_MAX`).

Window execution (Slice L): anchored on the first matched token's
`global_position`; every subsequent step lands in `[base.gp, base.gp + n]`
within the same `book`. Book boundaries are blocked (different authors /
scrolls); chapter boundaries are crossable (editorial overlay).

`clause`, `sentence`, `pericope`, `chapter` parsed into the prior `StrEnum`
but were inert at execute time; in Slice L they fail at parse time. Future
slices that ship these units will add the corresponding `ScopeUnit*`
sibling.

## Match Mode

<!-- REQ:05.match-mode -->
```
MatchMode: "exact" | "variant" | "conceptual" | "hybrid"
```

- **exact**: Only token/lemma-level matches
- **variant**: Lemma + morphological variants
- **conceptual**: Concept-level matching (expands via concept registry)
- **hybrid**: All of the above, ranked by specificity

## Expansion

<!-- REQ:05.expansion-directive -->
### ExpansionDirective
Instructs the engine to explore beyond the stated sequence.

```
ExpansionDirective
├── direction: "forward" | "backward" | "both"
├── depth: integer               # Number of positions to explore
```

DSL syntax mapping:
- `=> forward:2` → `ExpansionDirective { direction: "forward", depth: 2 }`
- `=> expand:2` → `ExpansionDirective { direction: "both", depth: 2 }`

## Ranking

<!-- REQ:05.ranking-prefs -->
### RankingPrefs
Optional user-specified ranking preferences.

```
RankingPrefs
├── weights: Map<RankingFactor, float>
```

Where `RankingFactor` is one of:
- `lexical_alignment`
- `morphology_alignment`
- `semantic_overlap`
- `polarity_fidelity`
- `rarity`
- `contextual_coherence`

Default weights are engine-defined when RankingPrefs is null.

## Polarity in the AST

<!-- REQ:05.inverse-expr -->
### InverseExpr
The `inverse()` function in the DSL compiles to a wrapper that instructs the engine to resolve all nodes to their inverse-pole equivalents.

```
InverseExpr
├── inner: SequenceExpr          # The sequence to invert
```

`inverse(faith > hope > love)` compiles to:
```
InverseExpr {
  inner: SequenceExpr {
    steps: [
      NodeRef { type: "concept", value: "faith", polarity: null },
      NodeRef { type: "concept", value: "hope", polarity: null },
      NodeRef { type: "concept", value: "love", polarity: null }
    ],
    operators: [precedence, precedence]
  }
}
```

The engine resolves each node's inverse at execution time via the concept registry.

## Compilation Examples

### Simple sequence
**DSL**: `faith > hope > love`
```
QueryPlan {
  sequence: SequenceExpr {
    steps: [
      NodeRef { type: "concept", value: "faith" },
      NodeRef { type: "concept", value: "hope" },
      NodeRef { type: "concept", value: "love" }
    ],
    operators: [precedence, precedence]
  },
  scope: ScopeConstraint { ... },
  mode: "conceptual"
}
```

### Typed nodes with gap constraint
**DSL**: `lemma:pistis >{0,3} lemma:elpis > lemma:agape within:verse lang:grc`
```
QueryPlan {
  sequence: SequenceExpr {
    steps: [
      NodeRef { type: "lemma", value: "pistis" },
      NodeRef { type: "lemma", value: "elpis" },
      NodeRef { type: "lemma", value: "agape" }
    ],
    operators: [
      precedence { gap: { min: 0, max: 3 } },
      precedence { gap: null }
    ]
  },
  scope: ScopeConstraint { language: "grc", unit: "verse" },
  mode: "exact"
}
```

### Polarity with alternatives and expansion
**DSL**: `+concept:faith > +(concept:hope | concept:expectation) > +concept:love => forward:2`
```
QueryPlan {
  sequence: SequenceExpr {
    steps: [
      NodeRef { type: "concept", value: "faith", polarity: "+" },
      AlternativeExpr {
        options: [
          NodeRef { type: "concept", value: "hope", polarity: "+" },
          NodeRef { type: "concept", value: "expectation", polarity: "+" }
        ]
      },
      NodeRef { type: "concept", value: "love", polarity: "+" }
    ],
    operators: [precedence, precedence]
  },
  expansion: ExpansionDirective { direction: "forward", depth: 2 },
  mode: "conceptual"
}
```

### Inverse query
**DSL**: `inverse(faith > hope > love) within:verse corpus:nt`
```
QueryPlan {
  sequence: InverseExpr {
    inner: SequenceExpr {
      steps: [
        NodeRef { type: "concept", value: "faith" },
        NodeRef { type: "concept", value: "hope" },
        NodeRef { type: "concept", value: "love" }
      ],
      operators: [precedence, precedence]
    }
  },
  scope: ScopeConstraint { corpus: "nt", unit: "verse" },
  mode: "conceptual"
}
```

## Validation Contract Surface

The capability validator receives a `QueryPlan` and checks each node against the current engine capabilities. The AST makes this straightforward because every feature is explicitly represented as a typed structure rather than embedded in free text. See `06_capability-validator.md` for the full contract.

<!-- REQ:05.serialization -->
## Serialization

The AST must be serializable to JSON for:
- Logging (what query was actually executed)
- Caching (have we seen this exact plan before)
- Debugging (show the user what their NL compiled into)
- Comparison (diff two query plans)

The structures defined above map directly to JSON objects.

## Versioning
- **v0.1** (MVP): SequenceExpr, NodeRef (token, lemma, concept, morph, wildcard), OrderOperator (precedence, adjacency), ScopeConstraint, MatchMode, basic polarity on NodeRef
- **v0.2**: Root and domain node types, GapConstraint, CooccurrenceOperator, InverseExpr, ExpansionDirective, AlternativeExpr, OptionalExpr, compound morph filters
- **v0.3**: GroupExpr nesting, structural template references, intertwined sequence operators
- **v0.4**: Cross-lingual mediation nodes, discourse-role nodes

## Open Questions
1. Should the AST support named subqueries for reuse within a single plan?
2. How should `supersequence()` be represented — as an expansion directive or a distinct wrapper?
3. Should ranking preferences live in the AST or be a separate execution-time concern?

## Confidence and Volatility
- Confidence: Medium
- Volatility: High

## References
- Decisions: DEC-003, DEC-006, DEC-008, DEC-009
- Prior docs: 02_query-language-draft.md, 04_node-ontology.md
