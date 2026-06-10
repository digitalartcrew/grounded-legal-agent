"""Tests for the FastAPI surface.

The live agent turn (Gemini + CourtListener) is mocked, so these run offline with
no API key — they verify the HTTP contract, the JSON extraction, and the disclaimer
guarantee, not the model's reasoning.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import server
from app.server import _extract_json, app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "model" in body


def test_index_serves_web_ui():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Run Readiness Check" in resp.text  # the UI's submit button


def test_extract_json_pulls_object_from_noisy_text():
    text = "Here is your result:\n```json\n{\"a\": 1, \"b\": [2, 3]}\n```\nthanks!"
    assert _extract_json(text) == {"a": 1, "b": [2, 3]}


def test_extract_json_raises_without_object():
    with pytest.raises(ValueError):
        _extract_json("no json here")


def test_readiness_returns_review_and_defaults_disclaimer(monkeypatch):
    # Mock the agent turn so we don't call Gemini; omit disclaimer to prove the
    # server backfills it (a safety guarantee we don't want to depend on the model for).
    async def fake_run_review(payload):
        return {"readiness_summary": "ok", "strengths": ["s1"]}

    monkeypatch.setattr(server, "_run_review", fake_run_review)

    resp = client.post("/readiness", json={"case": {"state": "California"}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["readiness_summary"] == "ok"
    assert "not legal advice" in body["disclaimer"].lower()  # backfilled by the server
