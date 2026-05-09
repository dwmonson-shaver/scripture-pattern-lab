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
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

# ---------------------------------------------------------------------------
# Literal type aliases
# ---------------------------------------------------------------------------

Origin = Literal["curated", "ai_suggested", "lexicon_imported"]
VerificationState = Literal["unverified", "corpus_observed", "human_confirmed"]
Polarity = Literal["+", "-", "±"]


# ---------------------------------------------------------------------------
# SQLAlchemy 2.0 Core table mirrors
# ---------------------------------------------------------------------------

metadata: MetaData = MetaData()

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
