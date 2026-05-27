"""English-term → corpus-present MorphGNT lemma resolver (Slice N, Phase N3).

The deterministic Tier-1 reverse lookup (DEC-102/DEC-103). Given an English word
(e.g. "humility"), resolve the MorphGNT lemmas usually translated as it and
present in the SBLGNT corpus:

    term → strongs_glosses.gloss ILIKE '%term%' → Strong's set
         → lemma_strongs (the jtauber bridge) → MorphGNT lemma forms
         → INNER JOIN tokens (corpus-presence filter) → ResolvedLemma list

NO LLM. The lexicon datasets are the cited authority; the corpus is the
grounding. A term that maps to no corpus-present lemma resolves to
``unresolved=True`` — the honest "I can't do that yet" path.

Query-side, read-only (DEC-025): joins ``src/ingestion/lexicon`` Core mirrors
against ``src/ingestion/db.tokens_table``. Issues ``select(...)`` only.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, distinct, func, select

from src.ingestion.db import tokens_table
from src.ingestion.lexicon.db import lemma_strongs_table, strongs_glosses_table

# Cap how many corpus verse references we cite per lemma in the base evidence
# (the full set is queryable later; this keeps the resolution payload bounded).
_VERSE_SAMPLE_CAP: int = 12


class ResolvedLemma(BaseModel):
    """One MorphGNT lemma the term resolves to, with its lexicon provenance."""

    model_config = ConfigDict(frozen=True)

    lemma: str
    strongs: list[str]
    glosses: list[str]
    corpus_token_count: int


class LexiconResolution(BaseModel):
    """The resolver's full answer for one English term."""

    model_config = ConfigDict(frozen=True)

    english_term: str
    resolved_lemmas: list[ResolvedLemma]

    @property
    def unresolved(self) -> bool:
        """True iff no corpus-present lemma was found (honest dead-end)."""
        return not self.resolved_lemmas


def _strongs_for_term(connection, term: str) -> dict[str, list[str]]:  # type: ignore[no-untyped-def]
    """Return ``{strongs: [glosses...]}`` for glosses matching the term.

    Matches whole-word-ish: the term must appear as a token in the gloss. We use
    ``ILIKE '%term%'`` for recall, then keep the matched glosses so the article's
    comparative section can cite the exact rendering text. Both TBESG and Dodson
    rows participate.
    """
    pattern = f"%{term}%"
    stmt = (
        select(strongs_glosses_table.c.strongs, strongs_glosses_table.c.gloss)
        .where(strongs_glosses_table.c.gloss.ilike(pattern))
    )
    out: dict[str, list[str]] = {}
    for row in connection.execute(stmt):
        out.setdefault(row.strongs, [])
        if row.gloss not in out[row.strongs]:
            out[row.strongs].append(row.gloss)
    return out


def resolve_english_term(
    term: str,
    engine: Engine,
    *,
    corpus_id: str = "nt",
    language: str = "grc",
) -> LexiconResolution:
    """Resolve an English term to corpus-present MorphGNT lemmas.

    Deterministic; no LLM. Only lemmas with at least one token in the corpus
    (matching ``corpus_id`` + ``language``) are kept — a lexicon lemma absent
    from the loaded corpus is dropped (it cannot be queried). The returned
    ``ResolvedLemma`` rows carry the Strong's that bridged to them, the English
    glosses seen for those Strong's, and the corpus token count.
    """
    normalized = (term or "").strip()
    if not normalized:
        return LexiconResolution(english_term=term, resolved_lemmas=[])

    with engine.connect() as connection:
        strongs_to_glosses = _strongs_for_term(connection, normalized)
        if not strongs_to_glosses:
            return LexiconResolution(english_term=term, resolved_lemmas=[])

        strongs_set = list(strongs_to_glosses.keys())

        # Bridge: Strong's → MorphGNT lemma forms.
        bridge_stmt = select(
            lemma_strongs_table.c.morphgnt_lemma,
            lemma_strongs_table.c.strongs,
        ).where(lemma_strongs_table.c.strongs.in_(strongs_set))

        lemma_to_strongs: dict[str, list[str]] = {}
        for row in connection.execute(bridge_stmt):
            lemma_to_strongs.setdefault(row.morphgnt_lemma, [])
            if row.strongs not in lemma_to_strongs[row.morphgnt_lemma]:
                lemma_to_strongs[row.morphgnt_lemma].append(row.strongs)

        if not lemma_to_strongs:
            return LexiconResolution(english_term=term, resolved_lemmas=[])

        # Corpus-presence filter: keep only lemmas with >=1 token in the corpus.
        candidate_lemmas = list(lemma_to_strongs.keys())
        count_stmt = (
            select(
                tokens_table.c.lemma,
                func.count().label("n"),
            )
            .where(tokens_table.c.lemma.in_(candidate_lemmas))
            .where(tokens_table.c.corpus_id == corpus_id)
            .where(tokens_table.c.language == language)
            .group_by(tokens_table.c.lemma)
        )
        corpus_counts: dict[str, int] = {
            row.lemma: row.n for row in connection.execute(count_stmt)
        }

    resolved: list[ResolvedLemma] = []
    for lemma in sorted(candidate_lemmas):
        token_count = corpus_counts.get(lemma, 0)
        if token_count == 0:
            continue  # lexicon lemma absent from the corpus — cannot query it
        lemma_strongs = sorted(lemma_to_strongs[lemma])
        glosses: list[str] = []
        for s in lemma_strongs:
            for g in strongs_to_glosses.get(s, []):
                if g not in glosses:
                    glosses.append(g)
        resolved.append(
            ResolvedLemma(
                lemma=lemma,
                strongs=lemma_strongs,
                glosses=glosses,
                corpus_token_count=token_count,
            )
        )

    return LexiconResolution(english_term=term, resolved_lemmas=resolved)


def corpus_verse_refs_for_lemma(
    lemma: str,
    engine: Engine,
    *,
    corpus_id: str = "nt",
    language: str = "grc",
    cap: int = _VERSE_SAMPLE_CAP,
) -> list[tuple[str, int, int]]:
    """Return up to ``cap`` distinct (book, chapter, verse) tuples for a lemma.

    The corpus citations that ground a resolved lemma — the base evidence
    attached to an auto-created concept and rendered in the article's
    comparative section. Ordered by book/chapter/verse for stability.
    """
    stmt = (
        select(
            distinct(
                func.concat(
                    tokens_table.c.book,
                    "|",
                    tokens_table.c.chapter,
                    "|",
                    tokens_table.c.verse,
                )
            )
        )
        .where(tokens_table.c.lemma == lemma)
        .where(tokens_table.c.corpus_id == corpus_id)
        .where(tokens_table.c.language == language)
    )
    with engine.connect() as connection:
        keys = sorted(connection.execute(stmt).scalars())
    out: list[tuple[str, int, int]] = []
    for key in keys[:cap]:
        book, chapter, verse = key.split("|")
        out.append((book, int(chapter), int(verse)))
    return out
