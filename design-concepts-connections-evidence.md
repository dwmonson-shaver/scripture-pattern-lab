# Design Discussion: Concept Identification, Connections & Evidence (Umbrella Vision)

> **Scope note.** This is larger than a normal ~200-line single-slice design doc on purpose. It is the **umbrella vision** captured from the design conversation of **2026-06-20**, spanning several future slices. Each buildable slice (see *Proposed Slices*) will get its own tighter `design-*.md` + `structure-*.md` before code. Nothing here is built yet; this exists so the conversation's decisions don't evaporate. Decisions are logged as **DEC-127 … DEC-143** in `docs/governance/decision-log.md` (status: *Accepted (design); implementation OWED*).

## Goal
Give the human a **visual scripture-marking workbench** to identify **concepts** (what expressions mean) and **connections** (how concepts relate) directly in the biblical text, then accumulate **cited, two-sided, human-gated evidence** for each — turning the user's marks into hypotheses the symbolic engine and corpus can test.

## Current State (what we build on)
- **Corpus:** MorphGNT, 27 NT books, ~138K tokens with per-word `lemma`, `morph_code`, `pos`, `surface_form` (`tokens_table`, `src/engine/_schema.py`). No English text yet; no chapter/verse read endpoint (corpus is only reachable via the DSL pipeline).
- **Engine:** DSL parser + `src/engine/executor.py` supports `lemma:`/`concept:` nodes and **PRECEDENCE** (order-preserving, gap-tolerant) over verse / window scopes. `src/retrieval/contextualization.py` already computes **node baselines** (per-step corpus counts) and **alternative-ordering counts** — the raw material for the super-pattern honesty test.
- **Ontology:** `src/ontology/registry.py` — `concepts_table` (name, description, `origin`, `verification_state`), `concept_lemmas`, **`polarity_claims` (+/−/±)**, **`inverse_claims` (A inverse-of B)**. The last two are *primitive connections already*.
- **Tier-2 curator (Slice P):** `src/ontology/concept_grouping.py` — `Tier2Grouping` (always `unverified`), append-only `grouping_promotions` audit table, `promote_grouping` (human-actored, forward-only states unverified → corpus_observed → human_confirmed), `src/retrieval/grouping_evidence.py` (cooccurrence counts + sample refs; never advances state). Promotion API `POST /api/v1/concepts/{name}/grouping/promote`.
- **Frontend:** Nuxt 3 + Vue + Vuetify (`web/`), deployed to Cloudflare; typed proxy to backend; `gen:types` from OpenAPI. Conceptual Document already renders a **ground-truth lexicon section** (`ComparativeLexiconSection.vue`, green "Lexicon data") separate from **AI prose** (`EducationalArticleSection.vue`, disclaimer + model label + cited sources) — the ground-truth-vs-AI separation this vision generalizes.
- **Charter (CLAUDE.md, DEC-002/081/102):** symbolic retrieval is the core; AI is the assistant layer; the corpus tests priors, it does not confirm them; conceptual claims are human-gated and never auto-promoted.

## Desired End State (the product vision)

### 1. The Reader
A clean, chapter-by-chapter reading view (LDS-online-style), serif text, finger/Pencil-friendly. **Canon › Book › Chapter** breadcrumb that leaves room for OT, then other corpora (Book of Mormon, D&C, Pearl of Great Price, Nag Hammadi, Dead Sea Scrolls, Apocrypha). A **version switcher** over ingested English translations (default **KJV**; open: **BSB, ASV, YLT, WEB**; licensed/later: **LEB, ESV, NASB**). A **context-sensitive original-language toggle** ("Greek" for NT, "Hebrew" for OT, hidden for English-original texts) that reveals an interlinear; tapping an interlinear chip highlights the word it maps to (bidirectional). BSB's word-level alignment is the source for English↔Greek mapping.

