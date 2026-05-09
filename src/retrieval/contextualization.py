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

from typing import TYPE_CHECKING

from sqlalchemy import Engine, func, select

from src.engine._schema import tokens_table
from src.engine.executor import (
    build_scope_where,
    resolve_step_lemmas,
    validate_plan_shape,
)
from src.engine.models import (
    NodeBaseline,
    NodeRef,
    QueryPlan,
    ScopeConstraint,
)

if TYPE_CHECKING:
    from src.ontology.registry import ConceptRegistry


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
