"""Unit tests for ``src/nlp/explainer.py``.

The explainer is fully deterministic — fixtures build hand-crafted
RetrievalResults and assert on substring contents of the produced
ExplainedResultSet. No DB access. Cap/wrap helpers are pure functions
tested in isolation at known boundaries.
"""

from __future__ import annotations

from src.engine.models import (
    AlternativeOrderingCount,
    Contextualization,
    InverseExpr,
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
    _per_candidate_prose,
    _per_candidate_prose_llm,
    _truncate_lemmas,
    _truncate_llm_prose,
    _truncate_sequence_label,
    explain,
)
from src.nlp.llm_client import LLMClient, LLMUnavailable
from src.validation.validator import ValidationFinding, ValidationResult

# ---------------------------------------------------------------------------
# LLM stubs (Slice K — Phase K.2). Subclass LLMClient so any future
# anthropic-SDK shape change does not propagate into tests.
# ---------------------------------------------------------------------------


class _FakeLLMClient(LLMClient):
    """Returns a canned response from `.complete()`."""

    def __init__(self, canned: str) -> None:
        self._canned = canned
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.calls.append((system_prompt, user_message))
        return self._canned


class _FailingLLMClient(LLMClient):
    """Raises a configurable exception from `.complete()`."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.calls.append((system_prompt, user_message))
        raise self._exc

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

    def test_summary_at_most_five_lines(self) -> None:
        # Implementation cap is 5 lines (1 match-count + 1 singularity/multi-verse +
        # 1 alt-ordering + 1 baseline + 1 capped qualifier). Spec says ≤ 6 — we
        # assert the tighter actual bound so a regression that adds a sixth line
        # is caught by this test, not buried under the spec tolerance.
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
        assert len(lines) <= 5, f"summary exceeded 5 lines: got {len(lines)}\n{ers.summary}"

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


class TestExplainEdgePaths:
    """Closes F-F4F5-001 (P2): InverseExpr label, nl_source round-trip, text_display."""

    def test_inverse_expr_plan_label_in_summary(self) -> None:
        plan = QueryPlan(
            version="0.1",
            source="inverse(faith > hope)",
            sequence=InverseExpr(
                inner=SequenceExpr(
                    steps=[_node("faith"), _node("hope")],
                    operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
                )
            ),
            scope=ScopeConstraint(),
            mode="conceptual",
            metadata=QueryMetadata(),
        )
        result = RetrievalResult(candidates=[], stages_used=["symbolic"])
        ers = explain(result, plan, _supported_validation())
        assert "inverse(faith > hope)" in ers.summary

    def test_nl_source_round_trips_from_plan_metadata(self) -> None:
        plan = _plan_for_concepts("faith", "hope")
        plan = plan.model_copy(
            update={"metadata": QueryMetadata(nl_source="Does faith come before hope?")}
        )
        result = RetrievalResult(candidates=[], stages_used=["symbolic"])
        ers = explain(result, plan, _supported_validation())
        assert ers.nl_source == "Does faith come before hope?"

    def test_text_display_populated_from_alignment(self) -> None:
        result = RetrievalResult(
            candidates=[_candidate([("πίστις", "faith"), ("ἐλπίς", "hope")])],
            stages_used=["symbolic"],
        )
        ers = explain(result, _plan_for_concepts("faith", "hope"), _supported_validation())
        assert ers.results[0].text_display == "πίστις, ἐλπίς"

    def test_text_display_empty_when_no_alignment(self) -> None:
        t = _token("πίστις")
        c = MatchCandidate(
            tokens=[t], reference="1Cor 13:13", match_type="exact", alignment=[]
        )
        result = RetrievalResult(candidates=[c], stages_used=["symbolic"])
        ers = explain(result, _plan_for_concepts("faith"), _supported_validation())
        assert ers.results[0].text_display == ""


class TestVariantMatchType:
    """Closes F-F4F5-004 (P3): variant pass-through path."""

    def test_variant_match_type_preserved_in_per_candidate_prose(self) -> None:
        c = _candidate([("πίστις", "faith")], match_type="variant")
        result = RetrievalResult(candidates=[c], stages_used=["symbolic"])
        ers = explain(result, _plan_for_concepts("faith"), _supported_validation())
        assert len(ers.results) == 1
        assert ers.results[0].match_type == "variant"
        assert "variant" in ers.results[0].explanation.lower()


class TestPoseQualityFixes:
    """Confirms F-F4F5-002 and F-F4F5-003 closures: no redundant lines."""

    def test_n1_does_not_emit_singularity_line(self) -> None:
        plan = _plan_for_concepts("faith")
        result = RetrievalResult(
            candidates=[_candidate([("πίστις", "faith")])],
            stages_used=["symbolic"],
        )
        ers = explain(result, plan, _supported_validation())
        # Line 1 already names the verse; a redundant "only verse" line must NOT appear
        assert "only verse where the sequence fires" not in ers.summary

    def test_multi_verse_under_cap_does_not_repeat_count(self) -> None:
        plan = _plan_for_concepts("faith")
        result = RetrievalResult(
            candidates=[
                _candidate([("πίστις", "faith")], ref="Rom 1:17"),
                _candidate([("πίστις", "faith")], ref="Gal 3:11"),
            ],
            stages_used=["symbolic"],
        )
        ers = explain(result, plan, _supported_validation())
        # Line 1 enumerates the verses inline; line 2 must NOT repeat the count
        assert "fires across 2 distinct verses" not in ers.summary

    def test_multi_verse_over_cap_does_emit_count_line(self) -> None:
        plan = _plan_for_concepts("faith")
        # 4 distinct refs > _VERSE_LIST_CAP (3); inline list is truncated, so the
        # count line carries the total
        result = RetrievalResult(
            candidates=[
                _candidate([("πίστις", "faith")], ref="Rom 1:17"),
                _candidate([("πίστις", "faith")], ref="Gal 3:11"),
                _candidate([("πίστις", "faith")], ref="Heb 11:1"),
                _candidate([("πίστις", "faith")], ref="Jas 2:17"),
            ],
            stages_used=["symbolic"],
        )
        ers = explain(result, plan, _supported_validation())
        assert "fires across 4 distinct verses" in ers.summary


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


# ---------------------------------------------------------------------------
# Slice K — Phase K.3: explain() opt-in LLM path for conceptual prose
# ---------------------------------------------------------------------------


class TestExplainWithLLMClient:
    """End-to-end explain() behavior with an injected LLMClient.

    The slice's load-bearing contracts:
    (a) byte-identical envelope when no client is injected (backwards compat
        with 540 existing tests);
    (b) conceptual candidates' explanation strings reflect the LLM paraphrase
        when a client is injected;
    (c) variant / exact candidates never see the LLM regardless of client;
    (d) summary, baselines, alt-orderings, validation notes always
        deterministic regardless of client.
    """

    def _flagship_result(self) -> RetrievalResult:
        return RetrievalResult(
            candidates=[
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
                _candidate([("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")]),
            ],
            stages_used=["symbolic"],
            contextualization=_flagship_contextualization(),
        )

    def test_default_call_unchanged_when_no_llm_client(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = self._flagship_result()
        validation = _supported_validation()
        # Call once without llm_client, once with explicit None — they must
        # produce byte-identical dumps.
        ers_default = explain(result, plan, validation)
        ers_none = explain(result, plan, validation, llm_client=None)
        assert ers_default.model_dump() == ers_none.model_dump()

    def test_llm_paraphrases_conceptual_candidates(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = self._flagship_result()
        validation = _supported_validation()
        canned = (
            "At 1Cor 13:13 the lemmas πίστις, ἐλπίς, and ἀγάπη appear in "
            "the conceptual pattern faith > hope > love."
        )
        client = _FakeLLMClient(canned=canned)
        ers_det = explain(result, plan, validation)
        ers_llm = explain(result, plan, validation, llm_client=client)
        # Both conceptual candidates' explanation strings come from the LLM.
        for r in ers_llm.results:
            assert r.explanation == canned
        # The deterministic explanation differs (i.e., the LLM path actually
        # took effect — not a no-op).
        for r_det, r_llm in zip(ers_det.results, ers_llm.results):
            assert r_det.explanation != r_llm.explanation

    def test_llm_client_called_once_per_conceptual_candidate(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = self._flagship_result()
        client = _FakeLLMClient(canned="A grounded sentence at 1Cor 13:13 mentions πίστις.")
        explain(result, plan, _supported_validation(), llm_client=client)
        # Two conceptual candidates in fixture → two LLM calls.
        assert len(client.calls) == 2

    def test_variant_match_type_not_routed_through_llm(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        # Single variant candidate alongside one conceptual candidate.
        variant_cand = _candidate(
            [("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")],
            match_type="variant",
        )
        conceptual_cand = _candidate(
            [("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")],
            match_type="conceptual",
        )
        result = RetrievalResult(
            candidates=[variant_cand, conceptual_cand],
            stages_used=["symbolic"],
            contextualization=_flagship_contextualization(),
        )
        client = _FakeLLMClient(canned="LLM-prose 1Cor 13:13 πίστις ἐλπίς ἀγάπη.")
        ers = explain(result, plan, _supported_validation(), llm_client=client)
        # Only ONE LLM call (for the conceptual; the variant uses deterministic).
        assert len(client.calls) == 1
        # The variant's explanation matches the deterministic helper exactly.
        det_variant = _per_candidate_prose(variant_cand, "faith > hope > love")
        assert ers.results[0].explanation == det_variant
        # The conceptual's explanation came from the LLM.
        assert ers.results[1].explanation == "LLM-prose 1Cor 13:13 πίστις ἐλπίς ἀγάπη."

    def test_summary_unaffected_by_llm_client(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = self._flagship_result()
        validation = _supported_validation()
        client = _FakeLLMClient(canned="Anything 1Cor 13:13 πίστις.")
        ers_det = explain(result, plan, validation)
        ers_llm = explain(result, plan, validation, llm_client=client)
        assert ers_det.summary == ers_llm.summary

    def test_contextualization_unaffected_by_llm_client(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = self._flagship_result()
        validation = _supported_validation()
        client = _FakeLLMClient(canned="Anything 1Cor 13:13 πίστις.")
        ers_det = explain(result, plan, validation)
        ers_llm = explain(result, plan, validation, llm_client=client)
        # The full Contextualization payload (baselines, alt-orderings, etc.)
        # is byte-identical.
        assert ers_det.contextualization == ers_llm.contextualization

    def test_validation_notes_unaffected_by_llm_client(self) -> None:
        plan = _plan_for_concepts("faith", "hope", "love")
        result = self._flagship_result()
        # Validation with one warning finding to ensure the path is exercised.
        validation = ValidationResult(
            status="partial",
            executable_plan=None,
            findings=[
                ValidationFinding(
                    severity="warning",
                    code="REGISTRY_NOT_VERIFIED",
                    path="$.sequence.steps[0]",
                    message="concept 'faith' is prior-grounded (unverified)",
                ),
            ],
            engine_version="0.1",
        )
        client = _FakeLLMClient(canned="A 1Cor 13:13 πίστις paraphrase.")
        ers_det = explain(result, plan, validation)
        ers_llm = explain(result, plan, validation, llm_client=client)
        assert ers_det.validation_notes == ers_llm.validation_notes

    def test_llm_fallback_does_not_corrupt_envelope(self) -> None:
        """If the LLM raises, the conceptual candidate gets deterministic prose."""
        plan = _plan_for_concepts("faith", "hope", "love")
        result = self._flagship_result()
        validation = _supported_validation()
        client = _FailingLLMClient(exc=LLMUnavailable("simulated outage"))
        ers_fallback = explain(result, plan, validation, llm_client=client)
        ers_det = explain(result, plan, validation)
        # Full envelope is byte-identical to the deterministic envelope.
        assert ers_fallback.model_dump() == ers_det.model_dump()

    def test_exact_match_type_not_routed_through_llm(self) -> None:
        """K-MID-003: symmetric coverage with the variant test.

        match_type values are exact / variant / conceptual. The dispatch
        rule only routes conceptual through the LLM. Lock the exact case
        explicitly so a future regression that broadens the dispatch is
        caught by this test.
        """
        plan = _plan_for_concepts("faith", "hope", "love")
        exact_cand = _candidate(
            [("πίστις", "faith"), ("ἐλπίς", "hope"), ("ἀγάπη", "love")],
            match_type="exact",
        )
        result = RetrievalResult(
            candidates=[exact_cand],
            stages_used=["symbolic"],
            contextualization=_flagship_contextualization(),
        )
        client = _FakeLLMClient(canned="LLM-prose 1Cor 13:13 πίστις.")
        ers = explain(result, plan, _supported_validation(), llm_client=client)
        # NO LLM calls — exact-match candidates use deterministic prose.
        assert len(client.calls) == 0
        # The exact candidate's explanation matches the deterministic helper.
        det = _per_candidate_prose(exact_cand, "faith > hope > love")
        assert ers.results[0].explanation == det


# ---------------------------------------------------------------------------
# Slice K — Phase K.2: _per_candidate_prose_llm helper
# ---------------------------------------------------------------------------


class TestPerCandidateProseLLM:
    """Unit tests for the LLM-backed per-candidate prose helper.

    The deterministic _per_candidate_prose is the fallback contract: any
    failure (LLMUnavailable, unexpected Exception, FALLBACK sentinel, empty
    output) returns the deterministic output. Successful LLM output is
    truncated to _LLM_PROSE_MAX defense-in-depth.
    """

    @staticmethod
    def _flagship_candidate() -> MatchCandidate:
        return _candidate([
            ("πίστις", "faith"),
            ("ἐλπίς", "hope"),
            ("ἀγάπη", "love"),
        ])

    def test_returns_llm_output_when_successful(self) -> None:
        cand = self._flagship_candidate()
        canned = (
            "At 1Cor 13:13 the words πίστις, ἐλπίς and ἀγάπη appear in "
            "sequence matching the conceptual pattern."
        )
        client = _FakeLLMClient(canned=canned)
        prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
        assert prose == canned
        # The LLM was actually called once with the expected prompt shape.
        assert len(client.calls) == 1
        system, user = client.calls[0]
        assert "Do not invent" in system
        assert "Verse reference: 1Cor 13:13" in user

    def test_falls_back_when_llm_returns_fallback_token(self) -> None:
        cand = self._flagship_candidate()
        client = _FakeLLMClient(canned="FALLBACK")
        prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
        # Same as the deterministic helper would have returned.
        deterministic = _per_candidate_prose(cand, "faith > hope > love")
        assert prose == deterministic

    def test_falls_back_when_llm_returns_fallback_with_punctuation(self) -> None:
        """K-MID-001: ``FALLBACK.`` / ``FALLBACK!`` / mixed-case all bail.

        LLMs sometimes pad the bail-out with trailing punctuation. The
        token detector must recognize these variants without false
        positives on real prose containing the word.
        """
        cand = self._flagship_candidate()
        for variant in ["FALLBACK.", "FALLBACK!", "fallback", "Fallback ", "FALLBACK\n"]:
            client = _FakeLLMClient(canned=variant)
            prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
            deterministic = _per_candidate_prose(cand, "faith > hope > love")
            assert prose == deterministic, (
                f"variant {variant!r} should be recognized as FALLBACK signal"
            )

    def test_does_not_misidentify_prose_containing_word_fallback(self) -> None:
        """K-MID-001 negative: real prose mentioning fallback is NOT bailed."""
        cand = self._flagship_candidate()
        # A 60-char paraphrase that happens to start with FALLBACK-shape word.
        canned = "FALLBACK is what we say when 1Cor 13:13 πίστις cannot be paraphrased here."
        client = _FakeLLMClient(canned=canned)
        prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
        # Not the deterministic prose — the full LLM output (within cap).
        deterministic = _per_candidate_prose(cand, "faith > hope > love")
        assert prose != deterministic
        assert prose == canned

    def test_falls_back_when_llm_returns_empty_string(self) -> None:
        cand = self._flagship_candidate()
        client = _FakeLLMClient(canned="   \n  ")  # all whitespace
        prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
        deterministic = _per_candidate_prose(cand, "faith > hope > love")
        assert prose == deterministic

    def test_falls_back_on_llm_unavailable(self, caplog) -> None:
        cand = self._flagship_candidate()
        client = _FailingLLMClient(exc=LLMUnavailable("rate-limited"))
        with caplog.at_level("WARNING", logger="src.nlp.explainer"):
            prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
        deterministic = _per_candidate_prose(cand, "faith > hope > love")
        assert prose == deterministic
        # Log contains the candidate ref and the reason — operators can audit.
        messages = [rec.getMessage() for rec in caplog.records]
        assert any(
            "1Cor 13:13" in m and "rate-limited" in m for m in messages
        ), f"expected ref+reason in warnings; got {messages!r}"

    def test_falls_back_on_unexpected_exception(self, caplog) -> None:
        cand = self._flagship_candidate()
        client = _FailingLLMClient(exc=RuntimeError("boom"))
        with caplog.at_level("WARNING", logger="src.nlp.explainer"):
            prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
        deterministic = _per_candidate_prose(cand, "faith > hope > love")
        assert prose == deterministic
        # Log includes the candidate ref AND a traceback (exc_info=True).
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert warning_records, "expected at least one WARNING record"
        record = warning_records[-1]
        assert "1Cor 13:13" in record.getMessage()
        assert record.exc_info is not None, "expected exc_info=True traceback"

    def test_truncates_overlong_output(self) -> None:
        cand = self._flagship_candidate()
        long_canned = "1Cor 13:13 πίστις " + ("x" * 600)
        client = _FakeLLMClient(canned=long_canned)
        prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
        # Truncated to <= _LLM_PROSE_MAX (300) with ellipsis.
        assert len(prose) <= 300
        assert prose.endswith("…")

    def test_truncate_helper_passes_through_short_text(self) -> None:
        text = "A short sentence."
        assert _truncate_llm_prose(text) == text

    def test_truncate_helper_caps_long_text_with_ellipsis(self) -> None:
        text = "y" * 500
        result = _truncate_llm_prose(text, max_chars=50)
        assert len(result) == 50
        assert result.endswith("…")

    def test_grounded_input_can_round_trip_when_llm_obeys_rules(self) -> None:
        """When the LLM emits grounded prose, it is returned unchanged."""
        cand = self._flagship_candidate()
        grounded = (
            "At 1Cor 13:13 the lemmas πίστις, ἐλπίς, and ἀγάπη appear in the "
            "conceptual pattern faith > hope > love."
        )
        client = _FakeLLMClient(canned=grounded)
        prose = _per_candidate_prose_llm(cand, "faith > hope > love", client)
        assert prose == grounded
        # Sanity: every digit substring of the LLM output traces to the input.
        import re as _re
        for digit_run in _re.findall(r"\d+", prose):
            assert digit_run in cand.reference or digit_run in "faith > hope > love"
