"""LLM educational article section — Part 1 §2 of the Conceptual Document.

The presentation layer that sits ON TOP of the deterministic concept + the
deterministic comparative lexicon section. The LLM is strictly an
EXPLAINER/ASSEMBLER of the cited evidence it is handed: it writes
beginner-friendly prose, cites its sources, and the result is stored WITH those
citations and clearly labeled as generated. It NEVER feeds back into the
concept's lemma set or verification state — the concept is regenerable-proof
ground truth; this article is regenerable commentary (DEC-024 / DEC-081 /
DEC-102 / DEC-104).

This is the AI layer (src/nlp). It does not import src/app. On
``LLMUnavailable`` (or a FALLBACK / empty response) it returns ``None`` so the
caller persists Part 1 §1 only and regenerates §2 later — auto-creation of the
concept itself never depends on the LLM.
"""

from __future__ import annotations

import logging

from src.nlp.llm_client import LLMClient, LLMUnavailable
from src.nlp.prompts.concept_article_prompt import (
    CONCEPT_ARTICLE_SYSTEM_PROMPT,
    build_concept_article_user_message,
)
from src.ontology.concept_document import (
    ComparativeLexiconSection,
    EducationalArticleSection,
)

logger = logging.getLogger(__name__)

_FALLBACK_TOKEN = "FALLBACK"
_FALLBACK_MAX_LEN = len(_FALLBACK_TOKEN) + 5


def _is_fallback_signal(text: str) -> bool:
    """Recognize the LLM's FALLBACK bail-out (token + a little trailing punct)."""
    if len(text) > _FALLBACK_MAX_LEN:
        return False
    return text.upper().startswith(_FALLBACK_TOKEN)


def _model_label(llm_client: LLMClient) -> str:
    """Best-effort label of the model that produced the prose, for the citation."""
    return str(getattr(llm_client, "_model", "llm"))


def _cited_sources(comparative: ComparativeLexiconSection) -> list[str]:
    """The evidence handed to the LLM, recorded as the section's citations.

    This is the dataset list plus the corpus verse references — exactly what the
    LLM was given. Stored so a reader can trace every claim back to its source.
    """
    sources = list(comparative.generated_from)
    for row in comparative.rows:
        sources.extend(row.corpus_verse_refs)
    # De-dup preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for s in sources:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def build_educational_section(
    comparative: ComparativeLexiconSection,
    llm_client: LLMClient,
) -> EducationalArticleSection | None:
    """Generate the LLM educational section from the comparative evidence.

    Returns the stored-with-citations section, or ``None`` if the LLM is
    unavailable / bails (FALLBACK) / returns empty — in which case the caller
    persists Part 1 §1 only and may regenerate §2 later. NEVER raises on LLM
    trouble (the concept is already ground truth without it).

    The LLM sees ONLY the labeled comparative evidence (no free corpus access,
    no registry write path), structurally enforcing DEC-081's no-fabrication
    clause for the educational layer.
    """
    user_message = build_concept_article_user_message(comparative)
    try:
        raw = llm_client.complete(CONCEPT_ARTICLE_SYSTEM_PROMPT, user_message)
    except LLMUnavailable as exc:
        logger.warning(
            "concept-article LLM unavailable for %s; persisting Part 1 §1 only "
            "(regenerate §2 later): %s",
            comparative.english_term,
            exc,
        )
        return None
    except Exception:
        # Defensive: any unexpected LLM-side error must not corrupt the
        # deterministic concept/document. Log and degrade to §1-only.
        logger.exception(
            "unexpected error generating concept-article section for %s; "
            "persisting Part 1 §1 only",
            comparative.english_term,
        )
        return None

    cleaned = raw.strip()
    if not cleaned or _is_fallback_signal(cleaned):
        logger.info(
            "concept-article LLM emitted FALLBACK/empty for %s; §2 omitted",
            comparative.english_term,
        )
        return None

    return EducationalArticleSection(
        prose=cleaned,
        cited_sources=_cited_sources(comparative),
        generated=True,
        model_label=_model_label(llm_client),
    )
