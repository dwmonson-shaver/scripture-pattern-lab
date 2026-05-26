"""Capability registry — declarative manifest of engine capabilities.

Defines what node types, operators, modes, scopes, and features the
engine currently supports. The validator checks QueryPlans against this.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CapabilityRegistry(BaseModel):
    """Declarative manifest of what the engine currently supports.

    Slice L adds two fields that enumerate the executable scope-unit
    granularities (``scope_units``) and the maximum cross-verse window in
    tokens (``window_max_tokens``). The plain ``scope_fields`` list — which
    advertises ``unit`` as a known field — is preserved; ``scope_units``
    refines that with the kinds the executor actually runs today.
    """

    model_config = ConfigDict(frozen=True)

    version: str
    node_types: list[str]
    operators: list[str]
    match_modes: list[str]
    scope_fields: list[str]
    scope_units: list[str]
    max_sequence_length: int
    max_gap: int | None
    window_max_tokens: int
    polarity_support: bool
    inverse_support: bool
    expansion_support: bool
    compound_node_support: bool
    corpora: list[str]
    languages: list[str]

    @classmethod
    def mvp(cls) -> CapabilityRegistry:
        """Return the MVP v0.1 capability registry.

        Slice L: ``operators`` now advertises ``cooccurrence`` alongside
        ``precedence`` (``adjacency`` parses but is still rejected at the
        executor's second wall — kept here for parser-shape parity).
        ``scope_units`` lists the executable kinds (``verse`` + ``window``);
        ``window_max_tokens=50`` ceils ``ScopeUnitWindow.n`` (Decision #5).
        """
        return cls(
            version="0.1",
            node_types=["token", "lemma", "concept", "morph", "wildcard"],
            operators=["precedence", "adjacency", "cooccurrence"],
            match_modes=["exact", "variant", "conceptual", "hybrid"],
            scope_fields=["corpus", "language", "books", "unit"],
            scope_units=["verse", "window"],
            max_sequence_length=10,
            max_gap=None,
            window_max_tokens=50,
            polarity_support=True,
            inverse_support=False,
            expansion_support=False,
            compound_node_support=False,
            corpora=["nt"],
            languages=["grc"],
        )
