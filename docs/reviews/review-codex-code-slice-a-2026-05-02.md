---
type: codex-review
flavor: code
date: 2026-05-02
verdict: needs-attention
base: origin/main (Slice A surface — 25 commits)
scope: src/, tests/, data/schemas/, scripts/db/, governance and canonical edits in branch
plugin: codex@openai-codex 1.0.4
codex_cli: 0.125.0
findings_summary: 3 P2 (no P0/P1)
---

# Codex Code Review — 2026-05-02

Run before opening Slice B, paired with the adversarial design review in
`thoughts/review-codex-adversarial-design-2026-05-02.md`. Native review surface
(no focus text).

## Command

```
/codex:review --base origin/main --background
```

## Codex output (verbatim)

# Codex Review

Target: branch diff against origin/main

The patch introduces parser gaps for DSL constructs that are documented and represented in the AST, and validation can return a partial executable plan that still contains unsupported nested nodes. These issues can break valid queries or pass invalid plans downstream.

Full review comments:

- [P2] Handle polarity before parenthesized alternatives — /Users/dwmonson/Documents/Claude-Personal/scripture-pattern-lab/src/engine/parser.py:287-288
  For documented queries that put polarity on an alternative group, e.g. `+(concept:hope | concept:expectation)`, this fallback calls `parse_node_ref()`, which consumes `+` and then expects a WORD, so it rejects the following `(`. The canonical DSL examples include this form and expect the polarity to apply to each option, so these queries currently fail to parse.

- [P2] Tokenize wildcard nodes — /Users/dwmonson/Documents/Claude-Personal/scripture-pattern-lab/src/engine/parser.py:119-134
  The AST and MVP registry include `wildcard`, and `_parse_typed_value()` has a `word_tok.value == "*"` branch, but the tokenizer never emits `*` as a token. Any query using a wildcard step such as `* > concept:faith` fails immediately with `Unexpected character: '*'` before the parser can build a wildcard NodeRef.

- [P2] Reduce unsupported nodes inside composite steps — /Users/dwmonson/Documents/Claude-Personal/scripture-pattern-lab/src/validation/validator.py:424-427
  Partial reduction only drops unsupported nodes when the top-level step is a `NodeRef`, so an unsupported `root:` inside an `AlternativeExpr`, `GroupExpr`, or `OptionalExpr` remains in `executable_plan` even after validation reports a partial result. In mixed nested queries, this can hand the engine a plan that still contains capabilities the registry said are unsupported.

## Pending action (not in this artifact)

Triage of findings is deferred until the design review is also in hand
(`thoughts/review-codex-adversarial-design-2026-05-02.md`). Both will be
triaged together so doc and code remediation sequence correctly.
