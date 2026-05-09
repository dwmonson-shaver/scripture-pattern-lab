"""Retrieval pipeline orchestrator (REQ:09.retrieval-pipeline).

Per ``docs/canonical/09_backend-service-boundaries.md`` §6: a thin wrapper
around the pattern engine in MVP. Wraps :func:`execute` and optionally
attaches a :class:`Contextualization` envelope. The interface exists so
that semantic retrieval can be added later as additional stages without
changing the caller-facing API.

OQ #1 resolution (middle path) sets the engine-layer default for the
``contextualize`` flag to ``False``: tests and batch callers want
deterministic, cost-bounded behavior, while UI-layer consumers (CLI, API)
pass ``contextualize=True`` so users see calibrated counts by default —
the anti-confirmation-bias choice [DEC-024].
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Engine

from src.engine.executor import execute
from src.engine.models import QueryPlan, RetrievalResult, ScopeConstraint
from src.retrieval.contextualization import contextualize as _build_contextualization

if TYPE_CHECKING:
    from src.ontology.registry import ConceptRegistry


def retrieve(
    plan: QueryPlan,
    scope: ScopeConstraint,
    engine: Engine,
    *,
    contextualize: bool = False,
    registry: "ConceptRegistry | None" = None,
) -> RetrievalResult:
    """Execute ``plan`` against the corpus and (optionally) calibrate the result.

    Returns a :class:`RetrievalResult` with the candidate list and
    ``stages_used``. When ``contextualize=True``, also computes the
    per-node baselines + alternative-ordering counts and attaches them
    via :class:`Contextualization` (null-distribution is reserved as
    ``None`` in MVP).

    Exceptions from the pattern engine (``UnsupportedPlanShape``,
    ``RegistryRequired``, ``ConceptNotMapped``) propagate unchanged so
    the CLI exit-code taxonomy remains consistent across the pipeline.
    """
    candidates = execute(plan, scope, engine, concept_registry=registry)
    contextualization = None
    if contextualize:
        contextualization = _build_contextualization(
            plan, scope, candidates, engine, registry=registry
        )
    return RetrievalResult(
        candidates=candidates,
        stages_used=["symbolic"],
        contextualization=contextualization,
    )
