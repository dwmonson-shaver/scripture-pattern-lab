"""SQLAlchemy 2.0 Core mirrors and Pydantic models for the concept registry.

Realizes REQ:08.registry-epistemics (see docs/canonical/08_mvp-corpus-scope.md)
and DEC-024 (corpus is ground truth; registry entries are provisional priors).
The four ``Table`` definitions mirror ``data/schemas/02_concept_registry.sql``
column-for-column for typing and Core-style reads/inserts; this module never
issues DDL, and ``metadata.create_all`` is intentionally never called — the SQL
file is canonical (same discipline as ``src/ingestion/db.py``). The Pydantic
models are frozen value objects used at API and test boundaries.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    CheckConstraint,
    Column,
    Engine,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    select,
)

# ---------------------------------------------------------------------------
# Literal type aliases
# ---------------------------------------------------------------------------

Origin = Literal["curated", "ai_suggested", "lexicon_imported"]
VerificationState = Literal["unverified", "corpus_observed", "human_confirmed"]
Polarity = Literal["+", "-", "±"]


# ---------------------------------------------------------------------------
# SQLAlchemy 2.0 Core table mirrors
#
# CHECK-constraint expressions mirror the value-domain checks in
# data/schemas/02_concept_registry.sql (REQ:08.registry-epistemics).
# ---------------------------------------------------------------------------

metadata: MetaData = MetaData()

_ORIGIN_CHECK = "origin IN ('curated', 'ai_suggested', 'lexicon_imported')"
_VSTATE_CHECK = (
    "verification_state IN ('unverified', 'corpus_observed', 'human_confirmed')"
)
_POLARITY_CHECK = "polarity IN ('+', '-', '±')"
_CONFIDENCE_CHECK = "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)"
_EVIDENCE_CHECK = "evidence_count >= 0"

concepts_table: Table = Table(
    "concepts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(64), nullable=False, unique=True),
    Column("description", Text),
    Column("origin", String(20), nullable=False, server_default="curated"),
    Column(
        "verification_state",
        String(20),
        nullable=False,
        server_default="unverified",
    ),
    CheckConstraint(_ORIGIN_CHECK),
    CheckConstraint(_VSTATE_CHECK),
)

concept_lemmas_table: Table = Table(
    "concept_lemmas",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "concept_id",
        Integer,
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("lemma", Text, nullable=False),
    Column("language", String(5), nullable=False, server_default="grc"),
    Column("confidence", Float, nullable=True, default=None),
    Column("origin", String(20), nullable=False, server_default="curated"),
    Column(
        "verification_state",
        String(20),
        nullable=False,
        server_default="unverified",
    ),
    UniqueConstraint("lemma", "language", "concept_id"),
    CheckConstraint(_ORIGIN_CHECK),
    CheckConstraint(_VSTATE_CHECK),
    CheckConstraint(_CONFIDENCE_CHECK),
)

polarity_claims_table: Table = Table(
    "polarity_claims",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "concept_id",
        Integer,
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("polarity", String(2), nullable=False),
    Column("origin", String(20), nullable=False, server_default="curated"),
    Column("evidence_count", Integer, nullable=False, server_default="0"),
    Column(
        "verification_state",
        String(20),
        nullable=False,
        server_default="unverified",
    ),
    Column("confidence", Float, nullable=True, default=None),
    UniqueConstraint("concept_id", "polarity"),
    CheckConstraint(_POLARITY_CHECK),
    CheckConstraint(_ORIGIN_CHECK),
    CheckConstraint(_VSTATE_CHECK),
    CheckConstraint(_EVIDENCE_CHECK),
    CheckConstraint(_CONFIDENCE_CHECK),
)

inverse_claims_table: Table = Table(
    "inverse_claims",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "concept_id",
        Integer,
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "inverse_concept_id",
        Integer,
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("origin", String(20), nullable=False, server_default="curated"),
    Column("evidence_count", Integer, nullable=False, server_default="0"),
    Column(
        "verification_state",
        String(20),
        nullable=False,
        server_default="unverified",
    ),
    Column("confidence", Float, nullable=True, default=None),
    UniqueConstraint("concept_id", "inverse_concept_id"),
    CheckConstraint("concept_id <> inverse_concept_id"),
    CheckConstraint(_ORIGIN_CHECK),
    CheckConstraint(_VSTATE_CHECK),
    CheckConstraint(_EVIDENCE_CHECK),
    CheckConstraint(_CONFIDENCE_CHECK),
)


# ---------------------------------------------------------------------------
# Pydantic value-object models (frozen)
# ---------------------------------------------------------------------------


class Concept(BaseModel):
    """One concept registry entry. No polarity column — claims live in
    ``polarity_claims`` so each claim can carry its own provenance.
    """

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    description: str | None = None
    origin: Origin = "curated"
    verification_state: VerificationState = "unverified"


class ConceptLemma(BaseModel):
    """Lemma → concept mapping. ``confidence=None`` means "no estimate"; per
    DEC-024 the default is ``None`` and never ``1.0``.
    """

    model_config = ConfigDict(frozen=True)

    id: int
    concept_id: int
    lemma: str
    language: str = "grc"
    confidence: float | None = None
    origin: Origin = "curated"
    verification_state: VerificationState = "unverified"


class PolarityClaim(BaseModel):
    """Claim that a concept has a given polarity. Evidence-bearing: the
    ``evidence_count`` is bumped by the downstream observation pipeline.
    UNIQUE per ``(concept_id, polarity)``.
    """

    model_config = ConfigDict(frozen=True)

    id: int
    concept_id: int
    polarity: Polarity
    origin: Origin = "curated"
    evidence_count: int = 0
    verification_state: VerificationState = "unverified"
    confidence: float | None = None


class InverseClaim(BaseModel):
    """Claim that two concepts form an inverse pair. Asymmetric — the pair is
    stored as ordered ``(concept_id, inverse_concept_id)``. Self-inverse is
    forbidden by a CHECK constraint at the DB layer.
    """

    model_config = ConfigDict(frozen=True)

    id: int
    concept_id: int
    inverse_concept_id: int
    origin: Origin = "curated"
    evidence_count: int = 0
    verification_state: VerificationState = "unverified"
    confidence: float | None = None


class ConceptSummary(BaseModel):
    """Aggregate view of a concept + its lemma list, used by the HTTP layer
    to render the seeded registry without a second round-trip per concept.

    `lemma_count` is redundant with `len(lemmas)` — kept as a separate field
    so UI clients can render counts without traversing the array.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None
    verification_state: VerificationState = "unverified"
    lemma_count: int = 0
    lemmas: list[str] = []


