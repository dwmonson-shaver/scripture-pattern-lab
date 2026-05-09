#!/usr/bin/env python
"""Run a DSL query against the seeded corpus + registry and print matches.

Pipeline: parse → validate → retrieve (executor + contextualization) →
human-readable print. Mirrors ``scripts/db/ingest_corpus.py`` for the
sys.path bootstrap, argparse style, exit codes, and DATABASE_URL
redaction. Strictly a thin orchestrator over ``src.engine`` /
``src.retrieval`` / ``src.validation`` / ``src.ontology`` — no new logic.

The CLI is a UI-layer consumer, so it passes ``contextualize=True`` to
:func:`retrieve` per OQ #1 middle-path resolution: the user sees
calibrated counts (per-node baselines + alternative orderings) by
default, the anti-confirmation-bias choice [DEC-024]. Tests / batch
callers using the engine layer directly get ``contextualize=False``.

Exit codes:
    0   success — matches found OR no matches (empty result is valid)
    1   uncaught exception — traceback printed to stderr
    2   user error — ParseError, validator returned ``unsupported``, or the
        executor refused the plan shape
    3   registry not seeded OR concept not mapped — a concept node was used
        but either no registry was supplied or the registry has no lemma
        rows for the named concept (e.g. unknown / unseeded concept)
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

# Make repo root importable when invoked as a script (``uv run scripts/...``).
# Pytest adds repo root via ``pythonpath = ["."]``; standalone CLI invocation
# does not, so bootstrap it here. Idempotent: sys.path entries are deduped.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.engine.models import (  # noqa: E402
    ConceptNotMapped,
    Contextualization,
    MatchCandidate,
    NodeType,
    RegistryRequired,
    UnsupportedPlanShape,
)
from src.engine.parser import ParseError, parse  # noqa: E402
from src.ingestion.db import get_engine  # noqa: E402
from src.nlp.explainer import explain  # noqa: E402
from src.ontology.registry import ConceptRegistry  # noqa: E402
from src.retrieval.retrieve import retrieve  # noqa: E402
from src.validation.registry import CapabilityRegistry  # noqa: E402
from src.validation.validator import validate  # noqa: E402

EXIT_OK: int = 0
EXIT_UNCAUGHT: int = 1
EXIT_USER_ERROR: int = 2
EXIT_REGISTRY_EMPTY: int = 3


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="query.py",
        description="Run a DSL query and print matches in human-readable form.",
    )
    parser.add_argument("dsl", type=str, help="DSL query string (e.g. 'faith > hope > love').")
    parser.add_argument(
        "--limit", type=int, default=20, help="cap on candidates to print (default: 20)"
    )
    parser.add_argument(
        "--no-prose",
        action="store_true",
        help="suppress the deterministic prose explanation block (default: prose ON)",
    )
    return parser.parse_args(argv)


def _redact_database_url(url: str) -> str:
    """Replace any ``user:password@`` segment with ``user:***@``.

    Mirrors ``scripts/db/ingest_corpus.py``. Returns the input unchanged if
    there is no userinfo, no password, or the input is not URL-shaped.
    """
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    userinfo, host_part = rest.rsplit("@", 1)
    if ":" not in userinfo:
        return url
    user, _password = userinfo.split(":", 1)
    return f"{scheme}://{user}:***@{host_part}"


def _format_candidate(index: int, candidate: MatchCandidate) -> list[str]:
    """Render one candidate as indented lines using the alignment provenance."""
    lines: list[str] = [f"  [{index}] {candidate.reference}"]
    lemma_width = max((len(s.token.lemma) for s in candidate.alignment), default=0)
    for step in candidate.alignment:
        tag = f"({step.node_value})" if step.node_type == NodeType.CONCEPT else ""
        lines.append(
            f"        {step.token.lemma:<{lemma_width}}  {tag:<24}"
            f" @ position {step.token.position}"
        )
    return lines


def _print_results(
    dsl: str,
    status: str,
    grounding: str | None,
    candidates: list[MatchCandidate],
    limit: int,
) -> None:
    """Write the human-readable result block to stdout."""
    grounding_label = grounding if grounding is not None else "n/a"
    print(f"Query: {dsl}")
    print(f"Status: {status}   Grounding: {grounding_label}")
    if candidates:
        print(f"Match type: {candidates[0].match_type}")

    total = len(candidates)
    shown = min(total, max(0, limit))
    if total == 0:
        print("Found 0 matches.")
        return
    print(f"Found {total} matches (showing first {shown}):")
    print()
    for i, candidate in enumerate(candidates[:shown], start=1):
        for line in _format_candidate(i, candidate):
            print(line)
        print()


def _print_contextualization(ctx: Contextualization) -> None:
    """Render the Contextualization envelope in human-readable form.

    Per canonical-09 §8: surfaces the per-node baselines, alternative-ordering
    counts (with the observed ordering marked), and the null-distribution
    slot. Output order matches the design intent — observed count is shown
    first, baselines next, then alternative orderings sorted by count
    descending so the most-frequent siblings rise to the top.
    """
    print("Contextualization (REQ:09.contextualization):")
    print(f"  Observed count: {ctx.observed_count}")

    print("  Constituent baselines (scope-filtered tokens):")
    if ctx.node_baselines:
        name_width = max(len(nb.node_value) for nb in ctx.node_baselines)
        for nb in ctx.node_baselines:
            resolved = ", ".join(nb.resolved_lemmas)
            print(
                f"    {nb.node_value:<{name_width}}  →  "
                f"{resolved}: {nb.count}"
            )
    else:
        print("    (none — empty sequence)")

    print(
        f"  Alternative orderings ({len(ctx.alternative_orderings)} total"
        + (", capped" if ctx.alternative_orderings_capped else "")
        + ", observed marked *):"
    )
    # Sort by count desc, observed first within ties
    sorted_orderings = sorted(
        ctx.alternative_orderings,
        key=lambda o: (-o.count, not o.is_observed, o.permutation),
    )
    for o in sorted_orderings:
        marker = "*" if o.is_observed else " "
        print(f"    {marker}  {o.sequence_label}: {o.count}")

    if ctx.null_distribution is None:
        print("  Null distribution: not computed in MVP (schema slot reserved)")
    else:
        nd = ctx.null_distribution
        print(
            f"  Null distribution: mean={nd.mean:.2f} std={nd.std:.2f} "
            f"(n={nd.sample_size}, seed={nd.seed})"
        )


def _print_findings(prefix: str, findings: list, stream) -> None:
    """Print one validator finding per line to ``stream``."""
    print(prefix, file=stream)
    for f in findings:
        print(f"  {f.severity}: {f.code} at {f.path}: {f.message}", file=stream)


def _print_explanation(summary: str) -> None:
    """Render the deterministic prose explanation block to stdout.

    Heading on its own line; each summary line indented two spaces. Emitted
    only when ``--no-prose`` is NOT set. Per REQ:09.result-explainer (MVP)
    and DEC-061: deterministic, no LLM, no I/O.
    """
    print("Explanation:")
    for line in summary.splitlines():
        print(f"  {line}")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns process exit code; never raises on user error."""
    args = _parse_args(argv)
    dsl: str = args.dsl
    limit: int = args.limit
    no_prose: bool = args.no_prose

    url = os.environ.get("DATABASE_URL")
    redacted = _redact_database_url(url) if url else "<unset>"
    print(f"query={dsl!r} DATABASE_URL={redacted}", file=sys.stderr)

    try:
        plan = parse(dsl)
    except ParseError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        print(f"  {dsl}", file=sys.stderr)
        print(f"  {' ' * exc.pos}^", file=sys.stderr)
        return EXIT_USER_ERROR

    try:
        engine = get_engine()
        concept_registry = ConceptRegistry(engine)
        validation = validate(
            plan, CapabilityRegistry.mvp(), concept_registry=concept_registry
        )
    except Exception:
        traceback.print_exc()
        return EXIT_UNCAUGHT

    if validation.status == "unsupported" or validation.executable_plan is None:
        _print_findings(
            f"validator rejected plan: status={validation.status}",
            validation.findings,
            sys.stderr,
        )
        return EXIT_USER_ERROR

    if validation.status == "partial":
        _print_findings(
            "validator returned partial — proceeding with reduced executable plan",
            validation.findings,
            sys.stderr,
        )

    executable = validation.executable_plan
    try:
        result = retrieve(
            executable,
            executable.scope,
            engine,
            contextualize=True,
            registry=concept_registry,
        )
    except RegistryRequired as exc:
        print(
            f"registry not seeded: concept {exc.concept_name!r} has no "
            "lemma mapping. Run scripts/db/seed_registry.py first.",
            file=sys.stderr,
        )
        return EXIT_REGISTRY_EMPTY
    except ConceptNotMapped as exc:
        print(
            f"concept not mapped: {exc.concept_name!r} is not present in the "
            "concept registry (no lemma rows). Add it via "
            "scripts/db/seed_registry.py or correct the query.",
            file=sys.stderr,
        )
        return EXIT_REGISTRY_EMPTY
    except UnsupportedPlanShape as exc:
        print(f"executor rejected plan: {exc} (path={exc.path})", file=sys.stderr)
        return EXIT_USER_ERROR
    except Exception:
        traceback.print_exc()
        return EXIT_UNCAUGHT

    _print_results(
        dsl, validation.status, validation.grounding, result.candidates, limit
    )
    if result.contextualization is not None:
        print()
        _print_contextualization(result.contextualization)

    if not no_prose:
        explained = explain(result, executable, validation)
        print()
        _print_explanation(explained.summary)

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
