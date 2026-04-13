"""Capability registry — declarative manifest of engine capabilities.

Defines what node types, operators, modes, scopes, and features the
engine currently supports. The validator checks QueryPlans against this.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CapabilityRegistry(BaseModel):
    """Declarative manifest of what the engine currently supports."""

    model_config = ConfigDict(frozen=True)

    version: str
    node_types: list[str]
    operators: list[str]
    match_modes: list[str]
    scope_fields: list[str]
    max_sequence_length: int
    max_gap: int | None
    polarity_support: bool
    inverse_support: bool
    expansion_support: bool
    compound_node_support: bool
    corpora: list[str]
    languages: list[str]

    @classmethod
    def mvp(cls) -> CapabilityRegistry:
        """Return the MVP v0.1 capability registry."""
        return cls(
            version="0.1",
            node_types=["token", "lemma", "concept", "morph", "wildcard"],
            operators=["precedence", "adjacency"],
            match_modes=["exact", "variant", "conceptual", "hybrid"],
            scope_fields=["corpus", "language", "books", "unit"],
            max_sequence_length=10,
            max_gap=None,
            polarity_support=True,
            inverse_support=False,
            expansion_support=False,
            compound_node_support=False,
            corpora=["nt"],
            languages=["grc"],
        )
