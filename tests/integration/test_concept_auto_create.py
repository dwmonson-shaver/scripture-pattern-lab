"""Slice N exit gate: the dead-end killer, end-to-end (Phase N5/N8).

A query for a term NOT in the seeded registry but resolvable to corpus-present
lemmas auto-creates a machine/lexicon-sourced unverified concept, re-runs, and
surfaces an inline note; the concept now exists with origin='lexicon_imported';
and a persisted Conceptual Document (deterministic comparative Part 1 §1) is
retrievable. A truly-unresolvable term still raises ConceptNotMapped (422).

Requires a live Postgres via DATABASE_URL with all four schemas applied AND the
corpus + lexicon loaded (run apply_schemas.sh, ingest_corpus.py, ingest_lexicon.py).
Gated by ``@pytest.mark.integration``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from src.app.orchestration import run_dsl_query
from src.engine.models import ConceptNotMapped
from src.ingestion.db import get_engine
from src.ingestion.lexicon.datasets import (
    parse_dodson,
    parse_jtauber_mappings,
    parse_tbesg,
)
from src.ingestion.lexicon.db import truncate_lexicon
from src.ingestion.lexicon.loader import load_lexicon
from src.ontology.concept_document import get_document
from src.ontology.registry import ConceptRegistry

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "lexicon"

pytestmark = pytest.mark.integration

_TERM = "humility"  # not seeded; ταπεινοφροσύνη is in the corpus


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
    _drop_concept(eng, _TERM)
    yield eng
    _drop_concept(eng, _TERM)
    truncate_lexicon(eng)


def _drop_concept(engine: Engine, name: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM concepts WHERE name = :n"), {"n": name})


def _corpus_loaded(engine: Engine) -> bool:
    with engine.connect() as conn:
        return conn.execute(text("SELECT count(*) FROM tokens")).scalar_one() > 0


def test_exit_gate_unmapped_term_auto_creates_and_runs(engine: Engine) -> None:
    if not _corpus_loaded(engine):
        pytest.skip("corpus not loaded; exit gate needs real tokens")
    registry = ConceptRegistry(engine)

    response = run_dsl_query(f"concept:{_TERM}", engine, registry)

    # The 422 dead-end is gone: the query executed and carries the inline note.
    assert response.auto_created_concept is not None
    note = response.auto_created_concept
    assert note.concept_name == _TERM
    assert "ταπεινοφροσύνη" in note.lemmas
    assert note.document_available is True

    # The concept now exists as a machine/lexicon-sourced unverified prior.
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT origin, verification_state FROM concepts WHERE name = :n"
            ),
            {"n": _TERM},
        ).one()
    assert row.origin == "lexicon_imported"
    assert row.verification_state == "unverified"

    # The persisted Conceptual Document is retrievable; Part 1 §1 is present,
    # Part 1 §2 (LLM) is absent on the deterministic path, Part 2 is empty.
    document = get_document(_TERM, engine)
    assert document is not None
    assert document.part1_comparative.english_term == _TERM
    assert any(
        r.lemma == "ταπεινοφροσύνη" for r in document.part1_comparative.rows
    )
    assert document.part1_educational is None
    assert document.part2_grouping is None
    assert document.part2_grouping_pointer is None


def test_unresolvable_term_still_dead_ends(engine: Engine) -> None:
    registry = ConceptRegistry(engine)
    with pytest.raises(ConceptNotMapped):
        run_dsl_query("concept:zzqwlbblitzkrieg", engine, registry)