### 2. Marking & Concepts
Select a phrase → a minimal popup with verbs (**Mark as concept · Map a connection · Map a pattern · Tell me about this · Just highlight**). A **mark** is a *span annotation* (book/chapter/verse + token offsets) tying text to a concept — generalizing beyond single-lemma. Concept work happens in the **right panel** (search-as-you-type, create, edit). Concepts are user-editable: **title, color, polarity (+/−/±), opposite**. Marks are re-assignable (change concept, attach a second concept when undecided) and have **draggable handles** to adjust the span (word-snapping). Cross-verse / region selection is required for patterns (DEC-143).

### 3. Connections (the new first-class element)
A **connection** is a typed edge between concepts — *how* distinct concepts relate, not *what* they are. It carries its own evidence dossier (same machinery as concepts). **Types:**
- **opposite** (symmetric) — love ↔ hatred. *(generalizes `inverse_claims`)*
- **prerequisite** (directional) — humility → faith.
- **produces / yields** (directional) — tribulation → patience.
- **sequence** (directional, *n*-ary, ordered) — faith → hope → charity. *(this is what "pattern" is — DEC-132)*
- **compound** (directional, *n* sources → 1 target, conjunctive) — (faith + hope) → charity. *Declarable now; rigorous AND-proof deferred (DEC-134).*
- **association** (symmetric, weak) — co-discussed, relationship TBD.
- **unknown / emergent** — placeholder to refine.

**Axis (earned, not declared — DEC-133):** an `opposite` connection, *once it crosses an evidence threshold* (curator `corpus_observed`), unlocks a signed **axis node** (+pole / −pole). Other connections may then target a pole; a connection between two axes may be **polarity-aligned** (faith→life ‖ unbelief→death). This captures antithetical parallelism and lets the engine fire on either pole.

### 4. Patterns & the super-pattern
"Map a pattern" over a region records a **sequence connection** + its first **pattern-observation** (the region). Evidence is gathered by compiling the sequence to a precedence DSL query at the **concept** level (so analogues are caught, not just literal words). The honesty protocol below governs sequence claims only.

### 5. Evidence, dossiers, citations (shared by concepts AND connections)
Two layers (DEC-137): a **per-member dossier** (why *this* phrase/endpoint belongs) and a **rollup** (the "paper" arguing why the whole thing hangs together). Tabs: **Overview · Member-by-member · Citations**. A per-member **fit-strength** (the existing `GroupingMember.confidence` 0–1 — "maybe" vs "strong fit") and the curator state machine.
**Citation integrity (DEC-138):** every AI evidence item carries a **verbatim extracted quote + resolvable source link**, and passes three gates before counting: (a) quote-presence in the fetched source, (b) URL resolves *and is snapshotted*, (c) NLI entailment that the quote supports the claim. Failures are **flagged, not shown**. **Periodic audits** re-run the gates. AI never confirms or advances state.
**Storage (DEC-139):** archived sources stored as **Open Knowledge Format (OKF)** Markdown (Google Cloud OKF v0.1: Markdown + YAML frontmatter, spec in `GoogleCloudPlatform/knowledge-catalog`), **extended** with `author`, `source_url`, `retrieved_at`, `content_hash` (v0.1 lacks dedicated provenance fields — it has `resource:` + a `# Citations` body section). This is the wiki layer that defeats link-rot.

### 6. AI: two modes, both human-gated
- **Reactive explainer** (per-selection "Tell me about this"): ground-truth block (verifiable) + AI block (cited). For/against evidence appears **only once a concept hypothesis is named** — you can't argue a mapping you haven't proposed. Prompts are **context-sensitive** (no "Explain the Greek" for English-original texts).
- **Proactive discovery (DEC-140):** an agent scans one/several chapters (English + Greek) and proposes candidate concepts, connections, and connection *types* (Greek connectives are real type evidence). All output is `origin='ai_suggested'`, `verification_state='unverified'` — proposals into a human review queue, never facts.
- **Research lens (DEC-141):** a saved focus-set of concepts/connections directs the discovery agent's *attention* — but it is **required** to also report (1) where focus-concepts are **absent**, (2) **off-lens** findings, (3) **rival readings**. The lens directs attention, never conclusions.

