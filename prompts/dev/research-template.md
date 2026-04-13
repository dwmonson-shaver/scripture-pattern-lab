# Research: [Area of Codebase]

> IMPORTANT: This research prompt must NOT include the goal, ticket, or feature being built. The purpose is to gather objective facts about the codebase. Opinions and implementation suggestions are not wanted.

## Research Questions

_Each question should cause the agent to trace a specific path through the codebase and report facts._

1. How does [component/module] work? Trace the logic flow from entry point to output.
2. What types and interfaces does [module] expose?
3. What patterns does [area] follow for [specific concern]?
4. What tests exist for [component]? What do they cover?
5. What dependencies does [module] have?

## Output Format

Report only facts. For each question:
- **File paths** and line numbers of relevant code
- **Function signatures** and type definitions
- **Data flow** through the component
- **Existing tests** and what they verify
- **Patterns observed** (not recommended — just observed)

Do not suggest changes. Do not propose implementations. Do not offer opinions.
