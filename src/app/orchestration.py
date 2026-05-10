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

from src.app.schemas import QueryDSLResponse, QueryNLResponse, TranslationMetadata
from src.engine.parser import parse
from src.nlp.explainer import explain
from src.nlp.llm_client import LLMClient
from src.nlp.translator import TranslationContext, translate
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


def run_nl_query(
    nl_query: str,
    engine: Engine,
    registry: ConceptRegistry,
    llm_client: LLMClient,
    context: TranslationContext,
) -> QueryNLResponse:
    """Compile NL→DSL and then run the full DSL pipeline.

    Composes `translate()` (REQ:09.nl-to-dsl, canonical-09 §2) with
    `run_dsl_query()`. Translator-side exceptions propagate unchanged:

    - `LLMUnavailable` from the LLM client → route maps to 503 (DEC-070).
    - `NLCompileError` from the translator → route maps to 422
      `nl_compile_error` (DEC-070).

    Downstream pipeline exceptions (`ParseError`,
    `ValidationUnsupported`, `UnsupportedPlanShape`, `ConceptNotMapped`,
    `RegistryRequired`) propagate from `run_dsl_query()` unchanged.

    Returns a `QueryNLResponse` whose `query` field is the *compiled*
    DSL string (not the original NL — the original lives in the
    request body).
    """
    translation_result = translate(nl_query, context, llm_client)

    dsl_response = run_dsl_query(
        dsl=translation_result.dsl,
        engine=engine,
        registry=registry,
    )

    return QueryNLResponse(
        query=dsl_response.query,
        validation=dsl_response.validation,
        result=dsl_response.result,
        explanation=dsl_response.explanation,
        translation=TranslationMetadata(
            confidence=translation_result.confidence,
            alternatives=translation_result.alternatives,
            explanation=translation_result.explanation,
        ),
    )
