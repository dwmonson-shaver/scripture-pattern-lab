# CONV-002 — Architecture, Retrieval, and Query Language

Source type: Conversation-derived
Date captured: 2026-04-12
Confidence: Medium

## Summary
The product should use a symbolic core engine, with embeddings, hybrid retrieval, and LLM explanation as secondary layers. A query language should express sequence hypotheses, constraints, and scope in deterministic syntax.

## Key Takeaways
- RAG and embeddings are supporting layers, not the main engine.
- Postgres plus pgvector is a practical MVP stack; Elastic can come later.
- Query language should be a readable sequence graph DSL.
- Sequence neighborhood and extension analysis are important features.

## Influenced Decisions
- DEC-002
