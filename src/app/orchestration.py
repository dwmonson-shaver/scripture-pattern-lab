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

from src.app.schemas import (
    AutoCreatedConceptNote,
    ClarificationPayload,
    ConversationTurn,
    QueryDSLResponse,
    QueryNLResponse,
    TranslationMetadata,
)
from src.engine.models import ConceptNotMapped
from src.engine.parser import parse
from src.nlp.explainer import explain
from src.nlp.llm_client import LLMClient, Message
from src.nlp.translator import (
    TranslationContext,
    TranslationNeedsClarification,
    TranslationSuccess,
    translate,
)
from src.ontology.concept_document import (
    ConceptDocument,
    build_comparative_section,
    build_short_summary,
    get_document,
    persist_document,
)
from src.ontology.concept_writer import auto_create_cited_concept
from src.ontology.lexicon_resolver import resolve_english_term
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


def _attempt_auto_create_concept(
    concept_name: str,
    engine: Engine,
) -> AutoCreatedConceptNote | None:
    """Deterministically auto-create a Tier-1 concept for an unmapped term.

    Slice N (DEC-102/DEC-104): resolve the English term against the self-hosted
    lexicon (NO LLM), and if it maps to corpus-present lemmas, write a
    machine/lexicon-sourced unverified concept + persist its comparative
    Conceptual Document (Part 1 §1) + short summary, then return the inline
    note. Returns None if the term does not resolve to any corpus-present lemma
    (the caller then surfaces the honest dead-end — re-raises ConceptNotMapped).

    NO LLM on this path — the concept and the comparative document section are
    100% deterministic. The optional LLM educational section (Part 1 §2) is a
    separate opt-in step layered on top later; it never gates auto-creation.
    """
    resolution = resolve_english_term(concept_name, engine)
    if resolution.unresolved:
        return None

    outcome = auto_create_cited_concept(resolution, engine)

    # Persist (store-once) the deterministic comparative document + summary so
    # it is retrievable later and never regenerated per query.
    if get_document(outcome.concept_name, engine) is None:
        comparative = build_comparative_section(resolution, engine)
        document = ConceptDocument(
            concept_name=outcome.concept_name,
            short_summary=build_short_summary(resolution),
            part1_comparative=comparative,
        )
        persist_document(document, engine)

    return AutoCreatedConceptNote(
        concept_name=outcome.concept_name,
        lemmas=[rl.lemma for rl in resolution.resolved_lemmas],
        summary=build_short_summary(resolution),
        document_available=True,
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

    Slice N (DEC-104): if step 3 raises `ConceptNotMapped` for a term that
    resolves against the self-hosted lexicon, the unmapped concept is
    auto-created (deterministically) and the pipeline is re-run ONCE; the
    response carries an `auto_created_concept` note. A term that does not
    resolve to corpus-present lemmas re-raises `ConceptNotMapped` so the route
    returns the honest 422 ("the system says when it cannot do something yet").

    Returns a `QueryDSLResponse` carrying all four artifacts.
    """
    return _run_dsl_pipeline_with_optional_explainer_llm(
        dsl=dsl,
        engine=engine,
        registry=registry,
        explainer_llm=None,
    )


def run_nl_query(
    nl_query: str,
    engine: Engine,
    registry: ConceptRegistry,
    llm_client: LLMClient,
    context: TranslationContext,
    prior_turns: list[ConversationTurn] | None = None,
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

    Slice M (DEC-098): ``prior_turns`` carries a caller-assembled refinement
    conversation as app-schema :class:`ConversationTurn` objects. This is the
    clean app→nlp boundary crossing: the app-schema turns are converted to
    nlp-layer :class:`Message` dicts (``{"role": t.role, "content":
    t.content}``) HERE before being threaded into ``translate()`` — src/nlp
    never imports from src/app. When ``prior_turns`` is None/empty the
    single-shot path is byte-identical to today (``translate()`` receives
    ``None``). When non-empty, ``translate()`` assembles the multi-message
    array internally. All downstream branching (clarification vs success →
    parse/validate/retrieve/explain) is unchanged; a resubmitted answered
    clarification that now yields a :class:`TranslationSuccess` flows the full
    pipeline and returns a normal executed ``QueryNLResponse``.
    """
    # A client could forge an assistant turn (e.g. claim the translator said
    # "window 50"). Accepted by design (M-CLOSE-006): each request is stateless,
    # the translator re-derives DSL from the cookbook + corpus, and the corpus
    # is ground truth (DEC-024) — a forged turn at worst yields a DSL the caller
    # can inspect; there is no persistent state to corrupt.
    converted_turns: list[Message] | None = (
        [{"role": t.role, "content": t.content} for t in prior_turns]
        if prior_turns
        else None
    )

    translation_result = translate(
        nl_query, context, llm_client, prior_turns=converted_turns
    )

    # Slice L Decision #6: clarification short-circuits the pipeline. The
    # route returns a 200 carrying the question + suggested windows; no
    # query executes. Frontend handling is follow-up scope.
    if isinstance(translation_result, TranslationNeedsClarification):
        return QueryNLResponse(
            query=nl_query,
            clarification=ClarificationPayload(
                question=translation_result.question,
                suggested_windows=translation_result.suggested_windows,
                nl_source=translation_result.nl_source,
            ),
        )

    assert isinstance(translation_result, TranslationSuccess)

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
        auto_created_concept=dsl_response.auto_created_concept,
    )


def _run_dsl_pipeline_with_optional_explainer_llm(
    *,
    dsl: str,
    engine: Engine,
    registry: ConceptRegistry,
    explainer_llm: LLMClient | None,
) -> QueryDSLResponse:
    """Internal: the DSL pipeline with the explainer_llm thread + auto-create.

    Kept separate from the public run_dsl_query() docstring contract so the
    explainer-LLM thread (Slice K) and the Tier-1 auto-create-and-retry loop
    (Slice N) live in one place that both the /dsl and /nl paths funnel through.
    The /api/v1/query/dsl path passes explainer_llm=None so that surface stays
    explicitly LLM-free for the explanation; auto-creation itself is always
    LLM-free regardless of this flag.

    On a `ConceptNotMapped` from retrieve, attempt a deterministic auto-create
    of the unmapped term and retry the pipeline ONCE (bounded — a single retry,
    no loop). If the term does not resolve, or a *different* concept is still
    unmapped after the retry, the exception propagates so the route returns the
    honest 422.
    """
    note: AutoCreatedConceptNote | None = None
    attempts = 0
    while True:
        plan = parse(dsl)
        validation = validate(
            plan,
            CapabilityRegistry.mvp(),
            concept_registry=registry,
        )
        if validation.status == "unsupported" or validation.executable_plan is None:
            raise ValidationUnsupported(validation)
        executable = validation.executable_plan
        try:
            result = retrieve(
                executable,
                executable.scope,
                engine,
                contextualize=True,
                registry=registry,
            )
        except ConceptNotMapped as exc:
            # Bounded single retry: only attempt auto-create on the first miss.
            if attempts >= 1:
                raise
            attempts += 1
            created = _attempt_auto_create_concept(exc.concept_name, engine)
            if created is None:
                # Unresolvable term — honest dead-end (route → 422).
                raise
            note = created
            continue  # re-run the pipeline now that the concept exists

        explained = explain(result, executable, validation, llm_client=explainer_llm)
        return QueryDSLResponse(
            query=dsl,
            validation=validation,
            result=result,
            explanation=explained,
            auto_created_concept=note,
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
