"""Tests for the FastAPI app factory, lifespan, and DI providers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from src.app.dependencies import get_concept_registry, get_engine
from src.app.main import create_app
from src.ontology.registry import ConceptRegistry


@pytest.fixture
def app_no_db(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """App with DATABASE_URL + ANTHROPIC_API_KEY forcibly unset.

    Lifespan leaves engine, registry, llm_client, and translation_context
    all as None on app.state.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return create_app()


@pytest.fixture
def app_with_overrides(app_no_db: FastAPI) -> FastAPI:
    """App with DI overrides installed for engine + registry."""
    fake_engine = MagicMock(spec=Engine, name="fake_engine")
    fake_registry = ConceptRegistry.empty()
    app_no_db.dependency_overrides[get_engine] = lambda: fake_engine
    app_no_db.dependency_overrides[get_concept_registry] = lambda: fake_registry
    return app_no_db


class TestAppFactory:
    def test_create_app_returns_fastapi_instance(self) -> None:
        app = create_app()
        assert isinstance(app, FastAPI)
        assert app.title == "Scripture Pattern Lab"

    def test_each_create_app_call_is_independent(self) -> None:
        # Two factory calls must produce two distinct apps so test
        # dependency_overrides on one don't leak to the other.
        a = create_app()
        b = create_app()
        assert a is not b
        a.dependency_overrides[get_engine] = lambda: "from_a"
        assert get_engine not in b.dependency_overrides


class TestLifespanWithoutDatabaseUrl:
    def test_lifespan_runs_with_unset_database_url(
        self, app_no_db: FastAPI
    ) -> None:
        # Entering and exiting TestClient triggers the lifespan;
        # this should not raise.
        with TestClient(app_no_db):
            assert app_no_db.state.engine is None
            assert app_no_db.state.registry is None
            assert app_no_db.state.llm_client is None
            assert app_no_db.state.translation_context is None


class TestLifespanWithAnthropicApiKey:
    """Independent ANTHROPIC_API_KEY branch — DEC-074 + Slice H structure outline."""

    def test_lifespan_constructs_llm_client_and_context_when_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-stub-test-key")
        # Stub the builder so we don't hit anthropic.Anthropic() at import time.
        fake_llm = MagicMock(name="fake_llm_client")
        monkeypatch.setattr(
            "src.app.main.build_anthropic_client_from_env", lambda: fake_llm
        )
        app = create_app()
        with TestClient(app):
            assert app.state.llm_client is fake_llm
            # TranslationContext is built with non-empty summaries.
            ctx = app.state.translation_context
            assert ctx is not None
            assert ctx.capability_registry_summary
            assert ctx.concept_registry_summary

    def test_db_set_but_llm_unset_leaves_llm_state_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # DATABASE_URL and ANTHROPIC_API_KEY degrade independently.
        fake_engine = MagicMock(spec=Engine, name="fake_engine")
        monkeypatch.setenv("DATABASE_URL", "postgresql://stub")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "src.app.main.build_engine_from_env", lambda: fake_engine
        )
        app = create_app()
        with TestClient(app):
            assert app.state.engine is fake_engine
            assert app.state.llm_client is None
            assert app.state.translation_context is None


class TestLifespanWithDatabaseUrl:
    def test_lifespan_constructs_engine_and_registry_when_url_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Stub build_engine_from_env so we don't actually hit Postgres.
        fake_engine = MagicMock(spec=Engine, name="fake_engine")
        monkeypatch.setenv("DATABASE_URL", "postgresql://stub")
        monkeypatch.setattr(
            "src.app.main.build_engine_from_env", lambda: fake_engine
        )
        app = create_app()
        with TestClient(app):
            assert app.state.engine is fake_engine
            assert isinstance(app.state.registry, ConceptRegistry)
            assert app.state.registry.engine is fake_engine
        # On shutdown, engine.dispose() should have been called.
        fake_engine.dispose.assert_called_once()


class TestDependencyProviders:
    """Verify the get_engine / get_concept_registry providers are reachable
    from a route via Depends()."""

    def test_overrides_supersede_state_lookup(
        self, app_with_overrides: FastAPI
    ) -> None:
        captured: dict[str, str] = {}

        @app_with_overrides.get("/_probe")
        def _probe(
            engine: Engine = Depends(get_engine),
            registry: ConceptRegistry = Depends(get_concept_registry),
        ) -> dict[str, bool]:
            captured["engine_repr"] = repr(engine)
            captured["registry_type"] = type(registry).__name__
            return {"ok": True}

        with TestClient(app_with_overrides) as client:
            resp = client.get("/_probe")
        assert resp.status_code == 200
        assert "fake_engine" in captured["engine_repr"]
        assert captured["registry_type"] == "ConceptRegistry"

    def test_provider_returns_503_when_state_unset_and_no_override(
        self, app_no_db: FastAPI
    ) -> None:
        # No overrides installed; state.engine is None per lifespan.
        @app_no_db.get("/_probe")
        def _probe(engine: Engine = Depends(get_engine)) -> dict[str, bool]:
            return {"ok": True}

        with TestClient(app_no_db) as client:
            resp = client.get("/_probe")
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "engine_unavailable"

    def test_registry_provider_returns_503_when_state_unset(
        self, app_no_db: FastAPI
    ) -> None:
        @app_no_db.get("/_probe")
        def _probe(
            registry: ConceptRegistry = Depends(get_concept_registry),
        ) -> dict[str, bool]:
            return {"ok": True}

        with TestClient(app_no_db) as client:
            resp = client.get("/_probe")
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "registry_unavailable"


class TestModuleLevelApp:
    def test_module_level_app_exists(self) -> None:
        # Required for `uvicorn src.app.main:app` invocation.
        from src.app.main import app

        assert isinstance(app, FastAPI)
