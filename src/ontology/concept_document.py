"""Persisted two-part Conceptual Document (Slice N, Phase N6).

A first-class per-concept document, STORED on first creation and RETRIEVED
later — never regenerated per query (design "Output" section, DEC-102). Two
parts:

  * Part 1 = the Tier-1 article (this slice). Two clearly-labeled sections:
      §1 pure comparative lexicon analysis — DETERMINISTIC, NO LLM (lemmas,
         Strong's, usual English renderings, corpus verse refs). Built here.
      §2 LLM-generated educational analysis — built by src/nlp/concept_article.py
         and layered ON TOP. NEVER feeds back into the concept.
  * Part 2 = a placeholder/structure slot for the Tier-2 grouping artifact that
      grows over time. NOT built this slice (always None).

This module owns the document ENTITY: the Pydantic models, the Core table
mirror, the deterministic comparative-section builder + short summary, and
persist/get. The LLM §2 lives in the AI layer (src/nlp) and is attached by the
caller, so this query-side module never imports the LLM client.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.ontology.book_codes import bb_to_display
from src.ontology.concept_grouping import GroupingPointer, Tier2Grouping
from src.ontology.lexicon_resolver import (
    LexiconResolution,
    corpus_verse_refs_for_lemma,
)

# Cap how many resolved lemmas the short inline summary names before eliding.
_SUMMARY_LEMMA_CAP: int = 5

# ---------------------------------------------------------------------------
# Core table mirror (canonical SQL: data/schemas/04_concept_documents.sql)
# ---------------------------------------------------------------------------

metadata: MetaData = MetaData()

concept_documents_table = Table(
    "concept_documents",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "concept_name",
        String(64),
        ForeignKey("concepts.name", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
    ),
    Column("short_summary", Text, nullable=False),
    Column("part1_comparative", JSONB, nullable=False),
    Column("part1_educational", JSONB, nullable=True),
    Column("part2_grouping", JSONB, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("concept_name"),
)


# ---------------------------------------------------------------------------
# Pydantic models (frozen value objects)
# ---------------------------------------------------------------------------


class LexiconComparisonRow(BaseModel):
    """One row of the deterministic comparative table: a lemma and its data."""

    model_config = ConfigDict(frozen=True)

    lemma: str
    strongs: list[str]
    usual_renderings: list[str]
    corpus_verse_refs: list[str]  # display form, e.g. "1Cor 13:13"


class ComparativeLexiconSection(BaseModel):
    """Part 1 §1 — pure comparative lexicon analysis. NO LLM, no opinion."""

    model_config = ConfigDict(frozen=True)

    english_term: str
    rows: list[LexiconComparisonRow]
    generated_from: list[str]  # dataset citations


class EducationalArticleSection(BaseModel):
    """Part 1 §2 — LLM-generated educational analysis (built in src/nlp).

    Stored WITH its citations and a generated label. Mirrored here so the
    document entity can carry it; this module never CONSTRUCTS it.
    """

    model_config = ConfigDict(frozen=True)

    prose: str
    cited_sources: list[str]
    generated: bool = True
    model_label: str


class ConceptDocument(BaseModel):
    """The persisted two-part Conceptual Document.

    Part 2 (Tier-2 grouping) takes one of three shapes (Slice O):
      * ``part2_grouping`` — full Tier2Grouping, present ONLY on the anchor
        concept's document (DEC-113 anchor model).
      * ``part2_grouping_pointer`` — GroupingPointer back to the anchor(s),
        present on non-anchor member documents.
      * both ``None`` — concept is not yet a member of any grouping.

    These are mutually exclusive on a single document (an anchor doesn't also
    carry a pointer to itself); the reader populates whichever the JSONB shape
    indicates.
    """

    model_config = ConfigDict(frozen=True)

    concept_name: str
    short_summary: str
    part1_comparative: ComparativeLexiconSection
    part1_educational: EducationalArticleSection | None = None
    part2_grouping: Tier2Grouping | None = None
    part2_grouping_pointer: GroupingPointer | None = None


# ---------------------------------------------------------------------------
# Deterministic builders (NO LLM)
# ---------------------------------------------------------------------------


def _display_ref(book_bb: str, chapter: int, verse: int) -> str:
    """Render a (BB, chapter, verse) tuple as e.g. '1Cor 13:13'."""
    return f"{bb_to_display(book_bb)} {chapter}:{verse}"


def build_comparative_section(
    resolution: LexiconResolution,
    engine: Engine,
    *,
    corpus_id: str = "nt",
    language: str = "grc",
) -> ComparativeLexiconSection:
    """Build Part 1 §1 deterministically from a resolution + corpus citations.

    One row per resolved lemma: its Strong's, the usual English renderings
    (glosses), and a capped sample of corpus verse references. NO LLM, no
    assertion — straight from the ingested datasets + corpus.
    """
    rows: list[LexiconComparisonRow] = []
    for rl in resolution.resolved_lemmas:
        refs = corpus_verse_refs_for_lemma(
            rl.lemma, engine, corpus_id=corpus_id, language=language
        )
        rows.append(
            LexiconComparisonRow(
                lemma=rl.lemma,
                strongs=rl.strongs,
                usual_renderings=rl.glosses,
                corpus_verse_refs=[_display_ref(b, c, v) for (b, c, v) in refs],
            )
        )
    return ComparativeLexiconSection(
        english_term=resolution.english_term,
        rows=rows,
        generated_from=[
            "jtauber/greek-lemma-mappings (CC BY-SA 4.0)",
            "STEPBible TBESG (CC BY 4.0)",
            "Dodson Greek Lexicon (Public Domain)",
            "MorphGNT SBLGNT corpus",
        ],
    )


def build_short_summary(resolution: LexiconResolution) -> str:
    """Build the short inline summary surfaced in the query interaction.

    Deterministic. Names the auto-created concept + the Greek lemmas it maps to
    (capped), and states the epistemic status honestly (machine/lexicon-sourced,
    unverified, correctable).
    """
    lemmas = [rl.lemma for rl in resolution.resolved_lemmas]
    shown = lemmas[:_SUMMARY_LEMMA_CAP]
    more = len(lemmas) - len(shown)
    lemma_str = ", ".join(shown) + (f" (+{more} more)" if more > 0 else "")
    return (
        f"Auto-created concept '{resolution.english_term}' from open lexicon "
        f"data: {lemma_str}. Machine/lexicon-sourced and unverified — a "
        f"starting prior you can correct, not a confirmed claim."
    )


# ---------------------------------------------------------------------------
# Persistence (store-once, retrieve-later)
# ---------------------------------------------------------------------------


def persist_document(doc: ConceptDocument, engine: Engine) -> None:
    """Store the document on first creation; idempotent.

    Uses ON CONFLICT (concept_name) DO NOTHING so a re-run does not overwrite an
    existing document (store-once semantics; the document is retrieved later,
    not regenerated per query). To refresh the LLM §2 specifically, a future
    explicit-regenerate path will UPDATE — out of scope here.

    Part 2 grouping is also stored on initial persist when present. Grouping
    UPDATES (write/rewrite after the document already exists) go through
    ``src.ontology.concept_grouping.write_grouping`` which performs an explicit
    UPDATE on the part2_grouping column.
    """
    if doc.part2_grouping is not None:
        part2_blob: dict | None = doc.part2_grouping.model_dump(mode="json")
    elif doc.part2_grouping_pointer is not None:
        part2_blob = doc.part2_grouping_pointer.model_dump(mode="json")
    else:
        part2_blob = None
    with engine.begin() as connection:
        connection.execute(
            pg_insert(concept_documents_table)
            .values(
                concept_name=doc.concept_name,
                short_summary=doc.short_summary,
                part1_comparative=doc.part1_comparative.model_dump(mode="json"),
                part1_educational=(
                    doc.part1_educational.model_dump(mode="json")
                    if doc.part1_educational is not None
                    else None
                ),
                part2_grouping=part2_blob,
            )
            .on_conflict_do_nothing(index_elements=["concept_name"])
        )


def _decode_part2(blob: dict | None) -> tuple[Tier2Grouping | None, GroupingPointer | None]:
    """Auto-detect Tier-2 blob shape — full grouping vs pointer vs nothing.

    Both Tier2Grouping and GroupingPointer have non-overlapping required
    fields ('members' vs 'grouping_anchors'), so the discriminator is
    unambiguous. On parse failure we log and return (None, None) rather than
    propagate — DEC-114 R2 mitigation: a future schema drift on the JSONB
    blob must NOT make the entire document unreadable.
    """
    if not isinstance(blob, dict):
        return (None, None)
    try:
        if "members" in blob:
            return (Tier2Grouping.model_validate(blob), None)
        if "grouping_anchors" in blob:
            return (None, GroupingPointer.model_validate(blob))
    except Exception:  # noqa: BLE001 — see docstring
        # Surfaced as None to the caller; a future curator slice may attach a
        # log line + bucket-ticket here. For now the contract is "stale shape
        # degrades to no grouping rendered" not "stale shape breaks the doc".
        return (None, None)
    return (None, None)


def get_document(concept_name: str, engine: Engine) -> ConceptDocument | None:
    """Read a persisted document; None if not yet generated."""
    stmt = select(
        concept_documents_table.c.concept_name,
        concept_documents_table.c.short_summary,
        concept_documents_table.c.part1_comparative,
        concept_documents_table.c.part1_educational,
        concept_documents_table.c.part2_grouping,
    ).where(concept_documents_table.c.concept_name == concept_name)
    with engine.connect() as connection:
        row = connection.execute(stmt).first()
    if row is None:
        return None
    grouping, pointer = _decode_part2(row.part2_grouping)
    return ConceptDocument(
        concept_name=row.concept_name,
        short_summary=row.short_summary,
        part1_comparative=ComparativeLexiconSection.model_validate(
            row.part1_comparative
        ),
        part1_educational=(
            EducationalArticleSection.model_validate(row.part1_educational)
            if row.part1_educational is not None
            else None
        ),
        part2_grouping=grouping,
        part2_grouping_pointer=pointer,
    )
