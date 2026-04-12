# Query-to-AST Transformation Examples

## Purpose
Demonstrate how DSL surface syntax compiles into AST structures (as defined in `05_dsl-ast.md`) and how the capability validator (as defined in `06_capability-validator.md`) evaluates each plan. These examples validate the AST design and serve as a reference for parser implementors.

## Example 1: Simple Concept Sequence

### DSL
```
faith > hope > love
```

### Default resolution
Bare words without a type prefix are resolved as `concept:` nodes by the parser.

### AST
```json
{
  "version": "0.1",
  "source": "faith > hope > love",
  "sequence": {
    "type": "SequenceExpr",
    "steps": [
      { "type": "NodeRef", "nodeType": "concept", "value": "faith", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "concept", "value": "hope", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "concept", "value": "love", "polarity": null, "morphFilters": [], "negated": false }
    ],
    "operators": [
      { "type": "precedence", "gap": null },
      { "type": "precedence", "gap": null }
    ]
  },
  "scope": { "corpus": null, "language": null, "books": null, "unit": null },
  "mode": "conceptual",
  "expansion": null,
  "ranking": null,
  "metadata": { "nlSource": null }
}
```

### Validation (v0.1)
**Status**: `supported` — concept nodes, precedence operators, and conceptual mode are all in the MVP capability registry.

---

## Example 2: Typed Lemma Query with Gap and Scope

### DSL
```
lemma:pistis >{0,3} lemma:elpis > lemma:agape within:verse lang:grc corpus:nt
```

### AST
```json
{
  "version": "0.1",
  "source": "lemma:pistis >{0,3} lemma:elpis > lemma:agape within:verse lang:grc corpus:nt",
  "sequence": {
    "type": "SequenceExpr",
    "steps": [
      { "type": "NodeRef", "nodeType": "lemma", "value": "pistis", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "lemma", "value": "elpis", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "lemma", "value": "agape", "polarity": null, "morphFilters": [], "negated": false }
    ],
    "operators": [
      { "type": "precedence", "gap": { "min": 0, "max": 3 } },
      { "type": "precedence", "gap": null }
    ]
  },
  "scope": { "corpus": "nt", "language": "grc", "books": null, "unit": "verse" },
  "mode": "exact",
  "expansion": null,
  "ranking": null,
  "metadata": { "nlSource": null }
}
```

### Validation (v0.1)
**Status**: `supported` — lemma nodes, precedence operators, gap constraints, and all scope fields are in the MVP registry. Mode defaults to `exact` for typed lemma queries.

---

## Example 3: Polarity-Marked Concept Query

### DSL
```
+concept:faith > +concept:hope > +concept:love within:verse corpus:nt
```

### AST
```json
{
  "version": "0.1",
  "source": "+concept:faith > +concept:hope > +concept:love within:verse corpus:nt",
  "sequence": {
    "type": "SequenceExpr",
    "steps": [
      { "type": "NodeRef", "nodeType": "concept", "value": "faith", "polarity": "+", "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "concept", "value": "hope", "polarity": "+", "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "concept", "value": "love", "polarity": "+", "morphFilters": [], "negated": false }
    ],
    "operators": [
      { "type": "precedence", "gap": null },
      { "type": "precedence", "gap": null }
    ]
  },
  "scope": { "corpus": "nt", "language": null, "books": null, "unit": "verse" },
  "mode": "conceptual",
  "expansion": null,
  "ranking": null,
  "metadata": { "nlSource": null }
}
```

### Validation (v0.1)
**Status**: `supported` — polarity on concept nodes is supported in MVP. The engine filters matches to positive-pole realizations only.

---

## Example 4: Alternatives and Optional Nodes

### DSL
```
concept:faith > (concept:hope | concept:expectation) > [concept:endurance] > concept:love
```

### AST
```json
{
  "version": "0.1",
  "source": "concept:faith > (concept:hope | concept:expectation) > [concept:endurance] > concept:love",
  "sequence": {
    "type": "SequenceExpr",
    "steps": [
      { "type": "NodeRef", "nodeType": "concept", "value": "faith", "polarity": null, "morphFilters": [], "negated": false },
      {
        "type": "AlternativeExpr",
        "options": [
          { "type": "NodeRef", "nodeType": "concept", "value": "hope", "polarity": null, "morphFilters": [], "negated": false },
          { "type": "NodeRef", "nodeType": "concept", "value": "expectation", "polarity": null, "morphFilters": [], "negated": false }
        ],
        "negated": false
      },
      {
        "type": "OptionalExpr",
        "inner": { "type": "NodeRef", "nodeType": "concept", "value": "endurance", "polarity": null, "morphFilters": [], "negated": false }
      },
      { "type": "NodeRef", "nodeType": "concept", "value": "love", "polarity": null, "morphFilters": [], "negated": false }
    ],
    "operators": [
      { "type": "precedence", "gap": null },
      { "type": "precedence", "gap": null },
      { "type": "precedence", "gap": null }
    ]
  },
  "scope": { "corpus": null, "language": null, "books": null, "unit": null },
  "mode": "conceptual",
  "expansion": null,
  "ranking": null,
  "metadata": { "nlSource": null }
}
```

