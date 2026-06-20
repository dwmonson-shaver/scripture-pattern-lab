"""Integration test for the chapter-read route (Slice 1, DEC-128/148).

DATABASE_URL-gated. Requires the corpus + a KJV translation ingested. Reads
Romans 8 via the live app and asserts English + Greek come back aligned.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.app.main import create_app

pytestmark = pytest.mark.integration


def test_read_romans_8_returns_english_and_greek() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/api/v1/read/nt/rom/8?version=kjv")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["book_display"] == "Rom"
    assert body["chapter"] == 8
    assert len(body["verses"]) > 0
    # Romans 8:24 ("For we are saved by hope") is the prototype's anchor verse.
    v24 = next((v for v in body["verses"] if v["verse"] == 24), None)
    assert v24 is not None
    assert "hope" in v24["english_text"].lower()
    # Greek tokens should be present for the chapter.
    assert any(len(v["greek_tokens"]) > 0 for v in body["verses"])


def test_versions_lists_kjv() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/api/v1/read/versions")
    assert resp.status_code == 200
    codes = [v["code"] for v in resp.json()["versions"]]
    assert "kjv" in codes
