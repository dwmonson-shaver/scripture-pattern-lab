#!/usr/bin/env python
"""Seed the worked-example Tier-2 grouping (Slice O, Phase O4 / DEC-116).

The first concrete Tier-2 grouping the system ships: the humility cluster
surfaced by Bucket-N3 (where Tier-1 narrow recall produced only
``ταπεινοφροσύνη`` for "humility" because TBESG glosses verb/adjective forms
as "humble"/"humble oneself"). Tier-2's whole point is to bridge that
recall gap by GROUPING lexically-related concepts together.

This script is the worked example AND the reproducible demo fixture. Run it
once against a Neon (or local) Postgres with the corpus + lexicon already
loaded; it auto-creates the missing concepts via the Slice-N Tier-1 path,
then writes a Tier-2 grouping linking them with hand-picked confidences.

Idempotent. Safe to re-run.

Epistemics: every write is ``verification_state='unverified'``. The grouping
is a HYPOTHESIS the corpus + a human must validate (DEC-081); the runtime
guard (DEC-115) structurally prevents this script from accidentally writing
``human_confirmed``.

Exit codes:
    0   success (grouping written or already present)
    1   uncaught exception
    2   no anchor concept could be created (lexicon recall empty for anchor)

CLI lives under ``scripts/`` per DEC-025.
"""

from __future__ import annotations

import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

# Make repo root importable when invoked as a script. Idempotent.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import Engine  # noqa: E402

from src.ingestion.db import get_engine  # noqa: E402
from src.ontology.concept_document import (  # noqa: E402
    ConceptDocument,
    build_comparative_section,
    build_short_summary,
    get_document,
    persist_document,
)
from src.ontology.concept_grouping import (  # noqa: E402
    GroupingMember,
    Tier2Grouping,
    read_grouping_for_anchor,
    write_grouping,
)
from src.ontology.concept_writer import auto_create_cited_concept  # noqa: E402
from src.ontology.lexicon_resolver import (  # noqa: E402
    LexiconResolution,
    resolve_english_term,
)

# Hand-picked confidences (DEC-116). The anchor is closest to its own Greek
# (ταπεινοφροσύνη "humility of mind"); meekness / lowliness are adjacent
# clusters. Numbers are illustrative — real per-edge confidence weighting is a
# future scoring slice's territory.
HUMILITY_CLUSTER: list[tuple[str, float]] = [
    ("humility", 0.95),
    ("meekness", 0.85),
    ("lowliness", 0.75),
]
RATIONALE: str = (
    "Humility-cluster: lexically close Greek roots (ταπεινός / πραΰς) and "
    "translator alternation across NT pericopes (e.g. Mt 5:5, Mt 11:29, "
    "Php 2:3, Col 3:12). Bridges Bucket-N3 (Tier-1 narrow recall for "
    "'humility') by surfacing the wider conceptual neighborhood. "
    "Corpus-evidence audit pending Tier-2 evidence-finder slice."
)


def _ensure_concept_and_document(term: str, engine: Engine) -> str | None:
    """Resolve, auto-create, and persist the document for ``term``.

    Returns the concept name on success, None if the lexicon resolved zero
    corpus-present lemmas (Bucket-N3 reality — the script should still try the
    other members rather than blow up).
    """
    resolution: LexiconResolution = resolve_english_term(term, engine)
    if resolution.unresolved:
        print(
            f"  [skip] '{term}': lexicon resolved 0 corpus-present lemmas "
            "(Bucket-N3 narrow-recall territory; not failing).",
            file=sys.stderr,
        )
        return None

    outcome = auto_create_cited_concept(resolution, engine)
    if outcome.created:
        print(
            f"  [create] '{term}': {len(outcome.lemmas_written)} lemma(s) "
            f"({', '.join(outcome.lemmas_written)})",
            file=sys.stderr,
        )
    else:
        print(f"  [reuse] '{term}' already exists", file=sys.stderr)

    # Persist the deterministic Conceptual Document (Slice N §1; no LLM here).
    # store-once: if a doc already exists, this is a no-op.
    if get_document(term, engine) is None:
        persist_document(
            ConceptDocument(
                concept_name=term,
                short_summary=build_short_summary(resolution),
                part1_comparative=build_comparative_section(resolution, engine),
            ),
            engine,
        )
        print(f"  [doc] persisted deterministic §1 for '{term}'", file=sys.stderr)
    else:
        print(f"  [doc] '{term}' already has a document", file=sys.stderr)
    return term


def seed_humility_grouping(engine: Engine) -> Tier2Grouping | None:
    """Write the humility cluster grouping; idempotent.

    Returns the written grouping on success, or None if the anchor concept
    could not even be created (lexicon empty for "humility" — would mean the
    lexicon isn't loaded; the script's caller should exit 2).
    """
    print("[1/3] Auto-creating concepts via Slice-N Tier-1 path...", file=sys.stderr)
    created_members: list[tuple[str, float]] = []
    for term, conf in HUMILITY_CLUSTER:
        name = _ensure_concept_and_document(term, engine)
        if name is not None:
            created_members.append((name, conf))

    if not created_members:
        return None  # nothing to anchor on
    anchor_name = created_members[0][0]
    if anchor_name != HUMILITY_CLUSTER[0][0]:
        # Defensive: if the intended anchor ("humility") was the one that
        # failed to resolve, refuse — the worked example loses its meaning.
        print(
            f"[abort] anchor '{HUMILITY_CLUSTER[0][0]}' could not be created; "
            "lexicon may not be loaded. Run scripts/db/ingest_lexicon.py first.",
            file=sys.stderr,
        )
        return None
    if len(created_members) < 2:
        print(
            "[abort] only one concept could be created; a grouping needs >= 2 "
            "members. Lexicon recall is the bottleneck (Bucket-N3).",
            file=sys.stderr,
        )
        return None

    print(
        f"[2/3] Building Tier-2 grouping (anchor={anchor_name}, "
        f"{len(created_members)} member(s))...",
        file=sys.stderr,
    )
    grouping = Tier2Grouping(
        anchor_name=anchor_name,
        members=[
            GroupingMember(concept_name=n, confidence=c)
            for (n, c) in created_members
        ],
        rationale=RATIONALE,
        created_at=datetime.now(tz=UTC),
    )

    existing = read_grouping_for_anchor(anchor_name, engine)
    if existing is not None and {m.concept_name for m in existing.members} == {
        n for (n, _) in created_members
    }:
        print(
            f"[3/3] [reuse] grouping for anchor '{anchor_name}' already "
            "carries the same member set — no-op.",
            file=sys.stderr,
        )
        return existing

    print(f"[3/3] Writing grouping to anchor '{anchor_name}'...", file=sys.stderr)
    written = write_grouping(grouping, engine)
    print(
        f"[done] anchor='{anchor_name}' members="
        f"{[m.concept_name for m in written.members]} "
        f"vstate='{written.verification_state}' (DEC-081 invariant)",
        file=sys.stderr,
    )
    return written


def main(argv: list[str] | None = None) -> int:  # noqa: ARG001
    try:
        engine = get_engine()
        result = seed_humility_grouping(engine)
        if result is None:
            return 2
        return 0
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
