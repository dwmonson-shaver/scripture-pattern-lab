"""Integration tests for lexicon ingestion (Slice N, Phase N2).

Requires a live Postgres via DATABASE_URL with 03_lexicon.sql applied (run
``bash scripts/db/apply_schemas.sh``). Gated by ``@pytest.mark.integration``;
excluded from the default suite. Loads the small committed fixtures (not the
full vendored datasets) so the test is fast and deterministic.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from src.ingestion.db import get_engine
from src.ingestion.lexicon.datasets import (
    parse_dodson,
    parse_jtauber_mappings,
    parse_tbesg,
)
from src.ingestion.lexicon.db import truncate_lexicon
from src.ingestion.lexicon.loader import load_lexicon

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "lexicon"

pytestmark = pytest.mark.integration


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = get_engine()
    truncate_lexicon(eng)
    yield eng
    truncate_lexicon(eng)


def _load_fixtures(engine: Engine) -> dict[str, int]:
    return load_lexicon(
        engine,
        lemma_strongs=parse_jtauber_mappings(FIXTURES / "jtauber-sample.yaml"),
        tbesg_glosses=parse_tbesg(FIXTURES / "tbesg-sample.txt"),
        dodson_glosses=parse_dodson(FIXTURES / "dodson-sample.tsv"),
    )


def test_load_inserts_rows(engine: Engine) -> None:
    counts = _load_fixtures(engine)
    assert counts["lemma_strongs"] > 0
    assert counts["strongs_glosses"] > 0
    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM lemma_strongs")
        ).scalar_one() == counts["lemma_strongs"]


def test_bridge_row_for_humility_present(engine: Engine) -> None:
    _load_fixtures(engine)
    with engine.connect() as conn:
        strongs = conn.execute(
            text(
                "SELECT strongs FROM lemma_strongs "
                "WHERE morphgnt_lemma = :l"
            ),
            {"l": "ταπεινοφροσύνη"},
        ).scalar_one()
    assert strongs == "G5012"


def test_both_gloss_sources_land(engine: Engine) -> None:
    _load_fixtures(engine)
    with engine.connect() as conn:
        sources = set(
            conn.execute(
                text("SELECT DISTINCT source FROM strongs_glosses")
            ).scalars()
        )
    assert sources == {"tbesg", "dodson"}


def test_reload_is_idempotent_via_on_conflict(engine: Engine) -> None:
    _load_fixtures(engine)
    with engine.connect() as conn:
        first = conn.execute(text("SELECT count(*) FROM strongs_glosses")).scalar_one()
    # Re-load WITHOUT truncate — ON CONFLICT DO NOTHING means no growth.
    _load_fixtures(engine)
    with engine.connect() as conn:
        second = conn.execute(text("SELECT count(*) FROM strongs_glosses")).scalar_one()
    assert first == second
