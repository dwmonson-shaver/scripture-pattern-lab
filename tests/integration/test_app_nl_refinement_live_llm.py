"""Slice M exit-gate twin (M5) — LIVE-LLM two-round refinement.

Live-LLM, live-DB end-to-end counterpart to
tests/unit/test_app_nl_refinement.py. Submits an ambiguous cross-verse
proximity NL query with NO window size, asserts the real Anthropic-backed
translator emits a clarification, then resubmits carrying the prior turns
plus a window-size answer and asserts the pipeline reaches an EXECUTED
envelope with non-empty candidates (DEC-098 stateless echo-back; DEC-099
same route, no server conversation state).

Gated by BOTH `integration` and `live_llm` markers — needs DATABASE_URL
(for the corpus) AND ANTHROPIC_API_KEY (for the LLM call). Excluded by
default. Run with:

    pytest -m "live_llm" tests/integration/test_app_nl_refinement_live_llm.py

Network round-trips and tokens are real; run sparingly, typically only when
verifying the slice exit gate or the prompt template.

Test shape mirrors tests/integration/test_app_nl_route_live_llm.py so the
same corpus + registry preparation is reused.
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


# An ambiguous cross-verse proximity query with NO window size — the case the
# translator must NOT silently default (Slice L / DEC-097); it should emit a
# clarification asking for the window.
_AMBIGUOUS_QUERY = "passages where faith and love appear near each other"

# The window-size answer the caller resubmits in round 2. 20 is at/below the
# MVP window_max_tokens=50, so the resolved DSL is runnable (WINDOW_EXCEEDS_MAX
# would otherwise reject it).
_WINDOW_ANSWER = "use a window of 20 tokens"


def test_two_round_refinement_reaches_executed_result(
    client: TestClient,
) -> None:
    """Slice M exit gate (live): ambiguous → clarification → answered → executed.

    Round 1 asserts the real translator returns a clarification (no window
    given). Round 2 carries the prior turns + a window answer and asserts the
    pipeline reaches a normal executed envelope with non-empty candidates.
    """
    # -- Round 1: ambiguous query, no prior_turns -----------------------
    first = client.post(
        "/api/v1/query/nl",
        json={"nl_query": _AMBIGUOUS_QUERY},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()

    # The translator must ask for the window rather than silently defaulting.
    assert first_body["clarification"] is not None, (
        f"round 1 expected a clarification for an ambiguous proximity query; "
        f"got body={first_body!r}"
    )
    question = first_body["clarification"]["question"]
    assert question, "clarification question must be non-empty"
    assert first_body["clarification"]["nl_source"] == _AMBIGUOUS_QUERY
    # Clarification path: the four pipeline fields are absent.
    assert first_body["validation"] is None
    assert first_body["result"] is None
    assert first_body["explanation"] is None
    assert first_body["translation"] is None

    # -- Round 2: resubmit carrying prior_turns + a window answer -------
    resp = client.post(
        "/api/v1/query/nl",
        json={
            "nl_query": _WINDOW_ANSWER,
            "prior_turns": [
                {"role": "user", "content": _AMBIGUOUS_QUERY},
                {"role": "assistant", "content": question},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Executed path: clarification gone, all four pipeline fields present.
    assert body["clarification"] is None, (
        f"round 2 should have executed, not re-clarified; got "
        f"clarification={body['clarification']!r}, compiled query="
        f"{body.get('query')!r}"
    )
    assert body["validation"] is not None
    assert body["result"] is not None
    assert body["explanation"] is not None
    assert body["translation"] is not None

    # The compiled DSL is surfaced (whatever the LLM emitted from the answered
    # conversation) and the engine returned real candidates.
    assert body["query"], "compiled DSL must be non-empty on the executed path"
    candidates = body["result"]["candidates"]
    assert len(candidates) > 0, (
        f"round 2 produced an executed envelope with NO candidates; "
        f"compiled DSL was {body['query']!r}, translator explanation was "
        f"{body['translation']['explanation']!r}"
    )