### 7. Epistemic discipline — three grades of relational evidence (DEC-135)
Do **not** conflate these; each supports a different connection type, and the order-test applies to **only one**:
1. **Co-mention / proximity** → **association**. Order-blind. Out-of-order co-occurrence is *confirming*, not violating. (People don't talk in syllogisms.)
2. **Order-preserved recurrence** → **sequence**. *The only* claim the order-test and alternative-ordering counts govern.
3. **Explicit authorial statement** ("X leads to Y") → **prerequisite/produces**. Strongest; scored on its own track; **never overridden** by a statistical order-test. A real prerequisite *reinforces* a sequence, it is not erased by out-of-order discussion.

**Super-pattern honesty protocol (DEC-136)** — a sequence/pattern claim earns the name only by surviving:
- **Beat chance** — observed in-order count must exceed the null expectation from member frequencies (uses `compute_node_baselines`).
- **Beat alternatives** — faith→hope→charity must dwarf the other orderings, else it's co-occurrence, not sequence (uses `compute_alternative_orderings`).
- **Count violations/absences out loud** — report order breaks, 2-of-3 partials, missing members. A pattern never allowed to fail is never tested.
- **Hold out** — develop in one book, confirm in unseen books (1 Cor 13, 1 Thess).
- **Pre-register** — hypothesis recorded *before* the count; verdict (incl. failure) is binding.
- **Strict vs loose zoom** — report with literal lemmas *and* analogue-expanded concepts; a pattern visible only under generous expansion is flagged as weaker / more prior-dependent.

## Entity Model (summary)
- **Concept** — node: name, description, color, polarity, opposite, origin, verification_state, lemma/phrase members.
- **Annotation (mark)** — span: corpus + book/chapter/verse + token offsets → 1..n concept refs; actor; created_at.
- **Connection** — typed edge: type, ordered/unordered members (concept refs, with pole for axis targets), directional flag, description, dossier, curator_state.
- **Axis** — derived: a promoted `opposite` connection exposing +pole/−pole.
- **Evidence item** — {stance: supports|refutes|neutral, source_type: corpus|lexicon|pattern|scholarly_ai|human, quote, citation/OKF-ref, confidence, actor, audit_status}.
- **Pattern observation** — evidence for a sequence connection: a corpus region + the ordered concept instances exhibiting it.
- **Lens** — named focus-set: concept refs + connection refs (+ optional corpus range).

## Proposed Slices (sequencing)
1. **Slice 1 — Concept Identification UI:** reader (KJV + ≥1 open version, interlinear), span-mark annotations, concept create/edit (color/polarity), concept library, per-phrase Greek, the reactive explainer's *ground-truth* entry point. *(The clickable prototype proves this.)*
2. **Slice 2 — Connections & Axes:** the connection entity + types (incl. compound placeholder), the two new gestures, axis promotion, connection dossiers.
3. **Slice 3 — Evidence, Citations & OKF:** dossier tabs, fit-strength, the citation-integrity pipeline, OKF store, audits, the AI explainer's for/against track.
4. **Slice 4 — Patterns & the super-pattern:** sequence evidence via precedence DSL, the honesty protocol, contextualization wiring.
5. **Slice 5 — Discovery & Lens:** proactive scan, proposal queue, lens + bias guardrails.

## Key Design Decisions
| DEC | Decision |
|-----|----------|
| 127 | Next user-facing surface is a visual concept-identification reader (scripture-marker UI). |
| 128 | Ingest an English translation layer (KJV default; BSB/ASV/YLT/WEB open; LEB/ESV/NASB later), verse-aligned; original language surfaced per-token via interlinear (BSB alignment). |
| 129 | Marks are **span annotations** (offsets) → concept(s), generalizing beyond single-lemma. |
| 130 | Concepts gain user create/edit incl. **color**, polarity, opposite (new concept-write API). |
| 131 | **Connection** is a new first-class typed edge (opposite/prerequisite/produces/sequence/compound/association/unknown), generalizing `inverse_/polarity_claims`. |
| 132 | **Pattern is not a separate entity** — it is the `sequence` connection type + its observations. |
| 133 | **Axis is earned**: an `opposite` connection that reaches `corpus_observed` unlocks a signed axis node; cross-axis connections may be polarity-aligned. |
| 134 | **Compound** connection type is declarable now; rigorous AND-verification deferred. |
| 135 | **Three grades of relational evidence** (proximity→association / order→sequence / explicit→prerequisite); the order-test governs sequence only and never overrides an explicit prerequisite. |
| 136 | **Super-pattern honesty protocol** (beat-chance, beat-alternatives, count-violations, hold-out, pre-register, strict/loose zoom). |
| 137 | Concepts and connections share the **two-layer dossier** + citation machinery. |
| 138 | **Citation-integrity pipeline**: verbatim quote + resolvable link, gated by presence/resolution/entailment; failures flagged; periodic audits; AI never promotes. |
| 139 | **OKF** (extended frontmatter) is the archived-source wiki layer. |
| 140 | **Two AI modes**: reactive explainer + proactive discovery; both emit only `ai_suggested`/`unverified` proposals. |
| 141 | **Lens** directs attention but must report absence + off-lens + rival readings (bias guardrail). |
| 142 | iPad/touch is a first-class target (slide-over panel, large handles, selection-driven triggers). |
| 143 | **Cross-verse/region selection** is required (lifts single-verse marking for patterns). |

## Patterns to Follow
- Ground-truth-vs-AI visual separation already in `ComparativeLexiconSection.vue` / `EducationalArticleSection.vue`.
- Human-gated, append-only promotion + `origin`/`verification_state` epistemics (`concept_grouping.py`, `grouping_promotions`).
- `confidence` on `GroupingMember` as the fit-strength primitive.
- Precedence + contextualization for all order/pattern math (don't reinvent).

## Patterns to Avoid
- AI writing into the verified layer or advancing curator state (DEC-081/126).
- Treating co-occurrence as a sequence, or order-violation as disconfirming a prerequisite (DEC-135).
- Building the conjunction/logic engine before evidence demands it (DEC-134).
- A lens that only confirms (DEC-141).

## Open Questions
1. Endpoints of a connection: always concepts (mint inline if needed) — confirmed concept-to-concept. Any case needing a raw-span endpoint? (Currently: no.)
2. OKF license terms (check repo `LICENSE`) before adopting as the store.
3. Cross-verse selection UX on touch (native iOS selection across paragraphs is awkward) — needs prototyping.
4. Fit-strength: subjective slider vs. evidence-derived score vs. both?

## Risks and Concerns
- **Confirmation bias** is the dominant risk; the lens, discovery, and super-pattern tests all carry explicit counterweights, but they must be *enforced by schema/pipeline*, not convention.
- **Hallucinated citations** — mitigated by the three-gate pipeline + audits + OKF snapshots; un-snapshottable claims must never display as evidence.
- **Scope** — five slices; resist horizontal building. Slice 1 must ship a runnable surface before the rest.

## References
- Conversation 2026-06-20 (this design session); clickable prototype (concept-marking workbench).
- DEC-002, DEC-081, DEC-102 (charter: symbolic core, AI assistant, human-gated conceptual claims).
- DEC-119–126 (Slice P curator/promotion lineage this extends).
- Google Cloud **Open Knowledge Format v0.1** — `GoogleCloudPlatform/knowledge-catalog` (`okf/SPEC.md`).
- Citation-integrity literature: ALCE, RARR, Chain-of-Verification, FActScore, NLI-attribution.

## Spec Requirements Touched
_New REQ markers to be added to canonical docs as each slice's design firms up (reader, annotations, connections, evidence, discovery). Existing: REQ:08.registry-epistemics, REQ:08.curator-promotion, REQ:09.tier-2-groupings-api._
