# Prompt for Vibe Code Tool

You are setting up a project repository for an AI-assisted scripture pattern exploration platform.

## Your task
Using the markdown files already present in this folder, create a clean repository and preserve the docs as the source of truth.

## Folder structure to create
- /docs/canonical
- /docs/governance
- /docs/references/evidence
- /app
- /backend
- /frontend
- /schemas
- /queries
- /ontology
- /examples
- /prompts

## Required actions
1. Keep the existing docs intact and do not overwrite their content.
2. Create a root README that explains the project purpose and points to the canonical docs.
3. Create placeholder README files in backend, frontend, ontology, queries, schemas, and prompts describing what belongs in each folder.
4. Create a `ROADMAP_NEXT_STEPS.md` file at the root that summarizes the next implementation steps.
5. Create a `SESSION_HANDOFF.md` file at the root that tells the next working session to begin with `docs/canonical/04_node-ontology.md`.
6. Create a lightweight `CHANGELOG.md` initialized with the current documentation bootstrap.
7. Do not invent application code yet beyond minimal scaffolding and comments.

## Constraints
- Treat the docs as authoritative.
- Do not collapse the distinction between canonical docs, governance docs, and evidence notes.
- Preserve traceability.
- Keep scaffolding clean and minimal.

## Next-step priorities to write into ROADMAP_NEXT_STEPS.md
1. Define node ontology.
2. Define internal AST for the DSL.
3. Define capability validator contract.
4. Define example query-to-AST transformations.
5. Choose MVP corpus scope.
6. Sketch backend service boundaries.

## Important project rules
- Natural language must compile to DSL rather than bypass it.
- The system must say when it cannot do something yet.
- Symbolic retrieval is the core engine.
- Embeddings and semantic retrieval are secondary supporting layers.
- Polarity-aware and inverse-pattern analysis are part of the design foundation.
