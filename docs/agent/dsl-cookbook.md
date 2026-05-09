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

> **Note on the examples below.** The counts and verse references in Worked Example 1 are the ground-truth numbers captured during Slice D and recorded in the project's slice-exit-gate manual smoke. The exact stdout *formatting* (column widths, padding) is reconstructed from `scripts/query.py` rendering code; if you run the CLI yourself, expect the same fields with possibly slightly different spacing. Worked Examples 2 and 3 are constructed for shape-only — author them yourself against the live corpus to get real numbers.

### Worked Example 1: `faith > hope > love` (real corpus output)

Command:
```bash
scripts/query.py "faith > hope > love"
```

stderr (diagnostic line):
```
query='faith > hope > love' DATABASE_URL=postgresql://user:***@host:5432/db
```

stdout:
```
Query: faith > hope > love
Status: supported   Grounding: prior-grounded
Match type: conceptual
Found 2 matches (showing first 2):

  [1] 1Cor 13:13
        πίστις   (faith)            @ position 2
        ἐλπίς    (hope)             @ position 3
        ἀγάπη    (love)             @ position 4
  [2] 1Cor 13:13
        πίστις   (faith)            @ position 2
        ἐλπίς    (hope)             @ position 3
        ἀγάπη    (love)             @ position 4

Contextualization (REQ:09.contextualization):
  Observed count: 2
  Constituent baselines (scope-filtered tokens):
    faith  →  πίστις, πιστεύω: 483
    hope   →  ἐλπίς, ἐλπίζω: 84
    love   →  ἀγάπη, ἀγαπάω: 259
  Alternative orderings (6 total, observed marked *):
    *  faith > hope > love: 2
       faith > love > hope: 2
       hope > faith > love: 0
       hope > love > faith: 0
       love > faith > hope: 0
       love > hope > faith: 0
  Null distribution: not computed in MVP (schema slot reserved)
```

What this tells you about the corpus:
- The "faith > hope > love" sequence appears in exactly **one verse** of the NT (1 Cor 13:13), with 2 chain alignments at that verse.
- The "faith > love > hope" alternative ordering also produces 2 chains at the same verse — because 1 Cor 13:13 contains all three lemmas in adjacent positions, both directional readings find the same trio. This is a feature of the corpus, not a bug.
- The lemma πίστις (with πιστεύω) appears 483 times in the NT — a high-frequency baseline. ἐλπίς+ἐλπίζω is far rarer at 84. ἀγάπη+ἀγαπάω sits at 259.
- Null-distribution sampling is reserved for a future slice; until then, judge significance by comparing observed count (2) against the alternative orderings (also 2 for one ordering, 0 for the rest).

### Worked Example 2: lemma sequence with book filter (constructed — author live for real numbers)

Command:
```bash
scripts/query.py "lemma:πίστις > lemma:ἐλπίς > lemma:ἀγάπη within:verse lang:grc corpus:nt book:rom,1cor"
```

Expected output shape (real numbers will differ):
```
Query: lemma:πίστις > lemma:ἐλπίς > lemma:ἀγάπη within:verse lang:grc corpus:nt book:rom,1cor
Status: supported   Grounding: n/a
Match type: exact
Found 2 matches (showing first 2):

  [1] 1Cor 13:13
        πίστις   @ position 2
        ἐλπίς    @ position 3
        ἀγάπη    @ position 4
  [2] 1Cor 13:13
        πίστις   @ position 2
        ἐλπίς    @ position 3
        ἀγάπη    @ position 4

Contextualization (REQ:09.contextualization):
  Observed count: 2
  Constituent baselines (scope-filtered tokens):
    πίστις  →  πίστις: <count for rom+1cor>
    ἐλπίς   →  ἐλπίς: <count for rom+1cor>
    ἀγάπη   →  ἀγάπη: <count for rom+1cor>
  Alternative orderings (6 total, observed marked *):
    *  πίστις > ἐλπίς > ἀγάπη: 2
       <other 5 permutations>
  Null distribution: not computed in MVP (schema slot reserved)
```

Differences from Example 1:
- `Match type: exact` because every node is `lemma:` (not `concept:`). No registry resolution.
- `Grounding: n/a` because grounding only applies to concept queries (per registry epistemics).
- The per-step alignment lines have **no** `(concept_value)` annotation — that field only appears for `CONCEPT` nodes.
- Baselines list each lemma resolving to itself (one-to-one).
- `book:rom,1cor` narrows the scope — both candidate counts AND constituent baselines reflect this narrower scope.

### Worked Example 3: gap constraint (constructed)

Command:
```bash
scripts/query.py "faith >{0,5} grace within:verse corpus:nt"
```

