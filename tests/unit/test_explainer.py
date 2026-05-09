"""Unit tests for ``src/nlp/explainer.py``.

The explainer is fully deterministic — fixtures build hand-crafted
RetrievalResults and assert on substring contents of the produced
ExplainedResultSet. No DB access. Cap/wrap helpers are pure functions
tested in isolation at known boundaries.
"""

from __future__ import annotations

import pytest

from src.engine.models import (
    AlternativeOrderingCount,
    Contextualization,
    MatchCandidate,
    MatchedToken,
    NodeBaseline,
    NodeRef,
    NodeType,
    OperatorType,
    OrderOperator,
    QueryMetadata,
    QueryPlan,
    RetrievalResult,
    ScopeConstraint,
    SequenceExpr,
    StepMatch,
)
from src.nlp.explainer import (
    _format_alt_orderings_phrase,
    _format_baselines_phrase,
    _truncate_lemmas,
    _truncate_sequence_label,
    explain,
)
from src.validation.validator import ValidationFinding, ValidationResult

# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _node(value: str, node_type: NodeType = NodeType.CONCEPT) -> NodeRef:
    return NodeRef(type=node_type, value=value)


def _plan_for_concepts(*values: str) -> QueryPlan:
    nodes = [_node(v) for v in values]
    operators = [OrderOperator(type=OperatorType.PRECEDENCE)] * (len(nodes) - 1)
    return QueryPlan(
        version="0.1",
        source=" > ".join(values),
        sequence=SequenceExpr(steps=nodes, operators=operators),
        scope=ScopeConstraint(),
        mode="conceptual",
        metadata=QueryMetadata(),
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
    lemmas_with_concept: list[tuple[str, str]],
    ref: str = "1Cor 13:13",
    match_type: str = "conceptual",
) -> MatchCandidate:
    tokens = [_token(lem, ref, i + 1) for i, (lem, _c) in enumerate(lemmas_with_concept)]
    alignment = [
        StepMatch(
            step_index=i,
            node_type=NodeType.CONCEPT,
            node_value=concept,
            resolved_lemmas=[lemma],
            token=tokens[i],
        )
        for i, (lemma, concept) in enumerate(lemmas_with_concept)
    ]
    return MatchCandidate(
        tokens=tokens,
        reference=ref,
        match_type=match_type,  # type: ignore[arg-type]
        alignment=alignment,
    )


def _flagship_contextualization() -> Contextualization:
    """Reproduces the Slice D ground-truth output for faith > hope > love."""
    return Contextualization(
        observed_count=2,
        node_baselines=[
            NodeBaseline(
                node_index=0,
                node_type=NodeType.CONCEPT,
                node_value="faith",
                resolved_lemmas=["πίστις", "πιστεύω"],
                count=483,
            ),
            NodeBaseline(
                node_index=1,
                node_type=NodeType.CONCEPT,
                node_value="hope",
                resolved_lemmas=["ἐλπίς", "ἐλπίζω"],
                count=84,
            ),
            NodeBaseline(
                node_index=2,
                node_type=NodeType.CONCEPT,
                node_value="love",
                resolved_lemmas=["ἀγάπη", "ἀγαπάω"],
                count=259,
            ),
        ],
        alternative_orderings=[
            AlternativeOrderingCount(
                permutation=[0, 1, 2],
                sequence_label="faith > hope > love",
                count=2,
                is_observed=True,
            ),
            AlternativeOrderingCount(
                permutation=[0, 2, 1],
                sequence_label="faith > love > hope",
                count=2,
                is_observed=False,
            ),
            AlternativeOrderingCount(
                permutation=[1, 0, 2],
                sequence_label="hope > faith > love",
                count=0,
                is_observed=False,
            ),
            AlternativeOrderingCount(
                permutation=[1, 2, 0],
                sequence_label="hope > love > faith",
                count=0,
                is_observed=False,
            ),
            AlternativeOrderingCount(
                permutation=[2, 0, 1],
                sequence_label="love > faith > hope",
                count=0,
                is_observed=False,
            ),
            AlternativeOrderingCount(
                permutation=[2, 1, 0],
                sequence_label="love > hope > faith",
                count=0,
                is_observed=False,
            ),
        ],
        alternative_orderings_capped=False,
    )


