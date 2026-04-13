# Capability Validator Contract

## Purpose
Define the interface, rules, and behavior of the capability validator — a first-class system component that stands between the DSL parser and the pattern engine. Every query plan must pass through validation before execution. The validator enforces the rule: the system must say "I can't do that yet" rather than fabricate unsupported analysis. [DEC-006][CONV-004]

## Design Principles
- The validator is a component, not a prompt — it runs deterministic checks, not AI inference
- It operates on the AST (QueryPlan), not on raw DSL text or natural language
- It must produce structured, actionable output — not just pass/fail
- It must be versioned in lockstep with the DSL and engine capabilities
- It must never silently drop unsupported features [DEC-003][DEC-006]

## Input and Output

### Input
A `QueryPlan` as defined in `05_dsl-ast.md`.

### Output
<!-- REQ:06.validation-result -->
A `ValidationResult`:

```
ValidationResult
├── status: "supported" | "partial" | "unsupported"
├── executablePlan: QueryPlan | null       # The portion that can run (null if fully unsupported)
├── findings: ValidationFinding[]          # Itemized list of issues
├── engineVersion: string                  # Engine capability version checked against
└── suggestion: ExtensionSuggestion | null # Developer-mode only
```

<!-- REQ:06.validation-finding -->
### ValidationFinding
Each finding describes one specific capability gap or concern.

```
ValidationFinding
├── severity: "error" | "warning" | "info"
├── code: string                           # Machine-readable code (e.g., "UNSUPPORTED_NODE_TYPE")
├── path: string                           # JSONPath into the QueryPlan (e.g., "sequence.steps[2]")
├── message: string                        # Human-readable explanation
├── remediation: string | null             # Suggested fix if available
```

## Validation Outcomes

### Supported
All features in the QueryPlan are supported by the current engine version. The full plan is executable.

**Response**: `status: "supported"`, `executablePlan` = original plan, no error-level findings.

### Partial
Some features are supported, others are not. The validator produces a reduced plan that can execute, alongside clear documentation of what was removed and why.

**Response**: `status: "partial"`, `executablePlan` = reduced plan, findings explain each removed feature.

**Example**: A query uses `root:אמן` nodes but the engine is at v0.1 (root nodes are v0.2). The validator strips root nodes, substitutes known lemma expansions if available, and reports what was lost.

### Unsupported
No meaningful portion of the query can execute under current capabilities.

**Response**: `status: "unsupported"`, `executablePlan` = null, findings explain why.

### Developer Mode Extension
In developer mode, the validator may additionally produce an `ExtensionSuggestion` — a structured proposal for what DSL/engine extension would be needed to support the query.

```
ExtensionSuggestion
├── requiredFeatures: string[]             # e.g., ["root_node_type", "cross_lingual_mediation"]
├── estimatedVersion: string               # e.g., "v0.2"
├── description: string                    # Human-readable explanation of the gap
```

<!-- REQ:06.capability-registry -->
## Capability Registry

The validator checks the QueryPlan against a `CapabilityRegistry` — a declarative manifest of what the engine currently supports.

```
CapabilityRegistry
├── version: string
├── nodeTypes: string[]                    # Supported node types
├── operators: string[]                    # Supported operator types
├── matchModes: string[]                   # Supported match modes
├── scopeFields: string[]                  # Supported scope constraint fields
├── maxSequenceLength: integer             # Max steps in a sequence
├── maxGap: integer | null                 # Max gap constraint
├── polaritySupport: boolean               # Is polarity matching available
├── inverseSupport: boolean                # Is inverse() resolution available
├── expansionSupport: boolean              # Are expansion directives available
├── compoundNodeSupport: boolean           # Are compound nodes available
├── corpora: string[]                      # Available corpus identifiers
├── languages: string[]                    # Available language codes
```

### MVP Capability Registry (v0.1)
```json
{
  "version": "0.1",
  "nodeTypes": ["token", "lemma", "concept", "morph", "wildcard"],
  "operators": ["precedence", "adjacency"],
  "matchModes": ["exact", "variant", "conceptual", "hybrid"],
  "scopeFields": ["corpus", "language", "books", "unit"],
  "maxSequenceLength": 10,
  "maxGap": null,
  "polaritySupport": true,
  "inverseSupport": false,
  "expansionSupport": false,
  "compoundNodeSupport": false,
  "corpora": ["nt"],
  "languages": ["grc"]
}
```

## Validation Rules

The validator applies the following checks in order:

<!-- REQ:06.rule-1 -->
### 1. Version compatibility
Check that `QueryPlan.version` is compatible with the engine version.