# ---------------------------------------------------------------------------
# ConceptRegistry — read-only view over the four registry tables
# ---------------------------------------------------------------------------


class ConceptRegistry:
    """Read-only view over the registry tables. Query-side only — never
    imports ``src/ingestion``. Per DEC-025, the seed script (Phase 6) imports
    the ``Table`` mirrors directly, not this reader.

    All methods issue ``select(...)`` only; no inserts, updates, or deletes.
    Each call opens its own short-lived ``engine.connect()`` context. When the
    registry is constructed via :meth:`empty`, every method short-circuits to
    ``[]`` / ``False`` without touching a database — used by validator-rule-13
    unit tests that need a registry handle but no DB.
    """

    def __init__(self, engine: Engine | None) -> None:
        self.engine: Engine | None = engine

    @classmethod
    def empty(cls) -> ConceptRegistry:
        """Return an in-memory empty registry that requires no engine.

        All read methods return empty results / False. Suitable for unit tests
        that exercise validator paths needing a ``ConceptRegistry`` handle but
        not real registry data.
        """
        return cls(None)

    def get_by_lemma(self, lemma: str, language: str = "grc") -> list[Concept]:
        """Return parent ``Concept`` rows for every ``concept_lemmas`` row
        whose (lemma, language) match. Empty list if none match or if the
        registry is empty."""
        if self.engine is None:
            return []
        stmt = (
            select(concepts_table)
            .select_from(
                concepts_table.join(
                    concept_lemmas_table,
                    concepts_table.c.id == concept_lemmas_table.c.concept_id,
                )
            )
            .where(concept_lemmas_table.c.lemma == lemma)
            .where(concept_lemmas_table.c.language == language)
        )
        with self.engine.connect() as connection:
            rows = connection.execute(stmt).all()
        return [Concept.model_validate(row._mapping) for row in rows]

    def get_lemmas_for_concept(
        self, concept_name: str, language: str = "grc"
    ) -> list[str]:
        """Return all lemma strings mapped to the named concept (concept→lemma).

        Inverse of :meth:`get_by_lemma`. Issues a single SELECT joining
        ``concept_lemmas`` to ``concepts`` filtered by name + language.
        Returns ``[]`` when the concept is unknown or when the registry is
        empty (engine is None). Used by the executor (Slice C) to expand
        ``concept:X`` step nodes into the underlying lemmas before SQL
        matching against the tokens table.
        """
        if self.engine is None:
            return []
        stmt = (
            select(concept_lemmas_table.c.lemma)
            .select_from(
                concept_lemmas_table.join(
                    concepts_table,
                    concepts_table.c.id == concept_lemmas_table.c.concept_id,
                )
            )
            .where(concepts_table.c.name == concept_name)
            .where(concept_lemmas_table.c.language == language)
        )
        with self.engine.connect() as connection:
            rows = connection.execute(stmt).all()
        return [row[0] for row in rows]

    def get_polarity_claims(self, concept_id: int) -> list[PolarityClaim]:
        """Return all polarity claims for ``concept_id`` (any polarity)."""
        if self.engine is None:
            return []
        stmt = select(polarity_claims_table).where(
            polarity_claims_table.c.concept_id == concept_id
        )
        with self.engine.connect() as connection:
            rows = connection.execute(stmt).all()
        return [PolarityClaim.model_validate(row._mapping) for row in rows]

    def get_inverse_claims(self, concept_id: int) -> list[InverseClaim]:
        """Return all inverse claims where ``concept_id`` is the left side."""
        if self.engine is None:
            return []
        stmt = select(inverse_claims_table).where(
            inverse_claims_table.c.concept_id == concept_id
        )
        with self.engine.connect() as connection:
            rows = connection.execute(stmt).all()
        return [InverseClaim.model_validate(row._mapping) for row in rows]

    def list_all_concepts(self, language: str = "grc") -> list[ConceptSummary]:
        """Return all concepts with their lemma lists for a given language.

        Single SQL query: SELECT concepts LEFT JOIN concept_lemmas, ordered by
        concept name. Aggregation is done in Python (MVP scale ~30 concepts).
        Lemmas are included for the requested language only; concepts with no
        lemmas in that language still appear with `lemmas=[]`.

        Returns [] when the registry is empty (engine=None).
        """
        if self.engine is None:
            return []
        stmt = (
            select(
                concepts_table.c.name,
                concepts_table.c.description,
                concepts_table.c.verification_state,
                concept_lemmas_table.c.lemma,
                concept_lemmas_table.c.language,
            )
            .select_from(
                concepts_table.outerjoin(
                    concept_lemmas_table,
                    concepts_table.c.id == concept_lemmas_table.c.concept_id,
                )
            )
            .order_by(concepts_table.c.name, concept_lemmas_table.c.lemma)
        )
        with self.engine.connect() as connection:
            rows = connection.execute(stmt).all()

        # Aggregate: one entry per concept name; lemmas filtered by language.
        accumulator: dict[str, dict[str, object]] = {}
        for row in rows:
            name = row.name
            entry = accumulator.setdefault(
                name,
                {
                    "name": name,
                    "description": row.description,
                    "verification_state": row.verification_state,
                    "lemmas": [],
                },
            )
            if row.lemma is not None and row.language == language:
                entry["lemmas"].append(row.lemma)  # type: ignore[union-attr]

        return [
            ConceptSummary(
                name=entry["name"],  # type: ignore[arg-type]
                description=entry["description"],  # type: ignore[arg-type]
                verification_state=entry["verification_state"],  # type: ignore[arg-type]
                lemma_count=len(entry["lemmas"]),  # type: ignore[arg-type]
                lemmas=entry["lemmas"],  # type: ignore[arg-type]
            )
            for entry in accumulator.values()
        ]

    def is_prior_grounded(
        self, concept_name: str, polarity: Polarity | None
    ) -> bool:
        """Return True iff any backing polarity claim for the given concept
        (and optional polarity filter) has ``verification_state='unverified'``.

        Used by validator rule 13 (Phase 5). When the concept is not in the
        registry, returns False — no claim means nothing to flag.

        For Phase 4, only polarity claims are inspected. The inverse-claims
        case will be folded in alongside rule 13's inverse-usage interface in
        Phase 5; the docstring on the design spec calls that interface "TBD".
        """
        if self.engine is None:
            return False
        concept_stmt = select(concepts_table.c.id).where(
            concepts_table.c.name == concept_name
        )
        with self.engine.connect() as connection:
            concept_id = connection.execute(concept_stmt).scalar_one_or_none()
            if concept_id is None:
                return False
            claim_stmt = select(polarity_claims_table.c.verification_state).where(
                polarity_claims_table.c.concept_id == concept_id
            )
            if polarity is not None:
                claim_stmt = claim_stmt.where(
                    polarity_claims_table.c.polarity == polarity
                )
            states = connection.execute(claim_stmt).scalars().all()
        return any(state == "unverified" for state in states)
