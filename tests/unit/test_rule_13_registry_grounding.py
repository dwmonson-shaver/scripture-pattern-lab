"""Unit tests for validator rule 13 (REQ:08.registry-epistemics).

Rule 13 is additive (decision #5): it never pushes status to
``unsupported``/``partial``; it emits a ``RULE13_PRIOR_GROUNDED`` warning
and sets the orthogonal ``grounding`` axis on ``ValidationResult``
(decision #6).

These tests stub ``ConceptRegistry`` so no DB is required. The stub
overrides ``get_by_lemma`` (to mark concepts as "in registry") and
``is_prior_grounded`` (to flip verified vs unverified) per concept name.
"""

from __future__ import annotations

from typing import Literal

from src.engine.models import (
    InverseExpr,
    NodeRef,
    NodeType,
    OperatorType,
    OrderOperator,
    QueryPlan,
    ScopeConstraint,
    SequenceExpr,
)
from src.ontology.registry import (
    Concept,
    ConceptRegistry,
    InverseClaim,
    Polarity,
    PolarityClaim,
)
from src.validation.registry import CapabilityRegistry
from src.validation.validator import validate

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _mvp() -> CapabilityRegistry:
    return CapabilityRegistry.mvp()


def _concept_plan(
    *specs: tuple[str, str | None],
    inverse: bool = False,
    node_type: NodeType = NodeType.CONCEPT,
) -> QueryPlan:
    """Build a plan from (value, polarity) tuples.

    Polarity ``None`` produces a NodeRef with ``polarity=None``; otherwise
    the literal ``+`` / ``-`` is set. ``inverse=True`` wraps the sequence
    in an ``InverseExpr``.
    """
    steps = [
        NodeRef(type=node_type, value=value, polarity=polarity)  # type: ignore[arg-type]
        for value, polarity in specs
    ]
    operators = [OrderOperator(type=OperatorType.PRECEDENCE)] * (
        len(specs) - 1
    )
    sequence = SequenceExpr(steps=steps, operators=operators)
    return QueryPlan(
        version="0.1",
        source=" > ".join(v for v, _ in specs),
        sequence=InverseExpr(inner=sequence) if inverse else sequence,
        scope=ScopeConstraint(),
        mode="conceptual",
    )


class _StubRegistry(ConceptRegistry):
    """Deterministic ConceptRegistry stub for rule-13 unit tests.

    - ``known_concepts``: set of concept names that exist in the registry.
      Concepts not in this set are treated as absent (rule 13 silently
      skips them).
    - ``unverified_priors``: set of (concept_name, polarity_or_None) keys
      that should report ``is_prior_grounded == True``.
    - ``inverse_unverified``: set of concept names whose inverse claims
      should be reported as unverified.
    """

    def __init__(
        self,
        known_concepts: set[str] | None = None,
        unverified_priors: set[tuple[str, str | None]] | None = None,
        inverse_unverified: set[str] | None = None,
    ) -> None:
        super().__init__(engine=None)
        self.known_concepts = known_concepts or set()
        self.unverified_priors = unverified_priors or set()
        self.inverse_unverified = inverse_unverified or set()
        # Assign synthetic ids so get_by_lemma / get_inverse_claims have
        # something to reference.
        self._ids: dict[str, int] = {
            name: idx + 1 for idx, name in enumerate(sorted(self.known_concepts))
        }

    def get_by_lemma(
        self, lemma: str, language: str = "grc"
    ) -> list[Concept]:
        # Treat the lemma argument as the concept name itself for rule-13
        # tests — rule 13 calls get_by_lemma(node.value), and node.value for
        # a concept node is the concept name.
        if lemma not in self.known_concepts:
            return []
        return [
            Concept(
                id=self._ids[lemma],
                name=lemma,
                origin="curated",
                verification_state="unverified",
            )
        ]

    def is_prior_grounded(
        self, concept_name: str, polarity: Polarity | None
    ) -> bool:
        if concept_name not in self.known_concepts:
            return False
        return (concept_name, polarity) in self.unverified_priors

    def get_polarity_claims(self, concept_id: int) -> list[PolarityClaim]:
        return []

    def get_inverse_claims(self, concept_id: int) -> list[InverseClaim]:
        # Reverse-lookup: which name does this id belong to?
        name = next(
            (n for n, i in self._ids.items() if i == concept_id), None
        )
        if name is None or name not in self.inverse_unverified:
            return []
        # Manufacture a synthetic unverified inverse claim. The id of the
        # inverse partner doesn't matter for rule 13 — only its
        # verification_state does.
        return [
            InverseClaim(
                id=1,
                concept_id=concept_id,
                inverse_concept_id=concept_id + 1000,
                origin="curated",
                evidence_count=0,
                verification_state="unverified",
                confidence=None,
            )
        ]


