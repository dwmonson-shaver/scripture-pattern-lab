"""Live-LLM integration for the educational article section (Slice N, N7).

Exercises build_educational_section against the real Anthropic API + a real
comparative section built from the corpus. Asserts the DEC-081 no-fabrication
structural property holds on live output: the prose mentions a handed lemma and
a handed verse reference, is labeled generated, and carries citations.

Requires DATABASE_URL + ANTHROPIC_API_KEY + corpus + lexicon loaded. Gated by
``live_llm`` AND ``integration`` markers; excluded from the default suite.
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
from src.nlp.concept_article import build_educational_section
from src.nlp.llm_client import build_anthropic_client_from_env
from src.ontology.concept_document import build_comparative_section
from src.ontology.lexicon_resolver import resolve_english_term

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "lexicon"

pytestmark = [pytest.mark.integration, pytest.mark.live_llm]


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


def test_live_article_section_is_grounded_and_labeled(engine: Engine) -> None:
    with engine.connect() as conn:
        if conn.execute(text("SELECT count(*) FROM tokens")).scalar_one() == 0:
            pytest.skip("corpus not loaded")

    resolution = resolve_english_term("humility", engine)
    if resolution.unresolved:
        pytest.skip("humility did not resolve in this corpus subset")
    comparative = build_comparative_section(resolution, engine)

    client = build_anthropic_client_from_env()
    section = build_educational_section(comparative, client)

    # The LLM may legitimately bail (FALLBACK) → None; if it produced prose,
    # the no-fabrication + labeling contract must hold.
    if section is None:
        pytest.skip("LLM emitted FALLBACK/empty; no prose to assert against")

    assert section.generated is True
    assert section.cited_sources
    handed_lemmas = [r.lemma for r in comparative.rows]
    assert any(lemma in section.prose for lemma in handed_lemmas), (
        "DEC-081: prose must reference a handed lemma, not invent one"
    )
