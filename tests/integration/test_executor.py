"""Integration tests for ``src/engine/executor.py``.

Exercises the executor end-to-end against a live Postgres with the
canonical schemas applied (see ``bash scripts/db/apply_schemas.sh``).
Mirrors the fixture pattern in ``test_corpus_ingest.py`` and the registry
seed pattern in ``test_concept_registry_reader.py``.

The slice-level exit gate is :func:`test_full_corpus_faith_hope_love_in_1cor_13_13`.
It requires the full 27-book corpus AND the seeded registry; both are
prepared by the module-scoped ``loaded_full_corpus_with_registry`` fixture.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from src.engine.executor import execute
from src.engine.models import (
    GapConstraint,
    MatchCandidate,
    NodeRef,
    NodeType,
    OperatorType,
    OrderOperator,
    QueryPlan,
    ScopeConstraint,
    ScopeUnitVerse,
    SequenceExpr,
)
from src.engine.parser import parse
from src.ingestion.corpus_parser import parse_corpus_file
from src.ingestion.db import get_engine
from src.ingestion.loader import load_tokens
from src.ontology.registry import (
    ConceptRegistry,
    concept_lemmas_table,
    concepts_table,
)
from src.validation.registry import CapabilityRegistry
from src.validation.validator import validate

REAL_3JN_PATH = Path("data/raw/morphgnt-sblgnt/85-3Jn-morphgnt.txt")
REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_SCRIPT = REPO_ROOT / "scripts" / "db" / "ingest_corpus.py"
SEED_SCRIPT = REPO_ROOT / "scripts" / "db" / "seed_registry.py"


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _wipe_registry(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM inverse_claims"))
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concept_lemmas"))
        connection.execute(text("DELETE FROM concepts"))


@pytest.fixture(scope="module")
def loaded_3jn_engine() -> Iterator[Engine]:
    """Truncate ``tokens``, load 3 John, yield the engine.

    Module scope: one load shared across all 3-John executor tests.
    """
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE tokens RESTART IDENTITY"))
    load_tokens(engine, parse_corpus_file(REAL_3JN_PATH))
    yield engine


@pytest.fixture
def clean_registry(loaded_3jn_engine: Engine) -> Iterator[Engine]:
    """Wipe the registry before/after each test that needs the empty state."""
    _wipe_registry(loaded_3jn_engine)
    try:
        yield loaded_3jn_engine
    finally:
        _wipe_registry(loaded_3jn_engine)


@pytest.fixture(scope="module")
def loaded_full_corpus_with_registry() -> Iterator[tuple[Engine, ConceptRegistry]]:
    """Run the real ingest + seed scripts so the slice exit-gate test can run.

    Subprocess-style mirrors ``test_corpus_ingest.py::test_full_corpus_smoke``
    so the real CLI binaries are exercised (not in-process imports).
    """
    import os

    env = os.environ.copy()
    env["SPL_INGEST_CONFIRM_TRUNCATE"] = "1"
    env["SPL_REGISTRY_CONFIRM_TRUNCATE"] = "1"

    ingest = subprocess.run(
        [sys.executable, str(INGEST_SCRIPT), "--truncate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert ingest.returncode == 0, (
        f"ingest_corpus.py failed: stderr tail="
        f"{ingest.stderr.splitlines()[-15:]!r}"
    )

    seed = subprocess.run(
        [sys.executable, str(SEED_SCRIPT), "--truncate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert seed.returncode == 0, (
        f"seed_registry.py failed: stderr tail="
        f"{seed.stderr.splitlines()[-15:]!r}"
    )

    engine = get_engine()
    yield engine, ConceptRegistry(engine)


# ---------------------------------------------------------------------------
# 3-John tests
# ---------------------------------------------------------------------------


def _make_lemma_sequence(
    lemmas: list[str],
    *,
    gap: GapConstraint | None = None,
    scope: ScopeConstraint | None = None,
) -> QueryPlan:
    steps = [NodeRef(type=NodeType.LEMMA, value=lemma) for lemma in lemmas]
    operators: list[OrderOperator] = []
    for _ in range(len(lemmas) - 1):
        operators.append(
            OrderOperator(type=OperatorType.PRECEDENCE, gap=gap)
        )
    return QueryPlan(
        version="0.1",
        source=" > ".join(f"lemma:{lemma}" for lemma in lemmas),
        sequence=SequenceExpr(steps=steps, operators=operators),
        scope=scope or ScopeConstraint(unit=ScopeUnitVerse()),
        mode="exact",
    )


def test_single_lemma_step_returns_matches(loaded_3jn_engine: Engine) -> None:
    """A single-step plan for ``Γάϊος`` returns at least one candidate in 3Jn 1:1."""
    plan = _make_lemma_sequence(["Γάϊος"])
    results = execute(plan, plan.scope, loaded_3jn_engine)
    assert len(results) >= 1
    references = {c.reference for c in results}
    assert "3Jn 1:1" in references
    for candidate in results:
        assert candidate.match_type == "exact"
        assert isinstance(candidate, MatchCandidate)


def test_two_step_sequence_in_verse_returns_match(
    loaded_3jn_engine: Engine,
) -> None:
    """``Γάϊος > ἀγαπητός`` matches 3Jn 1:1 (positions 3 and 5)."""
    plan = _make_lemma_sequence(["Γάϊος", "ἀγαπητός"])
    results = execute(plan, plan.scope, loaded_3jn_engine)
    assert len(results) == 1
    candidate = results[0]
    assert candidate.reference == "3Jn 1:1"
    assert [t.lemma for t in candidate.tokens] == ["Γάϊος", "ἀγαπητός"]
    assert candidate.tokens[0].position < candidate.tokens[1].position
    assert candidate.match_type == "exact"


def test_two_step_sequence_no_match_returns_empty(
    loaded_3jn_engine: Engine,
) -> None:
    """A 2-step plan whose lemmas do not co-occur returns []."""
    # ``Γάϊος`` is in 3Jn 1:1; ``ξενοφών`` is not in 3 John at all.
    plan = _make_lemma_sequence(["Γάϊος", "ξενοφών"])
    results = execute(plan, plan.scope, loaded_3jn_engine)
    assert results == []


def test_concept_step_resolves_via_registry(clean_registry: Engine) -> None:
    """A concept step expands to its lemmas and the candidate is conceptual."""
    engine = clean_registry
    # Seed a tiny concept "greeting" with lemma Γάϊος (so there's a real
    # corpus hit when we run against 3 John).
    with engine.begin() as connection:
        cid = connection.execute(
            concepts_table.insert()
            .values(name="greeting")
            .returning(concepts_table.c.id)
        ).scalar_one()
        connection.execute(
            concept_lemmas_table.insert().values(
                concept_id=cid, lemma="Γάϊος", language="grc"
            )
        )

    registry = ConceptRegistry(engine)
    plan = QueryPlan(
        version="0.1",
        source="concept:greeting",
        sequence=SequenceExpr(
            steps=[NodeRef(type=NodeType.CONCEPT, value="greeting")],
            operators=[],
        ),
        scope=ScopeConstraint(unit=ScopeUnitVerse()),
        mode="conceptual",
    )
    results = execute(plan, plan.scope, engine, concept_registry=registry)
    assert len(results) >= 1
    for candidate in results:
        assert candidate.match_type == "conceptual"
        assert candidate.alignment[0].resolved_lemmas == ["Γάϊος"]
        assert candidate.alignment[0].node_value == "greeting"


def test_book_filter_normalizes_abbreviation(loaded_3jn_engine: Engine) -> None:
    """``scope.books=['3jn']`` resolves through book_abbrev_to_bb to BB '25'."""
    plan = _make_lemma_sequence(
        ["Γάϊος"],
        scope=ScopeConstraint(unit=ScopeUnitVerse(), books=["3jn"]),
    )
    results = execute(plan, plan.scope, loaded_3jn_engine)
    assert len(results) >= 1
    for candidate in results:
        assert candidate.tokens[0].book == "25"
        assert candidate.reference.startswith("3Jn ")


def test_gap_constraint_respected(loaded_3jn_engine: Engine) -> None:
    """Gap constraints filter out matches outside the [min, max] window.

    In 3Jn 1:1, ``Γάϊος`` is at position 3 and ``ἀγαπητός`` is at position 5
    (1 token between). A plan with ``gap.max=1`` should match (1 between
    is within the window). A plan with ``gap.max=0`` should NOT match
    (0 tokens between would require adjacency).
    """
    # gap.max=1 → up to 1 between → matches (1 between).
    plan_match = _make_lemma_sequence(
        ["Γάϊος", "ἀγαπητός"],
        gap=GapConstraint(min=0, max=1),
    )
    results_match = execute(plan_match, plan_match.scope, loaded_3jn_engine)
    assert len(results_match) == 1, (
        f"gap.max=1 should match 1-between but got {len(results_match)} results"
    )

    # gap.max=0 → 0 between → no match (Γάϊος and ἀγαπητός are 1 apart).
    plan_no_match = _make_lemma_sequence(
        ["Γάϊος", "ἀγαπητός"],
        gap=GapConstraint(min=0, max=0),
    )
    results_no_match = execute(
        plan_no_match, plan_no_match.scope, loaded_3jn_engine
    )
    assert results_no_match == []


# ---------------------------------------------------------------------------
# Slice-level exit-gate test (full corpus + seeded registry)
# ---------------------------------------------------------------------------


def test_full_corpus_faith_hope_love_in_1cor_13_13(
    loaded_full_corpus_with_registry: tuple[Engine, ConceptRegistry],
) -> None:
    """Slice-C exit gate: ``faith > hope > love`` resolves to 1Cor 13:13.

    Parses the canonical-07 example 1 DSL, validates it with rule 13
    enabled, then executes against the full 27-book corpus + seeded
    registry. Asserts at least one candidate references 1Cor 13:13.
    """
    engine, registry = loaded_full_corpus_with_registry

    plan = parse("faith > hope > love")

    capability_registry = CapabilityRegistry.mvp()
    validation = validate(
        plan, capability_registry, concept_registry=registry
    )
    assert validation.executable_plan is not None, (
        f"validator did not produce an executable plan: "
        f"findings={validation.findings!r}"
    )

    results = execute(
        validation.executable_plan,
        validation.executable_plan.scope,
        engine,
        concept_registry=registry,
    )
    references = {c.reference for c in results}
    assert "1Cor 13:13" in references, (
        f"expected 1Cor 13:13 in candidate references, got {sorted(references)!r}"
    )
    one_cor_candidates = [c for c in results if c.reference == "1Cor 13:13"]
    for candidate in one_cor_candidates:
        assert candidate.match_type == "conceptual"
        assert len(candidate.tokens) == 3
        assert len(candidate.alignment) == 3