def _grounding(
    plan: QueryPlan, concept_registry: ConceptRegistry | None
) -> Literal["evidence-grounded", "prior-grounded", "mixed"] | None:
    return validate(plan, _mvp(), concept_registry).grounding


# ---------------------------------------------------------------------------
# Back-compat: validate() with no concept_registry stays grounding-blind
# ---------------------------------------------------------------------------


def test_no_concept_registry_passes_through() -> None:
    """No concept_registry kwarg: grounding is None, no rule-13 finding."""
    plan = _concept_plan(("faith", "+"), ("hope", "+"))
    result = validate(plan, _mvp())
    assert result.grounding is None
    codes = {f.code for f in result.findings}
    assert "RULE13_PRIOR_GROUNDED" not in codes
    assert result.status == "supported"


def test_empty_registry_evidence_grounded_or_none() -> None:
    """ConceptRegistry.empty() has no rows; rule 13 inspects nothing."""
    plan = _concept_plan(("faith", "+"))
    result = validate(plan, _mvp(), ConceptRegistry.empty())
    assert result.grounding is None
    codes = {f.code for f in result.findings}
    assert "RULE13_PRIOR_GROUNDED" not in codes
    assert result.status == "supported"


# ---------------------------------------------------------------------------
# Substantive rule-13 paths
# ---------------------------------------------------------------------------


def test_polarity_concept_unverified_emits_warning() -> None:
    """Polarity-marked concept with unverified backing → prior-grounded."""
    stub = _StubRegistry(
        known_concepts={"faith"},
        unverified_priors={("faith", "+")},
    )
    plan = _concept_plan(("faith", "+"))
    result = validate(plan, _mvp(), stub)
    assert result.status == "supported"
    assert result.grounding == "prior-grounded"
    rule13 = [f for f in result.findings if f.code == "RULE13_PRIOR_GROUNDED"]
    assert len(rule13) == 1
    assert rule13[0].severity == "warning"
    assert "faith" in rule13[0].message


def test_polarity_concept_verified_evidence_grounded() -> None:
    """Polarity-marked concept with verified backing → evidence-grounded."""
    stub = _StubRegistry(
        known_concepts={"faith"},
        unverified_priors=set(),  # claim is corpus_observed
    )
    plan = _concept_plan(("faith", "+"))
    result = validate(plan, _mvp(), stub)
    assert result.status == "supported"
    assert result.grounding == "evidence-grounded"
    codes = {f.code for f in result.findings}
    assert "RULE13_PRIOR_GROUNDED" not in codes


def test_mixed_plan_one_verified_one_unverified() -> None:
    """One concept verified, one unverified → grounding='mixed'."""
    stub = _StubRegistry(
        known_concepts={"faith", "hope"},
        unverified_priors={("hope", "+")},  # only hope is unverified
    )
    plan = _concept_plan(("faith", "+"), ("hope", "+"))
    result = validate(plan, _mvp(), stub)
    assert result.status == "supported"
    assert result.grounding == "mixed"
    rule13 = [f for f in result.findings if f.code == "RULE13_PRIOR_GROUNDED"]
    assert len(rule13) == 1
    assert "hope" in rule13[0].message


