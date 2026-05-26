"""Capability validator — checks QueryPlans against engine capabilities.

Deterministic component (no AI). Implements 12 sequential validation rules
from docs/canonical/06_capability-validator.md plus a 13th additive
"registry grounding" rule (REQ:08.registry-epistemics) that labels a
QueryPlan as ``evidence-grounded`` / ``prior-grounded`` / ``mixed`` based
on the verification state of any concept-registry rows it touches.

Interface per docs/canonical/09_backend-service-boundaries.md:
    def validate(
        plan: QueryPlan,
        capability_registry: CapabilityRegistry,
        concept_registry: ConceptRegistry | None = None,
    ) -> ValidationResult
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.engine.models import (
    AlternativeExpr,
    GroupExpr,
    InverseExpr,
    NodeRef,
    NodeType,
    OperatorType,
    OptionalExpr,
    OrderOperator,
    QueryPlan,
    ScopeUnitWindow,
    SequenceExpr,
)
from src.ontology.registry import ConceptRegistry
from src.validation.registry import CapabilityRegistry

# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


class ValidationFinding(BaseModel):
    """One specific capability gap or concern."""

    model_config = ConfigDict(frozen=True)

    severity: Literal["error", "warning", "info"]
    code: str
    path: str
    message: str
    remediation: str | None = None


class ValidationResult(BaseModel):
    """Result of validating a QueryPlan against the capability registry.

    The optional ``grounding`` axis (REQ:08.registry-epistemics, decision #6)
    is orthogonal to ``status`` and ``match_mode``: it answers "is the
    resolution backed by corpus evidence" for any concept-registry-backed
    nodes in the plan. ``None`` means rule 13 was not run (no
    ``concept_registry`` was passed) or no concept nodes were inspected.
    """

    model_config = ConfigDict(frozen=True)

    status: Literal["supported", "partial", "unsupported"]
    executable_plan: QueryPlan | None
    findings: list[ValidationFinding]
    engine_version: str
    grounding: Literal["evidence-grounded", "prior-grounded", "mixed"] | None = None


# ---------------------------------------------------------------------------
# AST walkers
# ---------------------------------------------------------------------------


def _collect_node_refs(
    sequence: SequenceExpr | InverseExpr,
) -> list[tuple[str, NodeRef]]:
    """Collect all NodeRefs with their JSONPath from a sequence."""
    if isinstance(sequence, InverseExpr):
        return _collect_node_refs_from_seq(sequence.inner, "sequence.inner")
    return _collect_node_refs_from_seq(sequence, "sequence")


def _collect_node_refs_from_seq(
    seq: SequenceExpr, prefix: str
) -> list[tuple[str, NodeRef]]:
    refs: list[tuple[str, NodeRef]] = []
    for i, step in enumerate(seq.steps):
        path = f"{prefix}.steps[{i}]"
        refs.extend(_collect_from_step(step, path))
    return refs


def _collect_from_step(
    step: NodeRef | GroupExpr | AlternativeExpr | OptionalExpr, path: str
) -> list[tuple[str, NodeRef]]:
    if isinstance(step, NodeRef):
        return [(path, step)]
    if isinstance(step, GroupExpr):
        return _collect_node_refs_from_seq(step.sequence, f"{path}.sequence")
    if isinstance(step, AlternativeExpr):
        refs: list[tuple[str, NodeRef]] = []
        for j, opt in enumerate(step.options):
            refs.extend(_collect_from_step(opt, f"{path}.options[{j}]"))
        return refs
    if isinstance(step, OptionalExpr):
        return _collect_from_step(step.inner, f"{path}.inner")
    return []


def _collect_operators(
    sequence: SequenceExpr | InverseExpr,
) -> list[tuple[str, OrderOperator]]:
    """Collect all OrderOperators with their JSONPath."""
    if isinstance(sequence, InverseExpr):
        seq = sequence.inner
        prefix = "sequence.inner"
    else:
        seq = sequence
        prefix = "sequence"
    return [
        (f"{prefix}.operators[{i}]", op) for i, op in enumerate(seq.operators)
    ]


def _count_steps(sequence: SequenceExpr | InverseExpr) -> int:
    """Count top-level steps in the sequence."""
    if isinstance(sequence, InverseExpr):
        return len(sequence.inner.steps)
    return len(sequence.steps)


# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------


def _rule_1_version(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check version compatibility."""
    if plan.version != registry.version:
        return [
            ValidationFinding(
                severity="error",
                code="INCOMPATIBLE_VERSION",
                path="version",
                message=(
                    f"Query version '{plan.version}' is not compatible "
                    f"with engine version '{registry.version}'."
                ),
            )
        ]
    return []


def _rule_2_node_types(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check that all node types are supported."""
    findings = []
    for path, node in _collect_node_refs(plan.sequence):
        if node.type.value not in registry.node_types:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="UNSUPPORTED_NODE_TYPE",
                    path=path,
                    message=(
                        f"Node type '{node.type.value}' is not supported "
                        f"in engine v{registry.version}."
                    ),
                    remediation="Use lemma: or concept: nodes instead.",
                )
            )
    return findings


def _rule_3_operators(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check that all operators are supported."""
    findings = []
    for path, op in _collect_operators(plan.sequence):
        if op.type.value not in registry.operators:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="UNSUPPORTED_OPERATOR",
                    path=path,
                    message=(
                        f"Operator '{op.type.value}' is not supported "
                        f"in engine v{registry.version}."
                    ),
                )
            )
    return findings


