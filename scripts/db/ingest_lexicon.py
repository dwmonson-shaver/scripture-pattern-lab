#!/usr/bin/env python
"""Load the three self-hosted lexicon datasets into Postgres (Slice N, DEC-103).

Thin orchestrator over ``src.ingestion.lexicon``: reads the jtauber lemma↔Strong's
bridge, the STEPBible TBESG glosses, and the Dodson glosses from a directory of
vendored dataset files, streams them through ``load_lexicon`` in one transaction,
and prints one progress line per ``LexiconProgressEvent`` to stderr. One-time
wholesale ingest (mirrors ``scripts/db/ingest_corpus.py`` and
``scripts/db/seed_registry.py``).

Exit codes:
    0   success
    1   uncaught exception — traceback printed to stderr
    2   user error — refused destructive op or non-empty without --truncate
    3   missing dataset file(s)

Two-factor destructive-op gate on ``--truncate``: the flag AND the env var
``SPL_LEXICON_CONFIRM_TRUNCATE=1`` are both required.

CLI lives under ``scripts/`` per DEC-025 (no ``src/__main__``, no FastAPI route).
Schema apply (``apply_schemas.sh``) is a distinct prerequisite step, NOT re-run here.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path
from typing import TextIO

# Make repo root importable when invoked as a script. Idempotent.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import text  # noqa: E402

from src.ingestion.db import get_engine  # noqa: E402
from src.ingestion.lexicon.datasets import (  # noqa: E402
    parse_dodson,
    parse_jtauber_mappings,
    parse_tbesg,
)
from src.ingestion.lexicon.db import truncate_lexicon  # noqa: E402
from src.ingestion.lexicon.loader import (  # noqa: E402
    LexiconProgressCallback,
    LexiconProgressEvent,
    load_lexicon,
)

DEFAULT_LEXICON_DIR: Path = Path("data/raw/lexicon")
JTAUBER_FILE: str = "jtauber-lexemes.yaml"
TBESG_FILE: str = "TBESG.txt"
DODSON_FILE: str = "dodson.tsv"
TRUNCATE_CONFIRM_ENV: str = "SPL_LEXICON_CONFIRM_TRUNCATE"

EXIT_OK: int = 0
EXIT_UNCAUGHT: int = 1
EXIT_USER_ERROR: int = 2
EXIT_MISSING_DATA: int = 3


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ingest_lexicon.py",
        description="Load the jtauber + TBESG + Dodson lexicon datasets.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help=(
            "TRUNCATE the lexicon tables before loading. "
            f"Also requires {TRUNCATE_CONFIRM_ENV}=1."
        ),
    )
    parser.add_argument(
        "--lexicon-dir",
        type=Path,
        default=DEFAULT_LEXICON_DIR,
        help=f"directory of vendored dataset files (default: {DEFAULT_LEXICON_DIR})",
    )
    return parser.parse_args(argv)


def _redact_database_url(url: str) -> str:
    """Replace any ``user:password@`` segment in a DB URL with ``user:***@``."""
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


def _require_dataset_files(lexicon_dir: Path) -> dict[str, Path]:
    """Confirm the three dataset files exist; return a name→path map.

    Raises FileNotFoundError if any are missing — caller maps to EXIT_MISSING_DATA.
    """
    paths = {
        JTAUBER_FILE: lexicon_dir / JTAUBER_FILE,
        TBESG_FILE: lexicon_dir / TBESG_FILE,
        DODSON_FILE: lexicon_dir / DODSON_FILE,
    }
    missing = [str(p) for p in paths.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"missing lexicon dataset file(s): {missing}")
    return paths


def _build_progress_printer(stream: TextIO) -> LexiconProgressCallback:
    """Return a callback writing one human-readable line per event."""

    def _print(event: LexiconProgressEvent) -> None:
        if event.kind == "dataset_boundary":
            print(f"dataset_boundary dataset={event.dataset}", file=stream, flush=True)
        elif event.kind == "batch":
            print(
                f"batch dataset={event.dataset} rows_loaded={event.rows_loaded}",
                file=stream,
                flush=True,
            )
        else:
            print(f"done rows_loaded={event.rows_loaded}", file=stream, flush=True)

    return _print


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

    lexicon_dir: Path = args.lexicon_dir
    try:
        paths = _require_dataset_files(lexicon_dir)
    except FileNotFoundError as exc:
        print(f"lexicon-dir guard failed: {exc}", file=sys.stderr)
        return EXIT_MISSING_DATA

    try:
        url = os.environ.get("DATABASE_URL")
        if url:
            print(f"DATABASE_URL={_redact_database_url(url)}", file=sys.stderr)

        engine = get_engine()

        with engine.connect() as connection:
            existing = connection.execute(
                text("SELECT count(*) FROM lemma_strongs")
            ).scalar_one()

        if existing > 0 and not args.truncate:
            print(
                f"refusing to load: lemma_strongs table has {existing} rows; "
                f"pass --truncate (with {TRUNCATE_CONFIRM_ENV}=1) to wipe "
                "before loading.",
                file=sys.stderr,
            )
            return EXIT_USER_ERROR

        if args.truncate:
            truncate_lexicon(engine)

        callback = _build_progress_printer(sys.stderr)
        counts = load_lexicon(
            engine,
            lemma_strongs=parse_jtauber_mappings(paths[JTAUBER_FILE]),
            tbesg_glosses=parse_tbesg(paths[TBESG_FILE]),
            dodson_glosses=parse_dodson(paths[DODSON_FILE]),
            progress_callback=callback,
        )
        print(
            f"loaded {counts['lemma_strongs']} lemma_strongs rows, "
            f"{counts['strongs_glosses']} strongs_glosses rows",
            file=sys.stderr,
        )
        return EXIT_OK
    except Exception:
        traceback.print_exc()
        return EXIT_UNCAUGHT


if __name__ == "__main__":
    sys.exit(main())
