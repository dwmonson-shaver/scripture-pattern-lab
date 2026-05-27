"""Unit tests for src/nlp/concept_article.py (Slice N, Phase N7).

The LLM educational section (Part 1 §2). A scripted LLMClient subclass returns
canned prose so no live API is needed. The tests lock the epistemic contract:
the section is labeled generated, carries citations, degrades to None on
unavailable/FALLBACK/empty, and the no-fabrication structural property (the LLM
only sees the labeled comparative evidence).
"""

from __future__ import annotations

from src.nlp.concept_article import build_educational_section
from src.nlp.llm_client import LLMClient, LLMUnavailable
from src.nlp.prompts.concept_article_prompt import (
    build_concept_article_user_message,
)
from src.ontology.concept_document import (
    ComparativeLexiconSection,
    LexiconComparisonRow,
)


def _comparative() -> ComparativeLexiconSection:
    return ComparativeLexiconSection(
        english_term="humility",
        rows=[
            LexiconComparisonRow(
                lemma="ταπεινοφροσύνη",
                strongs=["G5012"],
                usual_renderings=["humility", "lowliness of mind"],
                corpus_verse_refs=["Php 2:3", "Col 3:12"],
            )
        ],
        generated_from=[
            "STEPBible TBESG (CC BY 4.0)",
            "MorphGNT SBLGNT corpus",
        ],
    )


class _ScriptedClient(LLMClient):
    def __init__(self, response: str, *, model: str = "claude-test") -> None:
        self._response = response
        self._model = model
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.last_system = system_prompt
        self.last_user = user_message
        return self._response


class _UnavailableClient(LLMClient):
    def complete(self, system_prompt: str, user_message: str) -> str:
        raise LLMUnavailable("simulated outage")


class _BoomClient(LLMClient):
    def complete(self, system_prompt: str, user_message: str) -> str:
        raise RuntimeError("unexpected")


class TestHappyPath:
    def test_returns_labeled_cited_section(self) -> None:
        client = _ScriptedClient(
            "The Greek word ταπεινοφροσύνη is usually rendered 'humility', as "
            "in Php 2:3. Sources: STEPBible TBESG; MorphGNT SBLGNT corpus."
        )
        section = build_educational_section(_comparative(), client)
        assert section is not None
        assert section.generated is True
        assert section.model_label == "claude-test"
        assert "ταπεινοφροσύνη" in section.prose

    def test_citations_include_datasets_and_verses(self) -> None:
        client = _ScriptedClient("Some prose. Sources: TBESG.")
        section = build_educational_section(_comparative(), client)
        assert section is not None
        assert "STEPBible TBESG (CC BY 4.0)" in section.cited_sources
        assert "Php 2:3" in section.cited_sources
        assert "Col 3:12" in section.cited_sources

    def test_llm_sees_only_handed_evidence(self) -> None:
        # Structural no-fabrication: the user message is built solely from the
        # comparative section (the LLM has nothing else to draw from).
        client = _ScriptedClient("prose")
        build_educational_section(_comparative(), client)
        assert client.last_user is not None
        assert "ταπεινοφροσύνη" in client.last_user
        assert "G5012" in client.last_user
        # And it matches the pure builder exactly.
        assert client.last_user == build_concept_article_user_message(_comparative())


class TestDegradesGracefully:
    def test_unavailable_returns_none(self) -> None:
        assert build_educational_section(_comparative(), _UnavailableClient()) is None

    def test_unexpected_error_returns_none(self) -> None:
        assert build_educational_section(_comparative(), _BoomClient()) is None

    def test_fallback_token_returns_none(self) -> None:
        assert build_educational_section(_comparative(), _ScriptedClient("FALLBACK")) is None

    def test_fallback_with_punctuation_returns_none(self) -> None:
        assert build_educational_section(_comparative(), _ScriptedClient("FALLBACK.")) is None

    def test_empty_returns_none(self) -> None:
        assert build_educational_section(_comparative(), _ScriptedClient("   ")) is None
