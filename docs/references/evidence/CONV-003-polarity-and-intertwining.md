# CONV-003 — Polarity, Inverse Patterns, and Intertwining

Source type: Conversation-derived
Date captured: 2026-04-12
Confidence: Medium

## Summary
The system should not only detect positive conceptual sequences, but also inverse, mixed-polarity, reversal, and intertwined variants. This implies a polarity-aware sequence model rather than a simple positive-only sequence matcher.

## Key Takeaways
- Positive and negative poles should be modeled explicitly.
- Antonyms should be treated as weighted inverse candidates rather than simple dictionary opposites.
- Mixed and braided sequences should be treated as important classes of results.

## Influenced Decisions
- DEC-005
