"""Pipeline orchestration for the FastAPI route layer.

`run_dsl_query()` is the service-layer counterpart to
`scripts/query.py::main`: it runs the same compile → validate →
retrieve → explain pipeline but returns a `QueryDSLResponse` instead
of writing to stdout/stderr and returning an exit code.

Pipeline exceptions (`ParseError`, `UnsupportedPlanShape`,
`ConceptNotMapped`, `RegistryRequired`) propagate unchanged; the
route handler maps them to HTTP status codes per
docs/canonical/09_backend-service-boundaries.md §1. Validator
status="unsupported" raises `ValidationUnsupported` so the same
catch-and-map pattern applies uniformly.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

from src.app.schemas import QueryDSLResponse
from src.engine.parser import parse
from src.nlp.explainer import explain
from src.ontology.registry import ConceptRegistry
from src.retrieval.retrieve import retrieve
from src.validation.registry import CapabilityRegistry
from src.validation.validator import ValidationResult, validate


class ValidationUnsupported(Exception):  # noqa: N818
    """Raised when validate() returns status='unsupported'.

    Carries the full `ValidationResult` so the HTTP layer can include
    the structured findings list in its 422 error response.
    """

    def __init__(self, validation: ValidationResult) -> None:
        self.validation = validation
        super().__init__(
            f"validator rejected plan: status={validation.status}"
        )


def run_dsl_query(
    dsl: str,
    engine: Engine,
    registry: ConceptRegistry,
) -> QueryDSLResponse:
    """Run the full DSL pipeline and return a response envelope.

    Steps mirror canonical-09 request-lifecycle 4–11 (the route layer
    handles step 1–2; step 3 is skipped on the /dsl path):

    1. `parse(dsl)` → `QueryPlan`. Raises `ParseError` on syntax error.
    2. `validate(plan, mvp, registry)` → `ValidationResult`.
       - status="unsupported" → raises `ValidationUnsupported`.
       - status="partial" or "supported" → proceeds with the
         validator's executable plan.
    3. `retrieve(executable, scope, engine, contextualize=True, registry=registry)`
       → `RetrievalResult` (with contextualization). Raises
       `UnsupportedPlanShape`, `ConceptNotMapped`, or
       `RegistryRequired` on the respective failure modes.
    4. `explain(result, executable, validation)` → `ExplainedResultSet`.

    Returns a `QueryDSLResponse` carrying all four artifacts.
    """
    plan = parse(dsl)

    validation = validate(
        plan,
        CapabilityRegistry.mvp(),
        concept_registry=registry,
    )

    if validation.status == "unsupported" or validation.executable_plan is None:
        raise ValidationUnsupported(validation)

    executable = validation.executable_plan

    result = retrieve(
        executable,
        executable.scope,
        engine,
        contextualize=True,
        registry=registry,
    )

    explained = explain(result, executable, validation)

    return QueryDSLResponse(
        query=dsl,
        validation=validation,
        result=result,
        explanation=explained,
    )
