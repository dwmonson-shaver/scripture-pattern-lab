#!/usr/bin/env python
"""Load all 27 MorphGNT books into the ``tokens`` table.

Thin orchestrator over ``src.ingestion``: discovers MorphGNT files, validates
the destructive-op gate (``--truncate`` + ``SPL_INGEST_CONFIRM_TRUNCATE=1``),
streams ``parse_corpus_file`` output through ``load_tokens`` in BB order, and
prints one progress line per ``ProgressEvent`` to stderr. Exits 0 on success,
2 on user-error (refused destructive op, missing env confirm), 3 on
filename-map drift, 1 on uncaught exception.

CLI lives under ``scripts/`` per DEC-025 (no ``src/__main__``, no FastAPI
route). Sits next to ``scripts/db/apply_schemas.sh``; schema apply is a
distinct step and is NOT re-run by this script.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

# Make repo root importable when invoked as a script (``uv run scripts/db/...``).
# Pytest adds repo root via ``pythonpath = ["."]``; standalone CLI invocation does
# not, so bootstrap it here. Idempotent: sys.path entries are deduped on insert.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import text  # noqa: E402

from src.ingestion.corpus_parser import (  # noqa: E402
    _BOOK_NUMBER_BY_FILENAME,
    CorpusToken,
    parse_corpus_file,
)
from src.ingestion.db import get_engine, truncate_tokens  # noqa: E402
from src.ingestion.loader import ProgressCallback, ProgressEvent, load_tokens  # noqa: E402

DEFAULT_CORPUS_DIR: Path = Path("data/raw/morphgnt-sblgnt")
TRUNCATE_CONFIRM_ENV: str = "SPL_INGEST_CONFIRM_TRUNCATE"

EXIT_OK: int = 0
EXIT_UNCAUGHT: int = 1
EXIT_USER_ERROR: int = 2
EXIT_CORPUS_DRIFT: int = 3


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ingest_corpus.py",
        description="Load all 27 MorphGNT books into the tokens table.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help=(
            "TRUNCATE the tokens table before loading. "
            f"Also requires {TRUNCATE_CONFIRM_ENV}=1."
        ),
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=DEFAULT_CORPUS_DIR,
        help=f"directory of MorphGNT files (default: {DEFAULT_CORPUS_DIR})",
    )
    return parser.parse_args(argv)


def _redact_database_url(url: str) -> str:
    """Replace any ``user:password@`` segment in a DB URL with ``user:***@``.

    Preserves scheme, username, host, port, path. Returns the original string
    if there is no userinfo, no password, or the input is not URL-shaped.
    Uses ``rsplit('@', 1)`` so a literal ``@`` inside the password does not
    confuse host detection.
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


def _assert_27_files_present(directory: Path) -> None:
    """Strict guard for the production corpus directory.

    Raises RuntimeError if ``directory`` does not contain *exactly* the 27
    filenames in ``_BOOK_NUMBER_BY_FILENAME`` — neither missing nor extra.
    Catches MorphGNT renames and stray files in one pre-flight check before
    any DB work begins.
    """
    found = {p.name for p in directory.iterdir() if p.is_file()}
    expected = set(_BOOK_NUMBER_BY_FILENAME)
    if found == expected:
        return
    missing = sorted(expected - found)
    extras = sorted(found - expected)
    parts: list[str] = []
    if missing:
        parts.append(f"missing={missing}")
    if extras:
        parts.append(f"unexpected={extras}")
    raise RuntimeError(
        f"corpus directory {directory} filename drift: {'; '.join(parts)}"
    )


def _present_filenames_in_bb_order(directory: Path) -> list[str]:
    """Return mapped filenames present in ``directory``, sorted by BB code.

    Relaxed counterpart to ``_assert_27_files_present``: any subset of the 27
    mapped files is acceptable, but extras (filenames not in the book map)
    raise RuntimeError. An empty mapped subset also raises — the script has
    nothing to do otherwise.
    """
    found = {p.name for p in directory.iterdir() if p.is_file()}
    extras = sorted(found - set(_BOOK_NUMBER_BY_FILENAME))
    if extras:
        raise RuntimeError(
            f"corpus directory {directory} has files not in book map: {extras}"
        )
    mapped = found & set(_BOOK_NUMBER_BY_FILENAME)
    if not mapped:
        raise RuntimeError(
            f"corpus directory {directory} contains no mapped MorphGNT files"
        )
    return sorted(mapped, key=_BOOK_NUMBER_BY_FILENAME.__getitem__)


def _stream_files(directory: Path, filenames: list[str]) -> Iterator[CorpusToken]:
    """Stream ``parse_corpus_file`` across ``filenames`` in given order.

    Threads ``global_position`` across files exactly the way
    ``parse_corpus_directory`` does for the full 27-book set, but iterates an
    explicit filename list so a subset (e.g. the 2-book multi fixture) can be
    loaded via ``--corpus-dir`` without changing parser-side semantics.
    """
    global_position = 1
    for filename in filenames:
        path = directory / filename
        for token in parse_corpus_file(path, start_global_position=global_position):
            yield token
            global_position = token.global_position + 1


def _build_progress_printer(stream: TextIO) -> ProgressCallback:
    """Return a callback that writes one human-readable line per ProgressEvent.

    Format:
      ``file_boundary book=BB after=N`` — entered a new BB, N tokens already committed
      ``batch tokens_loaded=N``         — a 1000-row batch just flushed
      ``done tokens_loaded=N``          — transaction committed; final count
    """

    def _print(event: ProgressEvent) -> None:
        if event.kind == "file_boundary":
            print(
                f"file_boundary book={event.book} after={event.tokens_loaded}",
                file=stream,
                flush=True,
            )
        elif event.kind == "batch":
            print(f"batch tokens_loaded={event.tokens_loaded}", file=stream, flush=True)
        else:
            print(f"done tokens_loaded={event.tokens_loaded}", file=stream, flush=True)

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

    corpus_dir: Path = args.corpus_dir
    is_default = corpus_dir == DEFAULT_CORPUS_DIR
    try:
        if is_default:
            _assert_27_files_present(corpus_dir)
        filenames = _present_filenames_in_bb_order(corpus_dir)
    except (RuntimeError, FileNotFoundError, NotADirectoryError) as exc:
        print(f"corpus-dir guard failed: {exc}", file=sys.stderr)
        return EXIT_CORPUS_DRIFT

    try:
        url = os.environ.get("DATABASE_URL")
        if url:
            print(f"DATABASE_URL={_redact_database_url(url)}", file=sys.stderr)

        engine = get_engine()

        with engine.connect() as connection:
            existing = connection.execute(
                text("SELECT count(*) FROM tokens")
            ).scalar_one()

        if existing > 0 and not args.truncate:
            print(
                f"refusing to load: tokens table has {existing} rows; "
                "pass --truncate (with "
                f"{TRUNCATE_CONFIRM_ENV}=1) to wipe before loading.",
                file=sys.stderr,
            )
            return EXIT_USER_ERROR

        if args.truncate:
            truncate_tokens(engine)

        callback = _build_progress_printer(sys.stderr)
        inserted = load_tokens(
            engine,
            _stream_files(corpus_dir, filenames),
            progress_callback=callback,
        )
        print(f"inserted {inserted} tokens", file=sys.stderr)
        return EXIT_OK
    except Exception:
        traceback.print_exc()
        return EXIT_UNCAUGHT


if __name__ == "__main__":
    sys.exit(main())
