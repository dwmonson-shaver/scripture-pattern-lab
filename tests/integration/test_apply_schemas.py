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

EXPECTED_REGISTRY_TABLES = {
    "concepts": {
        "id",
        "name",
        "description",
        "origin",
        "verification_state",
        # Slice 1 authored display metadata (DEC-146).
        "authored_color",
        "authored_polarity",
        "authored_opposite_name",
    },
    "concept_lemmas": {
        "id",
        "concept_id",
        "lemma",
        "language",
        "confidence",
        "origin",
        "verification_state",
    },
    "polarity_claims": {
        "id",
        "concept_id",
        "polarity",
        "origin",
        "evidence_count",
        "verification_state",
        "confidence",
    },
    "inverse_claims": {
        "id",
        "concept_id",
        "inverse_concept_id",
        "origin",
        "evidence_count",
        "verification_state",
        "confidence",
    },
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


def _drop_registry_tables(engine) -> None:
    """Drop registry tables in dependency order so a fresh apply can re-create them."""
    with engine.begin() as connection:
        # inverse_claims and concept_lemmas FK concepts; polarity_claims FKs concepts.
        for table in (
            "inverse_claims",
            "polarity_claims",
            "concept_lemmas",
            "concepts",
        ):
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def test_apply_schemas_creates_registry_tables_on_fresh_db() -> None:
    """DROP the four registry tables, run apply, verify columns reflect."""
    engine = get_engine()
    _drop_registry_tables(engine)

    _run_apply_schemas()

    for table_name, expected_cols in EXPECTED_REGISTRY_TABLES.items():
        reflected = Table(table_name, MetaData(), autoload_with=engine)
        assert set(reflected.columns.keys()) == expected_cols, (
            f"{table_name} columns mismatch: got {set(reflected.columns.keys())}, "
            f"expected {expected_cols}"
        )


def test_concept_lemmas_confidence_defaults_to_null() -> None:
    """Inserting a concept_lemmas row without confidence must yield NULL — never 1.0
    (REQ:08.registry-epistemics invariant 2).
    """
    engine = get_engine()
    _run_apply_schemas()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM concept_lemmas"))
        connection.execute(text("DELETE FROM concepts"))
        concept_id = connection.execute(
            text("INSERT INTO concepts (name) VALUES ('test_concept') RETURNING id"),
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO concept_lemmas (concept_id, lemma, language) "
                "VALUES (:cid, 'πίστις', 'grc')"
            ),
            {"cid": concept_id},
        )
        confidence = connection.execute(
            text("SELECT confidence FROM concept_lemmas WHERE concept_id = :cid"),
            {"cid": concept_id},
        ).scalar_one()
        # cleanup
        connection.execute(text("DELETE FROM concept_lemmas"))
        connection.execute(text("DELETE FROM concepts"))
    assert confidence is None, "confidence must default to NULL, not 1.0"


def test_origin_and_verification_state_defaults() -> None:
    """Every registry row gets origin='curated' and verification_state='unverified'
    when not specified (REQ:08.registry-epistemics invariants 1 and 3).
    """
    engine = get_engine()
    _run_apply_schemas()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM inverse_claims"))
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concept_lemmas"))
        connection.execute(text("DELETE FROM concepts"))

        cid_a = connection.execute(
            text("INSERT INTO concepts (name) VALUES ('a') RETURNING id"),
        ).scalar_one()
        cid_b = connection.execute(
            text("INSERT INTO concepts (name) VALUES ('b') RETURNING id"),
        ).scalar_one()
        connection.execute(
            text("INSERT INTO concept_lemmas (concept_id, lemma) VALUES (:c, 'x')"),
            {"c": cid_a},
        )
        connection.execute(
            text("INSERT INTO polarity_claims (concept_id, polarity) VALUES (:c, '+')"),
            {"c": cid_a},
        )
        connection.execute(
            text(
                "INSERT INTO inverse_claims (concept_id, inverse_concept_id) "
                "VALUES (:a, :b)"
            ),
            {"a": cid_a, "b": cid_b},
        )

        for table in ("concepts", "concept_lemmas", "polarity_claims", "inverse_claims"):
            row = connection.execute(
                text(f"SELECT origin, verification_state FROM {table} LIMIT 1"),
            ).one()
            assert row.origin == "curated", f"{table}.origin default mismatch: {row.origin}"
            assert row.verification_state == "unverified", (
                f"{table}.verification_state default mismatch: {row.verification_state}"
            )

        # cleanup
        connection.execute(text("DELETE FROM inverse_claims"))
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concept_lemmas"))
        connection.execute(text("DELETE FROM concepts"))


