"""Integration tests for ``src/retrieval/contextualization.py``.

Exercises ``compute_node_baselines`` end-to-end against a live Postgres
with the full NT corpus + seeded registry (mirrors the fixture pattern in
``test_executor.py``). Asserts the structural invariants from canonical-09
§8: counts are non-negative; concept-node counts equal the sum of the
underlying resolved-lemma counts; scope filters carry into the count.
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
    NodeRef,
    NodeType,
    OperatorType,
    OrderOperator,
    QueryPlan,
    ScopeConstraint,
    SequenceExpr,
)
from src.ingestion.db import get_engine
from src.ontology.registry import ConceptRegistry
from src.retrieval.contextualization import (
    compute_alternative_orderings,
    compute_node_baselines,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_SCRIPT = REPO_ROOT / "scripts" / "db" / "ingest_corpus.py"
SEED_SCRIPT = REPO_ROOT / "scripts" / "db" / "seed_registry.py"


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def loaded_full_corpus_with_registry() -> Iterator[tuple[Engine, ConceptRegistry]]:
    """Run ingest + seed scripts once for the module so baseline tests share state."""
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


def _make_plan(sequence: SequenceExpr, scope: ScopeConstraint | None = None) -> QueryPlan:
    return QueryPlan(
        version="0.1",
        source="<test>",
        sequence=sequence,
        scope=scope or ScopeConstraint(),
        mode="exact",
    )


def _count_lemma(engine: Engine, lemma: str) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT COUNT(*) FROM tokens WHERE lemma = :l"),
            {"l": lemma},
        ).scalar_one()


def test_lemma_baseline_matches_direct_count(
    loaded_full_corpus_with_registry: tuple[Engine, ConceptRegistry],
) -> None:
    """A LEMMA node baseline equals a direct COUNT(*) of that lemma."""
    engine, registry = loaded_full_corpus_with_registry
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )
    plan = _make_plan(seq)

    baselines = compute_node_baselines(plan, plan.scope, engine, registry=registry)

    expected = _count_lemma(engine, "πίστις")
    assert len(baselines) == 1
    assert baselines[0].count == expected
    assert baselines[0].count > 0  # πίστις occurs many times in the NT
    assert baselines[0].resolved_lemmas == ["πίστις"]


def test_concept_baseline_equals_sum_of_resolved_lemmas(
    loaded_full_corpus_with_registry: tuple[Engine, ConceptRegistry],
) -> None:
    """A CONCEPT node baseline = sum of COUNT(*) for each resolved lemma."""
    engine, registry = loaded_full_corpus_with_registry
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.CONCEPT, value="faith")],
        operators=[],
    )
    plan = _make_plan(seq)

    baselines = compute_node_baselines(plan, plan.scope, engine, registry=registry)

    nb = baselines[0]
    expected_per_lemma = [_count_lemma(engine, lem) for lem in nb.resolved_lemmas]
    assert nb.count == sum(expected_per_lemma)
    assert nb.count > 0
    assert nb.resolved_lemmas  # registry must have at least one lemma for "faith"


def test_three_concept_baselines_for_faith_hope_love(
    loaded_full_corpus_with_registry: tuple[Engine, ConceptRegistry],
) -> None:
    """The slice's flagship sequence: faith > hope > love → three NodeBaselines.

    Asserts: structural shape (one baseline per step, in original order),
    each count is the sum of its resolved lemmas, all counts > 0 in the NT.
    """
    engine, registry = loaded_full_corpus_with_registry
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.CONCEPT, value="faith"),
            NodeRef(type=NodeType.CONCEPT, value="hope"),
            NodeRef(type=NodeType.CONCEPT, value="love"),
        ],
        operators=[
            OrderOperator(type=OperatorType.PRECEDENCE),
            OrderOperator(type=OperatorType.PRECEDENCE),
        ],
    )
    plan = _make_plan(seq)

    baselines = compute_node_baselines(plan, plan.scope, engine, registry=registry)

    assert [nb.node_value for nb in baselines] == ["faith", "hope", "love"]
    assert [nb.node_index for nb in baselines] == [0, 1, 2]
    for nb in baselines:
        per_lemma = [_count_lemma(engine, lem) for lem in nb.resolved_lemmas]
        assert nb.count == sum(per_lemma)
        assert nb.count > 0


def test_book_scope_filter_reduces_count(
    loaded_full_corpus_with_registry: tuple[Engine, ConceptRegistry],
) -> None:
    """Scoping to a single book yields a count <= the unscoped count."""
    engine, registry = loaded_full_corpus_with_registry
    seq = SequenceExpr(
        steps=[NodeRef(type=NodeType.LEMMA, value="πίστις")],
        operators=[],
    )

    unscoped = compute_node_baselines(_make_plan(seq), ScopeConstraint(), engine)[0]
    scoped = compute_node_baselines(
        _make_plan(seq, ScopeConstraint(books=["3jn"])),
        ScopeConstraint(books=["3jn"]),
        engine,
    )[0]

    assert scoped.count <= unscoped.count


# ---------------------------------------------------------------------------
# Alternative-ordering counts against the seeded corpus
# ---------------------------------------------------------------------------


def test_faith_hope_love_alternative_orderings(
    loaded_full_corpus_with_registry: tuple[Engine, ConceptRegistry],
) -> None:
    """3-concept sequence yields 6 orderings; observed ordering matches execute()."""
    engine, registry = loaded_full_corpus_with_registry
    seq = SequenceExpr(
        steps=[
            NodeRef(type=NodeType.CONCEPT, value="faith"),
            NodeRef(type=NodeType.CONCEPT, value="hope"),
            NodeRef(type=NodeType.CONCEPT, value="love"),
        ],
        operators=[
            OrderOperator(type=OperatorType.PRECEDENCE),
            OrderOperator(type=OperatorType.PRECEDENCE),
        ],
    )
    plan = _make_plan(seq)

    orderings, capped = compute_alternative_orderings(
        plan, plan.scope, engine, registry=registry
    )

    assert capped is False
    assert len(orderings) == 6  # 3! permutations

    # Identity ordering is in the list and marked observed
    identity = [o for o in orderings if o.permutation == [0, 1, 2]]
    assert len(identity) == 1
    assert identity[0].is_observed is True
    assert identity[0].sequence_label == "faith > hope > love"

    # Identity count must equal what execute() returns directly for the same plan
    expected_observed = len(execute(plan, plan.scope, engine, concept_registry=registry))
    assert identity[0].count == expected_observed

    # All counts are non-negative integers
    for o in orderings:
        assert o.count >= 0

    # Exactly one ordering is the observed one; the other 5 are alternatives
    assert sum(1 for o in orderings if o.is_observed) == 1
    assert sum(1 for o in orderings if not o.is_observed) == 5
