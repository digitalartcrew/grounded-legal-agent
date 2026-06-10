"""Tests for the grounding tool and the @tool registry.

These run fully offline — the one test that exercises search_caselaw monkeypatches
the HTTP call, so no network or API key is needed.
"""

from __future__ import annotations

import json

from app import tools
from app.tools import TOOLS, search_caselaw, tool


def test_search_caselaw_is_registered():
    # The @tool decorator should have placed it in the shared registry.
    assert search_caselaw in TOOLS


def test_tool_decorator_registers_and_returns_function():
    @tool
    def dummy_tool(x: str) -> str:
        """A throwaway tool."""
        return x

    assert dummy_tool in TOOLS
    assert dummy_tool("hi") == "hi"  # decorator returns the function unchanged
    TOOLS.remove(dummy_tool)  # keep the registry clean for other tests


class _FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_search_caselaw_parses_real_results(monkeypatch):
    sample = {
        "results": [
            {
                "caseName": "Doe v. Roe",
                "citation": ["123 U.S. 456"],
                "court": "Supreme Court",
                "dateFiled": "2020-01-01",
                "absolute_url": "/opinion/1/doe-v-roe/",
            }
        ]
    }
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: _FakeResp(200, sample))

    out = json.loads(search_caselaw("credible threat", "California"))
    assert len(out) == 1
    case = out[0]
    assert case["caseName"] == "Doe v. Roe"
    assert case["citation"] == "123 U.S. 456"  # list collapsed to first cite
    assert case["url"] == "https://www.courtlistener.com/opinion/1/doe-v-roe/"
    assert case["topic"] == "credible threat"  # the query is echoed as the topic


def test_search_caselaw_returns_empty_on_error(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: _FakeResp(500, {}))
    assert json.loads(search_caselaw("anything")) == []


def test_search_caselaw_swallows_exceptions(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(tools.requests, "get", boom)
    # The grounding tool must never crash the agent — it degrades to no results.
    assert json.loads(search_caselaw("anything")) == []
