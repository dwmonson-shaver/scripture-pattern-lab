#!/usr/bin/env python
"""Load one English (or future other-language) translation into Postgres.

Slice 1 (DEC-128/144). Thin orchestrator over ``src.ingestion.translations``:
reads per-book translation JSON from a directory (or a single file), maps book
names to BB codes, and streams verses through ``load_translation`` in one
transaction. KJV is the mandatory public-domain default; pass ``--code`` /
``--name`` / ``--license`` / ``--public-domain`` for other versions.

Exit codes:
    0   success
    1   uncaught exception — traceback printed to stderr
    2   user error — refused destructive op or non-empty without --truncate
    3   missing source file(s)

Two-factor destructive-op gate on ``--truncate``: the flag AND the env var
``SPL_TRANSLATION_CONFIRM_TRUNCATE=1`` are both required (mirrors the corpus,
registry, and lexicon ingests). Schema apply (``apply_schemas.sh``) is a
distinct prerequisite, NOT re-run here. CLI lives under ``scripts/`` per DEC-025.
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
from src.ingestion.translations.db import truncate_translations  # noqa: E402
from src.ingestion.translations.loader import (  # noqa: E402
    TranslationProgressCallback,
    TranslationProgressEvent,
    load_translation,
)
from src.ingestion.translations.parser import (  # noqa: E402
    parse_translation_directory,
    parse_translation_file,
)

DEFAULT_SOURCE: Path = Path("data/raw/translations/kjv")
TRUNCATE_CONFIRM_ENV: str = "SPL_TRANSLATION_CONFIRM_TRUNCATE"

EXIT_OK: int = 0
EXIT_UNCAUGHT: int = 1
EXIT_USER_ERROR: int = 2
EXIT_MISSING_DATA: int = 3


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ingest_translation.py",
        description="Load a verse-aligned English translation (default: KJV).",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=(
            "directory of per-book JSON files OR a single JSON file "
            f"(default: {DEFAULT_SOURCE})"
        ),
    )
    parser.add_argument("--code", default="kjv", help="version code (default: kjv)")
    parser.add_argument(
        "--name",
        default="King James Version",
        help="human-readable name (default: King James Version)",
    )
    parser.add_argument(
        "--license", default="Public Domain", help="license string"
    )
    parser.add_argument(
        "--public-domain",
        action="store_true",
        default=True,
        help="mark this translation public domain (default: true)",
    )
    parser.add_argument(
        "--not-public-domain",
        dest="public_domain",
        action="store_false",
        help="mark this translation NOT public domain",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help=(
            "TRUNCATE the translation tables before loading. "
            f"Also requires {TRUNCATE_CONFIRM_ENV}=1."
        ),
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


def _build_progress_printer(stream: TextIO) -> TranslationProgressCallback:
    def _print(event: TranslationProgressEvent) -> None:
        if event.kind == "registry":
            print("registry upserted", file=stream, flush=True)
        elif event.kind == "batch":
            print(
                f"batch verses_loaded={event.verses_loaded}",
                file=stream,
                flush=True,
            )
        else:
            print(f"done verses_loaded={event.verses_loaded}", file=stream, flush=True)

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

    source: Path = args.source
    if not source.exists():
        print(f"source guard failed: {source} does not exist", file=sys.stderr)
        return EXIT_MISSING_DATA
    if source.is_dir() and not any(source.glob("*.json")):
        print(
            f"source guard failed: no *.json files in {source}", file=sys.stderr
        )
        return EXIT_MISSING_DATA

    try:
        url = os.environ.get("DATABASE_URL")
        if url:
            print(f"DATABASE_URL={_redact_database_url(url)}", file=sys.stderr)

        engine = get_engine()

        with engine.connect() as connection:
            existing = connection.execute(
                text("SELECT count(*) FROM translation_verses")
            ).scalar_one()

        if existing > 0 and not args.truncate:
            print(
                f"refusing to load: translation_verses has {existing} rows; "
                f"pass --truncate (with {TRUNCATE_CONFIRM_ENV}=1) to wipe first.",
                file=sys.stderr,
            )
            return EXIT_USER_ERROR

        if args.truncate:
            truncate_translations(engine)

        if source.is_dir():
            verses = parse_translation_directory(source)
        else:
            verses = parse_translation_file(source)

        callback = _build_progress_printer(sys.stderr)
        count = load_translation(
            engine,
            code=args.code,
            name=args.name,
            license=args.license,
            is_public_domain=args.public_domain,
            verses=verses,
            progress_callback=callback,
        )
        print(
            f"loaded {count} verses for code={args.code!r}", file=sys.stderr
        )
        return EXIT_OK
    except Exception:
        traceback.print_exc()
        return EXIT_UNCAUGHT


if __name__ == "__main__":
    sys.exit(main())