def _rule_4_gap_constraints(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check gap constraints are supported and within limits."""
    findings = []
    for path, op in _collect_operators(plan.sequence):
        if op.gap is not None:
            if registry.max_gap is not None and op.gap.max is not None:
                if op.gap.max > registry.max_gap:
                    findings.append(
                        ValidationFinding(
                            severity="error",
                            code="GAP_EXCEEDS_MAX",
                            path=f"{path}.gap",
                            message=(
                                f"Gap max {op.gap.max} exceeds engine limit "
                                f"of {registry.max_gap}."
                            ),
                        )
                    )
    return findings


def _rule_5_polarity(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check polarity support."""
    if registry.polarity_support:
        return []
    findings = []
    for path, node in _collect_node_refs(plan.sequence):
        if node.polarity is not None:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="UNSUPPORTED_POLARITY",
                    path=path,
                    message="Polarity markers are not supported in this engine version.",
                )
            )
    return findings


def _rule_6_inverse(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check inverse support."""
    if isinstance(plan.sequence, InverseExpr) and not registry.inverse_support:
        return [
            ValidationFinding(
                severity="error",
                code="UNSUPPORTED_INVERSE",
                path="sequence",
                message=(
                    "inverse() queries are not supported in engine "
                    f"v{registry.version}. Inverse resolution is planned for v0.2."
                ),
                remediation=(
                    "Remove the inverse() wrapper and manually specify "
                    "negative-pole concepts, or use polarity markers "
                    "(-concept:faith) on individual nodes."
                ),
            )
        ]
    return []


def _rule_7_expansion(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check expansion support."""
    if plan.expansion is not None and not registry.expansion_support:
        return [
            ValidationFinding(
                severity="warning",
                code="UNSUPPORTED_EXPANSION",
                path="expansion",
                message=(
                    f"Expansion directives (=> {plan.expansion.direction.value}"
                    f":{plan.expansion.depth}) are not supported in engine "
                    f"v{registry.version}. The core sequence will be executed "
                    "without expansion."
                ),
            )
        ]
    return []


def _rule_8_compound_nodes(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check compound node support."""
    if registry.compound_node_support:
        return []
    findings = []
    for path, node in _collect_node_refs(plan.sequence):
        if node.morph_filters:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="UNSUPPORTED_COMPOUND_NODE",
                    path=path,
                    message=(
                        "Compound nodes (morph filters) are not supported "
                        f"in engine v{registry.version}."
                    ),
                )
            )
    return findings


def _rule_9_match_mode(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check match mode support."""
    if plan.mode not in registry.match_modes:
        return [
            ValidationFinding(
                severity="error",
                code="UNSUPPORTED_MATCH_MODE",
                path="mode",
                message=(
                    f"Match mode '{plan.mode}' is not supported. "
                    f"Available: {registry.match_modes}."
                ),
            )
        ]
    return []


def _rule_10_scope(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check scope validation.

    Slice L extends rule 10 with two new finding codes:
    - ``WINDOW_EXCEEDS_MAX`` (error): a ``ScopeUnitWindow.n`` value above
      ``registry.window_max_tokens`` (Decision #5).
    - ``GAP_NARROWED_BY_WINDOW`` (warning): a step-level ``gap.max`` larger
      than the outer window's ``n`` — the gap will be silently narrowed by
      the window envelope (Decision #10). Surfaced to the user so the
      narrowing is explicit, not surprising.
    """
    findings = []
    scope = plan.scope

    if scope.corpus is not None and scope.corpus not in registry.corpora:
        findings.append(
            ValidationFinding(
                severity="error",
                code="UNKNOWN_CORPUS",
                path="scope.corpus",
                message=(
                    f"Corpus '{scope.corpus}' is not available. "
                    f"Available: {registry.corpora}."
                ),
            )
        )

    if scope.language is not None and scope.language not in registry.languages:
        findings.append(
            ValidationFinding(
                severity="error",
                code="UNKNOWN_LANGUAGE",
                path="scope.language",
                message=(
                    f"Language '{scope.language}' is not available. "
                    f"Available: {registry.languages}."
                ),
            )
        )

    if isinstance(scope.unit, ScopeUnitWindow):
        if scope.unit.n > registry.window_max_tokens:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="WINDOW_EXCEEDS_MAX",
                    path="scope.unit.n",
                    message=(
                        f"Window size {scope.unit.n} exceeds the engine's "
                        f"window_max_tokens limit of {registry.window_max_tokens}."
                    ),
                )
            )
        # Gap-narrowed-by-window warning: every step-level gap.max that
        # exceeds the outer window's n will be silently narrowed by the
        # window envelope. Emit one warning per offending operator so the
        # path is precise.
        for op_path, op in _collect_operators(plan.sequence):
            if (
                op.gap is not None
                and op.gap.max is not None
                and op.gap.max > scope.unit.n
            ):
                findings.append(
                    ValidationFinding(
                        severity="warning",
                        code="GAP_NARROWED_BY_WINDOW",
                        path=f"{op_path}.gap",
                        message=(
                            f"Step-level gap max={op.gap.max} exceeds the "
                            f"outer window size n={scope.unit.n}; the gap "
                            "will be narrowed by the window."
                        ),
                    )
                )

    return findings


def _rule_11_sequence_length(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check sequence length."""
    count = _count_steps(plan.sequence)
    if count > registry.max_sequence_length:
        return [
            ValidationFinding(
                severity="error",
                code="SEQUENCE_TOO_LONG",
                path="sequence",
                message=(
                    f"Sequence has {count} steps, exceeding the maximum "
                    f"of {registry.max_sequence_length}."
                ),
            )
        ]
    return []


def _rule_12_structural(
    plan: QueryPlan, registry: CapabilityRegistry
) -> list[ValidationFinding]:
    """Check structural well-formedness."""
    findings = []
    seq = plan.sequence.inner if isinstance(plan.sequence, InverseExpr) else plan.sequence

    if len(seq.steps) == 0:
        findings.append(
            ValidationFinding(
                severity="error",
                code="EMPTY_SEQUENCE",
                path="sequence",
                message="Sequence has no steps.",
            )
        )
    elif len(seq.operators) != len(seq.steps) - 1:
        findings.append(
            ValidationFinding(
                severity="error",
                code="MALFORMED_AST",
                path="sequence",
                message=(
                    f"Operator count ({len(seq.operators)}) does not match "
                    f"step count ({len(seq.steps)}) - expected "
                    f"{len(seq.steps) - 1} operators."
                ),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Partial plan reduction
# ---------------------------------------------------------------------------


def _reduce_step(step, registry: CapabilityRegistry):
    """Reduce one step. Returns None if the step is fully unsupported.

    Recurses into composite steps (AlternativeExpr, GroupExpr, OptionalExpr) so
    unsupported NodeRefs nested inside them are dropped instead of surviving in
    the executable plan.
    """
    if isinstance(step, NodeRef):
        if step.type.value not in registry.node_types:
            return None
        return step
    if isinstance(step, AlternativeExpr):
        new_options = [
            reduced
            for opt in step.options
            if (reduced := _reduce_step(opt, registry)) is not None
        ]
        if not new_options:
            return None
        if len(new_options) == 1:
            return new_options[0]  # single survivor — collapse the alternative
        return step.model_copy(update={"options": new_options})
    if isinstance(step, GroupExpr):
        reduced_seq = _reduce_sequence(step.sequence, registry)
        if reduced_seq is None:
            return None
        return step.model_copy(update={"sequence": reduced_seq})
    if isinstance(step, OptionalExpr):
        reduced_inner = _reduce_step(step.inner, registry)
        if reduced_inner is None:
            return None
        return step.model_copy(update={"inner": reduced_inner})
    return step


def _reduce_sequence(sequence: SequenceExpr, registry: CapabilityRegistry) -> SequenceExpr | None:
    """Drop unsupported steps + downgrade unsupported operators inside a sequence.

    Used by both the top-level plan reducer and GroupExpr's nested sequence.
    Returns None if the result has fewer than 2 steps.
    """
    new_steps: list = []
    new_operators: list = []
    for i, step in enumerate(sequence.steps):
        reduced = _reduce_step(step, registry)
        if reduced is None:
            continue
        new_steps.append(reduced)
        if i > 0 and len(new_operators) < len(new_steps) - 1:
            op_idx = i - 1
            if op_idx < len(sequence.operators):
                op = sequence.operators[op_idx]
                if op.type.value not in registry.operators:
                    op = OrderOperator(type=OperatorType.PRECEDENCE, gap=op.gap)
                new_operators.append(op)

    if len(new_steps) < 2:
        return None

    new_operators = new_operators[: len(new_steps) - 1]
    return SequenceExpr(steps=new_steps, operators=new_operators)


def _reduce_plan(plan: QueryPlan, registry: CapabilityRegistry) -> QueryPlan | None:
    """Build a reduced QueryPlan by stripping unsupported features.

    Returns None if the plan cannot be meaningfully reduced.
    """
    if isinstance(plan.sequence, InverseExpr):
        return None  # Can't meaningfully reduce an inverse query

    new_sequence = _reduce_sequence(plan.sequence, registry)
    if new_sequence is None:
        return None

    return QueryPlan(
        version=plan.version,
        source=plan.source,
        sequence=new_sequence,
        scope=plan.scope,
        mode=plan.mode,
        expansion=None,  # Strip expansion
        ranking=plan.ranking,
        metadata=plan.metadata,
    )


# ---------------------------------------------------------------------------
# Main validate function
# ---------------------------------------------------------------------------

_RULES = [
    _rule_1_version,
    _rule_2_node_types,
    _rule_3_operators,
    _rule_4_gap_constraints,
    _rule_5_polarity,
    _rule_6_inverse,
    _rule_7_expansion,
    _rule_8_compound_nodes,
    _rule_9_match_mode,
    _rule_10_scope,
    _rule_11_sequence_length,
    _rule_12_structural,
]


# ---------------------------------------------------------------------------
# Rule 13: registry grounding (REQ:08.registry-epistemics)
# ---------------------------------------------------------------------------
#
# Lives outside the _RULES list because its signature differs (it takes a
# ConceptRegistry as a third argument and returns a (findings, grounding)
# tuple instead of just findings). Per design decision #5, this rule is
# additive: it never pushes status to `unsupported` or `partial`. Per
# decision #6, the grounding axis is orthogonal to match_mode.


def _rule_13_registry_grounding(
    plan: QueryPlan,
    concept_registry: ConceptRegistry,
) -> tuple[
    list[ValidationFinding],
    Literal["evidence-grounded", "prior-grounded", "mixed"] | None,
]:
    """Walk the plan; for every concept ``NodeRef`` (including those nested
    inside an ``InverseExpr``), look up backing registry rows. Emit a
    ``RULE13_PRIOR_GROUNDED`` warning when any backing claim is unverified.

    Returns ``(findings, grounding)`` where ``grounding`` is:
      - ``None`` if no concept nodes were inspected (the registry had no
        rows for any of them, or the plan had no concept nodes at all);
      - ``"evidence-grounded"`` if every inspected concept is
        corpus-observed or human-confirmed;
      - ``"prior-grounded"`` if every inspected concept is unverified;
      - ``"mixed"`` if both kinds were observed.
    """
    findings: list[ValidationFinding] = []
    verified_seen = False
    unverified_seen = False

    inside_inverse = isinstance(plan.sequence, InverseExpr)
    concept_refs = [
        (path, node)
        for path, node in _collect_node_refs(plan.sequence)
        if node.type == NodeType.CONCEPT
    ]

    for path, node in concept_refs:
        # Determine whether the concept exists in the registry at all. If it
        # doesn't, we silently skip — no claim means nothing to flag.
        concepts = concept_registry.get_by_lemma(node.value)
        concept_in_registry = bool(concepts) or _concept_known_by_name(
            concept_registry, node.value
        )
        if not concept_in_registry:
            continue

        polarity = node.polarity if node.polarity in ("+", "-") else None
        is_prior = concept_registry.is_prior_grounded(node.value, polarity)
        if is_prior:
            unverified_seen = True
            findings.append(
                ValidationFinding(
                    severity="warning",
                    code="RULE13_PRIOR_GROUNDED",
                    path=path,
                    message=(
                        f"Concept '{node.value}' is backed by an unverified "
                        "registry claim; results are prior-grounded, not "
                        "corpus-evidence-grounded."
                    ),
                )
            )
        else:
            verified_seen = True

        # Inverse-context: a concept appearing inside an InverseExpr also
        # depends on the inverse-claim graph. If any inverse claim is
        # unverified, emit an additional warning. Only inspected when the
        # concept resolves to at least one Concept row in the registry.
        if inside_inverse and concepts:
            for concept in concepts:
                inverse_claims = concept_registry.get_inverse_claims(concept.id)
                if not inverse_claims:
                    continue
                if any(
                    claim.verification_state == "unverified"
                    for claim in inverse_claims
                ):
                    unverified_seen = True
                    findings.append(
                        ValidationFinding(
                            severity="warning",
                            code="RULE13_PRIOR_GROUNDED",
                            path=path,
                            message=(
                                f"Inverse claim for concept '{node.value}' "
                                "is unverified; inverse() resolution is "
                                "prior-grounded."
                            ),
                        )
                    )
                else:
                    verified_seen = True

    if not verified_seen and not unverified_seen:
        grounding: (
            Literal["evidence-grounded", "prior-grounded", "mixed"] | None
        ) = None
    elif verified_seen and unverified_seen:
        grounding = "mixed"
    elif unverified_seen:
        grounding = "prior-grounded"
    else:
        grounding = "evidence-grounded"

    return findings, grounding


def _concept_known_by_name(
    concept_registry: ConceptRegistry, name: str
) -> bool:
    """Best-effort check that a concept exists in the registry by name.

    ``ConceptRegistry`` exposes ``get_by_lemma`` (lemma → concepts) and
    ``is_prior_grounded`` (name → bool). For rule 13 we want to skip
    concepts that are entirely absent from the registry (so we don't flag
    every ad-hoc concept the user types). ``is_prior_grounded`` returns
    ``False`` both for "absent" and for "present but verified" — we use
    ``get_polarity_claims`` after a name lookup as a tiebreaker.

    Implementation detail: with no engine attached (``ConceptRegistry.empty``)
    every method returns empty; this helper returns ``False`` and the caller
    silently skips. With an engine attached, we query for the concept by
    name and return ``True`` iff a row exists.
    """
    if concept_registry.engine is None:
        return False
    from sqlalchemy import select

    from src.ontology.registry import concepts_table

    stmt = select(concepts_table.c.id).where(concepts_table.c.name == name)
    with concept_registry.engine.connect() as connection:
        return connection.execute(stmt).scalar_one_or_none() is not None


def validate(
    plan: QueryPlan,
    capability_registry: CapabilityRegistry,
    concept_registry: ConceptRegistry | None = None,
) -> ValidationResult:
    """Validate a QueryPlan against the capability registry.

    The first parameter is the engine-capability registry (renamed from
    ``registry`` for clarity; existing positional callers are unaffected).
    The optional ``concept_registry`` engages rule 13 (registry grounding):
    when ``None`` is passed, rule 13 is skipped and ``grounding`` is
    ``None`` on the result. When provided, rule 13 runs after the existing
    twelve rules; its findings are appended and the resulting grounding
    label is set on the ``ValidationResult``.

    Returns a ValidationResult with status, executable plan, findings, and
    optional grounding label.
    """
    findings: list[ValidationFinding] = []
    for rule in _RULES:
        findings.extend(rule(plan, capability_registry))

    grounding: (
        Literal["evidence-grounded", "prior-grounded", "mixed"] | None
    ) = None
    if concept_registry is not None:
        rule13_findings, grounding = _rule_13_registry_grounding(
            plan, concept_registry
        )
        findings.extend(rule13_findings)

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    if not errors and not warnings:
        return ValidationResult(
            status="supported",
            executable_plan=plan,
            findings=findings,
            engine_version=capability_registry.version,
            grounding=grounding,
        )

    if not errors and warnings:
        # Warnings only — distinguish "informational" warnings (which leave
        # the plan supported as-is) from "structural" warnings that require
        # reduction. Slice L: ``GAP_NARROWED_BY_WINDOW`` is informational —
        # the executor honors both the step-level gap and the outer window
        # natively (AND composition), so no reduction is needed; the
        # narrowing is surfaced for transparency.
        _informational_warning_codes = {
            "RULE13_PRIOR_GROUNDED",
            "GAP_NARROWED_BY_WINDOW",
        }
        non_informational_warnings = [
            f for f in warnings if f.code not in _informational_warning_codes
        ]
        if not non_informational_warnings:
            return ValidationResult(
                status="supported",
                executable_plan=plan,
                findings=findings,
                engine_version=capability_registry.version,
                grounding=grounding,
            )
        reduced = _reduce_plan(plan, capability_registry)
        if reduced is None:
            reduced = plan
        return ValidationResult(
            status="partial",
            executable_plan=reduced,
            findings=findings,
            engine_version=capability_registry.version,
            grounding=grounding,
        )

    # Has errors — try partial reduction unless an unreducible error fired.
    # Slice L: WINDOW_EXCEEDS_MAX is an error about the scope envelope itself,
    # not a structural property _reduce_plan can strip from the AST. Reduction
    # would leave the offending ``scope.unit.n`` in place and return a
    # `partial` plan that the executor would happily run — silently breaching
    # the capability surface. Force unsupported so the route returns 422.
    unreducible_error_codes = {"WINDOW_EXCEEDS_MAX"}
    if any(f.code in unreducible_error_codes for f in errors):
        return ValidationResult(
            status="unsupported",
            executable_plan=None,
            findings=findings,
            engine_version=capability_registry.version,
            grounding=grounding,
        )

    reduced = _reduce_plan(plan, capability_registry)
    if reduced is not None:
        return ValidationResult(
            status="partial",
            executable_plan=reduced,
            findings=findings,
            engine_version=capability_registry.version,
            grounding=grounding,
        )

    return ValidationResult(
        status="unsupported",
        executable_plan=None,
        findings=findings,
        engine_version=capability_registry.version,
        grounding=grounding,
    )
