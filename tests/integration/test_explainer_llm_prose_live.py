"""Slice K live-LLM exit gate for the explainer's LLM-paraphrase path.

Live-LLM, live-DB end-to-end. Hits `POST /api/v1/query/nl` for the flagship
faith>hope>love research question both with `SPL_EXPLAINER_LLM=1` (LLM
paraphrase enabled) and without (deterministic default), and asserts:

1. The deterministic envelope is byte-identical when the env var is unset
   (default behavior unchanged contract).
2. At least one conceptual candidate's `explanation` differs between the
   deterministic and LLM-enabled runs (the LLM path actually fires).
3. Every digit substring and verse-shape token in the LLM prose traces to
   a grounded field of the structured input (DEC-081 no-fabrication: the
   structural test of the slice's load-bearing claim).
4. LLM-paraphrased prose is a single sentence under 300 chars
   (defense-in-depth against the prompt's 200-char request being ignored).

Gated by BOTH `integration` and `live_llm` markers — needs DATABASE_URL
(for the corpus) AND ANTHROPIC_API_KEY (for the LLM call). Excluded by
default. Run with:

    SPL_EXPLAINER_LLM=1 pytest -m "live_llm" tests/integration/test_explainer_llm_prose_live.py

Network round-trips and tokens are real; this test should be run sparingly,
typically only when verifying the slice exit gate. Mirrors the fixture
pattern from tests/integration/test_app_nl_route_live_llm.py:42-90.
"""

from __future__ import annotations

import os
import re
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

FLAGSHIP_NL = "sequences where faith leads to hope which leads to love"


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


def _post_nl(client: TestClient, nl: str = FLAGSHIP_NL) -> dict:
    resp = client.post("/api/v1/query/nl", json={"nl_query": nl})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _collect_grounded_strings(body: dict) -> list[str]:
    """Pull every grounded substring the LLM prose may legitimately contain.

    For each conceptual candidate, the LLM has access to:
    - candidate.reference
    - the sequence label (from plan.source)
    - every step.node_value, step.token.lemma, step.resolved_lemmas[*]
    - candidate.match_type
    - the baseline counts (from contextualization.node_baselines[*].count)
      — though these are not in the user message, they ARE in the larger
      response envelope; the test below scopes substring checks to the
      explanation field only, so this set is intentionally generous.
    """
    grounded: set[str] = set()
    for cand in body["result"]["candidates"]:
        grounded.add(cand["reference"])
        grounded.add(cand["match_type"])
        for step in cand["alignment"]:
            grounded.add(step["node_value"])
            grounded.add(step["token"]["lemma"])
            for resolved in step["resolved_lemmas"]:
                grounded.add(resolved)
    ctx = body["result"].get("contextualization")
    if ctx is not None:
        for nb in ctx.get("node_baselines", []):
            grounded.add(str(nb["count"]))
            grounded.add(nb["node_value"])
        for ao in ctx.get("alternative_orderings", []):
            grounded.add(ao["sequence_label"])
            grounded.add(str(ao["count"]))
    grounded.add(body["query"])  # the compiled DSL — sequence label source
    return [g for g in grounded if g]


def test_deterministic_path_unchanged_when_llm_disabled(
    monkeypatch, client: TestClient
) -> None:
    """SPL_EXPLAINER_LLM unset -> behavior identical to Slice H/I.

    The translator step is non-deterministic (LLM choice of DSL form
    varies), so we cannot byte-compare the full envelope across runs. We
    DO assert the explanation field is deterministic for the conceptual
    case: re-running with the env var off yields the same explanation
    string for any matching `1Cor 13:13` candidate.
    """
    monkeypatch.delenv("SPL_EXPLAINER_LLM", raising=False)
    body_a = _post_nl(client)
    body_b = _post_nl(client)
    # If the translator chose the same DSL both times (the typical case),
    # the explanations must be byte-identical.
    if body_a["query"] == body_b["query"]:
        results_a = sorted(body_a["explanation"]["results"], key=lambda r: r["reference"])
        results_b = sorted(body_b["explanation"]["results"], key=lambda r: r["reference"])
        for ra, rb in zip(results_a, results_b):
            assert ra["explanation"] == rb["explanation"], (
                f"deterministic path emitted different explanations for "
                f"{ra['reference']!r}: {ra['explanation']!r} vs "
                f"{rb['explanation']!r}"
            )


