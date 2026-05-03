"""Integration smoke for corpus ingestion — full 3 John round-trip.

Requires a live Postgres reachable via DATABASE_URL with the canonical
``tokens`` schema already applied (run ``bash scripts/db/apply_schemas.sh``).
Gated by ``@pytest.mark.integration``; excluded from the default suite.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, MetaData, Table, select, text

from src.ingestion.corpus_parser import CorpusToken, parse_corpus_file
from src.ingestion.db import get_engine, tokens_table
from src.ingestion.loader import load_tokens

REAL_3JN_PATH = Path("data/raw/morphgnt-sblgnt/85-3Jn-morphgnt.txt")
REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_SCRIPT = REPO_ROOT / "scripts" / "db" / "ingest_corpus.py"
MULTI_FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "morphgnt" / "multi"


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


def _run_ingest_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Invoke ``scripts/db/ingest_corpus.py`` from repo root with parent env.

    Mirrors ``tests/integration/test_apply_schemas.py:42``'s subprocess style
    so the script is exercised as a real binary, not as an in-process call.
    """
    return subprocess.run(
        [sys.executable, str(INGEST_SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _import_ingest_module() -> ModuleType:
    """Load ``scripts/db/ingest_corpus.py`` as a module for in-process helper tests.

    ``scripts/`` is intentionally not a Python package (it holds CLI tools, not
    importable library code), so we go through ``importlib.util`` rather than
    a top-level import. The module's ``__main__`` guard prevents ``main()``
    from running on import.
    """
    spec = importlib.util.spec_from_file_location(
        "_ingest_corpus_under_test", INGEST_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_fails_loud_when_tokens_nonempty_without_truncate(
    loaded_engine: tuple[Engine, int],
) -> None:
    """Script must refuse to load when ``tokens`` is non-empty and no --truncate.

    The ``loaded_engine`` module-scope fixture has already inserted 219 rows
    of 3 John, so the table is guaranteed non-empty here. Use --corpus-dir to
    point at the 2-book multi fixture so the corpus-dir guard passes (it does
    not enforce count==27 when --corpus-dir is supplied; see Decision A).
    """
    _ = loaded_engine  # ensure the table is populated before the script runs
    result = _run_ingest_script(["--corpus-dir", str(MULTI_FIXTURE_DIR)])
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}; stderr={result.stderr!r}"
    )
    assert "tokens" in result.stderr.lower()
    assert "--truncate" in result.stderr


def test_script_truncate_requires_env_confirm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--truncate alone is not enough; SPL_INGEST_CONFIRM_TRUNCATE=1 is also required.

    The env-confirm check runs before any DB or filesystem access, so this
    test does not need ``loaded_engine`` or a valid corpus dir.
    """
    monkeypatch.delenv("SPL_INGEST_CONFIRM_TRUNCATE", raising=False)
    result = _run_ingest_script(["--truncate"])
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}; stderr={result.stderr!r}"
    )
    assert "SPL_INGEST_CONFIRM_TRUNCATE" in result.stderr


def test_script_redacts_password_in_database_url_print() -> None:
    """``_redact_database_url`` must blot out the password segment of any
    URL the script would print to stderr at startup.

    Tests the helper directly with synthetic URLs so the assertion does not
    depend on the real DATABASE_URL or on running the script. Covers the
    common shapes: full userinfo, missing userinfo, missing password.
    """
    module = _import_ingest_module()
    redact = module._redact_database_url

    full = "postgresql+psycopg://alice:s3cret@db.example.com:5432/spl"
    assert redact(full) == "postgresql+psycopg://alice:***@db.example.com:5432/spl"
    assert "s3cret" not in redact(full)

    no_userinfo = "postgresql://db.example.com/spl"
    assert redact(no_userinfo) == no_userinfo

    no_password = "postgresql://alice@db.example.com/spl"
    assert redact(no_password) == no_password

    at_in_password = "postgresql://alice:p@ssw0rd@db.example.com/spl"
    assert redact(at_in_password) == "postgresql://alice:***@db.example.com/spl"
    assert "p@ssw0rd" not in redact(at_in_password)
