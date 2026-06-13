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

from itertools import combinations
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, select

from src.engine.executor import execute
from src.engine.parser import parse
from src.ontology.registry import ConceptRegistry, concepts_table

if TYPE_CHECKING:
    from src.ontology.concept_grouping import Tier2Grouping

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


# ---------------------------------------------------------------------------
# Computation — compile to DSL, run the engine, assemble descriptive evidence.
#
# Compiles each member pair to a DSL string (`lemma:A ~ lemma:B
# within:window(N) corpus:nt`) and runs it through parse()+execute() — the
# canonical compile path (CLAUDE.md: "natural language compiles to DSL — never
# bypass it"). Deterministic; no LLM; advances no state.
# ---------------------------------------------------------------------------


def _primary_lemma(
    registry: ConceptRegistry, concept_name: str, language: str
) -> str | None:
    """Return the concept's first registered lemma, or None if it has none.

    A None here is the Bucket-N3 gloss-recall narrowness made visible: a member
    that resolved to no corpus lemma yields zero-evidence rather than silence.
    """
    lemmas = registry.get_lemmas_for_concept(concept_name, language=language)
    return lemmas[0] if lemmas else None


def _concept_ids(names: list[str], engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        rows = connection.execute(
            select(concepts_table.c.id, concepts_table.c.name).where(
                concepts_table.c.name.in_(names)
            )
        ).all()
    return {row.name: row.id for row in rows}


def _declared_inverse_pairs(
    member_names: list[str], registry: ConceptRegistry, engine: Engine
) -> set[frozenset[str]]:
    """Name-pairs the registry ALREADY declares as inverses/polarity opposites.

    Co-occurrence of a declared-inverse pair is expected-as-opposition, not as
    conceptual neighborhood — surfaced so a human is not misled (review finding 2).
    """
    ids = _concept_ids(member_names, engine)
    id_to_name = {cid: name for name, cid in ids.items()}
    pairs: set[frozenset[str]] = set()
    for name, cid in ids.items():
        for claim in registry.get_inverse_claims(cid):
            other = id_to_name.get(claim.inverse_concept_id)
            if other is not None and other != name:
                pairs.add(frozenset((name, other)))
    return pairs


def _pair_dsl(lemma_a: str, lemma_b: str, window_n: int) -> str:
    return f"lemma:{lemma_a} ~ lemma:{lemma_b} within:window({window_n}) corpus:nt"


def compute_grouping_evidence(
    grouping: "Tier2Grouping",
    engine: Engine,
    *,
    window_n: int = DEFAULT_EVIDENCE_WINDOW_N,
    sample_cap: int = 12,
    threshold: int = 1,
    language: str = "grc",
    registry: ConceptRegistry | None = None,
) -> GroupingEvidence:
    """Measure corpus co-occurrence for every member pair of a grouping.

    Runs one cooccurrence-window query per unordered member pair and reports
    match count + sample verse refs + whether the pair is a declared inverse.
    ``threshold`` only sets the DESCRIPTIVE ``cooccurrence_threshold_met`` flag;
    it gates NOTHING (DEC-120) — the human sees the raw count and decides.
    """
    registry = registry or ConceptRegistry(engine)
    member_names = [m.concept_name for m in grouping.members]
    lemmas = {name: _primary_lemma(registry, name, language) for name in member_names}
    inverse_pairs = _declared_inverse_pairs(member_names, registry, engine)

    pairs: list[EvidencePair] = []
    for member_a, member_b in combinations(member_names, 2):
        lemma_a, lemma_b = lemmas[member_a], lemmas[member_b]
        is_inverse = frozenset((member_a, member_b)) in inverse_pairs
        if lemma_a is None or lemma_b is None:
            pairs.append(
                EvidencePair(
                    member_a=member_a, member_b=member_b,
                    lemma_a=lemma_a, lemma_b=lemma_b,
                    match_count=0, window_n=window_n,
                    is_declared_inverse=is_inverse,
                )
            )
            continue
        plan = parse(_pair_dsl(lemma_a, lemma_b, window_n))
        candidates = execute(plan, plan.scope, engine, concept_registry=registry)
        refs = [c.reference for c in candidates][:sample_cap]
        pairs.append(
            EvidencePair(
                member_a=member_a, member_b=member_b,
                lemma_a=lemma_a, lemma_b=lemma_b,
                match_count=len(candidates), sample_refs=refs, window_n=window_n,
                is_declared_inverse=is_inverse,
                cooccurrence_threshold_met=len(candidates) >= threshold,
            )
        )
    return GroupingEvidence(anchor_name=grouping.anchor_name, window_n=window_n, pairs=pairs)

