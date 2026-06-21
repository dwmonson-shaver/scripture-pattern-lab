# Independent Review — Slice 1 reader-alignment (study-edition parchment)

- **Date:** 2026-06-21
- **Reviewer:** claude-fallback (Codex blocked by the recurring `~/.codex/sessions`
  root-ownership perms class — same Bucket-P-Codex blocker; `sudo chown -R $(whoami)
  /Users/dwmonson/.codex` still owed. The codex-rescue subagent reported the exact
  blocker this session.). Ran the same P0/P1/P2/P3 severity language + checklist as the
  Codex pass, per the E/F/J1/K/M/N/O/P fallback precedent.
- **Scope:** cumulative reader-alignment diff `c24fa43..b2d4969` — a Nuxt/Vue/Vuetify
  FRONTEND-only refactor of the existing Slice-1 reader toward the approved v8 spec
  `docs/design/reader-reference.html` under DEC-150/151/152. 6 phases:
  P1 parchment theme tokens + THEME.md; P2 illuminated opening + gilt versal + scripture
  typography; P3 Versed/Continuous mode toggle + interlinear placement; P4 selection-popup
  three-state dismissal; P5 multi-select concept highlight (dim-others-keep-underline) +
  gilt span handles + SpanHandles vitest fix; P6 app-shell + scroll-spy + iPad slide-over +
  ConceptPanel test fix.
- **Web DoD at review:** GREEN — lint:check + typecheck + vitest (187/187, then 189/189
  after fixes) + check:no-llm-sdk.

## Verdict: CLEAN (minor-fixes-recommended on P3s) → clean after fix

No P0/P1/P2 at any pass. Charter rules all satisfied: DEC-081 (no LLM SDK in the bundle —
grep-clean), alignment honesty (verse-level tokens only; flashGloss explicitly labeled
approximate; `TODO(DEC-align)`; no fabricated per-word alignment), and THEME discipline
(no `text-white`/`text-black`/Tailwind/stray chrome hex; the only sanctioned raw colors are
concept `authored_color` (content, inline) + the parchment grain data-URI + the gilt ramp).

## Findings ledger

| ID | Sev | Disposition |
|----|-----|-------------|
| F1 — DEC-081 no LLM SDK | info | CLEAN (grep-clean) |
| F2 — gilt gradient hex stops inline in ChapterView | P3 | **fixed inline `54fea65`** — lifted to `--gilt-hi`/`--gilt-lo` CSS vars in globals.css |
| F3 — selection's own trailing click dismissing popup | info | CORRECT (`!sel.isCollapsed` guard) |
| F4 — document listeners removed on unmount | info | CORRECT (`onBeforeUnmount` + SSR guards) |
| F5 — spyDriven boolean consumable by a coalesced real nav | P3 | **fixed inline `54fea65`** — replaced boolean with a chapter sentinel (`spyTarget`) + `lastLoaded` scope check |
| F6 — IntersectionObserver lifecycle | info | CORRECT (guarded, disconnect-on-unmount + re-observe) |
| F7 — alignment honesty | info | CLEAN (charter-compliant; code-honest). UI-cue gap noted → **Bucket-RA-1** |
| F8 — open→toggle rename: dead emits/props | info | CLEAN (no orphans) |
| F9 — concept-edit entry path wired-but-unreachable | P3 | **fixed inline `54fea65`** — added MarkDetail "Edit concept" (`@edit`) → reader `onMarkEdit` opens the edit form; reconnects the live update path |
| F10 — Vue/Nuxt idiom | info | CLEAN (script setup, defineModel/defineProps generics, no onMounted fetch, explicit vue lifecycle imports, Set-replacement reactivity) |
| F11 — light→parchment rename + localStorage migration | info | CORRECT (stale `'light'` falls through to default; no crash) |

## Buckets

- **Bucket-RA-1 (NEW) — visible "approximate alignment" UI cue.** The interlinear
  tap-flash (flashGloss) is honestly labeled as an approximate stem-match in code, but a
  reader sees no *on-screen* cue that the flash isn't true per-word alignment. **Trigger:**
  the BSB word-level alignment slice (when the read endpoint surfaces token→English-span
  alignment) — at which point flashGloss is replaced by real ruby AND any interim
  approximation gets a visible affordance. Rationale: adding a UI disclaimer now, ahead of
  real alignment, would be noise; the code is already honest and no per-word claim is
  *rendered*. P3, deferred.
- **Bucket-RA-2 (NEW) — multi-chapter continuous book scroll.** Scroll-spy is wired but a
  structural no-op (the read API is per-chapter; one chapter loads at a time). **Trigger:**
  any slice that loads adjacent chapters / the whole book so multiple openings exist. The
  F5 sentinel fix already hardens the reload-suppression for that future. P3, deferred.
- **Bucket-P-Codex — re-deferred.** Codex still blocked by the `~/.codex/sessions` perms
  class. Trigger unchanged: next session in which `sudo chown -R $(whoami) /Users/dwmonson/.codex`
  has been run and `/codex:rescue` is reachable — run an authoritative Codex pass over
  Slice P, Slice 1 (`975aeb3..b823065`), AND this reader-alignment diff
  (`c24fa43..54fea65`), with attention to DEC-152 theme discipline, the three-state
  dismissal logic, the scroll-spy guard, and alignment honesty.

## Closure SHAs

Phase chain: `e5e4d2a` (structure) → `f2b4660` (P1 theme) → `c9183c5` (P2 opening) →
`bc50d67` (P3 mode toggle) → `26a2a51` (P4 dismissal) → `4f7a4c7` (P5 multi-select +
span-handle fix) → `b2d4969` (P6 app-shell + scroll-spy) → `54fea65` (slice-close
F2/F5/F9 fixes). Baseline test fails inherited at `c24fa43` (SpanHandles x2, ConceptPanel
x2) all closed in-slice (P5 + P6). Final web DoD green: 189 vitest pass / 0 fail.
