"""Integration tests for the English→lemma resolver (Slice N, Phase N3).

Requires a live Postgres via DATABASE_URL with 01_tokens.sql + 03_lexicon.sql
applied AND the corpus loaded (the resolver's corpus-presence filter needs real
tokens). Loads the small lexicon fixtures, then resolves known terms. Gated by
``@pytest.mark.integration``.
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
from src.ontology.lexicon_resolver import (
    corpus_verse_refs_for_lemma,
    resolve_english_term,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "lexicon"

pytestmark = pytest.mark.integration


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = get_engine()
    truncate_lexicon(eng)
    load_lexicon(
        eng,
        lemma_strongs=parse_jtauber_mappings(FIXTURES / "jtauber-sample.yaml"),
        tbesg_glosses=parse_tbesg(FIXTURES / "tbesg-sample.txt"),
        dodson_glosses=parse_dodson(FIXTURES / "dodson-sample.tsv"),
    )
    yield eng
    truncate_lexicon(eng)


def _has_corpus(engine: Engine) -> bool:
    with engine.connect() as conn:
        return conn.execute(text("SELECT count(*) FROM tokens")).scalar_one() > 0


def test_humility_resolves_to_corpus_present_lemma(engine: Engine) -> None:
    if not _has_corpus(engine):
        pytest.skip("corpus not loaded; resolver corpus-presence filter needs tokens")
    res = resolve_english_term("humility", engine)
    assert not res.unresolved
    lemmas = {r.lemma for r in res.resolved_lemmas}
    assert "ταπεινοφροσύνη" in lemmas
    hit = next(r for r in res.resolved_lemmas if r.lemma == "ταπεινοφροσύνη")
    assert "G5012" in hit.strongs
    assert hit.corpus_token_count > 0


def test_nonsense_term_is_unresolved(engine: Engine) -> None:
    res = resolve_english_term("zxqwlbblitzkrieg", engine)
    assert res.unresolved


def test_corpus_absent_lemma_is_dropped(engine: Engine) -> None:
    # A gloss like "Aaron" bridges to Ἀαρών (G0002). If that lemma is absent
    # from the loaded corpus subset, the resolver must drop it (cannot query).
    if not _has_corpus(engine):
        pytest.skip("corpus not loaded")
    res = resolve_english_term("Aaron", engine)
    for rl in res.resolved_lemmas:
        assert rl.corpus_token_count > 0  # no zero-count lemmas leak through


def test_verse_refs_for_resolved_lemma(engine: Engine) -> None:
    if not _has_corpus(engine):
        pytest.skip("corpus not loaded")
    res = resolve_english_term("faith", engine)
    if res.unresolved:
        pytest.skip("faith did not resolve in this corpus subset")
    lemma = res.resolved_lemmas[0].lemma
    refs = corpus_verse_refs_for_lemma(lemma, engine)
    assert refs  # at least one citation
    assert all(isinstance(b, str) and c > 0 and v > 0 for (b, c, v) in refs)