### Validation (v0.1)
**Status**: `supported` — AlternativeExpr and OptionalExpr use only concept nodes and precedence operators, all within MVP scope.

---

## Example 5: Inverse Query

### DSL
```
inverse(faith > hope > love) within:verse corpus:nt
```

### AST
```json
{
  "version": "0.1",
  "source": "inverse(faith > hope > love) within:verse corpus:nt",
  "sequence": {
    "type": "InverseExpr",
    "inner": {
      "type": "SequenceExpr",
      "steps": [
        { "type": "NodeRef", "nodeType": "concept", "value": "faith", "polarity": null, "morphFilters": [], "negated": false },
        { "type": "NodeRef", "nodeType": "concept", "value": "hope", "polarity": null, "morphFilters": [], "negated": false },
        { "type": "NodeRef", "nodeType": "concept", "value": "love", "polarity": null, "morphFilters": [], "negated": false }
      ],
      "operators": [
        { "type": "precedence", "gap": null },
        { "type": "precedence", "gap": null }
      ]
    }
  },
  "scope": { "corpus": "nt", "language": null, "books": null, "unit": "verse" },
  "mode": "conceptual",
  "expansion": null,
  "ranking": null,
  "metadata": { "nlSource": null }
}
```

### Validation (v0.1)
**Status**: `unsupported` — `inverseSupport` is false in the v0.1 capability registry.

**Findings**:
```json
[
  {
    "severity": "error",
    "code": "UNSUPPORTED_INVERSE",
    "path": "sequence",
    "message": "inverse() queries are not supported in engine v0.1. Inverse resolution is planned for v0.2.",
    "remediation": "Remove the inverse() wrapper and manually specify negative-pole concepts, or use polarity markers (-concept:faith) on individual nodes."
  }
]
```

**User-facing message**: "The system cannot yet run inverse sequence queries. This feature is planned for v0.2. You can approximate this by querying for specific negative-pole concepts directly: `-concept:faith > -concept:hope > -concept:love`."

---

## Example 6: Expansion Directive

### DSL
```
lemma:pistis > lemma:elpis > lemma:agape => forward:2 within:verse corpus:nt lang:grc
```

### AST
```json
{
  "version": "0.1",
  "source": "lemma:pistis > lemma:elpis > lemma:agape => forward:2 within:verse corpus:nt lang:grc",
  "sequence": {
    "type": "SequenceExpr",
    "steps": [
      { "type": "NodeRef", "nodeType": "lemma", "value": "pistis", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "lemma", "value": "elpis", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "lemma", "value": "agape", "polarity": null, "morphFilters": [], "negated": false }
    ],
    "operators": [
      { "type": "precedence", "gap": null },
      { "type": "precedence", "gap": null }
    ]
  },
  "scope": { "corpus": "nt", "language": "grc", "books": null, "unit": "verse" },
  "mode": "exact",
  "expansion": { "direction": "forward", "depth": 2 },
  "ranking": null,
  "metadata": { "nlSource": null }
}
```

### Validation (v0.1)
**Status**: `partial` — the core sequence is supported, but expansion directives are not.

**Findings**:
```json
[
  {
    "severity": "warning",
    "code": "UNSUPPORTED_EXPANSION",
    "path": "expansion",
    "message": "Expansion directives (=> forward:2) are not supported in engine v0.1. The core sequence will be executed without expansion. Expansion is planned for v0.2.",
    "remediation": null
  }
]
```

**Executable plan**: Same as above but with `"expansion": null`. The engine runs the base sequence and returns matches without exploring what follows.

**User-facing message**: "The system found matches for the sequence pistis > elpis > agape, but cannot yet explore what concepts follow. Expansion analysis is planned for v0.2. Results below are for the base sequence only."

---

## Example 7: Partial — Root Nodes in v0.1

### DSL
```
root:אמן > root:תקו > root:אהב within:verse corpus:ot lang:heb
```

### AST (as parsed)
```json
{
  "version": "0.1",
  "source": "root:אמן > root:תקו > root:אהב within:verse corpus:ot lang:heb",
  "sequence": {
    "type": "SequenceExpr",
    "steps": [
      { "type": "NodeRef", "nodeType": "root", "value": "אמן", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "root", "value": "תקו", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "root", "value": "אהב", "polarity": null, "morphFilters": [], "negated": false }
    ],
    "operators": [
      { "type": "precedence", "gap": null },
      { "type": "precedence", "gap": null }
    ]
  },
  "scope": { "corpus": "ot", "language": "heb", "books": null, "unit": "verse" },
  "mode": "exact",
  "expansion": null,
  "ranking": null,
  "metadata": { "nlSource": null }
}
```

