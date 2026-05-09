"""Result-set contextualization — calibrate match counts against alternatives.

Per ``docs/canonical/09_backend-service-boundaries.md`` §8 and the design at
``thoughts/design-result-contextualization-2026-05-03.md`` (status:
design-stable, OQ-resolutions block at the bottom of the design doc):

- baselines: per-node ``COUNT(*)`` against the scoped corpus (this module)
- alternative orderings: re-run the executor on permutations (D4)
- null distribution: schema slot only in MVP (always ``None``; OQ #3)

The ``contextualize()`` orchestrator (D5) composes the three into a single
:class:`Contextualization` envelope hung on :class:`RetrievalResult`.
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from sqlalchemy import Engine, func, select

from src.engine._schema import tokens_table
from src.engine.executor import (
    build_scope_where,
    execute,
    resolve_step_lemmas,
    validate_plan_shape,
)
from src.engine.models import (
    AlternativeOrderingCount,
    NodeBaseline,
    NodeRef,
    QueryPlan,
    ScopeConstraint,
    SequenceExpr,
)

if TYPE_CHECKING:
    from src.ontology.registry import ConceptRegistry


# Cap on enumerated permutations per design decision 5: 4! = 24 fits; N >= 5
# uses the deterministic fallback subset (identity + reverse + adjacent
# pairwise swaps) so the engine re-entry count stays small. Recorded on the
# Contextualization envelope as ``alternative_orderings_capped``.
_FULL_ENUMERATION_THRESHOLD = 4


def compute_node_baselines(
    plan: QueryPlan,
    scope: ScopeConstraint,
    engine: Engine,
    registry: "ConceptRegistry | None" = None,
) -> list[NodeBaseline]:
    """Return one :class:`NodeBaseline` per step in the plan's sequence.

    For each constituent node, issues a scoped ``SELECT COUNT(*)`` against
    the ``tokens`` table for the node's resolved lemma set. Lemma nodes
    resolve to themselves; concept nodes resolve via
    :meth:`ConceptRegistry.get_lemmas_for_concept` per
    ``REQ:04.matching-rules``. Every count receives the same scope WHERE
    clauses (``corpus_id``, ``language``, ``books``) the executor uses, so
    a baseline is directly comparable to the observed count from
    :func:`execute`.

    Plan-shape contract is identical to :func:`execute`: ``InverseExpr``,
    ``negated`` steps, ``morph_filters``, non-precedence operators, and
    non-LEMMA/CONCEPT node types are rejected via
    :class:`UnsupportedPlanShape`. Concept nodes raise
    :class:`RegistryRequired` (registry handle is None) or
    :class:`ConceptNotMapped` (concept absent / not seeded) — same
    semantics as the executor so the CLI's exit-code taxonomy stays
    consistent across the pipeline.
    """
    sequence = validate_plan_shape(plan, scope)

    # The validated MVP shape guarantees every step is a NodeRef.
    steps: list[NodeRef] = list(sequence.steps)  # type: ignore[arg-type]

    language = scope.language or "grc"
    base_where = build_scope_where(scope)

    baselines: list[NodeBaseline] = []
    with engine.connect() as connection:
        for index, step in enumerate(steps):
            lemmas = resolve_step_lemmas(step, language, registry)
            stmt = select(func.count()).select_from(tokens_table).where(
                tokens_table.c.lemma.in_(lemmas)
            )
            for clause in base_where:
                stmt = stmt.where(clause)
            count = connection.execute(stmt).scalar_one()
            baselines.append(
                NodeBaseline(
                    node_index=index,
                    node_type=step.type,
                    node_value=step.value,
                    resolved_lemmas=lemmas,
                    count=count,
                )
            )
    return baselines


def compute_alternative_orderings(
    plan: QueryPlan,
    scope: ScopeConstraint,
    engine: Engine,
    registry: "ConceptRegistry | None" = None,
) -> tuple[list[AlternativeOrderingCount], bool]:
    """Return (counts, capped) for permutations of the plan's node sequence.

    For sequences of length ``N <= 4`` enumerates all ``N!`` permutations
    (capped=False). For ``N >= 5`` uses the design's deterministic fallback
    subset — identity + reverse + ``N-1`` adjacent pairwise swaps — so the
    engine re-entry count stays bounded (capped=True). Each permutation
    re-runs :func:`execute` with a new ``SequenceExpr`` whose steps are
    reordered per the permutation; operators and gap constraints are kept
    in their original positions per the design's "Risks" note (length is
    preserved, but ordering-specific gap windows propagate as-is — a
    documented MVP limitation).

    The original ordering is included in the returned list with
    ``is_observed=True`` so callers can render it alongside its siblings
    without comparing permutations themselves.
    """
    sequence = validate_plan_shape(plan, scope)
    steps: list[NodeRef] = list(sequence.steps)  # type: ignore[arg-type]
    n = len(steps)

    if n <= _FULL_ENUMERATION_THRESHOLD:
        permutations = [list(p) for p in itertools.permutations(range(n))]
        capped = False
    else:
        permutations = _fallback_permutations(n)
        capped = True

    identity = list(range(n))
    counts: list[AlternativeOrderingCount] = []
    for permutation in permutations:
        permuted_seq = SequenceExpr(
            steps=[steps[i] for i in permutation],
            operators=sequence.operators,
        )
        permuted_plan = plan.model_copy(update={"sequence": permuted_seq})
        candidates = execute(
            permuted_plan, scope, engine, concept_registry=registry
        )
        counts.append(
            AlternativeOrderingCount(
                permutation=permutation,
                sequence_label=_format_sequence_label(permuted_seq.steps),  # type: ignore[arg-type]
                count=len(candidates),
                is_observed=permutation == identity,
            )
        )
    return counts, capped


# ---------------------------------------------------------------------------
# Permutation helpers (private)
# ---------------------------------------------------------------------------


def _fallback_permutations(n: int) -> list[list[int]]:
    """Deterministic fallback subset for sequences of length ``N >= 5``.

    Returns ``identity + reverse + (N-1) adjacent pairwise swaps``.  All
    distinct (identity ≠ reverse for N >= 2; adjacent swaps are pairwise
    distinct from each other and from identity / reverse for N >= 3).
    Total = ``N + 1`` permutations.
    """
    identity = list(range(n))
    reverse = list(reversed(identity))
    permutations: list[list[int]] = [identity, reverse]
    for i in range(n - 1):
        swapped = identity.copy()
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        permutations.append(swapped)
    return permutations


def _format_sequence_label(steps: list[NodeRef]) -> str:
    """Render a node sequence as ``faith > hope > love`` for display."""
    return " > ".join(step.value for step in steps)