Expected output shape:
```
Query: faith >{0,5} grace within:verse corpus:nt
Status: supported   Grounding: prior-grounded
Match type: conceptual
Found <N> matches (showing first 20):

  [1] <book> <chapter>:<verse>
        <faith-lemma>  (faith)  @ position <p1>
        χάρις          (grace)  @ position <p2>     # p2 - p1 ∈ [1,6]; 0–5 tokens between
  [2] ...
  ...

Contextualization (REQ:09.contextualization):
  Observed count: <N>
  Constituent baselines (scope-filtered tokens):
    faith  →  πίστις, πιστεύω: 483
    grace  →  χάρις: <count>
  Alternative orderings (2 total, observed marked *):
    *  faith > grace: <N>
       grace > faith: <N'>
  Null distribution: not computed in MVP (schema slot reserved)
```

Notes on gap semantics:
- `>{0,5}` means "0 to 5 tokens between" — same-position is impossible (can't be in two places at once), so effective minimum is "next token." `{0,0}` would be the strict adjacency case.
- Gap is enforced per-pair, not cumulatively. In a 3-step chain `A >{0,3} B >{0,3} C`, A↔B can be 3 apart and B↔C can be 3 apart, total span 6.
- The contextualization's "Alternative orderings" only includes 2 permutations for a 2-step sequence. For an N-step sequence with N ≥ 5, the cap of 24 kicks in.

### Reading the Output: Field-by-Field

The CLI output has two top-level sections after the diagnostic stderr line: the **results** and the **contextualization envelope**. Both are printed every time (when `contextualization=True`, which is the CLI default).

**Header lines:**

| Line | Field | Meaning |
|---|---|---|
| `Query: ...` | echoed query | The DSL string you submitted |
| `Status:` | validator outcome | `supported` / `partial` / `unsupported` (latter exits with code 2) |
| `Grounding:` | registry-epistemics axis | `prior-grounded` / `evidence-grounded` / `mixed` / `n/a` (`n/a` for non-concept queries) |
| `Match type:` | per-result kind | `exact` / `variant` / `conceptual` (taken from the first candidate) |
| `Found N matches (showing first M):` | count + display cap | `M` is your `--limit` flag, default 20 |

**Per-candidate block** (one block per matching verse-chain):

```
  [INDEX] BOOK CHAPTER:VERSE
        LEMMA  (CONCEPT_ANNOTATION)  @ position POS
        ...
```

- `INDEX` is 1-based.
- `LEMMA` is the surface lemma the executor matched.
- `(CONCEPT_ANNOTATION)` only appears when the step's node was a `concept:` (or bare-word) node — it tells you *which* concept resolved to this lemma.
- `@ position POS` is the in-verse token position (1-based after preprocessing, generally aligned with morphological tokenization).

**Contextualization block:**

| Line | Field | Meaning |
|---|---|---|
| `Observed count: N` | `Contextualization.observed_count` | Number of candidate chains found by the engine — the number you'd care about answering "how often" |
| `Constituent baselines:` | `node_baselines` list | One row per sequence step; resolved-lemma list and total token count under the scope |
| `Alternative orderings (M total, observed marked *):` | `alternative_orderings` list | Counts for every permutation of the sequence; observed marked `*`. Compare these to gauge whether the observed ordering is special vs. one of many viable orderings. |
| `Alternative orderings (M total, capped, observed marked *):` | with `capped` flag | When sequence length ≥ 5, only a subset of permutations are evaluated (cap = 24). Use this signal to interpret cautiously. |
| `Null distribution: not computed in MVP (schema slot reserved)` | `null_distribution = None` | Always this fixed text in MVP. A future slice may replace it with sampling-based stats. |

**How to interpret a result set:**

- **Observed count ≫ alternative-ordering counts** → the observed sequence is a real pattern, not a permutation artifact.
- **Observed count ≈ alternative-ordering counts** → the lemmas co-occur, but in no particular preferred order.
- **Observed count = 0 but baselines are large** → the constituents exist abundantly but never co-occur in this order in this scope. Worth exploring.
- **Observed count = 0 and baselines are small** → the constituents are too rare to expect any sequence to fire. Try widening scope (drop `book:`) or relaxing constraints.

---

## Failure Modes and Recovery

Every observable failure mode of the CLI is listed here with its exact recognition signature (the string you will see in stderr or stdout) and the concrete recovery action. If you encounter something not on this list, that's a cookbook gap — report it.

### `parse error` — DSL syntax problem

**Recognition (stderr, exit code 2):**
```
parse error: <message> (at position <N>)
  <your DSL string>
        ^
```

The caret `^` points at the offending character.

**Common causes:**
- Missing colon after a directive: `lang grc` instead of `lang:grc`
- Stray operator: `faith > > hope` (two `>` in a row)
- Unbalanced bracket/paren/brace: `(faith > hope` (no closing `)`)
- Empty query: `""` (whitespace-only also fails)
- Unknown expansion direction: `=> sideways:2` (only `forward`, `backward`, `expand`, `both` are accepted by the parser)

**Recovery:**
1. Read the message and the position marker.
2. Re-check syntax against the "Authoring DSL Queries" section. Most parse errors are typos or misremembering operator syntax.
3. Re-author the DSL with explicit prefixes (`concept:` / `lemma:`) if you suspect ambiguity in token boundaries.

### `Status: unsupported` — validator rejected the query

**Recognition (stderr + exit code 2):**
```
validator returned unsupported — cannot execute
  error: <CODE> at <path>: <message>
```

**Common error codes (full list per `docs/canonical/06_capability-validator.md`):**

| Code | Cause | Recovery |
|---|---|---|
| `UNSUPPORTED_NODE_TYPE` | Used `token:`, `root:`, `morph:`, `domain:`, or `*` wildcard | Restrict to `concept:` and `lemma:` only |
| `UNSUPPORTED_OPERATOR` | Used `>>` or `~` | Use `>` (with optional gap) instead |
| `UNSUPPORTED_POLARITY` | Used `+`, `-`, or `±` | Drop the polarity prefix; future slice will enable polarity |
| `UNSUPPORTED_INVERSE` | Used `inverse(...)` | Reformulate as the explicit inverse sequence (e.g., for `inverse(faith > love)` try `unbelief > hatred`) — see the seeded inverse-claims pairs in canonical-08 |
| `UNSUPPORTED_COMPOUND_NODE` | Used `lemma:X+morph:Y` | Drop the `+morph:` filter |
| `UNSUPPORTED_MATCH_MODE` | Used a `mode:` value not in `exact \| variant \| conceptual \| hybrid` | Drop the explicit `mode:` directive — parser will infer correctly |
| `UNKNOWN_CORPUS` | Used `corpus:` not in `["nt"]` | Use `corpus:nt` only (MVP corpus) |
| `UNKNOWN_LANGUAGE` | Used `lang:` not in `["grc"]` | Use `lang:grc` only (MVP language) |
| `SEQUENCE_TOO_LONG` | More than 10 nodes | Break into multiple shorter queries |
| `EMPTY_SEQUENCE` / `MALFORMED_AST` | Edge case from parser | Re-author from scratch; report if the syntax looks valid |

### `Status: partial` — validator reduced the query (still ran)

**Recognition (stderr + exit code 0):**
```
validator returned partial — proceeding with reduced executable plan
  warning: <CODE> at <path>: <message>
```

**What happened:** The validator stripped unsupported features and ran a smaller executable plan. The most common cause is `UNSUPPORTED_EXPANSION` (the `=> forward:N` etc. directive).

**Recovery:** Read the printed findings to know what was dropped. The reduced plan still produced valid results — but the answer reflects the reduced query, not your original intent. Decide whether the reduction is acceptable. If not, reformulate without the dropped feature.

### `concept not mapped` — concept name unknown

**Recognition (stderr + exit code 3):**
```
concept not mapped: '<concept-name>' has no lemma rows in the registry
```

**Cause:** You used a `concept:` (or bare-word) node whose name is not in the 20-concept seeded list.

**Recovery:**
1. Check the seeded concepts table above. Pick a synonym if available.
2. If your concept truly isn't seeded, fall back to direct `lemma:` queries with the Greek lemma you have in mind.
3. If you don't know the Greek lemma, ask the user — adding new concepts is a registry-extension task, not a query-time recovery.

### `RegistryRequired` — concept used but registry not connected

**Recognition (stderr + exit code 3):**
```
RegistryRequired: concept registry is required to resolve concept node '<name>' but none was supplied
```

**Cause:** This shouldn't happen via the CLI in normal operation — the CLI always wires the registry. If you see it, it's a bug in the CLI invocation, not your query.

**Recovery:** Report the problem to the user; do not retry. This signals a regression in the CLI bootstrap path.

### `UnsupportedPlanShape` — executor's second wall

**Recognition (stderr + exit code 2):**
```
UnsupportedPlanShape: <message>
  path: <jsonpath>
```

**Cause:** A query that passed the parser AND the validator was still rejected by the executor. This is rare but possible — the executor checks shape invariants the validator does not (e.g., `validate_plan_shape` enforces stricter rules on operators, scope unit, book abbreviations).

**Recovery:**
1. Read the `path:` to see which AST node was unsupported (e.g., `$.scope.unit`, `$.sequence.steps[2]`, `$.scope.books[1]`).
2. Adjust the corresponding DSL part. Common: `within:` set to anything other than `verse`; book abbreviation typo.

### `Found 0 matches` — corpus is silent on this query

**Recognition (stdout + exit code 0):**
```
Found 0 matches (showing first 0):

Contextualization (REQ:09.contextualization):
  Observed count: 0
  ...
```

**This is NOT an error.** Exit code is 0. It means the corpus simply does not contain the pattern you asked for in the scope you specified.

**What to do:**
1. Read the contextualization. If baselines are LARGE but observed is 0, the constituents exist but never co-occur in this order in this scope — that's a real research finding, not a failure.
2. If baselines are SMALL or 0, the constituents are too rare. Widen the scope (drop `book:`) or check for typos in lemma syntax.
3. Don't fabricate a positive answer. The corpus is ground truth. If it's silent, report that it's silent.

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
