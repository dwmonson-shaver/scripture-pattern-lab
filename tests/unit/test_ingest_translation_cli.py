"""Unit tests for scripts/db/ingest_translation.py pre-DB gate paths (Slice 1).

Only the gate branches that return BEFORE opening a DB connection are unit-
tested here (the --truncate env gate and the missing-source guard). The live
load + non-empty refuse-without-truncate behavior is in
tests/integration/test_translation_ingest.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_CLI_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "db"
    / "ingest_translation.py"
)
_spec = importlib.util.spec_from_file_location("ingest_translation", _CLI_PATH)
assert _spec is not None and _spec.loader is not None
ingest_translation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ingest_translation)


class TestTruncateGate:
    def test_truncate_without_env_confirm_refuses(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv(ingest_translation.TRUNCATE_CONFIRM_ENV, raising=False)
        rc = ingest_translation.main(["--truncate"])
        assert rc == ingest_translation.EXIT_USER_ERROR
        assert "must be set" in capsys.readouterr().err

    def test_truncate_with_wrong_env_value_refuses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ingest_translation.TRUNCATE_CONFIRM_ENV, "0")
        rc = ingest_translation.main(["--truncate"])
        assert rc == ingest_translation.EXIT_USER_ERROR


class TestMissingSourceGuard:
    def test_missing_source_returns_exit_3(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = ingest_translation.main(["--source", str(tmp_path / "nope")])
        assert rc == ingest_translation.EXIT_MISSING_DATA
        assert "does not exist" in capsys.readouterr().err

    def test_empty_source_dir_returns_exit_3(self, tmp_path: Path) -> None:
        rc = ingest_translation.main(["--source", str(tmp_path)])
        assert rc == ingest_translation.EXIT_MISSING_DATA


class TestRedaction:
    def test_password_redacted(self) -> None:
        out = ingest_translation._redact_database_url(
            "postgresql://user:secret@host:5432/db"
        )
        assert "secret" not in out
        assert "user:***@host" in out
