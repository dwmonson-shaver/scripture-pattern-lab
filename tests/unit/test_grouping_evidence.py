"""Slice P Phase 2 — compute_grouping_evidence assembly (DB/engine stubbed).

These tests stub the engine (parse/execute) and the id lookup so they exercise
the assembly logic only: pair enumeration, unresolved-member handling, sample
cap, declared-inverse flagging, and the descriptive threshold flag. The live
engine path is covered in tests/integration/test_grouping_evidence.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import src.retrieval.grouping_evidence as ge
from src.ontology.concept_grouping import GroupingMember, Tier2Grouping
from src.retrieval.grouping_evidence import compute_grouping_evidence


def _grouping(*names: str) -> Tier2Grouping:
    members = [GroupingMember(concept_name=n, confidence=0.9) for n in names]
    return Tier2Grouping(
        anchor_name=names[0],
        members=members,
        rationale="test cluster",
        created_at=datetime.now(tz=UTC),
    )


class FakeRegistry:
    def __init__(
        self,
        lemmas: dict[str, list[str]],
        inverse: dict[int, list[SimpleNamespace]] | None = None,
    ) -> None:
        self._lemmas = lemmas
        self._inverse = inverse or {}

    def get_lemmas_for_concept(self, name: str, language: str = "grc") -> list[str]:
        return self._lemmas.get(name, [])

    def get_inverse_claims(self, concept_id: int) -> list[SimpleNamespace]:
        return self._inverse.get(concept_id, [])


def _stub_engine(monkeypatch, *, counts: dict[frozenset[str], int], ids: dict[str, int]):
    """Stub parse()/execute()/_concept_ids so no DB or real engine is touched.

    `counts` maps a lemma-pair (frozenset) to the number of fake candidates
    execute() should return for that pair's DSL.
    """
    def fake_parse(dsl: str):
        # Recover the two lemmas from `lemma:A ~ lemma:B within...`.
        la = dsl.split("lemma:", 1)[1].split(" ", 1)[0]
        lb = dsl.split("lemma:")[2].split(" ", 1)[0]
        return SimpleNamespace(scope="SCOPE", _pair=frozenset((la, lb)))

    def fake_execute(plan, scope, engine, concept_registry=None):
        n = counts.get(plan._pair, 0)
        return [SimpleNamespace(reference=f"REF {i}") for i in range(n)]

    monkeypatch.setattr(ge, "parse", fake_parse)
    monkeypatch.setattr(ge, "execute", fake_execute)
    monkeypatch.setattr(ge, "_concept_ids", lambda names, engine: ids)


class TestComputeAssembly:
    def test_resolved_pair_reports_count_and_refs(self, monkeypatch) -> None:
        reg = FakeRegistry({"humility": ["tap"], "meekness": ["prau"]})
        _stub_engine(monkeypatch, counts={frozenset(("tap", "prau")): 3}, ids={})
        ev = compute_grouping_evidence(
            _grouping("humility", "meekness"), engine=object(), registry=reg, threshold=2
        )
        assert ev.anchor_name == "humility"
        assert len(ev.pairs) == 1
        p = ev.pairs[0]
        assert p.match_count == 3
        assert p.sample_refs == ["REF 0", "REF 1", "REF 2"]
        assert p.cooccurrence_threshold_met is True  # 3 >= 2

    def test_threshold_flag_is_descriptive_only(self, monkeypatch) -> None:
        reg = FakeRegistry({"a": ["la"], "b": ["lb"]})
        _stub_engine(monkeypatch, counts={frozenset(("la", "lb")): 1}, ids={})
        ev = compute_grouping_evidence(
            _grouping("a", "b"), engine=object(), registry=reg, threshold=5
        )
        # Below threshold: flag False, but the raw count is still surfaced.
        assert ev.pairs[0].match_count == 1
        assert ev.pairs[0].cooccurrence_threshold_met is False

    def test_unresolved_member_yields_zero_evidence(self, monkeypatch) -> None:
        # 'lowliness' has no lemma → Bucket-N3 case; execute never called for it.
        reg = FakeRegistry({"humility": ["tap"], "lowliness": []})
        _stub_engine(monkeypatch, counts={}, ids={})
        ev = compute_grouping_evidence(
            _grouping("humility", "lowliness"), engine=object(), registry=reg
        )
        p = ev.pairs[0]
        assert p.lemma_b is None
        assert p.match_count == 0
        assert p.sample_refs == []
        assert p.cooccurrence_threshold_met is False

    def test_all_member_pairs_enumerated(self, monkeypatch) -> None:
        reg = FakeRegistry({"a": ["la"], "b": ["lb"], "c": ["lc"]})
        _stub_engine(
            monkeypatch,
            counts={
                frozenset(("la", "lb")): 1,
                frozenset(("la", "lc")): 2,
                frozenset(("lb", "lc")): 0,
            },
            ids={},
        )
        ev = compute_grouping_evidence(_grouping("a", "b", "c"), engine=object(), registry=reg)
        assert len(ev.pairs) == 3  # C(3,2)
        assert {p.match_count for p in ev.pairs} == {0, 1, 2}

    def test_sample_cap_limits_refs(self, monkeypatch) -> None:
        reg = FakeRegistry({"a": ["la"], "b": ["lb"]})
        _stub_engine(monkeypatch, counts={frozenset(("la", "lb")): 50}, ids={})
        ev = compute_grouping_evidence(
            _grouping("a", "b"), engine=object(), registry=reg, sample_cap=5
        )
        assert ev.pairs[0].match_count == 50
        assert len(ev.pairs[0].sample_refs) == 5

    def test_declared_inverse_pair_is_flagged(self, monkeypatch) -> None:
        # a(id1) declares b(id2) as inverse → the pair is flagged.
        reg = FakeRegistry(
            {"a": ["la"], "b": ["lb"]},
            inverse={1: [SimpleNamespace(inverse_concept_id=2)]},
        )
        _stub_engine(
            monkeypatch, counts={frozenset(("la", "lb")): 9}, ids={"a": 1, "b": 2}
        )
        ev = compute_grouping_evidence(_grouping("a", "b"), engine=object(), registry=reg)
        assert ev.pairs[0].is_declared_inverse is True
        # Co-occurrence is high, but the inverse flag warns it's opposition.
        assert ev.pairs[0].match_count == 9
