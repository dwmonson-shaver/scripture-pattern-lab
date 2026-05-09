#!/usr/bin/env python
"""Seed the concept registry with canonical-08's minimum viable concept set.

Realizes Phase 6 of Slice C Track 1 (registry epistemics) per
``thoughts/structure-registry-epistemics-2026-05-08.md`` and
``REQ:08.registry-epistemics`` in ``docs/canonical/08_mvp-corpus-scope.md``.

Reads four CSV files under ``data/seeds/registry/`` and inserts them into the
four registry tables in a single ``engine.begin()`` transaction (DEC-044).
Every row lands ``origin='curated'``, ``verification_state='unverified'``,
``confidence=NULL`` (where applicable). Nothing here flips to
``corpus_observed`` or ``human_confirmed`` — those transitions are downstream
slice work (DEC-024: corpus is ground truth; registry entries are provisional
priors).

Per DEC-025 (ingestion-side discipline), this script imports only the
``Table`` mirrors from ``src.ontology.registry``; it does NOT import the
``ConceptRegistry`` reader (that is a query-side construct).

Re-run idempotency: without ``--truncate`` the script refuses if ``concepts``
is non-empty (exit 2); ``INSERT ... ON CONFLICT DO NOTHING`` on the UNIQUE
constraints means re-running after a partial load is a clean no-op.

Two-factor destructive-op gate on ``--truncate``: the flag AND the env var
``SPL_REGISTRY_CONFIRM_TRUNCATE=1`` are both required. Mirrors
``scripts/db/ingest_corpus.py``.

Exit codes:
    0   success — ``seeded N concepts, M lemmas, P polarity claims, Q inverse claims``
    1   uncaught exception — traceback printed to stderr
    2   user error — refused destructive op (gate failed) or non-empty without --truncate
    3   missing seed CSV file
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import traceback
from pathlib import Path

# Make repo root importable when invoked as a script (``uv run scripts/db/...``).
# Pytest adds repo root via ``pythonpath = ["."]``; standalone CLI invocation
# does not, so bootstrap it here. Idempotent: sys.path entries are deduped on
# insert.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from src.ingestion.db import get_engine  # noqa: E402
from src.ontology.registry import (  # noqa: E402
    concept_lemmas_table,
    concepts_table,
    inverse_claims_table,
    polarity_claims_table,
)

DEFAULT_SEED_DIR: Path = Path("data/seeds/registry")
TRUNCATE_CONFIRM_ENV: str = "SPL_REGISTRY_CONFIRM_TRUNCATE"

CONCEPTS_CSV: str = "concepts.csv"
CONCEPT_LEMMAS_CSV: str = "concept_lemmas.csv"
POLARITY_CLAIMS_CSV: str = "polarity_claims.csv"
INVERSE_CLAIMS_CSV: str = "inverse_claims.csv"

EXIT_OK: int = 0
EXIT_UNCAUGHT: int = 1
EXIT_USER_ERROR: int = 2
EXIT_MISSING_SEED: int = 3


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="seed_registry.py",
        description=(
            "Seed the concept registry tables with the canonical 20 concepts "
            "and ~30 lemma mappings from data/seeds/registry/."
        ),
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help=(
            "TRUNCATE the four registry tables before loading. "
            f"Also requires {TRUNCATE_CONFIRM_ENV}=1."
        ),
    )
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=DEFAULT_SEED_DIR,
        help=f"directory of seed CSV files (default: {DEFAULT_SEED_DIR})",
    )
    return parser.parse_args(argv)


def _redact_database_url(url: str) -> str:
    """Replace any ``user:password@`` segment in a DB URL with ``user:***@``.

    Preserves scheme, username, host, port, path. Returns the original string
    if there is no userinfo, no password, or the input is not URL-shaped.
    Uses ``rsplit('@', 1)`` so a literal ``@`` inside the password does not
    confuse host detection. Mirrors ``scripts/db/ingest_corpus.py``.
    """
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    userinfo, host_part = rest.rsplit("@", 1)
    if ":" not in userinfo:
        return url
    user, _password = userinfo.split(":", 1)
    return f"{scheme}://{user}:***@{host_part}"


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV into a list of row dicts; strips leading/trailing whitespace."""
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [{k: (v.strip() if v is not None else v) for k, v in row.items()} for row in reader]


