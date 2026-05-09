# DSL Cookbook for Agents

> Caller-facing reference for authoring DSL queries against the Scripture Pattern Lab corpus. **Self-contained** — you should not need to read source or canonical docs to use the system from this file alone. Canonical docs (`docs/canonical/`) remain authoritative for invariant contracts; this cookbook documents what executes today.

## TL;DR

This codebase indexes the Greek New Testament (SBLGNT / MorphGNT). You query it with a small symbolic DSL and a CLI:

```bash
scripts/query.py "faith > hope > love"
```

That command finds verses where the lemma sets for `faith`, then `hope`, then `love` appear in that order. The CLI prints matching verses **plus** a contextualization envelope (constituent-node baselines, alternative-ordering counts) so you can tell whether the pattern is rare, expected, or pervasive.

You are reading this file because you are an LLM agent collaborating with a researcher. Your job is to translate research questions into DSL, run them, read the output, and synthesize answers grounded in **what the corpus actually contains**.

The DSL surface is small. Today's executable subset is documented exhaustively below. Larger surface (negation, polarity, expansion, alternatives) is parsed but raises `UnsupportedPlanShape` at execution; do not author those forms in primary queries.

---

## Authoring DSL Queries

### Mental Model

A DSL query describes a **sequence of nodes** the engine should find inside a **scope** (corpus / language / book / verse). Each node is either:

- A **`concept:`** node — resolves to a curated set of lemmas via the registry (e.g., `concept:faith` resolves to `πίστις, πιστεύω`).
- A **`lemma:`** node — exactly that lemma (e.g., `lemma:πίστις`).

Nodes are connected by the **precedence operator** `>`, which means "appears after, in the same scope." A **gap constraint** `>{min,max}` controls how many tokens may sit between two nodes.

A bare word with no prefix is treated as a `concept:` node. So `faith > hope > love` is shorthand for `concept:faith > concept:hope > concept:love`.

### Node Types You Can Use Today

The MVP executor supports two node types:

| Syntax | Type | Meaning |
|---|---|---|
| `concept:NAME` or just `NAME` | `CONCEPT` | Resolves to all lemmas mapped to NAME in the registry |
| `lemma:LEMMA` | `LEMMA` | Exactly the supplied lemma string (Greek surface OK: `lemma:πίστις`) |

> Other node types (`token:`, `root:`, `morph:`, `domain:`, `*` wildcard) parse successfully but raise `UnsupportedPlanShape` at execution. See "Coming Soon" below.

### The Sequence Operator and Gap Constraint

| Syntax | Meaning |
|---|---|
| `A > B` | A appears, then B appears later in the same scope |
| `A >{min,max} B` | A appears, then B appears with `min` to `max` other tokens between them |
| `A >{0,5} B` | A appears, then B appears within 5 tokens (no minimum gap) |

The validator's `max_sequence_length` is **10** — sequences longer than that are rejected.

> Other operators (`>>` adjacency, `~` cooccurrence) parse but raise `UnsupportedPlanShape`. Use only `>` (with optional gap) in primary queries.

### Scope Directives

Trailing `keyword:value` directives narrow where the engine searches:

| Directive | Values | Default |
|---|---|---|
| `within:` | `verse` | `verse` (the only supported unit today) |
| `lang:` | `grc` (Koine Greek) | `grc` |
| `corpus:` | `nt` (New Testament) | `nt` |
| `book:` | comma-separated abbreviations: `rom`, `1cor`, `2cor`, `gal`, `eph`, `php`, `col`, `1th`, `2th`, `1ti`, `2ti`, `tit`, `phm`, `heb`, `jas`, `1pe`, `2pe`, `1jn`, `2jn`, `3jn`, `jud`, `rev`, `mat`, `mar`, `luk`, `jhn`, `act` | (whole corpus) |

**Example with full scope:**

```
faith > hope > love within:verse lang:grc corpus:nt book:1cor
```

### Match Mode

