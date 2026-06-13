"""Corpus-evidence finder for Tier-2 groupings (Slice P, Scope C).

Given a ``Tier2Grouping`` (a CLAIM that 2+ concepts hang together), this module
measures whether the members' lemmas actually CO-OCCUR in the corpus, by running
the existing Slice-L cooccurrence/window engine over each member-pair. It lives in
``src/retrieval`` because it ORCHESTRATES the engine executor (multi-stage
retrieval) — ``src/ontology`` must never import the engine (architecture boundary,
CLAUDE.md). The promotion writer that consumes this evidence lives in
``src/ontology/concept_grouping.py``; the app layer wires the two together so the
import direction stays retrieval→engine and app→{retrieval, ontology}, never
ontology→retrieval (design OQ-6).

EPISTEMIC CONTRACT (DEC-120, after the Slice-P design review):
  * Evidence REPORTS, it never PROMOTES. Nothing here advances a grouping's
    curator_state. Every advance past 'unverified' is a human action.
  * ``cooccurrence_threshold_met`` is a DESCRIPTIVE boolean OFF the
    unverified→corpus_observed→human_confirmed lifecycle axis. It is a
    convenience flag over a raw count, not a verification state.
  * Co-occurrence is NOT proof of conceptual neighborhood — antonyms co-occur
    constantly (love/hate, life/death). So each pair also reports whether the
    registry already declares the pair an inverse/polarity relation, and the
    raw match_count + sample refs, so a human judges RELEVANCE, not frequency.

This module performs NO LLM calls (deterministic corpus measurement only).

The ``compute_grouping_evidence`` function lands in Phase 2; Phase 1 defines the
result models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

#: Default cooccurrence window in tokens — Slice-L paragraph scale (DEC-094).
DEFAULT_EVIDENCE_WINDOW_N: int = 50
#: Honest framing carried on every evidence record so no consumer mistakes a
#: co-occurrence count for an endorsement of the conceptual claim.
EVIDENCE_NOTE: str = (
    "Co-occurrence in the corpus is descriptive evidence, NOT confirmation that "
    "the members are conceptual neighbors. Antonyms and co-pericope terms "
    "co-occur frequently. A human curator weighs this evidence; the corpus does "
    "not advance the grouping's state on its own."
)


class EvidencePair(BaseModel):
    """Corpus co-occurrence evidence for one ordered-agnostic member pair.

    ``lemma_a`` / ``lemma_b`` are the primary resolved Greek lemmas for the two
    member concepts; ``None`` means the concept resolved to no corpus lemma
    (surfaces the Tier-1 gloss-recall narrowness, Bucket-N3). When either lemma
    is ``None`` the pair carries ``match_count=0`` and no sample refs.
    """

    model_config = ConfigDict(frozen=True)

    member_a: str = Field(min_length=1, max_length=64)
    member_b: str = Field(min_length=1, max_length=64)
    lemma_a: str | None = None
    lemma_b: str | None = None
    match_count: int = Field(ge=0)
    sample_refs: list[str] = Field(default_factory=list)
    window_n: int = Field(ge=1)
    # Does the registry ALREADY declare these two an inverse/polarity pair? If
    # so, their co-occurrence is expected-as-opposition, not as-neighborhood —
    # a human must not read it as supporting the grouping.
    is_declared_inverse: bool = False
    # DESCRIPTIVE convenience over match_count — NOT a lifecycle state.
    cooccurrence_threshold_met: bool = False


class GroupingEvidence(BaseModel):
    """Descriptive corpus-evidence bundle for a whole grouping. Read-only.

    Never carries or sets a curator_state. Stored only as an inert snapshot
    inside a ``grouping_promotions`` audit row at human-promotion time.
    """

    model_config = ConfigDict(frozen=True)

    anchor_name: str = Field(min_length=1, max_length=64)
    window_n: int = Field(ge=1)
    pairs: list[EvidencePair] = Field(default_factory=list)
    computed_note: str = EVIDENCE_NOTE