<!-- REQ:06.rule-2 -->
### 2. Node type support
For each `NodeRef` in the plan, verify `NodeRef.type` is in `CapabilityRegistry.nodeTypes`.

**Finding code**: `UNSUPPORTED_NODE_TYPE`

<!-- REQ:06.rule-3 -->
### 3. Operator support
For each `OrderOperator`, verify `OrderOperator.type` is in `CapabilityRegistry.operators`.

**Finding code**: `UNSUPPORTED_OPERATOR`

<!-- REQ:06.rule-4 -->
### 4. Gap constraint support
If any operator has a `GapConstraint`, verify gap constraints are supported and within `maxGap`.

**Finding code**: `UNSUPPORTED_GAP_CONSTRAINT`, `GAP_EXCEEDS_MAX`

<!-- REQ:06.rule-5 -->
### 5. Polarity support
If any `NodeRef` has a non-null polarity, verify `polaritySupport` is true.

**Finding code**: `UNSUPPORTED_POLARITY`

<!-- REQ:06.rule-6 -->
### 6. Inverse support
If the plan contains an `InverseExpr`, verify `inverseSupport` is true.

**Finding code**: `UNSUPPORTED_INVERSE`

<!-- REQ:06.rule-7 -->
### 7. Expansion support
If the plan has an `ExpansionDirective`, verify `expansionSupport` is true.

**Finding code**: `UNSUPPORTED_EXPANSION`

<!-- REQ:06.rule-8 -->
### 8. Compound node support
If any `NodeRef` has `morphFilters`, verify `compoundNodeSupport` is true.

**Finding code**: `UNSUPPORTED_COMPOUND_NODE`

<!-- REQ:06.rule-9 -->
### 9. Match mode support
Verify `QueryPlan.mode` is in `CapabilityRegistry.matchModes`.

**Finding code**: `UNSUPPORTED_MATCH_MODE`

<!-- REQ:06.rule-10 -->
### 10. Scope validation
Verify each scope field is supported. Verify corpus and language values exist in the registry.

**Finding codes**: `UNSUPPORTED_SCOPE_FIELD`, `UNKNOWN_CORPUS`, `UNKNOWN_LANGUAGE`

<!-- REQ:06.rule-11 -->
### 11. Sequence length
Verify the sequence length does not exceed `maxSequenceLength`.

**Finding code**: `SEQUENCE_TOO_LONG`

<!-- REQ:06.rule-12 -->
### 12. Structural validation
Verify the AST is well-formed: no empty sequences, no orphaned operators, no invalid compound combinations.

**Finding codes**: `EMPTY_SEQUENCE`, `MALFORMED_AST`, `INVALID_COMPOUND`

<!-- REQ:06.partial-reduction -->
## Partial Plan Reduction

When the status is `partial`, the validator must produce a reduced `executablePlan`. Reduction rules:

1. **Unsupported node type**: If a substitution is possible (e.g., expand `root:אמן` to known lemmas), substitute and add an info finding. If no substitution exists, remove the step and add a warning.
2. **Unsupported operator**: Downgrade to the nearest supported operator (e.g., `cooccurrence` → `precedence`) and add a warning.
3. **Unsupported features**: Strip the unsupported feature (expansion, inverse wrapper, compound filters) and add a warning for each.
4. **If stripping reduces the sequence to fewer than 2 steps**: Mark as `unsupported` instead of `partial`.

## Integration Points

### NL-to-DSL Pipeline
```
User NL → AI translator → DSL string → Parser → QueryPlan → Validator → Engine
                                                     │
                                                     └→ ValidationResult (returned to user if not fully supported)
```

### User-Facing Behavior
- **Supported**: Execute and return results
- **Partial**: Show the user what will run, what was excluded, and why. Ask for confirmation before executing the reduced plan.
- **Unsupported**: Explain what the system cannot do yet. In developer mode, show the extension suggestion.

## Versioning
- **v0.1** (MVP): All 12 validation rules. Capability registry for MVP node types/operators. Basic partial reduction (strip unsupported, no smart substitution).
- **v0.2**: Smart substitution for root→lemma expansion. Inverse and expansion validation. Compound node validation.
- **v0.3**: Structural template validation. Intertwined sequence validation.

## Confidence and Volatility
- Confidence: Medium-High
- Volatility: Medium

## References
- Decisions: DEC-003, DEC-006
- Evidence: CONV-004
- Prior docs: 04_node-ontology.md, 05_dsl-ast.md
