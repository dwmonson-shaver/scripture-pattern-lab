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
from sqlalchemy import Engine, select, update

from src.ontology.registry import Origin, VerificationState, concepts_table

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


# ---------------------------------------------------------------------------
# Persistence — writer + readers
#
# DEC-115 Layer A: write_grouping() takes NO verification_state parameter.
# The only value it ever writes is GROUPING_VSTATE. Combined with Layer B's
# model-level Literal + validator, this means a Tier-2 grouping CANNOT be
# auto-promoted to 'human_confirmed' from any code path through this module.
# ---------------------------------------------------------------------------


def _all_member_concepts_exist(member_names: list[str], engine: Engine) -> set[str]:
    """Return the subset of names NOT present in the concepts table.

    Empty set = all exist. Caller raises ValueError naming the missing ones.
    """
    with engine.connect() as connection:
        present_rows = connection.execute(
            select(concepts_table.c.name).where(concepts_table.c.name.in_(member_names))
        ).scalars().all()
    return set(member_names) - set(present_rows)


def write_grouping(grouping: Tier2Grouping, engine: Engine) -> Tier2Grouping:
    """Persist a Tier-2 grouping. Returns the (validated, persisted) grouping.

    DEC-115 Layer A: this function has NO verification_state parameter — the
    only value ever written is GROUPING_VSTATE='unverified'. The grouping
    argument is itself guarded by Layer B (Pydantic Literal + model_validator).

    Idempotent: re-writing the same grouping (same anchor + same member set)
    UPDATEs the existing anchor row in-place (last writer wins for rationale +
    confidences); member pointer rows are merged additively (a concept may be
    a member of multiple groupings).

    Raises:
      ValueError if any member concept does not exist (OQ-2 resolution: this
        slice does NOT auto-create members; the seed CLI does the Tier-1
        auto-create up front).
      ValueError if the anchor concept document does not yet exist (DEC-106
        store-once: a grouping is layered ON TOP of an existing document).
    """
    from src.ontology.concept_document import concept_documents_table

    member_names = [m.concept_name for m in grouping.members]
    missing = _all_member_concepts_exist(member_names, engine)
    if missing:
        raise ValueError(
            f"cannot write grouping anchored on {grouping.anchor_name!r}: "
            f"these member concepts do not exist: {sorted(missing)!r}. "
            "Auto-create them via the Slice-N path first."
        )

    blob = grouping.model_dump(mode="json")
    non_anchor = [n for n in member_names if n != grouping.anchor_name]

    with engine.begin() as connection:
        # Anchor doc must already exist (DEC-106 store-once).
        anchor_row = connection.execute(
            select(concept_documents_table.c.id).where(
                concept_documents_table.c.concept_name == grouping.anchor_name
            )
        ).first()
        if anchor_row is None:
            raise ValueError(
                f"anchor document for {grouping.anchor_name!r} does not exist; "
                "call persist_document(...) first to lay down the Tier-1 doc, "
                "then write the Tier-2 grouping on top."
            )
        # Layer A in action: only GROUPING_VSTATE is in the blob (the model
        # already enforces that). We never look at a caller-supplied
        # verification_state because the function has no such parameter.
        connection.execute(
            update(concept_documents_table)
            .where(concept_documents_table.c.concept_name == grouping.anchor_name)
            .values(part2_grouping=blob)
        )

        # Pointer rows on each non-anchor member. Merge additively: a concept
        # may already be a member of another grouping (the pointer's anchor
        # list grows). If the member doc doesn't exist yet, skip the pointer
        # write — the pointer is a navigational nicety, not load-bearing data
        # (the canonical store remains the anchor's grouping blob).
        for member_name in non_anchor:
            row = connection.execute(
                select(concept_documents_table.c.part2_grouping).where(
                    concept_documents_table.c.concept_name == member_name
                )
            ).first()
            if row is None:
                continue
            existing = row.part2_grouping if isinstance(row.part2_grouping, dict) else None
            # Refuse to clobber an anchor blob (data-loss guard, Bucket-O1
            # → Codex Slice-O P0): if this member's part2_grouping already
            # holds an anchor blob (has "members"), that means the concept
            # is anchor of a different grouping. Silently overwriting with
            # a pointer would lose the other grouping's data. Multi-role
            # membership (one concept anchors G1 and is member of G2)
            # requires a storage-model change; raise loudly until that
            # design lands.
            if existing is not None and "members" in existing:
                raise ValueError(
                    f"anchor-blob clobber: cannot write pointer for "
                    f"{member_name!r} because that concept is already the "
                    f"anchor of another grouping. Multi-role membership "
                    f"(one concept as anchor of one grouping AND member of "
                    f"another) requires a storage-model change — see "
                    f"Bucket-O1 in docs/governance/reviews-log.md."
                )
            existing_anchors: list[str] = []
            if existing is not None and "grouping_anchors" in existing:
                existing_anchors = list(existing.get("grouping_anchors") or [])
            if grouping.anchor_name not in existing_anchors:
                existing_anchors.append(grouping.anchor_name)
            pointer = GroupingPointer(grouping_anchors=existing_anchors)
            connection.execute(
                update(concept_documents_table)
                .where(concept_documents_table.c.concept_name == member_name)
                .values(part2_grouping=pointer.model_dump(mode="json"))
            )
    return grouping


def read_grouping_for_anchor(
    anchor_name: str, engine: Engine
) -> Tier2Grouping | None:
    """Read the canonical grouping blob from the anchor's document.

    Returns None if the anchor's document doesn't exist, has no part2_grouping
    blob, or the blob is a GroupingPointer (the concept is a member of
    another grouping, not an anchor).
    """
    from src.ontology.concept_document import concept_documents_table

    with engine.connect() as connection:
        row = connection.execute(
            select(concept_documents_table.c.part2_grouping).where(
                concept_documents_table.c.concept_name == anchor_name
            )
        ).first()
    if row is None or not isinstance(row.part2_grouping, dict):
        return None
    if "members" not in row.part2_grouping:
        return None  # it's a pointer, not an anchor blob
    try:
        return Tier2Grouping.model_validate(row.part2_grouping)
    except Exception:  # noqa: BLE001
        # Schema drift on JSONB → no grouping rendered, not a broken doc.
        return None


def read_grouping_pointer(
    concept_name: str, engine: Engine
) -> GroupingPointer | None:
    """Read the GroupingPointer for a non-anchor member, if present."""
    from src.ontology.concept_document import concept_documents_table

    with engine.connect() as connection:
        row = connection.execute(
            select(concept_documents_table.c.part2_grouping).where(
                concept_documents_table.c.concept_name == concept_name
            )
        ).first()
    if row is None or not isinstance(row.part2_grouping, dict):
        return None
    if "grouping_anchors" not in row.part2_grouping:
        return None
    try:
        return GroupingPointer.model_validate(row.part2_grouping)
    except Exception:  # noqa: BLE001
        return None
