"""Slice M exit-gate (M5) — deterministic two-round refinement test.

Proves the whole point of the slice: a multi-turn NL query that starts
ambiguous (cross-verse proximity, NO window size) reaches an EXECUTED result
after ONE clarification round, via stateless caller-driven ``prior_turns``
echo-back (DEC-098, DEC-099 — same route, no server conversation state).

Round 1: ``POST /api/v1/query/nl`` with no ``prior_turns`` → HTTP 200 with
``clarification`` set and the four pipeline fields ``None``.

Round 2: resubmit carrying ``prior_turns=[user(original), assistant(question)]``
plus a window-size answer as ``nl_query`` → HTTP 200, normal EXECUTED
``QueryNLResponse`` (validation/result/explanation/translation populated,
``clarification`` None, real candidates).

This runs in the DEFAULT pytest suite — NO database, NO live LLM. The two
non-determinism sources are stubbed exactly as the existing default-suite
route/orchestration tests do them:

- The LLM is a SCRIPTED fake :class:`LLMClient` (``_ScriptedLLMClient``):
  ``complete()`` (single-shot, round 1) returns a ``Clarification:`` block;
  ``complete_turns()`` (multi-message, round 2) returns Shape-A ``DSL:``.
  The fake records which seam was hit so round 2 can be asserted to have
  gone through ``complete_turns`` (the multi-turn path), not ``complete``.
- The DB-touching engine read is stubbed via
  ``monkeypatch.setattr("src.app.orchestration.retrieve", ...)`` (the same
  pattern as tests/unit/test_app_orchestration.py). The round-2 DSL is a
  lemma-only string (``πίστις``) so validation needs no registry lookup
  against the empty ConceptRegistry — again matching the orchestration
  tests' ``run_dsl_query("πίστις", ...)`` precedent.

The live-LLM twin is tests/integration/test_app_nl_refinement_live_llm.py.
"""

from __future__ import annotations

from typing import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from src.app.dependencies import (
    get_concept_registry,
    get_engine,
    get_llm_client,
    get_translation_context,
)
from src.app.main import create_app
from src.engine.models import (
    Contextualization,
    MatchCandidate,
    MatchedToken,
    NodeType,
    RetrievalResult,
    StepMatch,
)
from src.nlp.llm_client import LLMClient, Message
from src.nlp.translator import TranslationContext
from src.ontology.registry import ConceptRegistry

# An ambiguous cross-verse proximity query with NO window size — the case
# the translator must NOT silently default (Slice L / DEC-097).
_AMBIGUOUS_QUERY = "passages where faith and hope appear near each other"

# The window-size answer the caller resubmits in round 2.
_WINDOW_ANSWER = "use a window of 20 tokens"

# The clarification question the (fake) translator emits in round 1. Echoed
# back verbatim by the caller as the assistant turn in round 2.
_CLARIFICATION_QUESTION = (
    "How many tokens wide should the proximity window be? (suggested: 10, 20, 50)"
)

# Shape-A DSL the (fake) translator emits in round 2 once the window is known.
# Lemma-only (the cookbook's cooccurrence-within-window form) so validation
# needs no registry lookup against ConceptRegistry.empty().
_ROUND2_DSL = "πίστις ~ ἀγάπη within:window(20)"
_ROUND2_DSL_OUTPUT = (
    f"DSL: {_ROUND2_DSL}\n"
    "Confidence: 0.82\n"
    "Explanation: proximity window resolved to 20 tokens from the follow-up\n"
)


class _ScriptedLLMClient(LLMClient):
    """Two-round scripted fake LLM.

    Round 1 hits ``complete()`` (single-shot, empty prior_turns) → emits a
    ``Clarification:`` block. Round 2 hits ``complete_turns()`` (multi-message,
    prior_turns present) → emits Shape-A ``DSL:``. Records both call seams so
    the test can assert round 2 went through ``complete_turns``, not
    ``complete``.
    """

    def __init__(self) -> None:
        self.complete_calls: list[str] = []
        self.complete_turns_calls: list[list[Message]] = []

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.complete_calls.append(user_message)
        return f"Clarification: {_CLARIFICATION_QUESTION}\n"

    def complete_turns(self, system_prompt: str, turns: list[Message]) -> str:
        self.complete_turns_calls.append(turns)
        return _ROUND2_DSL_OUTPUT


def _stub_translation_context() -> TranslationContext:
    return TranslationContext(
        capability_registry_summary="cap-summary",
        concept_registry_summary="concepts: faith, hope, love",
    )


def _executed_retrieval_result() -> RetrievalResult:
    """A non-empty RetrievalResult so round 2 asserts REAL candidates."""
    token = MatchedToken(
        id=1,
        book="40",
        chapter=1,
        verse=1,
        position=0,
        global_position=0,
        surface_form="πίστις",
        normalized_form="πίστις",
        lemma="πίστις",
        pos="N",
    )
    candidate = MatchCandidate(
        tokens=[token],
        reference="Mat 1:1",
        match_type="exact",
        alignment=[
            StepMatch(
                step_index=0,
                node_type=NodeType.LEMMA,
                node_value="πίστις",
                resolved_lemmas=["πίστις"],
                token=token,
            )
        ],
    )
    return RetrievalResult(
        candidates=[candidate],
        stages_used=["pattern_engine"],
        contextualization=Contextualization(
            observed_count=1,
            node_baselines=[],
            alternative_orderings=[],
            alternative_orderings_capped=False,
            null_distribution=None,
        ),
    )


