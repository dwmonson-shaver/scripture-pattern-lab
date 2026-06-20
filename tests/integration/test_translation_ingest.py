"""Integration tests for the translation ingest path (Slice 1, DEC-128/144).

DATABASE_URL-gated (pytest -m integration). Applies the translation schema,
loads a small KJV-shape payload, and asserts a known verse round-trips with the
right BB code. Requires data/schemas/06_translations.sql applied.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import text

from src.ingestion.db import get_engine
from src.ingestion.translations.db import truncate_translations
from src.ingestion.translations.loader import load_translation
from src.ingestion.translations.parser import parse_translation_file

pytestmark = pytest.mark.integration


def test_kjv_chapter_round_trips(tmp_path: Path) -> None:
    engine = get_engine()
    truncate_translations(engine)

    path = tmp_path / "Romans.json"
    path.write_text(
        json.dumps(
            {
                "book": "Romans",
                "chapters": [
                    {
                        "chapter": "8",
                        "verses": [
                            {"verse": "24", "text": "For we are saved by hope:"},
                            {"verse": "25", "text": "But if we hope for that we see not"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    count = load_translation(
        engine,
        code="kjv",
        name="King James Version",
        license="Public Domain",
        is_public_domain=True,
        verses=parse_translation_file(path),
    )
    assert count == 2

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT tv.text FROM translation_verses tv "
                "JOIN translations t ON t.id = tv.translation_id "
                "WHERE t.code = 'kjv' AND tv.book = '06' "
                "AND tv.chapter = 8 AND tv.verse = 24"
            )
        ).scalar_one()
    assert row == "For we are saved by hope:"


def test_reload_is_idempotent(tmp_path: Path) -> None:
    engine = get_engine()
    truncate_translations(engine)
    path = tmp_path / "John.json"
    path.write_text(
        json.dumps(
            {
                "book": "John",
                "chapters": [
                    {"chapter": "3", "verses": [{"verse": "16", "text": "God so loved"}]}
                ],
            }
        ),
        encoding="utf-8",
    )
    load_translation(
        engine,
        code="kjv",
        name="King James Version",
        license="Public Domain",
        is_public_domain=True,
        verses=parse_translation_file(path),
    )
    # Re-run: ON CONFLICT DO NOTHING keeps the row count at 1.
    load_translation(
        engine,
        code="kjv",
        name="King James Version",
        license="Public Domain",
        is_public_domain=True,
        verses=parse_translation_file(path),
    )
    with engine.connect() as connection:
        n = connection.execute(
            text("SELECT count(*) FROM translation_verses")
        ).scalar_one()
    assert n == 1
