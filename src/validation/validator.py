"""Capability validator — checks QueryPlans against engine capabilities.

Deterministic component (no AI). Implements 12 sequential validation rules
from docs/canonical/06_capability-validator.md.

Interface per docs/canonical/09_backend-service-boundaries.md:
    def validate(plan: QueryPlan, registry: CapabilityRegistry) -> ValidationResult
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.engine.models import (
    AlternativeExpr,
    GroupExpr,
    InverseExpr,
    NodeRef,
    OperatorType,
    OptionalExpr,
    OrderOperator,
    QueryPlan,
    SequenceExpr,
)
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
    """Result of validating a QueryPlan against the capability registry."""

    model_config = ConfigDict(frozen=True)

    status: Literal["supported", "partial", "unsupported"]
    executable_plan: QueryPlan | None
    findings: list[ValidationFinding]
    engine_version: str


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
    """Check scope validation."""
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


def _reduce_plan(plan: QueryPlan, registry: CapabilityRegistry) -> QueryPlan | None:
    """Build a reduced QueryPlan by stripping unsupported features.

    Returns None if the plan cannot be meaningfully reduced.
    """
    # Strip inverse wrapper
    sequence = plan.sequence
    if isinstance(sequence, InverseExpr):
        return None  # Can't meaningfully reduce an inverse query

    # Strip unsupported node steps
    new_steps = []
    new_operators = []
    for i, step in enumerate(sequence.steps):
        if isinstance(step, NodeRef) and step.type.value not in registry.node_types:
            continue  # drop unsupported node
        new_steps.append(step)
        if i > 0 and len(new_operators) < len(new_steps) - 1:
            # Add the operator before this step if we kept the step
            op_idx = i - 1
            if op_idx < len(sequence.operators):
                op = sequence.operators[op_idx]
                # Downgrade unsupported operators
                if op.type.value not in registry.operators:
                    op = OrderOperator(type=OperatorType.PRECEDENCE, gap=op.gap)
                new_operators.append(op)

    if len(new_steps) < 2:
        return None  # Can't run a meaningful sequence with <2 steps

    # Ensure operator count matches
    new_operators = new_operators[: len(new_steps) - 1]

    new_sequence = SequenceExpr(steps=new_steps, operators=new_operators)

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


def validate(plan: QueryPlan, registry: CapabilityRegistry) -> ValidationResult:
    """Validate a QueryPlan against the capability registry.

    Returns a ValidationResult with status, executable plan, and findings.
    """
    findings: list[ValidationFinding] = []
    for rule in _RULES:
        findings.extend(rule(plan, registry))

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    if not errors and not warnings:
        return ValidationResult(
            status="supported",
            executable_plan=plan,
            findings=findings,
            engine_version=registry.version,
        )

    if not errors and warnings:
        # Warnings only (e.g., unsupported expansion) — partial
        reduced = _reduce_plan(plan, registry)
        if reduced is None:
            reduced = plan
        return ValidationResult(
            status="partial",
            executable_plan=reduced,
            findings=findings,
            engine_version=registry.version,
        )

    # Has errors — try partial reduction
    reduced = _reduce_plan(plan, registry)
    if reduced is not None:
        return ValidationResult(
            status="partial",
            executable_plan=reduced,
            findings=findings,
            engine_version=registry.version,
        )

    return ValidationResult(
        status="unsupported",
        executable_plan=None,
        findings=findings,
        engine_version=registry.version,
    )
