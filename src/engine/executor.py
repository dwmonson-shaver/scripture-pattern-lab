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

Algorithm (decision #10): iterative per-step, in Python. Step 0 issues one
SELECT for the lemma set; each step N issues one SELECT per step-(N-1)
candidate, scoped to the same verse + position window. Verse-grouped
``MatchCandidate``s are assembled in Python at the end. Canonical-09 §5
explicitly endorses this shape for the 138K-token MVP corpus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from sqlalchemy import Engine, select

from src.engine.models import (
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
from src.ingestion.db import tokens_table
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
    """
    sequence = _validate_plan_shape(plan, scope)

    # The validated MVP shape guarantees every step is a NodeRef.
    steps: list[NodeRef] = [step for step in sequence.steps]  # type: ignore[misc]

    language = scope.language or "grc"
    resolved_lemmas: list[list[str]] = [
        _resolve_step_lemmas(step, language, concept_registry) for step in steps
    ]

    # Validate book abbreviations up front so we fail loudly before any SQL.
    base_where, base_params = _build_scope_where(scope)

    has_concept_step = any(step.type == NodeType.CONCEPT for step in steps)
    match_type: Literal["exact", "conceptual"] = (
        "conceptual" if has_concept_step else "exact"
    )

    with engine.connect() as connection:
        # Step 0: seed with all candidates whose lemma is in the resolved set.
        step0_lemmas = resolved_lemmas[0]
        if not step0_lemmas:
            return []

        step0_stmt = (
            select(
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
            )
            .where(tokens_table.c.lemma.in_(step0_lemmas))
        )
        for clause in base_where:
            step0_stmt = step0_stmt.where(clause)

        step0_rows = connection.execute(step0_stmt, base_params).all()

        # ``chains`` accumulates a list of partial step-token lists. We extend
        # one step at a time. After step N, each chain has N+1 tokens.
        chains: list[list[MatchedToken]] = [
            [_row_to_matched_token(row)] for row in step0_rows
        ]

        for step_index in range(1, len(steps)):
            gap = sequence.operators[step_index - 1].gap
            next_lemmas = resolved_lemmas[step_index]
            if not next_lemmas:
                return []

            extended: list[list[MatchedToken]] = []
            for chain in chains:
                prev_token = chain[-1]
                rows = _match_step_in_verse(
                    connection,
                    prev_token=prev_token,
                    lemmas=next_lemmas,
                    gap=gap,
                )
                for row in rows:
                    extended.append([*chain, _row_to_matched_token(row)])
            chains = extended
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
    """
    if step.type == NodeType.LEMMA:
        return [step.value]
    if step.type == NodeType.CONCEPT:
        if concept_registry is None:
            raise RegistryRequired(step.value)
        return concept_registry.get_lemmas_for_concept(step.value, language)
    # Unreachable — _validate_plan_shape rejects other node types.
    raise UnsupportedPlanShape(  # pragma: no cover
        f"unexpected node type in resolution: {step.type.value!r}"
    )


def _build_scope_where(scope: ScopeConstraint) -> tuple[list, dict]:
    """Build the base WHERE clauses + params dict for the given scope.

    Returns ``(where_clauses, params_dict)``. ``params_dict`` is currently
    always empty (we use SQLAlchemy expression-binding rather than named
    params); the second element exists to keep the return shape stable for
    callers that may switch to text-binding in future.

    ``corpus=None`` and ``language=None`` produce no filter on those
    columns (design OQ #1 resolution, OQ for language predates it).
    """
    where_clauses: list = []
    params: dict = {}
    if scope.books is not None:
        bb_codes = [book_abbrev_to_bb(b) for b in scope.books]
        where_clauses.append(tokens_table.c.book.in_(bb_codes))
    if scope.corpus is not None:
        where_clauses.append(tokens_table.c.corpus_id == scope.corpus)
    if scope.language is not None:
        where_clauses.append(tokens_table.c.language == scope.language)
    return where_clauses, params


def _match_step_in_verse(
    connection,
    *,
    prev_token: MatchedToken,
    lemmas: list[str],
    gap: GapConstraint | None,
) -> list:
    """Return token rows matching ``lemmas`` after ``prev_token`` in-verse.

    Same verse as ``prev_token`` (book, chapter, verse). Position strictly
    greater than ``prev_token.position``; honors ``gap.min`` (minimum
    distance from prev) and ``gap.max`` (maximum distance) when present.
    """
    stmt = (
        select(
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
        )
        .where(tokens_table.c.book == prev_token.book)
        .where(tokens_table.c.chapter == prev_token.chapter)
        .where(tokens_table.c.verse == prev_token.verse)
        .where(tokens_table.c.lemma.in_(lemmas))
    )
    # gap.min == 0 means "any distance > 0" (the next token can be the
    # immediate successor). gap.min == k means at least k tokens between.
    min_gap = gap.min if gap is not None else 0
    # Distance is (position - prev.position). gap.min is the count of
    # intervening tokens; the canonical reading per canonical-05 is
    # min/max apply to the gap *between* the two matched tokens, so
    # position must be > prev.position + min_gap when min_gap > 0, and
    # > prev.position when min_gap == 0.
    if min_gap > 0:
        stmt = stmt.where(tokens_table.c.position > prev_token.position + min_gap)
    else:
        stmt = stmt.where(tokens_table.c.position > prev_token.position)
    if gap is not None and gap.max is not None:
        stmt = stmt.where(
            tokens_table.c.position <= prev_token.position + gap.max + 1
        )
    return connection.execute(stmt).all()


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
