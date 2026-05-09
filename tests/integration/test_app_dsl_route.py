"""Slice G exit-gate integration test for POST /api/v1/query/dsl.

Spins up the FastAPI app via TestClient with a real Engine + ConceptRegistry
backed by DATABASE_URL. Issues a real HTTP request with the slice's flagship
DSL ``faith > hope > love`` and asserts the JSON envelope mirrors what
``scripts/query.py`` produces.

Mirrors the ingest+seed fixture pattern from test_query_cli.py so the corpus
is in a known state. Gated ``@pytest.mark.integration`` and excluded by
default; runs with ``pytest -m integration``.
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


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def loaded_corpus_and_registry() -> Iterator[None]:
    """Run real ingest + seed scripts so the route sees a known corpus state.

    Same shape as test_query_cli.py::loaded_corpus_and_registry.
    """
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
    """A live TestClient against a real DATABASE_URL-backed FastAPI app."""
    _ = loaded_corpus_and_registry
    assert os.environ.get("DATABASE_URL"), (
        "DATABASE_URL must be set for the integration suite"
    )
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health_route_against_live_app(client: TestClient) -> None:
    """Sanity check: the live app's /health endpoint works."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_query_dsl_returns_flagship_sequence_envelope(
    client: TestClient,
) -> None:
    """Slice G exit gate: POST /api/v1/query/dsl with the flagship sequence
    returns the expected envelope shape against the real corpus.

    Same observable claims as the CLI Slice F exit-gate test, restated
    over JSON-over-HTTP:
    - 200 status
    - 2 candidates at 1Cor 13:13 (the flagship pattern's only verse)
    - 3 node baselines with the documented counts (483 / 84 / 259)
    - 6 alternative-ordering permutations (3! for a 3-step sequence)
    - null_distribution serialized as JSON null (DEC-G8 compliance)
    - explanation.summary is a non-empty string with at most 5 lines
    """
    resp = client.post(
        "/api/v1/query/dsl",
        json={"dsl": "faith > hope > love"},
    )
    assert resp.status_code == 200, (
        f"expected 200, got {resp.status_code}; body={resp.text}"
    )
    body = resp.json()

    # --- Envelope shape ---
    assert body["query"] == "faith > hope > love"
    assert body["validation"]["status"] in ("supported", "partial")

    # --- Match candidates ---
    candidates = body["result"]["candidates"]
    assert len(candidates) == 2, (
        f"expected 2 candidates at 1Cor 13:13, got {len(candidates)}"
    )
    for c in candidates:
        assert c["reference"] == "1Cor 13:13"
        assert c["match_type"] == "conceptual"

    # --- Contextualization (Slice D + G) ---
    ctx = body["result"]["contextualization"]
    assert ctx is not None, "API consumers expect contextualize=True default"
    assert ctx["observed_count"] == len(candidates)

    baselines = ctx["node_baselines"]
    assert len(baselines) == 3
    by_value = {b["node_value"]: b for b in baselines}
    assert "faith" in by_value
    assert "hope" in by_value
    assert "love" in by_value
    assert by_value["faith"]["count"] == 483
    assert by_value["hope"]["count"] == 84
    assert by_value["love"]["count"] == 259

    # 3! = 6 alternative orderings; one is observed.
    alt_orderings = ctx["alternative_orderings"]
    assert len(alt_orderings) == 6
    observed_orderings = [a for a in alt_orderings if a["is_observed"]]
    assert len(observed_orderings) == 1
    assert observed_orderings[0]["sequence_label"] == "faith > hope > love"

    # DEC-G8: null_distribution emits as null (key present, value None).
    assert "null_distribution" in ctx
    assert ctx["null_distribution"] is None

    # --- Explanation (Slice F + G) ---
    exp = body["explanation"]
    summary = exp["summary"]
    assert isinstance(summary, str) and summary.strip(), (
        "explanation.summary must be a non-empty string"
    )
    line_count = len(summary.splitlines())
    assert line_count <= 5, (
        f"summary should be ≤ 5 lines per canonical-09 §9; got {line_count}"
    )
    # Per-candidate ExplainedResult entries should mirror the candidates list.
    assert len(exp["results"]) == len(candidates)


def test_query_dsl_parse_error_returns_422(client: TestClient) -> None:
    """Live route returns 422 + structured parse_error body for malformed DSL."""
    resp = client.post(
        "/api/v1/query/dsl",
        json={"dsl": "faith > > > love"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["error"] == "parse_error"
    assert "position" in body["detail"]["details"]


def test_query_dsl_validation_unsupported_returns_422(
    client: TestClient,
) -> None:
    """Live route returns 422 + validation_unsupported body for inverse()."""
    resp = client.post(
        "/api/v1/query/dsl",
        json={"dsl": "inverse(faith > hope)"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["error"] == "validation_unsupported"
    findings = body["detail"]["details"]["findings"]
    assert any(f["code"] == "UNSUPPORTED_INVERSE" for f in findings)


def test_query_dsl_concept_not_mapped_returns_422(client: TestClient) -> None:
    """Live route returns 422 + concept_not_mapped for an unseeded concept."""
    resp = client.post(
        "/api/v1/query/dsl",
        json={"dsl": "concept:zzznotreal > faith"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["error"] == "concept_not_mapped"
    assert body["detail"]["details"]["concept_name"] == "zzznotreal"
