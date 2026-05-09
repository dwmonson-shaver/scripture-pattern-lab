"""Integration tests for ``scripts/db/seed_registry.py`` — Slice C Track 1 exit gate.

Phase 6 of registry-epistemics. Asserts that the canonical 20 concepts and
~30 lemma mappings load cleanly, that **every seeded row carries
``verification_state='unverified'`` and ``origin='curated'``** (the
corpus-is-ground-truth invariant — DEC-024), and that the destructive-op
gate refuses without the ``SPL_REGISTRY_CONFIRM_TRUNCATE=1`` env var.

Mirrors the subprocess pattern used by
``tests/integration/test_corpus_ingest.py`` so the script is exercised as a
real binary, not as an in-process call.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ontology.registry import ConceptRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = REPO_ROOT / "scripts" / "db" / "seed_registry.py"
SEED_DIR = REPO_ROOT / "data" / "seeds" / "registry"

CONCEPTS_CSV = SEED_DIR / "concepts.csv"
CONCEPT_LEMMAS_CSV = SEED_DIR / "concept_lemmas.csv"
POLARITY_CLAIMS_CSV = SEED_DIR / "polarity_claims.csv"
INVERSE_CLAIMS_CSV = SEED_DIR / "inverse_claims.csv"

REGISTRY_TABLES: tuple[str, ...] = (
    "concepts",
    "concept_lemmas",
    "polarity_claims",
    "inverse_claims",
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _csv_row_count(path: Path) -> int:
    """Return the number of data rows in a header-bearing CSV."""
    with path.open(encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def _wipe_registry(engine: Engine) -> None:
    """Delete every registry row in FK-safe order. Mirrors
    ``tests/integration/test_concept_registry_reader.py::_wipe_registry``."""
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM inverse_claims"))
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concept_lemmas"))
        connection.execute(text("DELETE FROM concepts"))


def _run_seed_script(
    args: list[str], extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Invoke ``scripts/db/seed_registry.py`` from repo root with parent env.

    Mirrors ``tests/integration/test_corpus_ingest.py::_run_ingest_script``.
    Optional ``extra_env`` is merged on top of the parent env so individual
    tests can set ``SPL_REGISTRY_CONFIRM_TRUNCATE=1`` without affecting the
    other tests in the module.
    """
    import os

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(SEED_SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.fixture
def clean_engine() -> Iterator[Engine]:
    """Yield an engine bound to a wiped registry; wipe again on teardown.

    Tests that seed the registry should depend on this fixture so each test
    starts from a clean slate (no contamination from a sibling test that
    pre-populated the tables).
    """
    engine = get_engine()
    _wipe_registry(engine)
    try:
        yield engine
    finally:
        _wipe_registry(engine)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_seed_runs_clean(clean_engine: Engine) -> None:
    """Running the script against a wiped registry exits 0 and prints a summary."""
    _ = clean_engine
    result = _run_seed_script([])
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )
    # Summary line shape: ``seeded N concepts, M lemmas, P polarity claims, Q inverse claims``
    assert "seeded" in result.stderr
    assert "concepts" in result.stderr
    assert "lemmas" in result.stderr
    assert "polarity claims" in result.stderr
    assert "inverse claims" in result.stderr


def test_seed_row_counts(clean_engine: Engine) -> None:
    """After seed, each table's row count matches the corresponding CSV."""
    result = _run_seed_script([])
    assert result.returncode == 0, result.stderr

    expected_concepts = _csv_row_count(CONCEPTS_CSV)
    expected_lemmas = _csv_row_count(CONCEPT_LEMMAS_CSV)
    expected_polarity = _csv_row_count(POLARITY_CLAIMS_CSV)
    expected_inverse = _csv_row_count(INVERSE_CLAIMS_CSV)

    # Slice C target: 20 concepts.
    assert expected_concepts == 20, (
        f"concepts.csv drifted from canonical-08 target of 20: "
        f"got {expected_concepts}"
    )

    with clean_engine.connect() as connection:
        n_concepts = connection.execute(
            text("SELECT count(*) FROM concepts")
        ).scalar_one()
        n_lemmas = connection.execute(
            text("SELECT count(*) FROM concept_lemmas")
        ).scalar_one()
        n_polarity = connection.execute(
            text("SELECT count(*) FROM polarity_claims")
        ).scalar_one()
        n_inverse = connection.execute(
            text("SELECT count(*) FROM inverse_claims")
        ).scalar_one()

    assert n_concepts == expected_concepts
    assert n_lemmas == expected_lemmas
    assert n_polarity == expected_polarity
    assert n_inverse == expected_inverse


def test_corpus_is_ground_truth_invariant(clean_engine: Engine) -> None:
    """TRACK 1 EXIT GATE: every seeded row has verification_state='unverified'.

    DEC-024: registry entries are provisional priors, NOT corpus-confirmed
    facts. Nothing in the seed flips to 'corpus_observed' or 'human_confirmed'
    — those transitions are downstream slice work.
    """
    result = _run_seed_script([])
    assert result.returncode == 0, result.stderr

    with clean_engine.connect() as connection:
        for table in REGISTRY_TABLES:
            states = set(
                connection.execute(
                    text(f"SELECT DISTINCT verification_state FROM {table}")
                ).scalars()
            )
            assert states == {"unverified"}, (
                f"{table}.verification_state invariant violated: got {states}; "
                "every seeded row must be 'unverified' (DEC-024)."
            )


