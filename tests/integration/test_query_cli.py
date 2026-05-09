"""Integration tests for ``scripts/query.py`` — the Slice C CLI exit point.

Mirrors ``test_corpus_ingest.py``'s subprocess pattern: invoke the script as
a real binary via ``subprocess.run`` and assert on stdout/stderr/returncode.

The module-scoped ``loaded_corpus_and_registry`` fixture runs the real
``ingest_corpus.py --truncate`` and ``seed_registry.py --truncate`` once so
the CLI tests below have a known corpus + registry state. The fixture
mirrors ``test_executor.py::loaded_full_corpus_with_registry`` exactly.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
QUERY_SCRIPT = REPO_ROOT / "scripts" / "query.py"
INGEST_SCRIPT = REPO_ROOT / "scripts" / "db" / "ingest_corpus.py"
SEED_SCRIPT = REPO_ROOT / "scripts" / "db" / "seed_registry.py"


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def loaded_corpus_and_registry() -> Iterator[None]:
    """Run real ingest + seed scripts so the CLI sees a known corpus + registry.

    Subprocess-style mirrors ``test_executor.py::loaded_full_corpus_with_registry``
    so the real CLI binaries are exercised, not in-process imports.
    """
    env = os.environ.copy()
    env["SPL_INGEST_CONFIRM_TRUNCATE"] = "1"
    env["SPL_REGISTRY_CONFIRM_TRUNCATE"] = "1"

    ingest = subprocess.run(
        [sys.executable, str(INGEST_SCRIPT), "--truncate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert ingest.returncode == 0, (
        f"ingest_corpus.py failed: stderr tail="
        f"{ingest.stderr.splitlines()[-15:]!r}"
    )

    seed = subprocess.run(
        [sys.executable, str(SEED_SCRIPT), "--truncate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert seed.returncode == 0, (
        f"seed_registry.py failed: stderr tail="
        f"{seed.stderr.splitlines()[-15:]!r}"
    )

    yield None


def _run_query(
    dsl: str,
    *,
    extra_args: list[str] | None = None,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke ``scripts/query.py`` as a subprocess, returning the result.

    Inherits the parent env (so ``DATABASE_URL`` is propagated) and lets
    callers override individual env vars (e.g. for the redaction test).
    """
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    args = [sys.executable, str(QUERY_SCRIPT), dsl, *(extra_args or [])]
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_runs_clean_supported_query(
    loaded_corpus_and_registry: None,
) -> None:
    """``faith > hope > love`` prints a 1Cor 13:13 candidate and exits 0."""
    _ = loaded_corpus_and_registry
    result = _run_query("faith > hope > love")
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )
    assert "1Cor 13:13" in result.stdout
    assert "Status: supported" in result.stdout
    assert "Grounding:" in result.stdout


def test_cli_partial_with_unsupported_expansion(
    loaded_corpus_and_registry: None,
) -> None:
    """A plan with ``=> forward:2`` is reduced to partial; CLI still exits 0."""
    _ = loaded_corpus_and_registry
    result = _run_query("lemma:πίστις > lemma:ἐλπίς > lemma:ἀγάπη => forward:2")
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )
    assert "Status: partial" in result.stdout
    # The reducer's partial-warning explanation should land on stderr.
    assert "partial" in result.stderr.lower()


def test_cli_unsupported_plan_exits_2(
    loaded_corpus_and_registry: None,
) -> None:
    """``inverse(...)`` is unsupported in v0.1; the CLI exits 2 with a reason."""
    _ = loaded_corpus_and_registry
    result = _run_query("inverse(faith > hope > love)")
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}; stdout={result.stdout!r}; "
        f"stderr={result.stderr!r}"
    )
    assert "unsupported" in result.stderr.lower()
    assert "UNSUPPORTED_INVERSE" in result.stderr


def test_cli_no_matches_exits_0(
    loaded_corpus_and_registry: None,
) -> None:
    """Plausible-but-unmatched lemmas return zero matches and exit 0."""
    _ = loaded_corpus_and_registry
    result = _run_query("lemma:zebra > lemma:elephant")
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )
    assert "Found 0 matches" in result.stdout


