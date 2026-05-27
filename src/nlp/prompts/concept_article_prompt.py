"""Concept-article LLM prompt assembly — Part 1 §2 educational section (Slice N).

The LLM is strictly an EXPLAINER/ASSEMBLER of the deterministic comparative
lexicon evidence it is handed (the Part 1 §1 ``ComparativeLexiconSection``). It
writes beginner-friendly prose explaining the Greek for a novice. It MUST cite
its sources, MUST NOT introduce lemmas/verses/claims not present in the handed
evidence, and its output is stored WITH those citations and clearly labeled as
LLM-generated. It NEVER feeds back into the concept's lemma set or verification
state (DEC-024 / DEC-081 / DEC-102).

Mirrors the structure of ``explainer_prompt.py``: a module-level system prompt
(the "explain only what you're handed" contract, with a FALLBACK escape) and a
pure per-call user-message builder that lays out the labeled comparative
evidence so the LLM has nothing else to draw from.
"""

from __future__ import annotations

from src.ontology.concept_document import ComparativeLexiconSection

CONCEPT_ARTICLE_SYSTEM_PROMPT: str = """\
You write a short, beginner-friendly explanation of a set of Biblical Greek
words for a reader with no Greek background. You are an EXPLAINER and ASSEMBLER
of the evidence handed to you — not a researcher, not an exegete, not a
theologian.

Strict rules:
1. Use ONLY the lemmas, Strong's numbers, English renderings, and verse
   references in the structured evidence below. Do NOT introduce any lemma,
   verse, Strong's number, gloss, or factual claim that is not in the evidence.
2. Do NOT supply theological interpretation, doctrinal commentary, or claims
   about what the words "really mean" beyond the renderings provided. You may
   explain, in plain language, what the listed renderings suggest and how the
   listed words relate as renderings of one English term — nothing more.
3. Write 2-5 short sentences of accessible prose. No headers, no Markdown
   tables, no bullet lists. Mention at least one verse reference and at least
   one Greek lemma verbatim from the evidence.
4. End with a one-line "Sources:" note listing the dataset names from the
   evidence (e.g. "Sources: STEPBible TBESG; MorphGNT SBLGNT corpus").
5. If you cannot write such an explanation using only the evidence, emit the
   single token: FALLBACK
"""


def build_concept_article_user_message(
    comparative: ComparativeLexiconSection,
) -> str:
    """Format the labeled comparative evidence for the LLM.

    Every datum the LLM may use is explicit and traceable to the deterministic
    ``ComparativeLexiconSection`` — the structural enforcement of the
    "explain only what you're handed" contract.
    """
    lines: list[str] = [
        f"English term: {comparative.english_term}",
        "",
        "Greek words usually translated as this term (from the lexicon "
        "datasets, present in the corpus):",
    ]
    for row in comparative.rows:
        renderings = ", ".join(row.usual_renderings) if row.usual_renderings else "—"
        strongs = ", ".join(row.strongs) if row.strongs else "—"
        refs = ", ".join(row.corpus_verse_refs) if row.corpus_verse_refs else "—"
        lines.append(
            f"- lemma {row.lemma} (Strong's {strongs}); usual renderings: "
            f"{renderings}; corpus verses: {refs}"
        )
    lines.append("")
    lines.append(f"Dataset sources: {', '.join(comparative.generated_from)}")
    lines.append("")
    lines.append(
        "Write the beginner-friendly explanation per the system rules, using "
        "ONLY the evidence above."
    )
    return "\n".join(lines)
