# Long-Term Architecture Vision

> Project north star. Captures where this project is going, beyond MVP code that already exists. Not a roadmap with deadlines — a description of the eventual shape.

Drafted: 2026-05-10 (during Slice I close-out conversation).

---

## The three-tier shape

The project ultimately resolves into **three distinct artifacts**, each with its own repo (or repo-set), each with a different purpose, each with a different relationship to the LLM:

```
┌──────────────────────────────────────────────────────────────────┐
│  TIER 1: THE TOOL                                                │
│  scripture-pattern-lab (this repo)                               │
│                                                                  │
│  - Deterministic computation: parser, validator, executor,       │
│    contextualization, explainer.                                 │
│  - LLM at translation boundaries only (NL→DSL in, prose out).    │
│  - Exposes HTTP API + (eventually) MCP server.                   │
│  - Generic. Anyone can fork and use for their own research.      │
│  - Seed registry (~30 concepts) is starter data, not source-     │
│    of-truth.                                                     │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │ uses (HTTP API; eventually MCP)
                              │ proposes feedback (one-directional)
                              │
┌──────────────────────────────────────────────────────────────────┐
│  TIER 2: A RESEARCH ENVIRONMENT                                  │
│  scripture-pattern-lab-research (sibling repo, per-researcher)   │
│                                                                  │
│  - Personal research findings as markdown documents.             │
│  - Tool-feedback findings (proposed changes back to Tier 1).     │
│  - Hypothesis logs, query history, cumulative evidence notes.    │
│  - Re-runnable queries with temporal comparison.                 │
│  - Drives concept curation against the live registry.            │
│  - LLM = research collaborator (Claude Code or MCP client).      │
│  - Per-researcher; not shipped as part of the tool.              │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │ research synthesizes into
                              │ public artifacts
                              │
┌──────────────────────────────────────────────────────────────────┐
│  TIER 3: AGENTIC PUBLICATIONS (future)                           │
│  Per-publication repos, or a dedicated publication system        │
│                                                                  │
│  - Long-form research artifacts (books, papers, articles)        │
│    written for human readers at varying technical levels.        │
│  - Each artifact ships with an embedded LLM agent that can       │
│    answer reader questions in real time, drawing on the full     │
│    research pool that backed the publication.                    │
│  - The reader experience: "you're reading a book; you can ask    │
│    it anything; the agent draws on the underlying tool + the     │
│    researcher's full body of evidence to answer."                │
│  - Multi-level: an 8th-grade reader gets one experience; an      │
│    advanced reader who wants to interrogate the evidence gets    │
│    a different one — same artifact.                              │
│  - This is a new kind of reading, not a UI on top of an old one. │
└──────────────────────────────────────────────────────────────────┘
```

The boundaries between tiers are **enforced one-directional dependencies**: each tier uses the tier below, but cannot modify it. The research environment uses the tool; the publication uses the research. Neither writes back into what it depends on except through deliberate, curated handoffs.

## Why three tiers, not one big system

This separation is load-bearing for several reasons:

1. **Generality.** The tool needs to remain general so others can use it for their own research. If the tool repo accumulates one researcher's specific findings, it stops being a tool and becomes that researcher's project. Forking and adapting becomes painful.
2. **Researcher independence.** A researcher should be able to use the tool, accumulate findings, and decide what to publish without anyone else's research polluting their workspace. The research repo is theirs.
3. **Reader experience innovation.** The agentic-publication tier is doing something genuinely new — embedding interactive agents into long-form content. Forcing this into the tool repo would muddy the tool's contract; forcing it into the research repo would muddy the researcher's library. It's its own thing.
4. **Distinct LLM roles.** The LLM has a different job in each tier. Tool: translator at boundaries. Research environment: collaborative partner who can propose but cannot validate. Publication: docent / interlocutor for readers. Same underlying model, different system prompts, different scopes of action.

## The cumulative-evidence model

A foundational principle that emerged during Slice I close-out conversation:

**Conceptual mappings (concept → lemmas, concept → polarity, concept → inverse) are claims that accumulate evidence over time.** They are not validated by a binary flip; they are validated by a body of evidence + a written human synthesis judgment over that body.

