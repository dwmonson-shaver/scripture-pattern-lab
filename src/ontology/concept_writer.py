"""Auto-create a Tier-1 concept from a lexicon resolution (Slice N, Phase N4).

The FIRST write path into the concept registry outside the seed script. Given a
deterministic ``LexiconResolution`` (Phase N3), this writes a concept + its
lemma rows as a machine/lexicon-sourced, unverified, corrigible prior:

    origin             = 'lexicon_imported'   (NEVER 'curated')
    verification_state = 'unverified'         (NEVER auto-promoted to
                                                'human_confirmed' or
                                                'corpus_observed')

This realizes DEC-102's Tier-1 distinction: a single English word ↔ the Greek
lemmas usually translated as it is a low-stakes, lexicon-documented prior that
MAY be auto-generated — but only as machine-sourced + unverified + correctable.
NO LLM touches this path. The concept is the ground truth of Tier 1; any LLM
commentary (Phase N7) is layered on top and never feeds back here.

DEC-081 runtime guard (backported from DEC-115 / Tier-2 in Slice O):

    Layer A (structural): ``auto_create_cited_concept(...)`` accepts NO
        ``verification_state`` or ``origin`` parameter. The only values ever
        written are the module constants ``LEXICON_VSTATE`` (always
        ``'unverified'``) and ``LEXICON_ORIGIN`` (always ``'lexicon_imported'``).
    Layer B-i (model-level Pydantic Literal): ``ConceptCreationOutcome``'s
        ``origin`` and ``verification_state`` are typed
        ``Literal['lexicon_imported']`` and ``Literal['unverified']``. Pydantic
        rejects any other value at construction.
    Layer B-ii (model_validator audit): ``_guard_dec_081`` re-asserts the
        invariant with a DEC-081-named error so any bypass (model_construct,
        future writer that takes a parameter, etc.) produces a debuggable
        trail naming the breached charter rule.

The Tier-2 grouping writer's guard (``src/ontology/concept_grouping.py``) is
the source of this shape; this module is the parallel guard for Tier-1.

Per DEC-025 this is ingestion-shaped registry mutation: it imports the
``Table`` mirrors directly, not the read-only ``ConceptRegistry`` reader, and
writes inside a single ``engine.begin()`` transaction with ON CONFLICT DO
NOTHING for idempotency (same discipline as ``scripts/db/seed_registry.py``).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import Engine, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.ontology.lexicon_resolver import LexiconResolution
from src.ontology.registry import (
    Origin,
    VerificationState,
    concept_lemmas_table,
    concepts_table,
)

LEXICON_ORIGIN: Origin = "lexicon_imported"
LEXICON_VSTATE: VerificationState = "unverified"


class ConceptCreationOutcome(BaseModel):
    """Result of an auto-create attempt. Frozen value object.

    DEC-081 Layer B-i: ``origin`` and ``verification_state`` are pinned to
    ``Literal['lexicon_imported']`` and ``Literal['unverified']``. This is the
    auto-create writer's outcome shape — it describes what THIS writer emits,
    not the read-side state of arbitrary registry rows. The broader
    ``Origin`` / ``VerificationState`` Literals live in ``registry.py`` for
    reader-side use (concepts in any verification state may be read).
    """

    model_config = ConfigDict(frozen=True)

    concept_name: str
    created: bool  # a new concept row was written this call
    reused_existing: bool  # an existing concept already covered the term
    lemmas_written: list[str]
    origin: Literal["lexicon_imported"]
    verification_state: Literal["unverified"]

    @model_validator(mode="after")
    def _guard_dec_081(self) -> "ConceptCreationOutcome":
        # Layer B-ii: defense in depth. Pydantic's Literal already rejects
        # bad values at construction; this re-assertion exists so any bypass
        # (e.g. model_construct, a future writer signature regression that
        # adds a verification_state parameter, direct __setattr__) still
        # produces a DEC-081-named error trail.
        if self.verification_state != "unverified":
            raise ValueError(
                "DEC-081 violation: Tier-1 auto-create NEVER emits a non-'unverified' "
                f"verification_state; got {self.verification_state!r}. Promotion to "
                "'human_confirmed' / 'corpus_observed' requires explicit human input "
                "through a curator path that does not exist yet."
            )
        if self.origin != "lexicon_imported":
            raise ValueError(
                "DEC-081 violation: Tier-1 auto-create NEVER emits a non-'lexicon_imported' "
                f"origin; got {self.origin!r}. Only the lexicon-sourced prior is allowed "
                "on this write path (DEC-102)."
            )
        return self


def find_existing_concept_id(name: str, engine: Engine) -> int | None:
    """Reflect/dedup: return the id of an existing concept with this exact name.

    MVP dedup is exact-name (concepts.name is UNIQUE). A richer
    overlap/alias dedup belongs to the Tier-2 grouping slice; here the goal is
    to avoid re-creating a concept a query already triggered once.
    """
    with engine.connect() as connection:
        return connection.execute(
            select(concepts_table.c.id).where(concepts_table.c.name == name)
        ).scalar_one_or_none()


def auto_create_cited_concept(
    resolution: LexiconResolution,
    engine: Engine,
    *,
    description: str | None = None,
) -> ConceptCreationOutcome:
    """Write a Tier-1 concept from a resolution; reflect/dedup first.

    Idempotent: a concept whose name already exists is reused (its lemma set is
    NOT mutated — the existing rows win). New lemmas for a new concept are
    written with the resolver's per-lemma confidence proxy left NULL (DEC-024:
    confidence is never auto-set to 1.0; lexicon presence is provenance, not a
    calibrated confidence).

    Raises ValueError if the resolution is unresolved — callers must check
    ``resolution.unresolved`` and surface the honest dead-end (422) rather than
    create an empty concept.

    INVARIANTS (asserted by tests):
      * origin is always 'lexicon_imported' on a fresh create.
      * verification_state is always 'unverified'.
      * NEVER 'human_confirmed' / 'corpus_observed'.
    """
    if resolution.unresolved:
        raise ValueError(
            f"cannot create concept for unresolved term {resolution.english_term!r}"
        )

    name = resolution.english_term.strip()
    existing_id = find_existing_concept_id(name, engine)
    if existing_id is not None:
        return ConceptCreationOutcome(
            concept_name=name,
            created=False,
            reused_existing=True,
            lemmas_written=[],
            origin=LEXICON_ORIGIN,
            verification_state=LEXICON_VSTATE,
        )

    lemmas = [rl.lemma for rl in resolution.resolved_lemmas]

    with engine.begin() as connection:
        connection.execute(
            pg_insert(concepts_table)
            .values(
                name=name,
                description=description,
                origin=LEXICON_ORIGIN,
                verification_state=LEXICON_VSTATE,
            )
            .on_conflict_do_nothing(index_elements=["name"])
        )
        concept_id = connection.execute(
            select(concepts_table.c.id).where(concepts_table.c.name == name)
        ).scalar_one()

        for rl in resolution.resolved_lemmas:
            connection.execute(
                pg_insert(concept_lemmas_table)
                .values(
                    concept_id=concept_id,
                    lemma=rl.lemma,
                    language="grc",
                    confidence=None,
                    origin=LEXICON_ORIGIN,
                    verification_state=LEXICON_VSTATE,
                )
                .on_conflict_do_nothing(
                    index_elements=["lemma", "language", "concept_id"]
                )
            )

    return ConceptCreationOutcome(
        concept_name=name,
        created=True,
        reused_existing=False,
        lemmas_written=lemmas,
        origin=LEXICON_ORIGIN,
        verification_state=LEXICON_VSTATE,
    )


def concept_verification_states(name: str, engine: Engine) -> set[str]:
    """Return the distinct verification_state values across a concept + its lemmas.

    Test/diagnostic helper backing the corpus-is-ground-truth invariant: an
    auto-created concept and all its lemma rows must read exactly
    ``{'unverified'}`` — nothing auto-promotes (mirrors the Slice C exit gate).
    """
    states: set[str] = set()
    with engine.connect() as connection:
        states.update(
            connection.execute(
                text(
                    "SELECT DISTINCT verification_state FROM concepts "
                    "WHERE name = :n"
                ),
                {"n": name},
            ).scalars()
        )
        states.update(
            connection.execute(
                text(
                    "SELECT DISTINCT cl.verification_state FROM concept_lemmas cl "
                    "JOIN concepts c ON c.id = cl.concept_id WHERE c.name = :n"
                ),
                {"n": name},
            ).scalars()
        )
    return states