def test_cli_redacts_password_in_log_line(
    loaded_corpus_and_registry: None,
) -> None:
    """A password in DATABASE_URL must NOT appear in stdout or stderr.

    Uses an unreachable host so the script exits before any DB work, but
    verifies the startup log line redacted the password and that ``secret``
    appears nowhere in either stream.
    """
    _ = loaded_corpus_and_registry
    bogus = "postgresql://user:secret@nonexistent-host-for-redaction:5432/db"
    result = _run_query(
        "faith > hope > love",
        env_overrides={"DATABASE_URL": bogus},
    )
    combined = result.stdout + result.stderr
    assert "secret" not in combined, (
        f"password leaked into output: combined={combined!r}"
    )
    assert "user:***@nonexistent-host-for-redaction" in result.stderr


def test_cli_parse_error_exits_2(
    loaded_corpus_and_registry: None,
) -> None:
    """Bad DSL (``faith > >``) raises ParseError → exit 2 with position pointer."""
    _ = loaded_corpus_and_registry
    result = _run_query("faith > >")
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}; stderr={result.stderr!r}"
    )
    assert "parse error" in result.stderr.lower()
    # The caret pointer line is part of the position-aware error rendering.
    assert "^" in result.stderr


def test_cli_unknown_concept_exits_3(
    loaded_corpus_and_registry: None,
) -> None:
    """C-CLOSE-006: a concept absent from the seeded registry exits 3.

    Distinguishes "concept not in registry" from "concept in registry but
    no corpus matches" — the latter still exits 0 with zero matches.
    """
    _ = loaded_corpus_and_registry
    result = _run_query("concept:zzznotreal")
    assert result.returncode == 3, (
        f"expected exit 3, got {result.returncode}; stdout={result.stdout!r}; "
        f"stderr={result.stderr!r}"
    )
    assert "zzznotreal" in result.stderr
    assert "concept not mapped" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Slice D exit gate: contextualization rendering on the flagship sequence
# ---------------------------------------------------------------------------


def test_cli_renders_contextualization_for_flagship_sequence(
    loaded_corpus_and_registry: None,
) -> None:
    """Slice D exit gate: ``faith > hope > love`` shows the Contextualization block.

    Asserts the four canonical-09 §8 invariants surface in stdout:
    - per-node baselines for faith, hope, love (with resolved-lemma names)
    - alternative-ordering counts (3! = 6 for the 3-step sequence)
    - the observed ordering is marked
    - null-distribution slot is rendered as "not computed in MVP"
    """
    _ = loaded_corpus_and_registry
    result = _run_query("faith > hope > love")
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )
    out = result.stdout

    # Match section (unchanged from Slice C)
    assert "1Cor 13:13" in out
    assert "Status: supported" in out

    # Contextualization block (new in Slice D)
    assert "Contextualization (REQ:09.contextualization):" in out
    assert "Observed count:" in out
    assert "Constituent baselines" in out
    # All three constituent concepts surface their resolved-lemma counts
    assert "faith" in out
    assert "hope" in out
    assert "love" in out
    # Alt-orderings: 3! = 6, observed marked with *
    assert "Alternative orderings (6 total" in out
    assert "*  faith > hope > love" in out  # observed marker
    # Null-distribution slot is reserved but not computed
    assert "Null distribution: not computed in MVP" in out


def test_cli_renders_no_match_with_contextualization(
    loaded_corpus_and_registry: None,
) -> None:
    """Zero-match query still renders the contextualization envelope.

    A query whose lemmas exist (so the executor runs) but never co-occur
    yields 0 candidates. The CLI should still print baselines + an
    alt-orderings table — the calibration is informative even when the
    observed count is 0.
    """
    _ = loaded_corpus_and_registry
    result = _run_query("lemma:zebra > lemma:elephant")
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )
    out = result.stdout
    assert "Found 0 matches" in out
    assert "Contextualization (REQ:09.contextualization):" in out
    assert "Observed count: 0" in out
    # 2-step sequence yields 2! = 2 orderings
    assert "Alternative orderings (2 total" in out
