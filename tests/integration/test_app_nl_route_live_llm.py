"""Slice H exit-gate integration test for POST /api/v1/query/nl.

Live-LLM, live-DB end-to-end. Submits a natural-language research question,
asserts the LLM-backed translator compiles it to DSL, the DSL-pipeline
returns the flagship envelope, and the response surfaces the compiled DSL
in `query` plus translator metadata in `translation`.

Gated by BOTH `integration` and `live_llm` markers — needs DATABASE_URL
(for the corpus) AND ANTHROPIC_API_KEY (for the LLM call). Excluded by
default. Run with:

    pytest -m "live_llm" tests/integration/test_app_nl_route_live_llm.py

Network round-trips and tokens are real; this test should be run sparingly,
typically only when verifying the slice exit gate or the prompt template.

Test shape mirrors tests/integration/test_app_dsl_route.py so the same
corpus + registry preparation is reused.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_SCRIPT = REPO_ROOT / "scripts" / "db" / "ingest_corpus.py"
SEED_SCRIPT = REPO_ROOT / "scripts" / "db" / "seed_registry.py"


pytestmark = [pytest.mark.integration, pytest.mark.live_llm]


@pytest.fixture(scope="module")
def loaded_corpus_and_registry() -> Iterator[None]:
    """Run real ingest + seed scripts so the route sees a known corpus."""
    env = os.environ.copy()
    env["SPL_INGEST_CONFIRM_TRUNCATE"] = "1"
    env["SPL_REGISTRY_CONFIRM_TRUNCATE"] = "1"

    ingest = subprocess.run(
        [sys.executable, str(INGEST_SCRIPT), "--truncate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert ingest.returncode == 0, (
        f"ingest_corpus.py failed: stderr tail="
        f"{ingest.stderr.splitlines()[-15:]!r}"
    )

    seed = subprocess.run(
        [sys.executable, str(SEED_SCRIPT), "--truncate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert seed.returncode == 0, (
        f"seed_registry.py failed: stderr tail="
        f"{seed.stderr.splitlines()[-15:]!r}"
    )

    yield None


@pytest.fixture
def client(loaded_corpus_and_registry: None) -> Iterator[TestClient]:
    """Live TestClient with both DATABASE_URL and ANTHROPIC_API_KEY set."""
    _ = loaded_corpus_and_registry
    assert os.environ.get("DATABASE_URL"), (
        "DATABASE_URL must be set for the live-LLM integration suite"
    )
    assert os.environ.get("ANTHROPIC_API_KEY"), (
        "ANTHROPIC_API_KEY must be set for the live-LLM integration suite"
    )
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_nl_query_compiles_and_returns_flagship_envelope(
    client: TestClient,
) -> None:
    """Slice H exit gate: NL query for `faith → hope → love` round-trips.

    The flagship NL question must compile to DSL that hits the same two
    candidates at 1Cor 13:13 with the same baselines (483 / 84 / 259) +
    6 alternative orderings + summary ≤ 5 lines. Plus the response must
    surface the compiled DSL in `query` and the translator metadata in
    `translation`.
    """
    resp = client.post(
        "/api/v1/query/nl",
        json={"nl_query": "sequences where faith leads to hope which leads to love"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # The compiled DSL is surfaced — it's whatever the LLM emitted.
    assert body["query"], "compiled DSL must be non-empty"

    # Translator metadata block is populated.
    assert "translation" in body
    assert isinstance(body["translation"]["confidence"], (int, float))
    assert isinstance(body["translation"]["alternatives"], list)
    assert isinstance(body["translation"]["explanation"], str)

    # The downstream envelope mirrors Slice G's flagship invariants —
    # the LLM had better translate the obvious request to a faith→hope→love
    # sequence (or a near-equivalent that hits 1Cor 13:13).
    candidates = body["result"]["candidates"]
    assert len(candidates) == 2, (
        f"expected 2 candidates at 1Cor 13:13; got {len(candidates)}: "
        f"compiled DSL was {body['query']!r}; LLM explanation was "
        f"{body['translation']['explanation']!r}"
    )
    refs = {c["reference"] for c in candidates}
    assert refs == {"1Cor 13:13"}, (
        f"expected both candidates at 1Cor 13:13; got {refs}; "
        f"compiled DSL was {body['query']!r}"
    )

    # Contextualization invariants from Slice D + G.
    ctx = body["result"]["contextualization"]
    counts = {b["resolved_lemmas"][0] if b["resolved_lemmas"] else b["node_label"]: b["count"]
              for b in ctx["node_baselines"]}
    # The LLM's exact choice of concept names + capability hints can move
    # baselines between 'faith', 'hope', 'love' depending on whether it
    # used `concept:` or `lemma:` form — but the totals across the three
    # nodes should sum near 826 (483+84+259).
    total = sum(b["count"] for b in ctx["node_baselines"])
    assert 600 <= total <= 1000, (
        f"sum of node baselines outside expected range; got {total} "
        f"with breakdown {counts!r}"
    )

    # 6 alternative-orderings = 3! permutations of the three nodes.
    assert len(ctx["alternative_orderings"]) == 6
    assert ctx["null_distribution"] is None  # DEC-065

    # Explanation summary still ≤ 5 lines (Slice F invariant).
    summary = body["explanation"]["summary"]
    assert len([line for line in summary.split("\n") if line.strip()]) <= 5


def test_nl_query_for_unsupported_form_surfaces_alternatives(
    client: TestClient,
) -> None:
    """An ambiguous NL query should produce alternatives, not silent fabrication.

    The translator's explicit instruction is to surface ambiguity via the
    Alternatives field rather than pick one interpretation. This test
    verifies that on a deliberately vague question, the response either
    (a) populates `translation.alternatives` with at least one entry, OR
    (b) returns 422 nl_compile_error. Either is honest; silent
    confidence-1.0 single-DSL emission is the failure mode this checks.
    """
    resp = client.post(
        "/api/v1/query/nl",
        json={"nl_query": "what does the corpus actually say"},
    )
    # Either path is acceptable — both honestly surface uncertainty.
    if resp.status_code == 200:
        body = resp.json()
        # Confidence below 0.9 OR alternatives non-empty — the translator
        # signaled ambiguity rather than confidently emitting one DSL.
        confidence_low = body["translation"]["confidence"] < 0.9
        has_alternatives = len(body["translation"]["alternatives"]) > 0
        assert confidence_low or has_alternatives, (
            f"vague NL query produced overconfident single DSL: "
            f"compiled={body['query']!r}, confidence="
            f"{body['translation']['confidence']}, alternatives="
            f"{body['translation']['alternatives']}"
        )
    else:
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] in ("nl_compile_error", "parse_error")
