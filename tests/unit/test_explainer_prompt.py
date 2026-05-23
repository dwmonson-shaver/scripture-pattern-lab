"""Unit tests for ``src/nlp/prompts/explainer_prompt.py``.

The system prompt is a literal string; the user-message helper is a pure
function. Both are substring-tested at the points that matter for DEC-081
conformance (no-fabrication clause, grounded fields, sentence shape).
"""

from __future__ import annotations

from src.engine.models import (
    MatchCandidate,
    MatchedToken,
    NodeType,
    StepMatch,
)
from src.nlp.prompts.explainer_prompt import (
    EXPLAINER_SYSTEM_PROMPT,
    build_explainer_user_message,
)


def _token(lemma: str, ref: str = "1Cor 13:13", position: int = 1) -> MatchedToken:
    book, rest = ref.split(" ", 1)
    chap_str, verse_str = rest.split(":")
    return MatchedToken(
        id=position,
        book=book,
        chapter=int(chap_str),
        verse=int(verse_str),
        position=position,
        global_position=position,
        surface_form=lemma,
        normalized_form=lemma,
        lemma=lemma,
        pos="N",
    )


def _candidate(
    pairs: list[tuple[str, str, list[str]]],
    ref: str = "1Cor 13:13",
    match_type: str = "conceptual",
) -> MatchCandidate:
    """Build a candidate from (lemma, concept, resolved_lemmas) tuples."""
    tokens = [_token(lemma, ref, i + 1) for i, (lemma, _c, _r) in enumerate(pairs)]
    alignment = [
        StepMatch(
            step_index=i,
            node_type=NodeType.CONCEPT,
            node_value=concept,
            resolved_lemmas=resolved,
            token=tokens[i],
        )
        for i, (_lemma, concept, resolved) in enumerate(pairs)
    ]
    return MatchCandidate(
        tokens=tokens,
        reference=ref,
        match_type=match_type,  # type: ignore[arg-type]
        alignment=alignment,
    )


# ---------------------------------------------------------------------------
# System prompt — the no-fabrication contract
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_contains_no_fabrication_clause(self) -> None:
        assert "Do not invent" in EXPLAINER_SYSTEM_PROMPT

    def test_contains_no_commentary_clause(self) -> None:
        assert "Do not add interpretive" in EXPLAINER_SYSTEM_PROMPT

    def test_contains_single_sentence_constraint(self) -> None:
        assert "exactly one sentence" in EXPLAINER_SYSTEM_PROMPT

    def test_contains_character_cap(self) -> None:
        assert "Under 200 characters" in EXPLAINER_SYSTEM_PROMPT

    def test_contains_fallback_token_instruction(self) -> None:
        assert "FALLBACK" in EXPLAINER_SYSTEM_PROMPT

    def test_requires_verse_and_lemmas_verbatim(self) -> None:
        assert "verse reference and the matched lemmas" in EXPLAINER_SYSTEM_PROMPT
        assert "verbatim" in EXPLAINER_SYSTEM_PROMPT

    def test_forbids_markdown(self) -> None:
        assert "No Markdown" in EXPLAINER_SYSTEM_PROMPT
        assert "No bullets" in EXPLAINER_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# User message — grounded-fields-only contract
# ---------------------------------------------------------------------------


class TestUserMessage:
    def test_includes_verse_reference(self) -> None:
        cand = _candidate(
            [("πίστις", "faith", ["πίστις", "πιστεύω"])],
            ref="1Cor 13:13",
        )
        msg = build_explainer_user_message(cand, "faith")
        assert "Verse reference: 1Cor 13:13" in msg

    def test_includes_sequence_label(self) -> None:
        cand = _candidate([("πίστις", "faith", ["πίστις"])])
        msg = build_explainer_user_message(cand, "faith > hope > love")
        assert "Sequence pattern: faith > hope > love" in msg

    def test_includes_match_type(self) -> None:
        cand = _candidate([("πίστις", "faith", ["πίστις"])])
        msg = build_explainer_user_message(cand, "faith")
        assert "Match type: conceptual" in msg

    def test_includes_every_step_lemma(self) -> None:
        cand = _candidate(
            [
                ("πίστις", "faith", ["πίστις", "πιστεύω"]),
                ("ἐλπίς", "hope", ["ἐλπίς", "ἐλπίζω"]),
                ("ἀγάπη", "love", ["ἀγάπη", "ἀγαπάω"]),
            ]
        )
        msg = build_explainer_user_message(cand, "faith > hope > love")
        assert "πίστις" in msg
        assert "ἐλπίς" in msg
        assert "ἀγάπη" in msg

    def test_includes_every_resolved_lemma(self) -> None:
        cand = _candidate(
            [
                ("πίστις", "faith", ["πίστις", "πιστεύω"]),
                ("ἐλπίς", "hope", ["ἐλπίς", "ἐλπίζω"]),
            ]
        )
        msg = build_explainer_user_message(cand, "faith > hope")
        # All four resolved lemmas should be present.
        assert "πιστεύω" in msg
        assert "ἐλπίζω" in msg

    def test_step_count_matches_alignment_count(self) -> None:
        cand = _candidate(
            [
                ("πίστις", "faith", ["πίστις"]),
                ("ἐλπίς", "hope", ["ἐλπίς"]),
                ("ἀγάπη", "love", ["ἀγάπη"]),
            ]
        )
        msg = build_explainer_user_message(cand, "faith > hope > love")
        assert msg.count("Step 0:") == 1
        assert msg.count("Step 1:") == 1
        assert msg.count("Step 2:") == 1
        assert "Step 3:" not in msg

    def test_is_pure_function(self) -> None:
        cand = _candidate(
            [
                ("πίστις", "faith", ["πίστις", "πιστεύω"]),
                ("ἐλπίς", "hope", ["ἐλπίς", "ἐλπίζω"]),
            ]
        )
        msg1 = build_explainer_user_message(cand, "faith > hope")
        msg2 = build_explainer_user_message(cand, "faith > hope")
        assert msg1 == msg2

    def test_handles_empty_resolved_lemmas(self) -> None:
        # Defensive: if a lemma step (not concept) has resolved_lemmas as
        # [single lemma], confirm the empty-string fallback branch works.
        cand = _candidate([("πίστις", "faith", [])])
        msg = build_explainer_user_message(cand, "faith")
        # Should still produce a Step 0 line with an empty bracket pair.
        assert "Step 0:" in msg
        assert "registry resolves to []" in msg

    def test_includes_paraphrase_instruction_footer(self) -> None:
        cand = _candidate([("πίστις", "faith", ["πίστις"])])
        msg = build_explainer_user_message(cand, "faith")
        assert "Paraphrase the match above" in msg

    def test_step_lines_appear_in_alignment_order(self) -> None:
        cand = _candidate(
            [
                ("πίστις", "faith", ["πίστις"]),
                ("ἐλπίς", "hope", ["ἐλπίς"]),
                ("ἀγάπη", "love", ["ἀγάπη"]),
            ]
        )
        msg = build_explainer_user_message(cand, "faith > hope > love")
        i_step0 = msg.index("Step 0:")
        i_step1 = msg.index("Step 1:")
        i_step2 = msg.index("Step 2:")
        assert i_step0 < i_step1 < i_step2
