# CONV-004 — NL-to-DSL Boundary and Documentation Strategy

Source type: Conversation-derived
Date captured: 2026-04-12
Confidence: Medium

## Summary
Natural language must compile into query syntax rather than bypass it. The system needs a validator to prevent unsupported behavior. The project should use canonical docs plus evidence/governance docs with traceable references.

## Key Takeaways
- Capability boundary is a core requirement.
- Standard and developer modes should behave differently when unsupported requests arise.
- Documentation should separate decisions, assumptions, references, and evidence.

## Influenced Decisions
- DEC-003
- DEC-004
- DEC-006
