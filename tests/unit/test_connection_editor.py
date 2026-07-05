"""Unit tests for src/ontology/connections.py (Slice 2, 2026-07-05).

A fake engine records the SQL issued and serves canned rows so we can assert
validation, name resolution, ordered-member insertion, multi-type claims, and
the DEC-146-style firewall: a connection write never touches the evidence tables
(polarity_claims / inverse_claims). No DB.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from src.ontology.connections import (
    ConnectionNotFound,
    InvalidConnection,
    UnknownConcept,
    create_connection,
    delete_connection,
)


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows

    def first(self) -> object | None:
        return self._rows[0] if self._rows else None

    def scalar_one(self) -> object:
        return self._rows[0]

    def scalars(self) -> "_Result":
        return self

    def __iter__(self):  # noqa: ANN204
        return iter(self._rows)


class _NamedRow:
    def __init__(self, **kw: object) -> None:
        self.__dict__.update(kw)


class _CapturingConnection:
    """Serves canned results in call order and records SQL text."""

    def __init__(self, results: list[_Result]) -> None:
        self.statements: list[str] = []
        self._results = results
        self._i = 0

    def execute(self, stmt: object, *args: object) -> _Result:
        self.statements.append(str(stmt).lower())
        res = self._results[self._i] if self._i < len(self._results) else _Result([])
        self._i += 1
        return res


class _FakeEngine:
    def __init__(self, results: list[_Result]) -> None:
        self.connection = _CapturingConnection(results)

    @contextmanager
    def begin(self) -> Iterator[_CapturingConnection]:
        yield self.connection


def _assert_no_evidence_writes(conn: _CapturingConnection) -> None:
    for sql in conn.statements:
        assert "polarity_claims" not in sql, sql
        assert "inverse_claims" not in sql, sql


class TestValidation:
    def test_needs_two_members(self) -> None:
        with pytest.raises(InvalidConnection, match="at least two"):
            create_connection(
                _FakeEngine([]),  # type: ignore[arg-type]
                member_names=["faith"],
                claim_types=["interchange"],
            )

    def test_members_must_be_distinct(self) -> None:
        with pytest.raises(InvalidConnection, match="distinct"):
            create_connection(
                _FakeEngine([]),  # type: ignore[arg-type]
                member_names=["faith", "faith"],
                claim_types=["sequence"],
            )

    def test_needs_a_type(self) -> None:
        with pytest.raises(InvalidConnection, match="at least one type"):
            create_connection(
                _FakeEngine([]),  # type: ignore[arg-type]
                member_names=["faith", "hope"],
                claim_types=[],
            )

    def test_rejects_unknown_type(self) -> None:
        with pytest.raises(InvalidConnection, match="unknown connection type"):
            create_connection(
                _FakeEngine([]),  # type: ignore[arg-type]
                member_names=["faith", "hope"],
                claim_types=["causation"],
            )


class TestCreate:
    def _engine_for_create(self) -> _FakeEngine:
        # execute() call order in create_connection:
        # 1. resolve names -> ids
        # 2. insert connection (returning id)
        # 3. insert members (executemany)
        # 4. insert claims (executemany)
        # then _load_connection: 5. head, 6. members, 7. types
        return _FakeEngine(
            [
                _Result([_NamedRow(id=10, name="righteousness"),
                         _NamedRow(id=11, name="faith")]),  # resolve
                _Result([7]),  # insert connection returning id
                _Result([]),  # insert members
                _Result([]),  # insert claims
                _Result([_NamedRow(id=7, note="Rom 1:17", actor="local",
                                   created_at=None, updated_at=None)]),  # head
                _Result([_NamedRow(name="righteousness"),
                         _NamedRow(name="faith")]),  # members (ordered)
                _Result([_NamedRow(claim_type="interchange")]),  # types
            ]
        )

    def test_create_returns_connection_with_members_and_types(self) -> None:
        engine = self._engine_for_create()
        conn = create_connection(
            engine,  # type: ignore[arg-type]
            member_names=["righteousness", "faith"],
            claim_types=["interchange"],
            note="Rom 1:17",
        )
        assert conn.id == 7
        assert conn.members == ["righteousness", "faith"]
        assert conn.types == ["interchange"]
        assert conn.note == "Rom 1:17"

    def test_create_never_writes_evidence_tables(self) -> None:
        engine = self._engine_for_create()
        create_connection(
            engine,  # type: ignore[arg-type]
            member_names=["righteousness", "faith"],
            claim_types=["interchange"],
        )
        _assert_no_evidence_writes(engine.connection)
        assert any("insert into connections" in s for s in engine.connection.statements)

    def test_unknown_member_raises(self) -> None:
        # resolve returns only one of the two requested names.
        engine = _FakeEngine([_Result([_NamedRow(id=10, name="faith")])])
        with pytest.raises(UnknownConcept, match="hope"):
            create_connection(
                engine,  # type: ignore[arg-type]
                member_names=["faith", "hope"],
                claim_types=["sequence"],
            )


class TestDelete:
    def test_delete_missing_raises(self) -> None:
        engine = _FakeEngine([_Result([])])  # delete returning -> no row
        with pytest.raises(ConnectionNotFound):
            delete_connection(engine, 999)  # type: ignore[arg-type]

    def test_delete_present_ok(self) -> None:
        engine = _FakeEngine([_Result([_NamedRow(id=7)])])
        delete_connection(engine, 7)  # type: ignore[arg-type]
        assert any("delete from connections" in s for s in engine.connection.statements)