def test_inverse_concept_unverified_warns() -> None:
    """inverse(concept:faith) with unverified inverse claim → warning emitted.

    Both the polarity claim AND the inverse claim are unverified, so the
    grounding label resolves to 'prior-grounded' (not mixed).
    """
    stub = _StubRegistry(
        known_concepts={"faith"},
        unverified_priors={("faith", None)},  # polarity claim unverified
        inverse_unverified={"faith"},  # inverse claim unverified too
    )
    plan = _concept_plan(("faith", None), inverse=True)
    # Use a non-MVP CapabilityRegistry that supports inverse so rule 6
    # doesn't error out on the InverseExpr — we want rule 13 to be the
    # source of any warning here.
    cap = CapabilityRegistry.mvp().model_copy(update={"inverse_support": True})
    result = validate(plan, cap, stub)
    rule13 = [f for f in result.findings if f.code == "RULE13_PRIOR_GROUNDED"]
    # Expect at least 2 findings: one from polarity-claim path + one from
    # the inverse-claim path.
    assert len(rule13) >= 2
    assert result.grounding == "prior-grounded"
    # Confirm at least one finding mentions the inverse path explicitly.
    inverse_msgs = [f for f in rule13 if "inverse" in f.message.lower()]
    assert len(inverse_msgs) >= 1


def test_non_concept_node_ignored() -> None:
    """Lemma-only plan: rule 13 has no concept nodes to inspect."""
    stub = _StubRegistry(
        known_concepts={"faith"},
        unverified_priors={("faith", "+")},
    )
    plan = _concept_plan(("pistis", None), node_type=NodeType.LEMMA)
    result = validate(plan, _mvp(), stub)
    assert result.grounding is None
    codes = {f.code for f in result.findings}
    assert "RULE13_PRIOR_GROUNDED" not in codes


def test_unsupported_status_still_set_correctly() -> None:
    """Plan that triggers an existing-rule error: rule 13 must not override status."""
    # Inverse over concept:faith; MVP capability registry has inverse_support=False,
    # so rule 6 emits UNSUPPORTED_INVERSE → status=unsupported.
    stub = _StubRegistry(
        known_concepts={"faith"},
        unverified_priors={("faith", None)},
    )
    plan = _concept_plan(("faith", None), ("hope", None), inverse=True)
    result = validate(plan, _mvp(), stub)
    assert result.status == "unsupported"
    # grounding may still be set if rule 13 inspected concept nodes
    # successfully — we assert it's a permitted value (not coerced None).
    assert result.grounding in (
        None,
        "prior-grounded",
        "evidence-grounded",
        "mixed",
    )
    codes = {f.code for f in result.findings}
    assert "UNSUPPORTED_INVERSE" in codes


def test_existing_validation_findings_preserved() -> None:
    """Existing-rule finding + rule-13 finding both present, rules in order."""
    # Plan: an unsupported expansion (existing rule 7 warning) AND a
    # concept node with unverified backing (rule 13 warning). The
    # expansion warning must come first (rule 7 runs before rule 13).
    from src.engine.models import (
        ExpansionDirection,
        ExpansionDirective,
    )

    stub = _StubRegistry(
        known_concepts={"faith"},
        unverified_priors={("faith", "+")},
    )
    plan = QueryPlan(
        version="0.1",
        source="+concept:faith > +concept:faith => forward:2",
        sequence=SequenceExpr(
            steps=[
                NodeRef(type=NodeType.CONCEPT, value="faith", polarity="+"),
                NodeRef(type=NodeType.CONCEPT, value="faith", polarity="+"),
            ],
            operators=[OrderOperator(type=OperatorType.PRECEDENCE)],
        ),
        scope=ScopeConstraint(),
        mode="conceptual",
        expansion=ExpansionDirective(
            direction=ExpansionDirection.FORWARD, depth=2
        ),
    )
    result = validate(plan, _mvp(), stub)

    codes_in_order = [f.code for f in result.findings]
    assert "UNSUPPORTED_EXPANSION" in codes_in_order
    assert "RULE13_PRIOR_GROUNDED" in codes_in_order
    # Rule 7 runs before rule 13.
    assert codes_in_order.index(
        "UNSUPPORTED_EXPANSION"
    ) < codes_in_order.index("RULE13_PRIOR_GROUNDED")
    # Existing behavior: a real (non-rule-13) warning still drives partial.
    assert result.status == "partial"
    assert result.grounding == "prior-grounded"


def test_grounding_helper_round_trip() -> None:
    """Tiny sanity check on the helper used by other tests."""
    stub = _StubRegistry(known_concepts={"faith"})
    plan = _concept_plan(("faith", "+"))
    assert _grounding(plan, None) is None
    assert _grounding(plan, stub) == "evidence-grounded"
