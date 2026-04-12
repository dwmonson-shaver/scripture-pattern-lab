# Scripture Pattern Lab

Scripture Pattern Lab is an AI-assisted research platform for exploring original-language scripture sequences, conceptual patterns, polarity-aware inversions, and intertext relationships across Judeo-Christian texts.

## Purpose

The project is designed to help users test and explore sequence and pattern hypotheses in ancient scripture using original languages rather than relying only on English translations. The platform is intended to support lexical, conceptual, structural, and polarity-aware analysis while preserving transparency in how results are found and ranked.

## Core Product Principle

Natural language is the user entry point, but all executable analysis must compile into a validated query language. AI assists with translation, explanation, and refinement. It must not silently exceed system capabilities.

## What the Platform Will Do

The platform is being designed to let users:

- Ask research questions in natural language
- Convert those questions into a formal query syntax
- Search for ordered sequences of words, lemmas, concepts, and related patterns
- Detect approximate, conceptual, expanded, inverse, and intertwined sequence variants
- Explore how patterns extend forward or backward with additional concepts
- Examine polarity-aware patterns such as positive and negative conceptual counterparts
- Inspect transparent evidence for every result returned

## Initial Use Cases

Example use cases include:

- Determining whether a sequence such as faith -> hope -> love appears elsewhere exactly, approximately, or conceptually
- Exploring whether that sequence extends forward or backward with additional concepts
- Testing whether an inverse or negative-pole pattern such as unbelief -> despair -> hatred also appears
- Identifying whether positive and negative forms of a pattern are intertwined in ways that make them harder to detect
- Comparing lexical, conceptual, and structural realizations of a sequence across corpora and languages

## Current Focus

This repository currently captures the early product foundation for an MVP centered on sequence hypothesis exploration. Current design work focuses on:

- Query language design
- Natural language to DSL translation
- Capability validation
- Symbolic retrieval and scoring
- Polarity-aware sequence analysis
- Hybrid architecture planning for symbolic and semantic retrieval
- Node ontology planning

## Planned Architecture Direction

The platform is expected to use a hybrid approach:

- A symbolic engine for deterministic sequence, lexical, morphological, and structural matching
- A semantic layer using embeddings for conceptual expansion and analogy discovery
- An AI layer for natural language interpretation, query translation, explanation, and refinement
- A capability validator to ensure AI does not generate or imply unsupported queries

This is not intended to be a generic chatbot over scripture text. The core value is an inspectable hypothesis exploration engine.

## Repository Structure

```text
docs/
  canonical/
  governance/
  references/

product/
  roadmap/
  specs/

prompts/
  system/
  dev/
  research/

src/
  app/
  engine/
  ontology/
  nlp/
  retrieval/
  scoring/
  validation/

tests/
  unit/
  integration/
  fixtures/

scripts/
  setup/
  ingest/
  maintenance/

data/
  sample/
  schemas/
```