### Validation (v0.1)
**Status**: `unsupported` — three compounding issues.

**Findings**:
```json
[
  {
    "severity": "error",
    "code": "UNSUPPORTED_NODE_TYPE",
    "path": "sequence.steps[0]",
    "message": "Node type 'root' is not supported in engine v0.1. Root nodes are planned for v0.2.",
    "remediation": "Use lemma: nodes instead. For root:אמן, try lemma:אֱמוּנָה or concept:faith."
  },
  {
    "severity": "error",
    "code": "UNSUPPORTED_NODE_TYPE",
    "path": "sequence.steps[1]",
    "message": "Node type 'root' is not supported in engine v0.1.",
    "remediation": "Use lemma: or concept: nodes instead."
  },
  {
    "severity": "error",
    "code": "UNSUPPORTED_NODE_TYPE",
    "path": "sequence.steps[2]",
    "message": "Node type 'root' is not supported in engine v0.1.",
    "remediation": "Use lemma: or concept: nodes instead."
  },
  {
    "severity": "error",
    "code": "UNKNOWN_CORPUS",
    "path": "scope.corpus",
    "message": "Corpus 'ot' is not available in engine v0.1. Available corpora: ['nt'].",
    "remediation": null
  },
  {
    "severity": "error",
    "code": "UNKNOWN_LANGUAGE",
    "path": "scope.language",
    "message": "Language 'heb' is not available in engine v0.1. Available languages: ['grc'].",
    "remediation": null
  }
]
```

No partial reduction is possible — the corpus and language are unavailable, and all three nodes use unsupported types. Status is `unsupported`.

**User-facing message**: "This query cannot be executed yet. The Hebrew Bible corpus, Hebrew language support, and root-based search are all planned for future versions. The current MVP supports Greek New Testament searches using lemma and concept nodes."

---

## Example 8: NL-Sourced Query

### Natural language input
"Does the sequence faith, hope, love appear in Paul's letters? Show me exact Greek matches within individual verses."

### AI-translated DSL
```
lemma:pistis > lemma:elpis > lemma:agape within:verse lang:grc corpus:nt book:rom,1cor,2cor,gal,eph,php,col,1th,2th,1ti,2ti,tit,phm
```

### AST
```json
{
  "version": "0.1",
  "source": "lemma:pistis > lemma:elpis > lemma:agape within:verse lang:grc corpus:nt book:rom,1cor,2cor,gal,eph,php,col,1th,2th,1ti,2ti,tit,phm",
  "sequence": {
    "type": "SequenceExpr",
    "steps": [
      { "type": "NodeRef", "nodeType": "lemma", "value": "pistis", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "lemma", "value": "elpis", "polarity": null, "morphFilters": [], "negated": false },
      { "type": "NodeRef", "nodeType": "lemma", "value": "agape", "polarity": null, "morphFilters": [], "negated": false }
    ],
    "operators": [
      { "type": "precedence", "gap": null },
      { "type": "precedence", "gap": null }
    ]
  },
  "scope": {
    "corpus": "nt",
    "language": "grc",
    "books": ["rom", "1cor", "2cor", "gal", "eph", "php", "col", "1th", "2th", "1ti", "2ti", "tit", "phm"],
    "unit": "verse"
  },
  "mode": "exact",
  "expansion": null,
  "ranking": null,
  "metadata": {
    "nlSource": "Does the sequence faith, hope, love appear in Paul's letters? Show me exact Greek matches within individual verses."
  }
}
```

### Validation (v0.1)
**Status**: `supported` — all features within MVP scope. The `metadata.nlSource` field preserves the original natural language for transparency.

**User-facing display**: The UI shows the generated DSL alongside the original question, allowing the user to verify and edit the translation before execution.

---

## Summary: Validation Outcome Matrix

| Example | Key Features | v0.1 Status | Reason |
|---------|-------------|-------------|--------|
| 1. Simple sequence | concept nodes, precedence | supported | All MVP features |
| 2. Typed lemma + gap | lemma nodes, gap constraint, scope | supported | All MVP features |
| 3. Polarity-marked | + polarity on concepts | supported | Basic polarity in MVP |
| 4. Alternatives + optional | AlternativeExpr, OptionalExpr | supported | Structural features on MVP nodes |
| 5. Inverse query | inverse() wrapper | unsupported | inverseSupport = false |
| 6. Expansion | => forward:2 | partial | Core sequence runs; expansion stripped |
| 7. Root + Hebrew | root nodes, OT corpus, Hebrew | unsupported | Node type, corpus, and language all unavailable |
| 8. NL-sourced | AI translation to DSL | supported | Translated to MVP-compatible lemma query |

## Confidence and Volatility
- Confidence: Medium-High
- Volatility: Medium (AST structures may evolve as parser is implemented)

## References
- Prior docs: 05_dsl-ast.md, 06_capability-validator.md, 04_node-ontology.md
