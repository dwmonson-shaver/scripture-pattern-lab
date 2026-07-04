"""Unit tests for src/ontology/concept_editor.py (Slice 1, DEC-130/146/147).

A fake engine captures the SQL statements issued so we can assert (1) create/
update shape and (2) the DEC-146 firewall: a human-authored concept create/edit
NEVER touches polarity_claims / inverse_claims. No DB.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from src.ontology.concept_editor import (
    ConceptExists,
    ConceptNotFound,
    create_concept,
    delete_concept,
    update_concept,
)


class _Row:
    def __init__(self, **kw: object) -> None:
        self.id = kw.get("id", 1)
        self.name = kw.get("name", "Hope")
        self.description = kw.get("description")
        self.origin = kw.get("origin", "curated")
        self.verification_state = kw.get("verification_state", "unverified")
        self.authored_color = kw.get("authored_color")
        self.authored_polarity = kw.get("authored_polarity")
        self.authored_opposite_name = kw.get("authored_opposite_name")


class _Result:
    def __init__(self, row: _Row | None) -> None:
        self._row = row

    def first(self) -> _Row | None:
        return self._row


class _CapturingConnection:
    """Records every executed statement's lowercased SQL text."""

    def __init__(self, returns: list[_Row | None]) -> None:
        self.statements: list[str] = []
        self._returns = returns
        self._i = 0

    def execute(self, stmt: object) -> _Result:
        self.statements.append(str(stmt).lower())
        row = self._returns[self._i] if self._i < len(self._returns) else None
        self._i += 1
        return _Result(row)


class _FakeEngine:
    def __init__(self, returns: list[_Row | None]) -> None:
        self.connection = _CapturingConnection(returns)

    @contextmanager
    def begin(self) -> Iterator[_CapturingConnection]:
        yield self.connection


def _assert_no_claim_writes(conn: _CapturingConnection) -> None:
    """DEC-146 firewall: no statement may touch the evidence-bearing tables."""
    for sql in conn.statements:
        assert "polarity_claims" not in sql, sql
        assert "inverse_claims" not in sql, sql


class TestCreateConcept:
    def test_create_returns_concept(self) -> None:
        engine = _FakeEngine([_Row(name="Hope", authored_color="#E0A12E",
                                   authored_polarity="+")])
        concept = create_concept(
            engine,  # type: ignore[arg-type]
            name="Hope",
            authored_color="#E0A12E",
            authored_polarity="+",
            authored_opposite_name="Despair",
        )
        assert concept.name == "Hope"
        assert concept.origin == "curated"
        assert concept.verification_state == "unverified"
        assert concept.authored_polarity == "+"

    def test_conflict_raises_concept_exists(self) -> None:
        engine = _FakeEngine([None])  # ON CONFLICT DO NOTHING → no row returned
        with pytest.raises(ConceptExists):
            create_concept(engine, name="Hope")  # type: ignore[arg-type]

    def test_create_never_writes_claim_tables(self) -> None:
        """DEC-146 guardrail (c): authored polarity must not feed the evidence layer."""
        engine = _FakeEngine([_Row(authored_polarity="+")])
        create_concept(
            engine,  # type: ignore[arg-type]
            name="Hope",
            authored_polarity="+",
            authored_opposite_name="Despair",
        )
        _assert_no_claim_writes(engine.connection)
        # And it DID write the concepts row.
        assert any("concepts" in s for s in engine.connection.statements)


class TestUpdateConcept:
    def test_update_changes_only_provided_fields(self) -> None:
        engine = _FakeEngine([_Row(name="Hope", authored_color="#fff")])
        concept = update_concept(
            engine,  # type: ignore[arg-type]
            "Hope",
            authored_color="#fff",
        )
        assert concept.authored_color == "#fff"
        joined = " ".join(engine.connection.statements)
        assert "update" in joined
        _assert_no_claim_writes(engine.connection)

    def test_update_missing_raises_not_found(self) -> None:
        engine = _FakeEngine([None])
        with pytest.raises(ConceptNotFound):
            update_concept(engine, "Nope", description="x")  # type: ignore[arg-type]

    def test_update_no_fields_reads_back(self) -> None:
        engine = _FakeEngine([_Row(name="Hope")])
        concept = update_concept(engine, "Hope")  # type: ignore[arg-type]
        assert concept.name == "Hope"
        # No-field update issues a SELECT, not an UPDATE.
        assert any(s.startswith("select") for s in engine.connection.statements)
        _assert_no_claim_writes(engine.connection)


class TestDeleteConcept:
    def test_delete_issues_single_delete_on_concepts(self) -> None:
        engine = _FakeEngine([_Row(name="Hope")])
        delete_concept(engine, "Hope")  # type: ignore[arg-type]
        statements = engine.connection.statements
        assert len(statements) == 1
        assert statements[0].startswith("delete from concepts")
        # Dependent cleanup is the schema's ON DELETE CASCADE, not extra SQL —
        # and the evidence tables are never addressed directly (DEC-146).
        _assert_no_claim_writes(engine.connection)

    def test_delete_missing_raises_not_found(self) -> None:
        engine = _FakeEngine([None])
        with pytest.raises(ConceptNotFound):
            delete_concept(engine, "Nope")  # type: ignore[arg-type]