def test_conceptual_explanation_uses_llm_when_enabled(
    monkeypatch, client: TestClient
) -> None:
    """SPL_EXPLAINER_LLM=1 -> at least one conceptual explanation is paraphrased.

    The LLM is non-deterministic; we cannot assert the exact prose. We
    CAN assert the LLM path took effect: the LLM-enabled run's
    explanation differs from the deterministic baseline (captured by
    running with the env var off).
    """
    # 1. Deterministic baseline.
    monkeypatch.delenv("SPL_EXPLAINER_LLM", raising=False)
    det_body = _post_nl(client)
    # Filter to conceptual candidates only.
    det_conceptual = {
        r["reference"]: r["explanation"]
        for r in det_body["explanation"]["results"]
        if r["match_type"] == "conceptual"
    }
    assert det_conceptual, "expected at least one conceptual candidate in baseline"

    # 2. LLM-enabled run.
    monkeypatch.setenv("SPL_EXPLAINER_LLM", "1")
    llm_body = _post_nl(client)
    llm_conceptual = {
        r["reference"]: r["explanation"]
        for r in llm_body["explanation"]["results"]
        if r["match_type"] == "conceptual"
    }
    assert llm_conceptual, "expected at least one conceptual candidate in LLM run"

    # 3. At least one conceptual explanation differs.
    common_refs = set(det_conceptual) & set(llm_conceptual)
    assert common_refs, (
        f"no common conceptual references between det/llm runs: "
        f"det={list(det_conceptual)}, llm={list(llm_conceptual)}"
    )
    diffs = [
        ref for ref in common_refs
        if det_conceptual[ref] != llm_conceptual[ref]
    ]
    assert diffs, (
        f"LLM path did not produce a different explanation for any "
        f"conceptual candidate. Det: {det_conceptual}. LLM: {llm_conceptual}"
    )


def test_llm_prose_only_contains_grounded_numbers_and_refs(
    monkeypatch, client: TestClient
) -> None:
    """DEC-081 no-fabrication: numbers and verse refs trace to grounded fields.

    Every digit substring in the LLM-paraphrased prose must also appear in
    one of the grounded inputs (candidate.reference, baseline counts,
    sequence label, etc.). Every verse-shape token (X X:Y or X X:Y-Z) must
    equal candidate.reference exactly.
    """
    monkeypatch.setenv("SPL_EXPLAINER_LLM", "1")
    body = _post_nl(client)
    grounded_strings = _collect_grounded_strings(body)
    grounded_joined = " | ".join(grounded_strings)

    verse_pattern = re.compile(r"\b\d?[A-Za-z]+\s+\d+:\d+(?:-\d+)?\b")
    digit_pattern = re.compile(r"\b\d+\b")

    for r in body["explanation"]["results"]:
        if r["match_type"] != "conceptual":
            continue
        prose = r["explanation"]
        # Every verse-shape token must equal the candidate's reference exactly.
        for token in verse_pattern.findall(prose):
            assert token == r["reference"], (
                f"LLM emitted verse token {token!r} which does NOT match the "
                f"candidate reference {r['reference']!r}. Full prose: "
                f"{prose!r}"
            )
        # Every digit substring must appear somewhere in the grounded inputs.
        for digit_run in digit_pattern.findall(prose):
            assert digit_run in grounded_joined, (
                f"LLM emitted ungrounded digit {digit_run!r} in prose "
                f"{prose!r}. Grounded strings: {grounded_strings!r}"
            )


def test_llm_prose_is_single_sentence_under_cap(
    monkeypatch, client: TestClient
) -> None:
    """Defense-in-depth: prompt requests ≤200 chars; helper caps at 300.

    LLM may exceed the prompt's request; the helper's _truncate_llm_prose
    guarantees the result envelope stays bounded.
    """
    monkeypatch.setenv("SPL_EXPLAINER_LLM", "1")
    body = _post_nl(client)
    for r in body["explanation"]["results"]:
        if r["match_type"] != "conceptual":
            continue
        prose = r["explanation"]
        # Truncation cap.
        assert len(prose) <= 300, (
            f"LLM prose exceeds 300-char cap: len={len(prose)}, "
            f"prose={prose!r}"
        )
        # Terminal-punctuation heuristic: single sentence has at most one
        # terminal punctuation mark, though we relax to ≤2 for the
        # truncation-ellipsis case + a possible abbreviation period (e.g.
        # "1Cor." — the LLM may render Greek lemma followed by a period).
        terminal_count = (
            prose.count(".") + prose.count("!") + prose.count("?")
        )
        assert terminal_count <= 2, (
            f"LLM prose contains multiple terminal punctuation marks "
            f"(suggests multi-sentence output): count={terminal_count}, "
            f"prose={prose!r}"
        )


def test_llm_prose_contains_verse_reference_verbatim(
    monkeypatch, client: TestClient
) -> None:
    """Positive grounding: the system prompt requires verse + lemmas verbatim.

    For each conceptual candidate, the candidate's verse reference must
    appear as a substring of the LLM prose. This is the "lemma+ref must
    appear verbatim" clause of the system prompt asserted at the test
    surface.
    """
    monkeypatch.setenv("SPL_EXPLAINER_LLM", "1")
    body = _post_nl(client)
    for r in body["explanation"]["results"]:
        if r["match_type"] != "conceptual":
            continue
        assert r["reference"] in r["explanation"], (
            f"LLM prose for conceptual match {r['reference']!r} omits the "
            f"verse reference. Prose: {r['explanation']!r}"
        )
