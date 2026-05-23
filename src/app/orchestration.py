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

import logging
import os

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

logger = logging.getLogger(__name__)

# Slice K — explainer LLM opt-in.
# The env var is read at call time (not lifespan-scoped). The truthy set
# matches src/app/main.py:137-142's empty-string-as-disabled convention.
_EXPLAINER_LLM_ENV_VAR = "SPL_EXPLAINER_LLM"
_EXPLAINER_LLM_TRUTHY = {"1", "true"}
_EXPLAINER_LLM_FALSY = {"", "0", "false"}


def _explainer_llm_opted_in() -> bool:
    """Return True iff ``SPL_EXPLAINER_LLM`` is set to a recognized truthy value.

    Unset, empty, "0", "false" (case-insensitive) → False (default).
    "1", "true" (case-insensitive) → True.
    Any other value → False + WARNING log (avoid silent misconfigure).
    """
    raw = os.environ.get(_EXPLAINER_LLM_ENV_VAR, "")
    normalized = raw.strip().lower()
    if normalized in _EXPLAINER_LLM_TRUTHY:
        return True
    if normalized in _EXPLAINER_LLM_FALSY:
        return False
    logger.warning(
        "%s=%r is not a recognized boolean value; treating as disabled. "
        "Set to '1' or 'true' to opt in.",
        _EXPLAINER_LLM_ENV_VAR,
        raw,
    )
    return False


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

    # Slice K: if SPL_EXPLAINER_LLM is opted in, the same LLM client used by
    # the translator is also passed into explain() so conceptual-match
    # explanations are LLM-paraphrased. Deterministic baseline remains the
    # fallback inside explain() — env var unset is the default and behavior
    # is unchanged from Slice H/I.
    explainer_llm = llm_client if _explainer_llm_opted_in() else None

    dsl_response = _run_dsl_pipeline_with_optional_explainer_llm(
        dsl=translation_result.dsl,
        engine=engine,
        registry=registry,
        explainer_llm=explainer_llm,
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


def _run_dsl_pipeline_with_optional_explainer_llm(
    *,
    dsl: str,
    engine: Engine,
    registry: ConceptRegistry,
    explainer_llm: LLMClient | None,
) -> QueryDSLResponse:
    """Internal: identical to run_dsl_query but threads explainer_llm.

    Kept separate from run_dsl_query() so that the public /api/v1/query/dsl
    path remains explicitly LLM-free (no env-var read, no LLM dependency at
    the DSL surface — that path is for callers who already have a DSL
    string and have not opted into LLM augmentation).
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
    explained = explain(result, executable, validation, llm_client=explainer_llm)
    return QueryDSLResponse(
        query=dsl,
        validation=validation,
        result=result,
        explanation=explained,
    )


def run_validate_only(dsl: str, registry: ConceptRegistry) -> ValidationResult:
    """Run parse + validate, no retrieve, no explain.

    The HTTP companion to `POST /api/v1/query/validate`. Returns a
    `ValidationResult` carrying the verdict (supported / partial /
    unsupported) and any findings. Raises `ParseError` if the DSL is
    syntactically malformed; never raises `ValidationUnsupported`
    (DEC-079: validate's contract is "always return the verdict" —
    `unsupported` is information, not an error).
    """
    plan = parse(dsl)
    return validate(
        plan,
        CapabilityRegistry.mvp(),
        concept_registry=registry,
    )
