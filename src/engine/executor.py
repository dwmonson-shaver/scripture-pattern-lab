"""Pattern-engine executor — turns a validated QueryPlan into MatchCandidates.

Per ``docs/canonical/09_backend-service-boundaries.md`` §5 and the design at
``thoughts/design-pattern-engine-executor-2026-05-09.md`` (status: approved).

MVP contract (decision #4 in the design):
- ``plan.sequence`` MUST be a :class:`SequenceExpr` (no ``InverseExpr``).
- Each step MUST be a :class:`NodeRef` with type ``LEMMA`` or ``CONCEPT``.
- All operators MUST be ``OperatorType.PRECEDENCE``; gap constraints honored.
- ``scope.unit`` is treated as ``VERSE`` (the only unit the corpus supports).
- ``scope.books`` abbreviations MUST resolve via :func:`book_abbrev_to_bb`;
  unknown abbreviations raise :class:`UnsupportedPlanShape` (no silent miss).
- ``scope.corpus=None`` and ``scope.language=None`` produce no filter on
  those columns. Resolution per design OQ #1: with only NT loaded today
  this is functionally equivalent to ``corpus='nt'``; revisit when OT or
  LXX corpus lands so users know whether unspecified means "any" or "NT".
- ``NodeRef.negated=True`` is rejected — exclusion semantics are not yet
  designed. ``NodeRef.morph_filters`` (any non-empty list) is rejected for
  the same reason.
- ``len(sequence.operators)`` must equal ``len(sequence.steps) - 1`` —
  the second wall against malformed plans that slipped past the validator.

Algorithm (decision #10): iterative per-step with **batched** SELECTs.
Step 0 issues one SELECT for the lemma set. Each later step N issues ONE
SELECT scoped to the union of surviving step-(N-1) verses, then groups
result rows by (book, chapter, verse) in Python and pairs each row with
each surviving step-(N-1) candidate that has ``prev.position < this.position``
(and honors the gap constraint). Per-candidate fan-out (one SELECT per
chain) was eliminated in C-CLOSE-004; this trades N×M SELECTs for one
SELECT plus an in-memory join. Verse-grouped ``MatchCandidate``s are
assembled at the end. Canonical-09 §5 explicitly endorses this shape for
the 138K-token MVP corpus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from sqlalchemy import Engine, select, tuple_

from src.engine._schema import tokens_table
from src.engine.models import (
    ConceptNotMapped,
    GapConstraint,
    InverseExpr,
    MatchCandidate,
    MatchedToken,
    NodeRef,
    NodeType,
    OperatorType,
    OrderOperator,
    QueryPlan,
    RegistryRequired,
    ScopeConstraint,
    ScopeUnit,
    SequenceExpr,
    StepMatch,
    UnsupportedPlanShape,
)
from src.ontology.book_codes import bb_to_display, book_abbrev_to_bb

if TYPE_CHECKING:
    from src.ontology.registry import ConceptRegistry


_SUPPORTED_NODE_TYPES = {NodeType.LEMMA, NodeType.CONCEPT}


def execute(
    plan: QueryPlan,
    scope: ScopeConstraint,
    engine: Engine,
    concept_registry: "ConceptRegistry | None" = None,
) -> list[MatchCandidate]:
    """Execute a validated ``QueryPlan`` against the ``tokens`` table.

    Returns verse-grouped ``MatchCandidate``s (empty list = no matches).
    Raises :class:`UnsupportedPlanShape` if the plan exceeds the MVP
    contract documented in this module's docstring.
    Raises :class:`RegistryRequired` if the plan contains a concept node
    but no ``concept_registry`` is supplied.
    Raises :class:`ConceptNotMapped` if a concept node resolves to no
    lemmas in the registry (concept absent or not seeded).
    """
    sequence = _validate_plan_shape(plan, scope)

    # The validated MVP shape guarantees every step is a NodeRef.
    steps: list[NodeRef] = [step for step in sequence.steps]  # type: ignore[misc]

    language = scope.language or "grc"
    resolved_lemmas: list[list[str]] = [
        _resolve_step_lemmas(step, language, concept_registry) for step in steps
    ]

    # Validate book abbreviations up front so we fail loudly before any SQL.
    base_where = _build_scope_where(scope)

    has_concept_step = any(step.type == NodeType.CONCEPT for step in steps)
    match_type: Literal["exact", "conceptual"] = (
        "conceptual" if has_concept_step else "exact"
    )

    with engine.connect() as connection:
        # Step 0: seed with all candidates whose lemma is in the resolved set.
        step0_lemmas = resolved_lemmas[0]
        if not step0_lemmas:
            # Defensive: _resolve_step_lemmas raises ConceptNotMapped on
            # empty CONCEPT resolution and a LEMMA step always returns one
            # element, so this branch is only reachable if a future caller
            # mutates resolved_lemmas. Keep the early-return for safety.
            return []

        step0_stmt = select(*_token_columns()).where(
            tokens_table.c.lemma.in_(step0_lemmas)
        )
        for clause in base_where:
            step0_stmt = step0_stmt.where(clause)

        step0_rows = connection.execute(step0_stmt).all()

        # ``chains`` accumulates a list of partial step-token lists. We extend
        # one step at a time. After step N, each chain has N+1 tokens.
        chains: list[list[MatchedToken]] = [
            [_row_to_matched_token(row)] for row in step0_rows
        ]

        for step_index in range(1, len(steps)):
            if not chains:
                return []
            gap = sequence.operators[step_index - 1].gap
            next_lemmas = resolved_lemmas[step_index]
            if not next_lemmas:
                return []

            chains = _extend_chains_one_step(
                connection,
                chains=chains,
                lemmas=next_lemmas,
                gap=gap,
                base_where=base_where,
            )
            if not chains:
                return []

    # Convert each completed chain into a MatchCandidate.
    candidates: list[MatchCandidate] = []
    for chain in chains:
        first = chain[0]
        reference = f"{bb_to_display(first.book)} {first.chapter}:{first.verse}"
        alignment = [
            StepMatch(
                step_index=i,
                node_type=steps[i].type,
                node_value=steps[i].value,
                resolved_lemmas=resolved_lemmas[i],
                token=chain[i],
            )
            for i in range(len(steps))
        ]
        candidates.append(
            MatchCandidate(
                tokens=chain,
                reference=reference,
                match_type=match_type,
                alignment=alignment,
            )
        )

    # Stable-order by (book, chapter, verse, first-token position) for
    # deterministic test assertions.
    candidates.sort(
        key=lambda c: (
            c.tokens[0].book,
            c.tokens[0].chapter,
            c.tokens[0].verse,
            c.tokens[0].position,
        )
    )
    # Group-by-verse is implicit here: each chain's tokens already share a
    # verse (enforced by the per-step WHERE clause). We do not collapse
    # multiple chains within the same verse — different starting positions
    # are distinct candidates per canonical-09 §5.
    return candidates


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _token_columns() -> list:
    """Return the column list used by every executor SELECT (stable shape)."""
    return [
        tokens_table.c.id,
        tokens_table.c.book,
        tokens_table.c.chapter,
        tokens_table.c.verse,
        tokens_table.c.position,
        tokens_table.c.global_position,
        tokens_table.c.surface_form,
        tokens_table.c.normalized_form,
        tokens_table.c.lemma,
        tokens_table.c.pos,
    ]


def _validate_plan_shape(plan: QueryPlan, scope: ScopeConstraint) -> SequenceExpr:
    """Enforce the MVP contract; return the validated SequenceExpr.

    Raises :class:`UnsupportedPlanShape` on any violation. The validator
    (``src/validation/validator.py``) is the first wall; this function is
    the second wall (decision #4) and fails loudly rather than coerce.
    """
    if isinstance(plan.sequence, InverseExpr):
        raise UnsupportedPlanShape(
            "InverseExpr is not supported by the MVP executor",
            path="$.sequence",
        )
    if not isinstance(plan.sequence, SequenceExpr):
        # Defensive: the discriminated union should make this unreachable.
        raise UnsupportedPlanShape(
            f"unsupported sequence type: {type(plan.sequence).__name__}",
            path="$.sequence",
        )

    sequence = plan.sequence

    if len(sequence.steps) < 1:
        raise UnsupportedPlanShape(
            "executor requires at least one step",
            path="$.sequence.steps",
        )

    # C-CLOSE-002: the operator count must match the step count exactly.
    # Too few would index off the end inside the per-step loop; too many
    # would silently drop operators. Either way, the plan is malformed.
    expected_operators = len(sequence.steps) - 1
    if len(sequence.operators) != expected_operators:
        raise UnsupportedPlanShape(
            f"operator count {len(sequence.operators)} does not match "
            f"steps-1 count {expected_operators}",
            path="$.sequence.operators",
        )

    for index, step in enumerate(sequence.steps):
        path = f"$.sequence.steps[{index}]"
        if not isinstance(step, NodeRef):
            raise UnsupportedPlanShape(
                f"step expression {type(step).__name__} is not supported "
                "by the MVP executor (only NodeRef steps with type=LEMMA "
                "or type=CONCEPT)",
                path=path,
            )
        if step.type not in _SUPPORTED_NODE_TYPES:
            raise UnsupportedPlanShape(
                f"node type {step.type.value!r} is not supported by the "
                "MVP executor (only LEMMA and CONCEPT)",
                path=path,
            )
        # C-CLOSE-001: exclusion semantics are not yet designed; a negated
        # node must not silently flow through to a positive resolution.
        if step.negated:
            raise UnsupportedPlanShape(
                "negated NodeRef not supported in MVP",
                path=path,
            )
        # C-CLOSE-002: morph filters are ignored by the resolution path
        # today, so accepting them would silently broaden the match.
        if step.morph_filters:
            raise UnsupportedPlanShape(
                "NodeRef.morph_filters not supported in MVP",
                path=path,
            )

    for index, op in enumerate(sequence.operators):
        path = f"$.sequence.operators[{index}]"
        if not isinstance(op, OrderOperator):
            raise UnsupportedPlanShape(
                f"operator {type(op).__name__} is not supported",
                path=path,
            )
        if op.type != OperatorType.PRECEDENCE:
            raise UnsupportedPlanShape(
                f"operator type {op.type.value!r} is not supported by the "
                "MVP executor (only PRECEDENCE)",
                path=path,
            )

    # Scope unit: treat None as verse; only VERSE is supported explicitly.
    if scope.unit is not None and scope.unit != ScopeUnit.VERSE:
        raise UnsupportedPlanShape(
            f"scope unit {scope.unit.value!r} is not supported by the "
            "MVP executor (only VERSE; corpus has no clause/sentence/"
            "pericope/chapter annotations)",
            path="$.scope.unit",
        )

    # Validate book abbreviations up front (loud on unknown abbreviation).
    if scope.books is not None:
        for index, abbrev in enumerate(scope.books):
            try:
                book_abbrev_to_bb(abbrev)
            except KeyError as exc:
                raise UnsupportedPlanShape(
                    f"unknown book abbreviation {abbrev!r}; valid forms "
                    "are the canonical lowercase NT abbreviations "
                    "(e.g. 'rom', '1cor', '3jn')",
                    path=f"$.scope.books[{index}]",
                ) from exc

    return sequence


def _resolve_step_lemmas(
    step: NodeRef,
    language: str,
    concept_registry: "ConceptRegistry | None",
) -> list[str]:
    """Resolve a step into the concrete lemma strings to match.

    LEMMA node: ``[step.value]``.
    CONCEPT node: ``concept_registry.get_lemmas_for_concept(step.value, language)``.
    Raises :class:`RegistryRequired` if a CONCEPT node is encountered but
    no registry is supplied.
    Raises :class:`ConceptNotMapped` if the concept resolves to ``[]``
    (the registry has no lemma rows for the named concept).
    """
    if step.type == NodeType.LEMMA:
        return [step.value]
    if step.type == NodeType.CONCEPT:
        if concept_registry is None:
            raise RegistryRequired(step.value)
        lemmas = concept_registry.get_lemmas_for_concept(step.value, language)
        if not lemmas:
            raise ConceptNotMapped(step.value)
        return lemmas
    # Unreachable — _validate_plan_shape rejects other node types.
    raise UnsupportedPlanShape(  # pragma: no cover
        f"unexpected node type in resolution: {step.type.value!r}"
    )


def _build_scope_where(scope: ScopeConstraint) -> list:
    """Build the base WHERE clauses for the given scope.

    Returns a list of SQLAlchemy ColumnElement clauses that callers ``.where()``
    onto step queries. Every step query MUST receive these clauses (C-CLOSE-003);
    otherwise later-step matches can silently leak across corpora or languages
    that share structural verse keys.

    ``corpus=None`` and ``language=None`` produce no filter on those
    columns (design OQ #1 resolution, OQ for language predates it).
    """
    where_clauses: list = []
    if scope.books is not None:
        bb_codes = [book_abbrev_to_bb(b) for b in scope.books]
        where_clauses.append(tokens_table.c.book.in_(bb_codes))
    if scope.corpus is not None:
        where_clauses.append(tokens_table.c.corpus_id == scope.corpus)
    if scope.language is not None:
        where_clauses.append(tokens_table.c.language == scope.language)
    return where_clauses


def _extend_chains_one_step(
    connection,
    *,
    chains: list[list[MatchedToken]],
    lemmas: list[str],
    gap: GapConstraint | None,
    base_where: list,
) -> list[list[MatchedToken]]:
    """Extend each chain by one matching token. ONE SELECT, in-memory join.

    Replaces the prior per-candidate fan-out (one SELECT per surviving chain
    per step). For each step k ≥ 1 we now issue exactly one SELECT scoped to
    the union of surviving step-(k-1) verses, then group rows in Python and
    pair each result row with every chain whose last token shares the same
    ``(book, chapter, verse)`` and satisfies the position + gap constraints.
    Honors C-CLOSE-003 by carrying ``base_where`` (corpus/language/books)
    into every step query.
    """
    # Collect the unique verses the surviving chains terminate in. We use a
    # tuple-IN filter so the DB can index-scan the verse keys rather than
    # OR-of-equalities scaling with the chain count.
    verse_keys: set[tuple[str, int, int]] = {
        (chain[-1].book, chain[-1].chapter, chain[-1].verse) for chain in chains
    }

    stmt = select(*_token_columns()).where(tokens_table.c.lemma.in_(lemmas))
    for clause in base_where:
        stmt = stmt.where(clause)
    stmt = stmt.where(
        tuple_(
            tokens_table.c.book,
            tokens_table.c.chapter,
            tokens_table.c.verse,
        ).in_([tuple(key) for key in verse_keys])
    )

    rows = connection.execute(stmt).all()

    # Group rows by their verse key for O(1) lookup per chain. Each value is a
    # list of MatchedToken (preserving DB row order) so the in-memory join
    # below remains stable.
    rows_by_verse: dict[tuple[str, int, int], list[MatchedToken]] = {}
    for row in rows:
        token = _row_to_matched_token(row)
        rows_by_verse.setdefault(
            (token.book, token.chapter, token.verse), []
        ).append(token)

    extended: list[list[MatchedToken]] = []
    for chain in chains:
        prev = chain[-1]
        verse_rows = rows_by_verse.get((prev.book, prev.chapter, prev.verse))
        if not verse_rows:
            continue
        for next_token in verse_rows:
            if not _gap_satisfied(prev.position, next_token.position, gap):
                continue
            extended.append([*chain, next_token])
    return extended


def _gap_satisfied(
    prev_position: int, next_position: int, gap: GapConstraint | None
) -> bool:
    """Return True iff ``next_position`` follows ``prev_position`` in-window.

    Mirrors the inequality the prior per-candidate SELECT encoded in SQL:
    next must be strictly after prev (position-wise), at least
    ``prev + gap.min + 1`` when ``gap.min > 0`` (i.e. ``gap.min`` tokens
    BETWEEN prev and next), and at most ``prev + gap.max + 1`` when
    ``gap.max`` is set. ``gap`` is None on adjacency-style operators or
    operators with no gap window.
    """
    min_gap = gap.min if gap is not None else 0
    if min_gap > 0:
        if next_position <= prev_position + min_gap:
            return False
    else:
        if next_position <= prev_position:
            return False
    if gap is not None and gap.max is not None:
        if next_position > prev_position + gap.max + 1:
            return False
    return True


def _row_to_matched_token(row) -> MatchedToken:
    """Project a SQLAlchemy Row into a frozen :class:`MatchedToken`."""
    return MatchedToken(
        id=row.id,
        book=row.book,
        chapter=row.chapter,
        verse=row.verse,
        position=row.position,
        global_position=row.global_position,
        surface_form=row.surface_form,
        normalized_form=row.normalized_form,
        lemma=row.lemma,
        pos=row.pos,
    )
