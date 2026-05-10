"""Slice I exit-gate integration test for the three new endpoints.

Spins up the FastAPI app via TestClient with a real Engine + ConceptRegistry
backed by DATABASE_URL. Issues real HTTP requests to:
- GET /api/v1/capabilities
- GET /api/v1/concepts
- POST /api/v1/query/validate

Mirrors the ingest+seed fixture pattern from test_app_dsl_route.py so the
corpus is in a known state. Gated `@pytest.mark.integration`; runs with
`pytest -m integration`.
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
    """Run real ingest + seed scripts so the route sees a known corpus state."""
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
    _ = loaded_corpus_and_registry
    assert os.environ.get("DATABASE_URL"), (
        "DATABASE_URL must be set for the integration suite"
    )
    app = create_app()
    with TestClient(app) as c:
        yield c


# -- /api/v1/capabilities -----------------------------------------------


def test_capabilities_returns_mvp_registry(client: TestClient) -> None:
    """Slice I exit gate (1/3): capabilities endpoint round-trip.

    Asserts the live route returns the same MVP registry contents that
    `CapabilityRegistry.mvp()` produces in-process.
    """
    resp = client.get("/api/v1/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "0.1"
    assert body["polarity_support"] is True
    assert body["inverse_support"] is False
    assert body["max_sequence_length"] == 10
    assert body["corpora"] == ["nt"]
    assert body["languages"] == ["grc"]
    assert "lemma" in body["node_types"]
    assert "concept" in body["node_types"]


# -- /api/v1/concepts ---------------------------------------------------


def test_concepts_returns_seeded_registry(client: TestClient) -> None:
    """Slice I exit gate (2/3): concepts endpoint round-trip against seeded DB.

    Asserts the response carries at least the three flagship concepts
    (faith, hope, love) with verification_state populated and lemma
    lists non-empty.
    """
    resp = client.get("/api/v1/concepts")
    assert resp.status_code == 200
    body = resp.json()
    assert "concepts" in body
    names = {c["name"] for c in body["concepts"]}
    assert {"faith", "hope", "love"}.issubset(names), (
        f"expected faith/hope/love in concepts; got {sorted(names)}"
    )
    faith = next(c for c in body["concepts"] if c["name"] == "faith")
    assert faith["verification_state"] == "unverified"  # seed default
    assert faith["lemma_count"] == len(faith["lemmas"])
    assert faith["lemma_count"] >= 1, (
        f"faith has no lemmas in the live registry: {faith}"
    )
    # Greek lemma for faith — at least one of these should appear.
    assert any(
        lemma in {"πίστις", "πιστεύω"} for lemma in faith["lemmas"]
    ), f"expected πίστις or πιστεύω in faith.lemmas; got {faith['lemmas']}"


# -- /api/v1/query/validate ---------------------------------------------


def test_validate_supported_dsl_returns_200(client: TestClient) -> None:
    """Slice I exit gate (3/3 happy path): validate happy path on live registry.

    Real `faith > hope > love` DSL parses + validates against the seeded
    concept registry. Returns 200 with status=supported.
    """
    resp = client.post(
        "/api/v1/query/validate",
        json={"dsl": "faith > hope > love"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["query"] == "faith > hope > love"
    assert body["validation"]["status"] in ("supported", "partial")
    # No `result` or `explanation` — validate-only path.
    assert "result" not in body
    assert "explanation" not in body


def test_validate_parse_error_returns_422(client: TestClient) -> None:
    """Slice I exit gate (3/3 sad path 1): malformed DSL → 422 parse_error."""
    resp = client.post(
        "/api/v1/query/validate",
        json={"dsl": "faith > > > hope"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["error"] == "parse_error"
    assert "position" in body["detail"]["details"]


def test_validate_unsupported_returns_200_not_422(client: TestClient) -> None:
    """Slice I exit gate (3/3 sad path 2 — DEC-079 live regression guard).

    Inverse() is parseable but rejected by the validator (inverse_support=False
    in MVP). DEC-079 contract: this is a 200 response with
    body.validation.status='unsupported', NEVER a 422.
    """
    resp = client.post(
        "/api/v1/query/validate",
        json={"dsl": "inverse(faith)"},
    )
    assert resp.status_code == 200, (
        f"DEC-079 live regression: unsupported must be 200, not {resp.status_code}. "
        f"body={resp.text}"
    )
    body = resp.json()
    assert body["validation"]["status"] == "unsupported"
    assert any(
        f["code"] == "UNSUPPORTED_INVERSE"
        for f in body["validation"]["findings"]
    )