@pytest.fixture
def scripted_llm() -> _ScriptedLLMClient:
    return _ScriptedLLMClient()


@pytest.fixture
def app(
    monkeypatch: pytest.MonkeyPatch, scripted_llm: _ScriptedLLMClient
) -> FastAPI:
    """App with all four DI providers overridden — no real DB / LLM.

    The LLM provider returns the SAME scripted client instance across both
    rounds (so the test can inspect its recorded calls). ``retrieve`` is
    stubbed so the DSL pipeline never touches a database.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SPL_EXPLAINER_LLM", raising=False)
    monkeypatch.setattr(
        "src.app.orchestration.retrieve",
        lambda *a, **kw: _executed_retrieval_result(),
    )
    fastapi_app = create_app()
    fastapi_app.dependency_overrides[get_engine] = lambda: MagicMock(
        spec=Engine, name="fake_engine"
    )
    fastapi_app.dependency_overrides[get_concept_registry] = (
        lambda: ConceptRegistry.empty()
    )
    fastapi_app.dependency_overrides[get_llm_client] = lambda: scripted_llm
    fastapi_app.dependency_overrides[get_translation_context] = (
        _stub_translation_context
    )
    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


class TestTwoRoundRefinementExitGate:
    """Slice M exit gate: ambiguous → clarification → answered → executed."""

    def test_round_one_returns_clarification(
        self, client: TestClient, scripted_llm: _ScriptedLLMClient
    ) -> None:
        """Round 1: ambiguous cross-verse proximity, no prior_turns → 200 with
        ``clarification`` set and the four pipeline fields ``None``."""
        resp = client.post(
            "/api/v1/query/nl",
            json={"nl_query": _AMBIGUOUS_QUERY},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Clarification path: question echoed, pipeline fields absent.
        assert body["clarification"] is not None
        assert body["clarification"]["question"] == _CLARIFICATION_QUESTION
        assert body["clarification"]["nl_source"] == _AMBIGUOUS_QUERY
        assert body["clarification"]["suggested_windows"]  # non-empty default
        assert body["validation"] is None
        assert body["result"] is None
        assert body["explanation"] is None
        assert body["translation"] is None
        # ``query`` echoes the original NL on the clarification path.
        assert body["query"] == _AMBIGUOUS_QUERY

        # Round 1 went through the single-shot seam, NOT complete_turns.
        assert len(scripted_llm.complete_calls) == 1
        assert scripted_llm.complete_turns_calls == []

    def test_round_two_resolves_to_executed_result(
        self, client: TestClient, scripted_llm: _ScriptedLLMClient
    ) -> None:
        """Round 2: resubmit carrying prior_turns + a window answer → 200 with
        a normal EXECUTED envelope (pipeline fields populated, ``clarification``
        None, real candidates), and the call went through ``complete_turns``."""
        # Round 1 (drives the clarification so round 2 carries a real question).
        first = client.post(
            "/api/v1/query/nl",
            json={"nl_query": _AMBIGUOUS_QUERY},
        )
        assert first.status_code == 200, first.text
        question = first.json()["clarification"]["question"]

        # Round 2: caller echoes back the conversation + answers the question.
        resp = client.post(
            "/api/v1/query/nl",
            json={
                "nl_query": _WINDOW_ANSWER,
                "prior_turns": [
                    {"role": "user", "content": _AMBIGUOUS_QUERY},
                    {"role": "assistant", "content": question},
                ],
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Executed path: clarification absent, all four pipeline fields present.
        assert body["clarification"] is None
        assert body["validation"] is not None
        assert body["result"] is not None
        assert body["explanation"] is not None
        assert body["translation"] is not None

        # ``query`` carries the COMPILED DSL (not the NL) on the executed path.
        assert body["query"] == _ROUND2_DSL
        assert body["translation"]["confidence"] == 0.82

        # Real candidates flowed through the (stubbed) engine read.
        assert len(body["result"]["candidates"]) == 1
        assert body["result"]["candidates"][0]["reference"] == "Mat 1:1"
        assert len(body["explanation"]["results"]) == 1

        # Round 2 MUST have gone through complete_turns (the multi-turn seam),
        # not complete — this is the load-bearing refinement assertion.
        assert len(scripted_llm.complete_turns_calls) == 1
        sent_turns = scripted_llm.complete_turns_calls[0]
        roles = [t["role"] for t in sent_turns]
        # turn[0] user (rebuilt w/ registry summaries), assistant question,
        # then the current window answer as the latest user turn.
        assert roles == ["user", "assistant", "user"]
        # The registry summaries ride on the rebuilt first user turn.
        assert "Concept registry summary" in sent_turns[0]["content"]
        assert _AMBIGUOUS_QUERY in sent_turns[0]["content"]
        assert sent_turns[1]["content"] == question
        assert sent_turns[2]["content"] == _WINDOW_ANSWER