def test_origin_is_curated_for_all_seed_rows(clean_engine: Engine) -> None:
    """Every seeded row has origin='curated' (REQ:08.registry-epistemics inv. 1)."""
    result = _run_seed_script([])
    assert result.returncode == 0, result.stderr

    with clean_engine.connect() as connection:
        for table in REGISTRY_TABLES:
            origins = set(
                connection.execute(
                    text(f"SELECT DISTINCT origin FROM {table}")
                ).scalars()
            )
            assert origins == {"curated"}, (
                f"{table}.origin invariant violated: got {origins}; "
                "every seeded row must be 'curated'."
            )


def test_concept_lemmas_confidence_is_null(clean_engine: Engine) -> None:
    """confidence defaults to NULL — never 1.0 (REQ:08.registry-epistemics inv. 2)."""
    result = _run_seed_script([])
    assert result.returncode == 0, result.stderr

    with clean_engine.connect() as connection:
        non_null = connection.execute(
            text("SELECT count(*) FROM concept_lemmas WHERE confidence IS NOT NULL")
        ).scalar_one()
    assert non_null == 0, (
        f"confidence invariant violated: {non_null} concept_lemmas rows have "
        "non-NULL confidence; seed must leave confidence NULL."
    )


def test_seed_is_reproducible_via_truncate(clean_engine: Engine) -> None:
    """Re-running with --truncate produces the same row counts every time.

    The seed is a deterministic function of the CSVs, so ``truncate + reseed``
    must yield identical row counts on every run. (Re-running *without*
    ``--truncate`` against a non-empty registry is rejected by the
    non-emptiness gate — see ``test_seed_refuses_when_nonempty_without_truncate``;
    that contract was tightened in response to the 2026-05-08 Codex P1 finding.)
    """
    first = _run_seed_script(
        ["--truncate"], extra_env={"SPL_REGISTRY_CONFIRM_TRUNCATE": "1"}
    )
    assert first.returncode == 0, first.stderr

    with clean_engine.connect() as connection:
        before = {
            table: connection.execute(
                text(f"SELECT count(*) FROM {table}")
            ).scalar_one()
            for table in REGISTRY_TABLES
        }

    second = _run_seed_script(
        ["--truncate"], extra_env={"SPL_REGISTRY_CONFIRM_TRUNCATE": "1"}
    )
    assert second.returncode == 0, (
        f"second seed run failed: rc={second.returncode} stderr={second.stderr!r}"
    )

    with clean_engine.connect() as connection:
        after = {
            table: connection.execute(
                text(f"SELECT count(*) FROM {table}")
            ).scalar_one()
            for table in REGISTRY_TABLES
        }

    assert before == after, (
        f"row counts changed across truncate+reseed runs: before={before}, after={after}"
    )


def test_seed_refuses_without_env_confirm_truncate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--truncate alone is not enough; SPL_REGISTRY_CONFIRM_TRUNCATE=1 is also required.

    The env-confirm check runs before any DB access, so this test does not
    need the ``clean_engine`` fixture. Mirrors
    ``tests/integration/test_corpus_ingest.py::test_script_truncate_requires_env_confirm``.
    """
    monkeypatch.delenv("SPL_REGISTRY_CONFIRM_TRUNCATE", raising=False)
    result = _run_seed_script(["--truncate"])
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}; stderr={result.stderr!r}"
    )
    assert "SPL_REGISTRY_CONFIRM_TRUNCATE" in result.stderr


def test_seed_refuses_when_nonempty_without_truncate(clean_engine: Engine) -> None:
    """If concepts is pre-populated with foreign content, the script refuses to load.

    Insert a single placeholder concept (count != 20, so the script's
    idempotency probe knows the existing rows are not its own seed) and run
    without --truncate. Expect exit 2 with a refusal message.
    """
    with clean_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO concepts (name) VALUES ('foreign_concept')")
        )
    result = _run_seed_script([])
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}; stderr={result.stderr!r}"
    )
    assert "concepts" in result.stderr.lower()
    assert "--truncate" in result.stderr


def test_seed_truncate_with_env_confirm_succeeds(clean_engine: Engine) -> None:
    """--truncate + SPL_REGISTRY_CONFIRM_TRUNCATE=1 wipes and reseeds cleanly.

    Pre-populate concepts with a foreign row, run with both factors set, and
    verify the foreign row is gone and the canonical seed is in place.
    """
    with clean_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO concepts (name) VALUES ('foreign_concept')")
        )

    result = _run_seed_script(
        ["--truncate"], extra_env={"SPL_REGISTRY_CONFIRM_TRUNCATE": "1"}
    )
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )

    with clean_engine.connect() as connection:
        n_concepts = connection.execute(
            text("SELECT count(*) FROM concepts")
        ).scalar_one()
        foreign = connection.execute(
            text("SELECT count(*) FROM concepts WHERE name = 'foreign_concept'")
        ).scalar_one()
    assert n_concepts == _csv_row_count(CONCEPTS_CSV)
    assert foreign == 0, "TRUNCATE must have removed the foreign row"


def test_end_to_end_reader_returns_seeded_concept(clean_engine: Engine) -> None:
    """ConceptRegistry.get_by_lemma('πίστις') returns the seeded faith concept.

    Closes the loop: seed script writes via Table mirrors → reader queries via
    Table mirrors → Pydantic Concept comes back with verification_state='unverified'.
    """
    result = _run_seed_script([])
    assert result.returncode == 0, result.stderr

    registry = ConceptRegistry(clean_engine)
    matches = registry.get_by_lemma("πίστις", "grc")

    assert len(matches) == 1, (
        f"expected one Concept for πίστις, got {len(matches)}: {matches!r}"
    )
    concept = matches[0]
    assert concept.name == "faith"
    assert concept.verification_state == "unverified"
    assert concept.origin == "curated"
