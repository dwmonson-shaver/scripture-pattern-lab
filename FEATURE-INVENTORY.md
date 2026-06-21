# Feature Inventory — Scripture Pattern Lab Workbench

> **Why this exists.** Features were being demonstrated across *two different mockups* (an interactive prototype and a visual design reference) plus the built backend, and it became unclear what we had and where. This is the **single source of truth**: every feature we've designed, which slice it belongs to, its status, and where it was last seen. Update this whenever a feature is added, moved between slices, or built. Created 2026-06-20.

## Legend
- **Status:** `built` (code on main) · `proto` (works in the interactive prototype) · `ref` (shown in the visual design reference) · `designed` (in a doc/DEC, not yet shown) · `proposed` (discussed, not yet specified)
- **Seen in:** `IP` = interactive prototype (artifact `94eb62aa…`) · `VR` = visual reference (artifact `54af6e3c…`) · `code` = built in repo
- ⚠️ = **regressed**: was demonstrated, then dropped from the newest artifact — must be recovered.

---

## SLICE 1 — Concept Identification (the workbench)

| Feature | Status | Seen in | Notes |
|---|---|---|---|
| Chapter reader (English text) | built + ref | code, VR | read API `GET /read/{corpus}/{book}/{chapter}` |
| English versions + switcher (KJV default; WEB/BSB/ASV/YLT) | built (KJV) / proto | code, IP | VR switcher is cosmetic; IP had it functional |
| Canon › Book › Chapter navigation | proto | IP | VR shows it cosmetic; backend read API exists |
| Continuous scroll through a book; chapter # in margin | ref | VR | |
| Versed ↔ Continuous reading mode toggle | ref | VR | **default = Versed** |
| Original-language interlinear toggle (context-sensitive; hidden for English-original) | ref | VR | Greek/Hebrew per corpus |
| Word-level Greek alignment + transliteration always shown | ref | VR | each Greek word ↔ its English word |
| Tap a Greek word → flash the English it translates (bidirectional) | ref | VR | |
| Select a phrase of text | proto | IP | |
| Selection handles — expand/shrink across lines, finger/Pencil-friendly | proto + ref | IP, VR | **recovered into VR (v7).** Offset-model resize, word-snapping, within-verse (across visual lines); cross-verse still the open hard case |
| Selection popup — action set on a selection | proto + ref | IP, VR | **recovered into VR (v7).** Mark as concept / Just highlight / Cancel + 3-state dismissal |
| Marks = span annotations (cross-verse) | built | code | marks CRUD API |
| Concept create (name, color, polarity, opposite) | built + proto + ref | code, IP, VR | |
| Concept edit (name, color) + paired opposite (name, color) | ref | VR | **recovered + extended into VR** (the axis-pairing edit screen) |
| **Edit a concept's polar opposite (name + color) on the same screen; see both poles** | designed | — | new design — the axis pairing; specified below |
| Concept library list + live search | ref + proto | VR, IP | |
| Reassign a mark's concept / add a 2nd concept | proto | IP | |
| Multi-select concepts (toggle, click-empty-to-clear) | ref | VR | |
| Dimming on select (dim fill, keep underline) | ref | VR | |
| iPad/touch: slide-over panel + large tap targets; app-shell (only text scrolls) | proto + ref | IP, VR | IP drawer; VR shell + iPad preview |
| Marker-stroke highlight aesthetic + illuminated opening | ref | VR | |

**Selection action set (what you can DO to a selection) — Slice 1:** `Mark as concept` · `Just highlight`. *(Later: `Make connection` → Slice 2; `Tell me about this` → Slice 3.)*

## SLICE 2 — Connections & Axes
| Feature | Status | Notes |
|---|---|---|
| Connection entity — typed edges (opposite/prerequisite/produces/sequence/compound/association/unknown) | designed | DEC-131 |
| **"Make connection" interaction** — select concept → *Make connection* → tap the other concept | proposed | interface specified below |
| **Visual representation of a connection** (arc/line between marks; Connections library tab) | proposed | specified below |
| Axis — promoted opposite-connection with signed poles; polarity-aligned | designed | DEC-133; the edit-opposite screen is its Slice-1 seed |
| Pattern = sequence connection + observations | designed | DEC-132 |
| Compound connection (declarable now) | designed | DEC-134 |

## SLICE 3 — Evidence, Citations & OKF
| Feature | Status | Notes |
|---|---|---|
| Per-selection AI explainer ("Tell me about this") — ground-truth vs AI, cited | proto | IP; for/against requires a named hypothesis |
| Two-layer dossier (Overview / Member-by-member / Citations tabs) | designed | DEC-137 |
| Fit-strength per member | designed | reuses `GroupingMember.confidence` |
| Citation-integrity pipeline (quote + link + 3 gates + audits) | designed | DEC-138 |
| OKF source archive (wiki layer) | designed | DEC-139 |
| Context-sensitive AI prompts | ref | VR (explainer chips) |

## SLICE 4 — Patterns & the super-pattern
| Feature | Status | Notes |
|---|---|---|
| Super-pattern honesty protocol (beat-chance / beat-alternatives / count-violations / hold-out / pre-register / strict-loose) | designed | DEC-136 |
| Three grades of relational evidence (proximity / order / explicit) | designed | DEC-135 |

## SLICE 5 — Discovery & Lens
| Feature | Status | Notes |
|---|---|---|
| Proactive discovery agent (proposals only; ai_suggested/unverified) | designed | DEC-140 |
| Research lens + bias guardrails (absence + off-lens + rival readings) | designed | DEC-141 |

---

## Process rule (so this doesn't happen again)
Before publishing a new mockup iteration, diff it against this inventory: any Slice-1 feature marked `proto`/`ref` that the new version drops gets a ⚠️ here and is recovered or explicitly re-scoped — never silently lost. **As of v7 the two mockups are unified** — the visual reference (VR) now carries both the visual identity *and* the interactions (selection popup, resize handles, concept+opposite editing). The interactive prototype (IP) remains as the historical reference. No ⚠️ open.
