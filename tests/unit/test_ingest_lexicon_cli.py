"""Unit tests for scripts/db/ingest_lexicon.py pre-DB gate paths (Slice N, N2).

Only the gate branches that return BEFORE opening a DB connection are unit-
tested here (the --truncate env gate and the missing-file guard). The live
load + non-empty refuse-without-truncate behavior is in
tests/integration/test_lexicon_ingest.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_CLI_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "db" / "ingest_lexicon.py"
)
_spec = importlib.util.spec_from_file_location("ingest_lexicon", _CLI_PATH)
assert _spec is not None and _spec.loader is not None
ingest_lexicon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ingest_lexicon)


class TestTruncateGate:
    def test_truncate_without_env_confirm_refuses(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv(ingest_lexicon.TRUNCATE_CONFIRM_ENV, raising=False)
        rc = ingest_lexicon.main(["--truncate"])
        assert rc == ingest_lexicon.EXIT_USER_ERROR
        assert "must be set" in capsys.readouterr().err

    def test_truncate_with_wrong_env_value_refuses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ingest_lexicon.TRUNCATE_CONFIRM_ENV, "0")
        rc = ingest_lexicon.main(["--truncate"])
        assert rc == ingest_lexicon.EXIT_USER_ERROR


class TestMissingFileGuard:
    def test_missing_dataset_dir_returns_exit_3(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = ingest_lexicon.main(["--lexicon-dir", str(tmp_path / "nope")])
        assert rc == ingest_lexicon.EXIT_MISSING_DATA
        assert "missing lexicon dataset file" in capsys.readouterr().err

    def test_partial_dataset_dir_returns_exit_3(self, tmp_path: Path) -> None:
        # Only one of three files present → still exit 3.
        (tmp_path / ingest_lexicon.JTAUBER_FILE).write_text("x:\n  strongs: 1\n")
        rc = ingest_lexicon.main(["--lexicon-dir", str(tmp_path)])
        assert rc == ingest_lexicon.EXIT_MISSING_DATA


class TestRedaction:
    def test_password_redacted(self) -> None:
        out = ingest_lexicon._redact_database_url(
            "postgresql://user:secret@host:5432/db"
        )
        assert "secret" not in out
        assert "user:***@host" in out
