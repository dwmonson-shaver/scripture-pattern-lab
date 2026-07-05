"""Typed-connection CRUD HTTP surface (Slice 2, 2026-07-05).

POST creates a human-authored connection between concepts (ordered members +
one-or-more typed claims). GET lists all connections. DELETE removes one. A
connection is a corrigible prior, never a corpus-tested fact — ordering evidence
is computed elsewhere and never advances a connection's standing here. Writes are
bearer-gated by BearerAuthMiddleware when a token is configured.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine

from src.app.dependencies import get_engine
from src.app.schemas import (
    ConnectionCreateRequest,
    ConnectionOut,
    ConnectionsResponse,
    ErrorResponse,
)
from src.ontology.connections import (
    Connection,
    ConnectionNotFound,
    InvalidConnection,
    UnknownConcept,
    create_connection,
    delete_connection,
    list_connections,
)

router = APIRouter()


def _to_out(connection: Connection) -> ConnectionOut:
    return ConnectionOut(
        id=connection.id,
        note=connection.note,
        actor=connection.actor,
        members=connection.members,
        types=connection.types,
    )


@router.post(
    "/api/v1/connections", response_model=ConnectionOut, status_code=201
)
def create_connection_route(
    body: ConnectionCreateRequest,
    engine: Engine = Depends(get_engine),
) -> ConnectionOut:
    """Create a typed connection between concepts.

    422 if the members/types are structurally invalid; 404 if a member concept
    name is not in the registry.
    """
    try:
        connection = create_connection(
            engine,
            member_names=body.member_names,
            claim_types=body.types,
            note=body.note,
        )
    except InvalidConnection as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ErrorResponse(
                error="invalid_connection", message=str(exc), details=None
            ).model_dump(),
        ) from exc
    except UnknownConcept as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="unknown_concept", message=str(exc), details=None
            ).model_dump(),
        ) from exc
    return _to_out(connection)


@router.get("/api/v1/connections", response_model=ConnectionsResponse)
def list_connections_route(
    engine: Engine = Depends(get_engine),
) -> ConnectionsResponse:
    """Return all connections (newest first)."""
    return ConnectionsResponse(
        connections=[_to_out(c) for c in list_connections(engine)]
    )


@router.delete(
    "/api/v1/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_connection_route(
    connection_id: int,
    engine: Engine = Depends(get_engine),
) -> None:
    """Delete a connection (members + claims cascade). 404 if absent."""
    try:
        delete_connection(engine, connection_id)
    except ConnectionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="connection_not_found",
                message=str(exc),
                details={"connection_id": connection_id},
            ).model_dump(),
        ) from exc
