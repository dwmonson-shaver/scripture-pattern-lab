"""Unit tests for ``src/retrieval/retrieve.py``.

Stubs ``execute`` and ``contextualize`` (the imports inside ``retrieve``)
so the wrapper's branching is exercised without a real DB. Real SQL
exercise is in ``tests/integration/test_contextualization.py``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.engine.models import (
    Contextualization,
    MatchCandidate,
    NodeRef,
    NodeType,
    QueryPlan,
    RetrievalResult,
    ScopeConstraint,
    SequenceExpr,
    UnsupportedPlanShape,
)
from src.retrieval.retrieve import retrieve


def _make_plan(seq: SequenceExpr, scope: ScopeConstraint | None = None) -> QueryPlan:
    return QueryPlan(
        version="0.1",
        source="<test>",
        sequence=seq,
        scope=scope or ScopeConstraint(),
        mode="exact",
    )


def _candidates(*references: str) -> list[MatchCandidate]:
    return [
        MatchCandidate(
            tokens=[],
            reference=ref,
            match_type="exact",
            alignment=[],
        )
        for ref in references
    ]


def _ctx_stub(*, observed: int = 2) -> Contextualization:
    return Contextualization(
        observed_count=observed,
        node_baselines=[],
        alternative_orderings=[],
        alternative_orderings_capped=False,
    )


def _stub_execute_returning(candidates: list[MatchCandidate]) -> Any:
    def _stub(*_args: Any, **_kw: Any) -> list[MatchCandidate]:
        return candidates
    return _stub


def _stub_execute_raising(exc: Exception) -> Any:
    def _stub(*_args: Any, **_kw: Any) -> list[MatchCandidate]:
        raise exc
    return _stub


def _stub_contextualize(ctx: Contextualization) -> Any:
    def _stub(*_args: Any, **_kw: Any) -> Contextualization:
        return ctx
    return _stub


def test_default_off_returns_no_contextualization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Engine-layer default is contextualize=False per OQ #1 middle path."""
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )
    plan = _make_plan(seq)
    cands = _candidates("1Cor 13:13")
    monkeypatch.setattr(
        "src.retrieval.retrieve.execute", _stub_execute_returning(cands)
    )

    result = retrieve(plan, plan.scope, MagicMock())

    assert isinstance(result, RetrievalResult)
    assert result.candidates == cands
    assert result.stages_used == ["symbolic"]
    assert result.contextualization is None


def test_contextualize_true_attaches_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )
    plan = _make_plan(seq)
    cands = _candidates("1Cor 13:13", "Rom 1:1")
    expected_ctx = _ctx_stub(observed=2)
    monkeypatch.setattr(
        "src.retrieval.retrieve.execute", _stub_execute_returning(cands)
    )
    monkeypatch.setattr(
        "src.retrieval.retrieve._build_contextualization",
        _stub_contextualize(expected_ctx),
    )

    result = retrieve(plan, plan.scope, MagicMock(), contextualize=True)

    assert result.candidates == cands
    assert result.contextualization is expected_ctx


def test_executor_exceptions_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    """UnsupportedPlanShape from execute() is not caught by retrieve()."""
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )
    plan = _make_plan(seq)
    monkeypatch.setattr(
        "src.retrieval.retrieve.execute",
        _stub_execute_raising(UnsupportedPlanShape("malformed", path="$.x")),
    )

    with pytest.raises(UnsupportedPlanShape):
        retrieve(plan, plan.scope, MagicMock(), contextualize=True)


def test_empty_candidate_list_still_attaches_contextualization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zero matches still produces a Contextualization envelope when requested."""
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="not_a_real_lemma")],
        operators=[],
    )
    plan = _make_plan(seq)
    expected_ctx = _ctx_stub(observed=0)
    monkeypatch.setattr(
        "src.retrieval.retrieve.execute", _stub_execute_returning([])
    )
    monkeypatch.setattr(
        "src.retrieval.retrieve._build_contextualization",
        _stub_contextualize(expected_ctx),
    )

    result = retrieve(plan, plan.scope, MagicMock(), contextualize=True)

    assert result.candidates == []
    assert result.contextualization is expected_ctx


def test_registry_is_passed_through_to_execute_and_contextualize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The registry handle threads through both execute() and contextualize()."""
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )
    plan = _make_plan(seq)
    captured: dict[str, Any] = {}

    def _capture_execute(*args: Any, **kwargs: Any) -> list[MatchCandidate]:
        captured["execute_kwargs"] = kwargs
        return []

    def _capture_ctx(*args: Any, **kwargs: Any) -> Contextualization:
        captured["ctx_kwargs"] = kwargs
        return _ctx_stub(observed=0)

    monkeypatch.setattr("src.retrieval.retrieve.execute", _capture_execute)
    monkeypatch.setattr(
        "src.retrieval.retrieve._build_contextualization", _capture_ctx
    )

    sentinel = object()
    retrieve(plan, plan.scope, MagicMock(), contextualize=True, registry=sentinel)

    assert captured["execute_kwargs"]["concept_registry"] is sentinel
    assert captured["ctx_kwargs"]["registry"] is sentinel