def _require_seed_files(seed_dir: Path) -> dict[str, Path]:
    """Confirm all four seed CSVs exist; return a name -> path map.

    Raises FileNotFoundError if any are missing — caller maps to EXIT_MISSING_SEED.
    """
    paths = {
        CONCEPTS_CSV: seed_dir / CONCEPTS_CSV,
        CONCEPT_LEMMAS_CSV: seed_dir / CONCEPT_LEMMAS_CSV,
        POLARITY_CLAIMS_CSV: seed_dir / POLARITY_CLAIMS_CSV,
        INVERSE_CLAIMS_CSV: seed_dir / INVERSE_CLAIMS_CSV,
    }
    missing = [str(p) for p in paths.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"missing seed CSV file(s): {missing}")
    return paths


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns process exit code; never raises on user error."""
    args = _parse_args(argv)

    if args.truncate and os.environ.get(TRUNCATE_CONFIRM_ENV) != "1":
        print(
            f"--truncate refused: {TRUNCATE_CONFIRM_ENV}=1 must be set "
            "to confirm a destructive wipe.",
            file=sys.stderr,
        )
        return EXIT_USER_ERROR

    seed_dir: Path = args.seed_dir
    try:
        seed_paths = _require_seed_files(seed_dir)
    except FileNotFoundError as exc:
        print(f"seed-dir guard failed: {exc}", file=sys.stderr)
        return EXIT_MISSING_SEED

    try:
        url = os.environ.get("DATABASE_URL")
        if url:
            print(f"DATABASE_URL={_redact_database_url(url)}", file=sys.stderr)

        # Read all four CSVs up front so a malformed seed file fails before
        # we open a transaction.
        concepts_rows = _read_csv(seed_paths[CONCEPTS_CSV])
        concept_lemmas_rows = _read_csv(seed_paths[CONCEPT_LEMMAS_CSV])
        polarity_claims_rows = _read_csv(seed_paths[POLARITY_CLAIMS_CSV])
        inverse_claims_rows = _read_csv(seed_paths[INVERSE_CLAIMS_CSV])

        engine = get_engine()

        # Pre-flight gate: refuse to load against a non-empty registry without
        # an explicit --truncate. Strict non-emptiness check — matches the
        # corpus-ingest gate exactly. Closes Codex P1 (2026-05-08): a
        # row-count-equals-CSV-count predicate would let a foreign registry
        # with the same row count slip through and get its concepts attached
        # to seed-named rows via ON CONFLICT DO NOTHING.
        with engine.connect() as connection:
            existing = connection.execute(
                text("SELECT count(*) FROM concepts")
            ).scalar_one()

        if existing > 0 and not args.truncate:
            print(
                f"refusing to load: concepts table has {existing} rows; "
                f"pass --truncate (with {TRUNCATE_CONFIRM_ENV}=1) "
                "to wipe before loading.",
                file=sys.stderr,
            )
            return EXIT_USER_ERROR

        with engine.begin() as connection:
            if args.truncate:
                # FK-safe single TRUNCATE with CASCADE; RESTART IDENTITY so
                # autoincrement IDs reset across runs.
                connection.execute(
                    text(
                        "TRUNCATE TABLE concepts, concept_lemmas, "
                        "polarity_claims, inverse_claims "
                        "RESTART IDENTITY CASCADE"
                    )
                )

            # ---- concepts -------------------------------------------------
            for row in concepts_rows:
                connection.execute(
                    pg_insert(concepts_table)
                    .values(
                        name=row["name"],
                        description=row.get("description") or None,
                        origin="curated",
                        verification_state="unverified",
                    )
                    .on_conflict_do_nothing(index_elements=["name"])
                )

            # Build name -> id map from current DB state (covers both fresh
            # inserts and idempotent re-runs where rows already exist).
            name_to_id: dict[str, int] = dict(
                connection.execute(
                    select(concepts_table.c.name, concepts_table.c.id)
                ).all()
            )

            # ---- concept_lemmas ------------------------------------------
            for row in concept_lemmas_rows:
                concept_id = name_to_id.get(row["concept_name"])
                if concept_id is None:
                    raise RuntimeError(
                        f"concept_lemmas.csv references unknown concept "
                        f"name={row['concept_name']!r}"
                    )
                connection.execute(
                    pg_insert(concept_lemmas_table)
                    .values(
                        concept_id=concept_id,
                        lemma=row["lemma"],
                        language=row.get("language") or "grc",
                        confidence=None,
                        origin="curated",
                        verification_state="unverified",
                    )
                    .on_conflict_do_nothing(
                        index_elements=["lemma", "language", "concept_id"]
                    )
                )

            # ---- polarity_claims -----------------------------------------
            for row in polarity_claims_rows:
                concept_id = name_to_id.get(row["concept_name"])
                if concept_id is None:
                    raise RuntimeError(
                        f"polarity_claims.csv references unknown concept "
                        f"name={row['concept_name']!r}"
                    )
                connection.execute(
                    pg_insert(polarity_claims_table)
                    .values(
                        concept_id=concept_id,
                        polarity=row["polarity"],
                        origin="curated",
                        evidence_count=0,
                        verification_state="unverified",
                        confidence=None,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["concept_id", "polarity"]
                    )
                )

            # ---- inverse_claims ------------------------------------------
            for row in inverse_claims_rows:
                concept_id = name_to_id.get(row["concept_name"])
                inverse_id = name_to_id.get(row["inverse_concept_name"])
                if concept_id is None or inverse_id is None:
                    raise RuntimeError(
                        f"inverse_claims.csv references unknown concept "
                        f"name={row['concept_name']!r} or "
                        f"{row['inverse_concept_name']!r}"
                    )
                connection.execute(
                    pg_insert(inverse_claims_table)
                    .values(
                        concept_id=concept_id,
                        inverse_concept_id=inverse_id,
                        origin="curated",
                        evidence_count=0,
                        verification_state="unverified",
                        confidence=None,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["concept_id", "inverse_concept_id"]
                    )
                )

            # Final counts for the summary line.
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

        print(
            f"seeded {n_concepts} concepts, {n_lemmas} lemmas, "
            f"{n_polarity} polarity claims, {n_inverse} inverse claims",
            file=sys.stderr,
        )
        return EXIT_OK
    except Exception:
        traceback.print_exc()
        return EXIT_UNCAUGHT


if __name__ == "__main__":
    sys.exit(main())
