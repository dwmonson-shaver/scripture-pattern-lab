# Research: Prior Art for Visually Representing Typed Connections in Text (2026-07-05)

Background research (subagent, web sources) for the connections feature — how to
mark and, especially, **visually represent typed connections between passages**
using the margin/gutter of a page. Feeds the Slice 2+ connection-display design.
Not a spec; a source of borrowable ideas.

## The single strongest finding

**Bracketing + the Biblearc "arcing" 18-relationship taxonomy** is the closest
prior art to what we're building: a teachable, decades-refined method for
diagramming **typed, labeled, hierarchical connections between propositions in
scripture**, rendered as **nested brackets in the margin** with a relationship
abbreviation at each bracket. It solves almost exactly our problem.

## Ranked shortlist (most applicable first)

1. **Bracketing + the 18-relationship arcing vocabulary (Biblearc / Piper–Fuller;
   Schreiner "Tracing the Argument"; Naselli "Phrasing").** Already a gutter
   idiom (nested brackets spanning lines, labeled with a typed relationship) AND
   a ready controlled vocabulary. The 18 relationships group as **Coordinate**
   (Series, Progression, Alternative) vs **Subordinate** (support by Restatement
   / Distinct statement / Contrary statement — Ground `G`, Inference `∴`,
   Bilateral, Conditional `If/Th`, Concessive, etc.), each with a compact
   abbreviation. Direction matters (Ground vs Inference = same relation, opposite
   reading order) — a clean model for our interchange direction (divine→human
   vs human→divine). Map the Coordinate/Subordinate super-grouping to color
   families so type is legible at a glance.
2. **Talmud page (Vilna Shas) — typed lanes + spatial anchoring.** Each *kind* of
   commentary gets its own reserved margin ring (Rashi inner = gloss, Tosafot
   outer = dialectical, Masoret ha-Shas = cross-reference), and vertical
   adjacency to the source line *is* the link — no leader lines. Our layout
   backbone: reserve a gutter lane per connection category, anchor by vertical
   position.
3. **Arc diagrams (Harrison & Römhild "Visualizing the Bible" → Viz.Bible),
   scoped to one chapter, colored by type, revealed on hover/toggle.** The proven
   way to draw many links over linear text; the field's own lesson is *filter to
   visible scope + reveal on interaction* or it becomes "beautiful but unreadable"
   (their 340k-link version). Good fit for the "show all connections in this
   chapter" toggle state — an arc band beside the text.
4. **Tufte anchored sidenotes + responsive collapse.** Put connection labels in
   the margin at the anchor's vertical position; collapse into the existing
   iPad slide-over on narrow viewports. Secondary info visible but out of the
   eye's way = the core anti-clutter principle.
5. **TEI stand-off model + Thompson Chain "thread" traversal.** Storage:
   connections as a separate typed layer keyed to offsets/IDs, never mutating the
   corpus (matches "corpus is ground truth"; supports overlapping/discontinuous
   spans). Interaction: a connection can be a *traversable thread* ("jump to the
   other end / next instance"), not just a static line.

## Recommended chapter-view rendering (synthesis)

- **Reading state:** quiet gutter markers only — a colored vertical rule beside
  each span in a connection, colored by category; count badge if multiple.
- **"Show connections" toggle:** open a gutter/margin band; each connection = a
  **bracket spanning its source span** + a **curved tie-line to its target**,
  with the **typed abbreviation at the bracket vertex**; color by category; draw
  the tie-line only on hover/selection (avoids spaghetti). Arrow/bracket
  orientation shows direction.
- **Depth:** nested brackets / indentation for composed connections.
- **Responsive:** collapse the band into the slide-over on iPad.
- **Data:** stand-off annotations (offset refs, `type`, direction).

## Other systems surveyed

- **Adler "How to Mark a Book":** #4 numbers = *sequence* link; #5 other-page
  numbers = *associative "belongs-together"* link; #2 vertical margin line =
  span-across-lines indicator. A minimal two-type taxonomy + the span-rule glyph.
- **Recogito / CATMA:** proof non-technical users can draw typed links between
  highlighted spans and export structured data; the two-view pattern (annotate
  in-text, then a graph/network view of the relations).
- **hypothes.is (W3C Web Annotation):** strong span-anchoring/selector model
  (robust re-location on reflow); weak on typed span-to-span links.
- **Lexham Discourse Greek NT:** ~20 enumerated, queryable discourse relations
  across the whole corpus — precedent for a controlled connection-type
  vocabulary (matches our DSL-first, typed-match charter).
- **Glossa Ordinaria / catenae / Masorah / Thompson Chain / Treasury of Scripture
  Knowledge:** the recurring pattern is *anchor mark in text → typed note in a
  reserved margin zone, tiered by depth/kind*; links by attribution/category,
  not lines.
- **Argument mapping (Toulmin/Walton), Semantic Structure Analysis (SIL):**
  general-purpose typed directed-edge vocabularies (ground/warrant/rebuttal;
  reason/result/manner/condition) — the cousins of arcing.

## Implication for our type vocabulary

Our current claim types (opposite, prerequisite, produces, sequence, compound,
association, interchange, unknown) overlap the arcing set: sequence≈Progression,
prerequisite/produces≈Ground/Inference/Action-Result, opposite≈Negative-Positive,
association≈Series. When we design the connection *display*, consider aligning
our labels/abbreviations and Coordinate-vs-Subordinate color grouping with the
arcing convention rather than inventing our own — it's field-tested for exactly
this reading surface. `interchange` is our addition (divine↔human), with no
direct arcing equivalent — which is a point in its favor as a genuinely new type.