Three kinds of evidence accumulate per claim:

- **Internal corpus evidence** — patterns the system finds. e.g., "πίστις, ἐλπίς, ὑπομονή co-occur in proximity-with-precedence patterns in Rom 5:3-4 and 1 Thes 1:3."
- **External evidence** — citations from outside scholarship, lexical resources, translation data. e.g., "BDAG entry for ὑπομονή links it to ἐλπίς via the 'waiting-for-promised-good' semantic field."
- **Linguistic / structural evidence** — from translation studies, morphology, root analysis. e.g., "ὑπομονή derives from μένω + ὑπό, sharing durational aspect with hope-words across the LXX."

The lifecycle is:

- **`unverified`** — claim exists as a hypothesis. Zero or some evidence. No synthesis.
- **(implicit "evidence accumulating")** — evidence rows continue to attach. The claim's strength grows. No state change is required because the evidence table itself reflects the state.
- **`human_synthesized`** — a researcher has written a synthesis judgment over the evidence set, dated, with rationale. The synthesis points at a specific evidence-set version.
- **`synthesis_stale`** — a derived state: a synthesis exists, but new evidence has been added since. The system flags for re-review. The researcher decides whether to revise or re-affirm.

This is more rigorous than a binary flip. It mirrors how scholarship actually works — claims aren't proven; they accumulate evidence and survive (or don't) successive re-examinations.

A claim can be re-synthesized as the evidence base grows. Multiple synthesis judgments may exist over a claim's lifetime, each a snapshot of one researcher's reading at one point in time.

## The LLM-as-translator boundary (DEC-081)

The LLM participates only at translation boundaries. Computation is deterministic. Probabilistic generation may convert between human-natural-language and structured data, but may not introduce factual claims, validate concepts, or render results that aren't grounded in the deterministic output.

This applies in all three tiers:

- **Tool**: NL→DSL translator (Slice H), result→prose explainer (Slice F deterministic; Bucket 7 may add LLM augmentation under strict no-fabrication constraints).
- **Research environment**: agent translates user intent ("propose patience") into deterministic CLI invocations. Cannot decide concepts on its own. Cannot mark anything synthesized without explicit human action.
- **Agentic publication**: agent translates reader questions into queries against the research pool. Cannot fabricate evidence. Cannot assert claims the underlying research doesn't support.

DEC-081 in the decision log is the canonical statement.

## Statistical-significance question (deferred — Bucket 10)

A real question raised during Slice I close-out: how does the system distinguish patterns that are deliberate (authored) from patterns that are random (accidental co-occurrence)?

Today's contextualization envelope (Slice D) provides part of the answer: alternative-orderings counts show whether a specific ordering is unique vs. one of many. But it doesn't compute statistical significance against a null distribution.

Future work (Bucket 10): compute null distribution from random permutations of the corpus; surface a p-value-style measure; integrate with the contextualization envelope.

## What this means for current decisions

Every architectural choice from here forward should be evaluated against this north star. Specifically:

- **Don't muddy the tool with research-specific data.** Concepts that one researcher curates live in their DB and (eventually) their concept-overlay file in their research repo. Not in `data/seeds/registry/`.
- **Don't muddy the research environment with tool development.** Tool friction generates feedback findings; feedback findings get triaged into tool slices. Don't fix the tool from a research session.
- **Design the API surface as if MCP were already in front of it.** Every endpoint will eventually be exposed as an MCP tool. Every CLI subcommand will eventually be a tool too. Naming, error semantics, and idempotency should be MCP-clean.
- **The agentic-publication tier is downstream of the research environment.** Don't build it until the research environment is producing real findings worth publishing. But keep the architecture open to it — JSON-able findings, citable evidence, traceable provenance.

## Repository names (working)

- Tier 1 — `scripture-pattern-lab` (this repo).
- Tier 2 — `scripture-pattern-lab-research` (sibling, to be created in Slice J0).
- Tier 3 — TBD; per-publication or single dedicated repo. Decided when we're ready to publish.

## Status

This document is the project's north star. It is not a slice scope. It does not bind any specific slice; it constrains what slices are reasonable to scope. Update it when the vision evolves; review it at every slice boundary.