def _supported_validation() -> ValidationResult:
    return ValidationResult(
        status="supported",
        executable_plan=None,
        findings=[],
        engine_version="0.1",
    )


# ---------------------------------------------------------------------------
# explain() — flagship summary
# ---------------------------------------------------------------------------


class TestExplainFlagship:
    def test_summary_cites_pattern_count_and_verse(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = RetrievalResult(
            candidates=[
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
            ],
            stages_used=["symbolic"],
            contextualization=_flagship_contextualization(),
        )
        ers = explain(result, plan, _supported_validation())

        assert "faith > hope > love" in ers.summary
        assert "2 times" in ers.summary
        assert "1Cor 13:13" in ers.summary

    def test_summary_includes_baselines_with_resolved_lemmas(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = RetrievalResult(
            candidates=[
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
            ],
            stages_used=["symbolic"],
            contextualization=_flagship_contextualization(),
        )
        ers = explain(result, plan, _supported_validation())
        assert "Baselines:" in ers.summary
        # Baselines call out specific lemmas + counts
        assert "πίστις" in ers.summary
        assert "483" in ers.summary
        assert "84" in ers.summary
        assert "259" in ers.summary

    def test_summary_includes_alt_ordering_observation(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = RetrievalResult(
            candidates=[
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
            ],
            stages_used=["symbolic"],
            contextualization=_flagship_contextualization(),
        )
        ers = explain(result, plan, _supported_validation())
        # The flagship case has top non-observed alt at count=2 (tied with observed)
        # → "alternative ordering ... also fires N times"
        assert "alternative ordering" in ers.summary.lower()
        assert "faith > love > hope" in ers.summary

    def test_summary_at_most_six_lines(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = RetrievalResult(
            candidates=[
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
            ],
            stages_used=["symbolic"],
            contextualization=_flagship_contextualization(),
        )
        ers = explain(result, plan, _supported_validation())
        lines = ers.summary.splitlines()
        assert len(lines) <= 6, f"summary exceeded 6 lines: got {len(lines)}\n{ers.summary}"

    def test_per_candidate_explanation_cites_verse_and_lemmas(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = RetrievalResult(
            candidates=[
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
            ],
            stages_used=["symbolic"],
            contextualization=_flagship_contextualization(),
        )
        ers = explain(result, plan, _supported_validation())
        assert len(ers.results) == 2
        for er in ers.results:
            assert er.reference == "1Cor 13:13"
            assert "πίστις" in er.explanation
            assert "ἐλπίς" in er.explanation
            assert "ἀγάπη" in er.explanation
            assert er.match_type == "conceptual"
            assert er.score is None

    def test_query_shown_round_trips_plan_source(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = RetrievalResult(
            candidates=[],
            stages_used=["symbolic"],
            contextualization=None,
        )
        ers = explain(result, plan, _supported_validation())
        assert ers.query_shown == "faith > hope > love"


# ---------------------------------------------------------------------------
# Zero-match handling
# ---------------------------------------------------------------------------


class TestExplainZeroMatch:
    def test_zero_match_summary_says_does_not_appear(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = RetrievalResult(
            candidates=[],
            stages_used=["symbolic"],
            contextualization=Contextualization(
                observed_count=0,
                node_baselines=[
                    NodeBaseline(
                        node_index=0,
                        node_type=NodeType.LEMMA,
                        node_value="πίστις",
                        resolved_lemmas=["πίστις"],
                        count=483,
                    ),
                ],
                alternative_orderings=[],
                alternative_orderings_capped=False,
            ),
        )
        ers = explain(result, plan, _supported_validation())
        assert "does not appear" in ers.summary.lower()
        assert "0 matches" in ers.summary
        assert ers.results == []

    def test_zero_match_no_alt_ordering_phrase_when_empty(self) -> None:
        plan = _plan_for_concepts("zebra", "elephant")
        result = RetrievalResult(
            candidates=[],
            stages_used=["symbolic"],
            contextualization=Contextualization(
                observed_count=0,
                node_baselines=[],
                alternative_orderings=[],
                alternative_orderings_capped=False,
            ),
        )
        ers = explain(result, plan, _supported_validation())
        # Should still produce a summary; just no alt-ordering content
        assert ers.summary
        assert "alternative ordering" not in ers.summary.lower()


# ---------------------------------------------------------------------------
# Validation notes
# ---------------------------------------------------------------------------


class TestValidationNotes:
    def test_supported_yields_empty_notes(self) -> None:
        plan = _plan_for_concepts("faith", "hope")
        result = RetrievalResult(candidates=[], stages_used=["symbolic"])
        ers = explain(result, plan, _supported_validation())
        assert ers.validation_notes == []

    def test_partial_findings_become_raw_strings(self) -> None:
        plan = _plan_for_concepts("faith", "hope")
        result = RetrievalResult(candidates=[], stages_used=["symbolic"])
        validation = ValidationResult(
            status="partial",
            executable_plan=None,
            findings=[
                ValidationFinding(
                    severity="warning",
                    code="UNSUPPORTED_EXPANSION",
                    path="sequence.expansion",
                    message="expansion directives are not yet supported",
                ),
            ],
            engine_version="0.1",
        )
        ers = explain(result, plan, validation)
        assert len(ers.validation_notes) == 1
        assert "UNSUPPORTED_EXPANSION" in ers.validation_notes[0]
        assert "sequence.expansion" in ers.validation_notes[0]


# ---------------------------------------------------------------------------
# Cap/wrap helpers (Bucket 4 closure)
# ---------------------------------------------------------------------------


class TestTruncateLemmas:
    def test_under_cap_no_suffix(self) -> None:
        assert _truncate_lemmas(["a", "b", "c"]) == "a, b, c"

    def test_at_cap_no_suffix(self) -> None:
        assert _truncate_lemmas(["a", "b", "c", "d", "e"]) == "a, b, c, d, e"

    def test_over_cap_adds_suffix(self) -> None:
        result = _truncate_lemmas(["a", "b", "c", "d", "e", "f", "g"])
        assert result == "a, b, c, d, e (+2 more)"

    def test_empty_list_returns_empty_string(self) -> None:
        assert _truncate_lemmas([]) == ""

    def test_custom_cap_value(self) -> None:
        assert _truncate_lemmas(["a", "b", "c"], cap=2) == "a, b (+1 more)"


class TestTruncateSequenceLabel:
    def test_under_max_unchanged(self) -> None:
        assert _truncate_sequence_label("faith > hope > love") == "faith > hope > love"

    def test_at_max_unchanged(self) -> None:
        s = "x" * 64
        assert _truncate_sequence_label(s) == s

    def test_over_max_truncates_at_separator_when_possible(self) -> None:
        long = " > ".join(["alpha"] * 20)
        result = _truncate_sequence_label(long, max_chars=64)
        assert result.endswith("…")
        assert len(result) <= 64

    def test_over_max_truncates_mid_token_when_no_separator(self) -> None:
        long = "x" * 200
        result = _truncate_sequence_label(long, max_chars=64)
        assert result.endswith("…")
        assert len(result) <= 64

    def test_zero_chars_does_not_crash(self) -> None:
        # Edge case — should still return something sane
        result = _truncate_sequence_label("faith > hope", max_chars=4)
        assert len(result) <= 4 or result.endswith("…")


# ---------------------------------------------------------------------------
# Phrase composers
# ---------------------------------------------------------------------------


class TestFormatBaselinesPhrase:
    def test_concept_with_multiple_resolved_lemmas(self) -> None:
        baselines = [
            NodeBaseline(
                node_index=0,
                node_type=NodeType.CONCEPT,
                node_value="faith",
                resolved_lemmas=["πίστις", "πιστεύω"],
                count=483,
            ),
        ]
        out = _format_baselines_phrase(baselines)
        assert "faith" in out
        assert "πίστις" in out
        assert "483" in out

    def test_lemma_baseline_omits_redundant_resolved_list(self) -> None:
        baselines = [
            NodeBaseline(
                node_index=0,
                node_type=NodeType.LEMMA,
                node_value="πίστις",
                resolved_lemmas=["πίστις"],
                count=483,
            ),
        ]
        out = _format_baselines_phrase(baselines)
        # When node_value == resolved list, don't double-print
        assert "πίστις at 483" in out

    def test_empty_baselines_returns_empty(self) -> None:
        assert _format_baselines_phrase([]) == ""


class TestFormatAltOrderingsPhrase:
    def test_all_alts_zero(self) -> None:
        orderings = [
            AlternativeOrderingCount(
                permutation=[0, 1],
                sequence_label="a > b",
                count=2,
                is_observed=True,
            ),
            AlternativeOrderingCount(
                permutation=[1, 0],
                sequence_label="b > a",
                count=0,
                is_observed=False,
            ),
        ]
        out = _format_alt_orderings_phrase(orderings, observed_count=2)
        assert "0 matches" in out or "only one" in out

    def test_top_alt_tied_with_observed(self) -> None:
        orderings = [
            AlternativeOrderingCount(
                permutation=[0, 1, 2],
                sequence_label="a > b > c",
                count=2,
                is_observed=True,
            ),
            AlternativeOrderingCount(
                permutation=[0, 2, 1],
                sequence_label="a > c > b",
                count=2,
                is_observed=False,
            ),
        ]
        out = _format_alt_orderings_phrase(orderings, observed_count=2)
        assert "a > c > b" in out
        assert "adjacency" in out.lower() or "also fires" in out.lower()

    def test_top_alt_lower_than_observed(self) -> None:
        orderings = [
            AlternativeOrderingCount(
                permutation=[0, 1],
                sequence_label="a > b",
                count=10,
                is_observed=True,
            ),
            AlternativeOrderingCount(
                permutation=[1, 0],
                sequence_label="b > a",
                count=3,
                is_observed=False,
            ),
        ]
        out = _format_alt_orderings_phrase(orderings, observed_count=10)
        assert "b > a" in out
        assert "more frequent" in out.lower()

    def test_top_alt_higher_than_observed(self) -> None:
        orderings = [
            AlternativeOrderingCount(
                permutation=[0, 1],
                sequence_label="a > b",
                count=2,
                is_observed=True,
            ),
            AlternativeOrderingCount(
                permutation=[1, 0],
                sequence_label="b > a",
                count=8,
                is_observed=False,
            ),
        ]
        out = _format_alt_orderings_phrase(orderings, observed_count=2)
        assert "b > a" in out
        assert "NOT" in out or "not the dominant" in out.lower()

    def test_only_observed_in_list_returns_empty(self) -> None:
        orderings = [
            AlternativeOrderingCount(
                permutation=[0],
                sequence_label="a",
                count=1,
                is_observed=True,
            ),
        ]
        out = _format_alt_orderings_phrase(orderings, observed_count=1)
        assert out == ""


# ---------------------------------------------------------------------------
# Edge — long sequence (capped)
# ---------------------------------------------------------------------------


class TestCappedSummary:
    def test_capped_qualifier_appears_when_capped(self) -> None:
        plan = _plan_for_concepts("a", "b", "c", "d", "e")
        result = RetrievalResult(
            candidates=[],
            stages_used=["symbolic"],
            contextualization=Contextualization(
                observed_count=0,
                node_baselines=[],
                alternative_orderings=[
                    AlternativeOrderingCount(
                        permutation=[0, 1, 2, 3, 4],
                        sequence_label="a > b > c > d > e",
                        count=0,
                        is_observed=True,
                    ),
                ],
                alternative_orderings_capped=True,
            ),
        )
        ers = explain(result, plan, _supported_validation())
        assert "capped" in ers.summary.lower()
