"""Integration smoke for corpus ingestion — full 3 John round-trip.

Requires a live Postgres reachable via DATABASE_URL with the canonical
``tokens`` schema already applied (run ``bash scripts/db/apply_schemas.sh``).
Gated by ``@pytest.mark.integration``; excluded from the default suite.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, MetaData, Table, select, text

from src.ingestion.corpus_parser import CorpusToken, parse_corpus_file
from src.ingestion.db import get_engine, tokens_table
from src.ingestion.loader import load_tokens

REAL_3JN_PATH = Path("data/raw/morphgnt-sblgnt/85-3Jn-morphgnt.txt")


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def loaded_engine() -> Iterator[tuple[Engine, int]]:
    """Truncate ``tokens``, load all of 3 John, yield (engine, inserted_count).

    Module scope: one load shared across the read-only assertions below.
    """
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE tokens RESTART IDENTITY"))
    inserted = load_tokens(engine, parse_corpus_file(REAL_3JN_PATH))
    yield engine, inserted


def test_load_tokens_returns_219(loaded_engine: tuple[Engine, int]) -> None:
    _, inserted = loaded_engine
    assert inserted == 219


def test_table_row_count_is_219(loaded_engine: tuple[Engine, int]) -> None:
    engine, _ = loaded_engine
    with engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM tokens")).scalar_one()
    assert count == 219


def test_known_row_has_expected_lemma_and_normalized_form(
    loaded_engine: tuple[Engine, int],
) -> None:
    """Row at (book='25', chapter=1, verse=1, position=3) is 'Γαΐῳ' / lemma 'Γάϊος'."""
    engine, _ = loaded_engine
    stmt = select(tokens_table.c.lemma, tokens_table.c.normalized_form).where(
        tokens_table.c.book == "25",
        tokens_table.c.chapter == 1,
        tokens_table.c.verse == 1,
        tokens_table.c.position == 3,
    )
    with engine.connect() as connection:
        row = connection.execute(stmt).one()

    assert row.lemma == "Γάϊος"
    assert row.normalized_form == "Γαΐῳ"
    assert "⸀" not in row.normalized_form


def test_schema_three_way_consistency(loaded_engine: tuple[Engine, int]) -> None:
    """Live SQL columns must match both the SQLAlchemy mirror and CorpusToken fields.

    Catches silent drift between ``data/schemas/01_tokens.sql``,
    ``src/ingestion/db.py``'s ``tokens_table`` mirror, and the ``CorpusToken``
    Pydantic model. ``id`` is the auto-increment PK; not present in CorpusToken.
    """
    engine, _ = loaded_engine
    reflected_metadata = MetaData()
    reflected = Table("tokens", reflected_metadata, autoload_with=engine)

    reflected_cols = set(reflected.columns.keys())
    mirror_cols = set(tokens_table.columns.keys())
    pydantic_fields = set(CorpusToken.model_fields.keys())

    assert reflected_cols == mirror_cols, (
        f"SQL ↔ Table-mirror drift: only-in-SQL={reflected_cols - mirror_cols}, "
        f"only-in-mirror={mirror_cols - reflected_cols}"
    )
    assert reflected_cols - {"id"} == pydantic_fields, (
        f"SQL ↔ CorpusToken drift: "
        f"only-in-SQL={(reflected_cols - {'id'}) - pydantic_fields}, "
        f"only-in-pydantic={pydantic_fields - (reflected_cols - {'id'})}"
    )


def test_get_engine_raises_when_database_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No fallback: missing DATABASE_URL must raise a clear, named error."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        get_engine()