The parser infers the `mode:` directive from your query. If any node is `concept:` (or a bare word), the mode becomes `conceptual` (lemmas inside a concept's mapping all match). If every node is `lemma:`, mode is `exact`. You usually don't write `mode:` yourself.

### Quick Reference: Operators and Tokens

| DSL | What it does | Executable today? |
|---|---|---|
| `>` | precedence (later in scope) | ✅ |
| `>{m,n}` | precedence with gap window | ✅ |
| `>>` | strict adjacency | ❌ parses, raises `UnsupportedPlanShape` |
| `~` | cooccurrence (no order) | ❌ parses, raises `UnsupportedPlanShape` |
| `+`, `-`, `±` (polarity prefix) | polarity marker on a node | ❌ parses, validator rejects |
| `!` (negation prefix) | negate a node | ❌ parses, executor rejects |
| `[step]` | optional step | ❌ parses, executor rejects |
| `(a \| b)` | alternative options | ❌ parses, executor rejects |
| `inverse(...)` | inverse of a sequence | ❌ parses, validator rejects |
| `=> forward:N` / `=> backward:N` / `=> expand:N` | expansion directive | ❌ parses, validator warns; query reduces |
| `lemma:X+morph:Y` | compound morph filter | ❌ parses, validator rejects |

### Quick Reference: CLI Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success — matches found OR zero matches (both are valid outcomes) |
| `1` | Uncaught exception (Python traceback in stderr — should not happen in normal use) |
| `2` | User-side error: `parse error`, validator status `unsupported`, OR `UnsupportedPlanShape` |
| `3` | Concept registry problem: `concept not mapped` OR `RegistryRequired` |

---

## Concept Registry

The registry is the curated map from concept names to Greek lemma sets. There are **20 seeded concepts** as of slice E. If you need a concept not on this list, fall back to direct `lemma:` queries.

### Seeded Concepts

| Concept | Resolved Lemmas (language: grc) |
|---|---|
| `faith` | πίστις, πιστεύω |
| `hope` | ἐλπίς, ἐλπίζω |
| `love` | ἀγάπη, ἀγαπάω |
| `unbelief` | ἀπιστία, ἀπιστέω |
| `doubt` | διακρίνω, διστάζω |
| `despair` | ἐξαπορέω |
| `hatred` | μῖσος, μισέω |
| `righteousness` | δικαιοσύνη, δίκαιος |
| `sin` | ἁμαρτία, ἁμαρτάνω |
| `grace` | χάρις |
| `law` | νόμος |
| `salvation` | σωτηρία, σῴζω |
| `death` | θάνατος, ἀποθνῄσκω |
| `life` | ζωή, ζάω |
| `spirit` | πνεῦμα |
| `flesh` | σάρξ |
| `truth` | ἀλήθεια |
| `knowledge` | γνῶσις, γινώσκω |
| `joy` | χαρά, χαίρω |
| `peace` | εἰρήνη |

### What If My Concept Isn't Listed?

Two options:

1. **Use `lemma:` directly.** If you know the Greek lemma, query it: `lemma:δόξα` for "glory." This bypasses the concept registry entirely.
2. **Combine multiple lemmas with separate queries.** The MVP DSL has no in-query alternative `(a | b)` execution. You can run two queries and combine answers manually.

If you author a query with a concept name not in the table above, the CLI exits with code `3` and stderr says `concept not mapped`. See "Failure Modes" below.

---

## Running Queries via CLI

### Setup

The CLI requires `DATABASE_URL` set in the environment, pointing at a running PostgreSQL instance with the corpus loaded:

```bash
export DATABASE_URL="postgresql://USER:PASS@HOST:5432/DB"
scripts/query.py "faith > hope > love"
```

The password is redacted (`***`) in the diagnostic startup line. If `DATABASE_URL` is unset, you get a `RuntimeError`.

The `--limit N` flag caps how many candidate verses are printed (default 20). It does not affect the contextualization envelope, which always describes the full result set.

### Worked Example 1: `faith > hope > love`

```
[E2 placeholder: insert verbatim captured stdout from a live run during E2]
```

### Worked Example 2: lemma sequence with book filter

```
[E2 placeholder]
```

### Worked Example 3: gap constraint

```
[E2 placeholder]
```

### Reading the Output

```
[E2 placeholder: line-by-line annotation of the captured output]
```

---

## Failure Modes and Recovery

```
[E3 placeholder]
```

---

## Limits

- **Maximum sequence length**: 10 nodes. Longer sequences are rejected with `SEQUENCE_TOO_LONG`.
- **No maximum gap**: `>{0,9999}` is accepted by the validator. If you author absurd gaps, you may get many matches.
- **Contextualization permutation cap**: when a sequence has 5+ steps, alternative-ordering enumeration is capped at 24 permutations (full enumeration up to 4 steps; cap kicks in at N ≥ 5). The output's `alternative_orderings_capped: true` flag tells you when the cap was hit.

---

## Coming Soon (parsed but not yet executable)

These DSL features are recognized by the parser but raise `UnsupportedPlanShape` at execution today. **Do not use them in primary queries.** Future slices will make them executable; this section will be updated.

- `inverse(SEQUENCE)` — find sequences expressing the inverse pattern (e.g., negative pole of trust)
- `>>` — strict adjacency (no tokens between)
- `~` — cooccurrence without order
- `+`, `-`, `±` polarity prefixes
- `!` negation
- `[step]` optional step
- `(a | b | c)` alternative options
- `=> forward:N` / `=> backward:N` / `=> expand:N` sequence expansion
- `lemma:X+morph:Y` compound morph filter
- `token:`, `root:`, `morph:`, `domain:` node types
- `*` wildcard in sequence
- `within:clause`, `within:sentence`, `within:pericope`, `within:chapter` (only `within:verse` works today)

---

## Where to Read More (Optional)

You should not need these to use the system. They exist if you want deeper context:

- `docs/canonical/02_query-language-draft.md` — full DSL grammar surface (parsed superset)
- `docs/canonical/04_node-ontology.md` — node type semantics
- `docs/canonical/05_dsl-ast.md` — AST shape produced by the parser
- `docs/canonical/06_capability-validator.md` — validator rules and reduction
- `docs/canonical/07_query-to-ast-examples.md` — 8 worked DSL→AST examples
- `docs/canonical/09_backend-service-boundaries.md` — service interfaces (parser, executor, retrieve, contextualize)
