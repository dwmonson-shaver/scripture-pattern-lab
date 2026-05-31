"""Tier-2 concept-grouping artifact (Slice O, Phase O1).

A Tier-2 grouping is a CLAIM that 2+ existing concepts "hang together"
conceptually — distinct from Tier-1 lexicon translation mappings (DEC-102).
Per DEC-081 + DEC-115, Tier-2 claims are HYPOTHESES the corpus must test and a
human must validate; this module's writer NEVER auto-promotes a grouping to
``verification_state='human_confirmed'``. The runtime guard is two-layered:

    Layer A (structural): ``write_grouping(...)`` accepts no
        ``verification_state`` parameter. Only the module constant
        ``GROUPING_VSTATE: Literal['unverified']`` is ever written.

    Layer B (model-level): ``Tier2Grouping.verification_state`` is typed
        ``Literal['unverified']`` (Pydantic enforces at construction) AND a
        ``model_validator`` re-asserts the invariant, producing an explicit
        error message naming DEC-081.

Both layers are deliberate — Layer A protects new caller paths, Layer B
protects against direct model instantiation (test code, future MCP tools,
future curator UI). The promotion path (`human_confirmed`) is the scope of a
future curator slice; this module exists in part precisely to prevent that
path from being added by accident.

The grouping itself persists as a JSONB blob in the existing
``concept_documents.part2_grouping`` column (DEC-106/DEC-114). Members other
than the anchor receive a lightweight ``GroupingPointer`` in their own
document's ``part2_grouping`` so any concept in the grouping can be navigated
back to the canonical anchor.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.ontology.registry import Origin, VerificationState

# DEC-115 Layer A: the only verification_state this writer ever emits.
GROUPING_VSTATE: VerificationState = "unverified"
# Default origin for hand-curated groupings. ai_suggested is also permitted
# (future LLM-assembled groupings); lexicon_imported is NOT (groupings are
# Tier-2 claims, not lexicon facts).
GROUPING_ORIGIN: Origin = "curated"


class GroupingMember(BaseModel):
    """One member of a Tier-2 grouping with its per-edge confidence."""

    model_config = ConfigDict(frozen=True)

    concept_name: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0.0, le=1.0)
    note: str | None = None


class Tier2Grouping(BaseModel):
    """Persisted Tier-2 grouping claim. ALWAYS ``verification_state='unverified'``.

    INVARIANTS (DEC-081 / DEC-115):
      * verification_state is ``Literal['unverified']`` — Pydantic rejects any
        other value at construction (Layer B-i).
      * ``_guard_dec_081`` re-asserts the invariant and produces an explicit
        DEC-081-named error if the Literal is bypassed (Layer B-ii).
      * NEVER auto-promoted to ``human_confirmed`` or ``corpus_observed``.
        Promotion belongs to a future curator slice with explicit human input.

    Storage shape (JSONB serialized via ``.model_dump(mode='json')``):
      anchor_name : str — the concept whose document carries this blob
      members     : list[GroupingMember] (>= 2)
      rationale   : str — free-text explanation of why the members cluster
      origin      : 'curated' | 'ai_suggested' (NEVER 'lexicon_imported')
      verification_state : 'unverified' (NEVER 'human_confirmed')
      created_at  : datetime
    """

    model_config = ConfigDict(frozen=True)

    anchor_name: str = Field(min_length=1, max_length=64)
    members: list[GroupingMember] = Field(min_length=2)
    rationale: str = Field(min_length=1)
    origin: Literal["curated", "ai_suggested"] = GROUPING_ORIGIN
    verification_state: Literal["unverified"] = GROUPING_VSTATE
    created_at: datetime

    @model_validator(mode="after")
    def _guard_dec_081(self) -> "Tier2Grouping":
        # Layer B-ii: defense in depth. Pydantic's Literal already rejects
        # bad verification_state at construction; this re-assertion exists so
        # any bypass (e.g. model_construct, direct __setattr__ via a
        # mutability hole) still produces a DEC-081-named error explaining
        # what was breached and why.
        if self.verification_state != "unverified":
            raise ValueError(
                "DEC-081 violation: Tier-2 groupings are NEVER auto-promoted; "
                f"verification_state must be 'unverified', got "
                f"{self.verification_state!r}. Promotion to 'human_confirmed' "
                "requires the curator slice (not yet built)."
            )
        member_names = {m.concept_name for m in self.members}
        if self.anchor_name not in member_names:
            raise ValueError(
                f"anchor {self.anchor_name!r} must appear in members "
                f"(got members={sorted(member_names)!r})"
            )
        # Distinct member names — duplicates would silently inflate the
        # grouping size and produce ambiguous pointer writes.
        if len(member_names) != len(self.members):
            raise ValueError(
                "Tier-2 grouping members must have distinct concept_names "
                f"(got {[m.concept_name for m in self.members]!r})"
            )
        return self


class GroupingPointer(BaseModel):
    """Pointer stored on a non-anchor member's document.

    Lets any concept in a grouping be navigated back to the anchor (which
    holds the canonical grouping blob). A single concept may be a member of
    multiple groupings, hence the list.
    """

    model_config = ConfigDict(frozen=True)

    grouping_anchors: list[str] = Field(min_length=1)
