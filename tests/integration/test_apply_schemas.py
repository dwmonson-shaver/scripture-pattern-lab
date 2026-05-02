"""Integration test for scripts/db/apply_schemas.sh.

Verifies the apply script (a) creates the canonical schema on a fresh DB and
(b) is a no-op when re-run against an already-applied DB. Closes the coverage
gap left open by DEC-028, which chose TRUNCATE over subprocess re-apply for
the corpus-ingest integration test's reset path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from sqlalchemy import MetaData, Table, text

from src.ingestion.db import get_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
APPLY_SCRIPT = REPO_ROOT / "scripts" / "db" / "apply_schemas.sh"

EXPECTED_TOKENS_COLUMNS = {
    "id",
    "book",
    "chapter",
    "verse",
    "position",
    "global_position",
    "surface_form",
    "normalized_form",
    "lemma",
    "morph_code",
    "pos",
    "language",
    "corpus_id",
}


pytestmark = pytest.mark.integration


def _run_apply_schemas() -> subprocess.CompletedProcess[str]:
    """Invoke apply_schemas.sh from repo root with the parent process env."""
    return subprocess.run(
        ["bash", str(APPLY_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def test_apply_schemas_creates_table_on_fresh_db() -> None:
    """DROP tokens, run apply script, verify the canonical schema is recreated."""
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS tokens CASCADE"))

    _run_apply_schemas()

    reflected = Table("tokens", MetaData(), autoload_with=engine)
    assert set(reflected.columns.keys()) == EXPECTED_TOKENS_COLUMNS


def test_apply_schemas_is_idempotent() -> None:
    """Running apply twice in a row must succeed (CREATE ... IF NOT EXISTS)."""
    _run_apply_schemas()
    result = _run_apply_schemas()
    assert result.returncode == 0
