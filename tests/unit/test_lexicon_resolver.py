"""Unit tests for src/ontology/lexicon_resolver.py (Slice N, Phase N3).

Covers the no-DB-touch guard paths and the LexiconResolution.unresolved
property. The full SQL resolution path is exercised against a live DB in
tests/integration/test_lexicon_resolver.py.
"""

from __future__ import annotations

from src.ontology.lexicon_resolver import (
    LexiconResolution,
    ResolvedLemma,
    resolve_english_term,
)


class _NeverConnectedEngine:
    """An engine whose .connect() must never be called (guard-path tests)."""

    def connect(self) -> object:  # pragma: no cover - asserts it's not reached
        raise AssertionError("resolver should not open a connection for blank input")


class TestBlankInputShortCircuits:
    def test_empty_term_resolves_unresolved_without_db(self) -> None:
        res = resolve_english_term("", _NeverConnectedEngine())  # type: ignore[arg-type]
        assert res.unresolved
        assert res.resolved_lemmas == []

    def test_whitespace_term_resolves_unresolved_without_db(self) -> None:
        res = resolve_english_term("   ", _NeverConnectedEngine())  # type: ignore[arg-type]
        assert res.unresolved


class TestResolutionModel:
    def test_unresolved_property_true_when_empty(self) -> None:
        res = LexiconResolution(english_term="x", resolved_lemmas=[])
        assert res.unresolved is True

    def test_unresolved_property_false_when_populated(self) -> None:
        res = LexiconResolution(
            english_term="humility",
            resolved_lemmas=[
                ResolvedLemma(
                    lemma="ταπεινοφροσύνη",
                    strongs=["G5012"],
                    glosses=["humility"],
                    corpus_token_count=7,
                )
            ],
        )
        assert res.unresolved is False

    def test_resolved_lemma_is_frozen(self) -> None:
        rl = ResolvedLemma(
            lemma="x", strongs=["G1"], glosses=["g"], corpus_token_count=1
        )
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            rl.lemma = "y"  # type: ignore[misc]