def test_polarity_claims_unique_per_concept_pole() -> None:
    """UNIQUE (concept_id, polarity) — second insert of same pole must raise."""
    engine = get_engine()
    _run_apply_schemas()
    from sqlalchemy.exc import IntegrityError

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concepts"))
        cid = connection.execute(
            text("INSERT INTO concepts (name) VALUES ('uniqueness_test') RETURNING id"),
        ).scalar_one()
        connection.execute(
            text("INSERT INTO polarity_claims (concept_id, polarity) VALUES (:c, '+')"),
            {"c": cid},
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO polarity_claims (concept_id, polarity) "
                    "VALUES (:c, '+')"
                ),
                {"c": cid},
            )

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concepts"))


def test_inverse_claims_self_inverse_check_constraint() -> None:
    """CHECK (concept_id <> inverse_concept_id) — self-inverse must raise."""
    engine = get_engine()
    _run_apply_schemas()
    from sqlalchemy.exc import IntegrityError

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM inverse_claims"))
        connection.execute(text("DELETE FROM concepts"))
        cid = connection.execute(
            text("INSERT INTO concepts (name) VALUES ('self_inverse_test') RETURNING id"),
        ).scalar_one()

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO inverse_claims (concept_id, inverse_concept_id) "
                    "VALUES (:c, :c)"
                ),
                {"c": cid},
            )

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM concepts"))


# ---------------------------------------------------------------------------
# Domain CHECK constraints (closes Codex P2 from 2026-05-08 review)
# ---------------------------------------------------------------------------


def _seed_one_concept_for_checks(engine, name: str) -> int:
    """Create a single concepts row and return its id; used by the CHECK tests."""
    with engine.begin() as connection:
        return connection.execute(
            text(f"INSERT INTO concepts (name) VALUES ('{name}') RETURNING id"),
        ).scalar_one()


def test_origin_check_rejects_invalid_value() -> None:
    """origin must be in ('curated', 'ai_suggested', 'lexicon_imported')."""
    engine = get_engine()
    _run_apply_schemas()
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO concepts (name, origin) VALUES ('bad_origin', 'invented')"),
            )


def test_verification_state_check_rejects_invalid_value() -> None:
    """verification_state must be in
    ('unverified', 'corpus_observed', 'human_confirmed').
    """
    engine = get_engine()
    _run_apply_schemas()
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO concepts (name, verification_state) "
                    "VALUES ('bad_vstate', 'verified')"
                ),
            )


def test_polarity_check_rejects_invalid_value() -> None:
    """polarity_claims.polarity must be in ('+', '-', '±')."""
    engine = get_engine()
    _run_apply_schemas()
    from sqlalchemy.exc import IntegrityError

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concepts"))
    cid = _seed_one_concept_for_checks(engine, "polarity_check_test")

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO polarity_claims (concept_id, polarity) "
                    "VALUES (:c, '?')"
                ),
                {"c": cid},
            )

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM concepts"))


def test_evidence_count_check_rejects_negative_value() -> None:
    """polarity_claims.evidence_count must be >= 0; same for inverse_claims."""
    engine = get_engine()
    _run_apply_schemas()
    from sqlalchemy.exc import IntegrityError

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM polarity_claims"))
        connection.execute(text("DELETE FROM concepts"))
    cid = _seed_one_concept_for_checks(engine, "evidence_count_test")

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO polarity_claims (concept_id, polarity, evidence_count) "
                    "VALUES (:c, '+', -1)"
                ),
                {"c": cid},
            )

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM concepts"))


def test_confidence_check_rejects_out_of_range() -> None:
    """confidence must be NULL or in [0.0, 1.0] on every table that has it."""
    engine = get_engine()
    _run_apply_schemas()
    from sqlalchemy.exc import IntegrityError

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM concept_lemmas"))
        connection.execute(text("DELETE FROM concepts"))
    cid = _seed_one_concept_for_checks(engine, "confidence_test")

    # Above 1.0 — must fail.
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO concept_lemmas (concept_id, lemma, confidence) "
                    "VALUES (:c, 'x', 1.5)"
                ),
                {"c": cid},
            )

    # Below 0.0 — must fail.
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO concept_lemmas (concept_id, lemma, confidence) "
                    "VALUES (:c, 'y', -0.1)"
                ),
                {"c": cid},
            )

    # NULL — must succeed (DEC-024 default).
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO concept_lemmas (concept_id, lemma, confidence) "
                "VALUES (:c, 'z', NULL)"
            ),
            {"c": cid},
        )

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM concepts"))
