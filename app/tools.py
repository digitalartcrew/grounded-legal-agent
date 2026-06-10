"""Agent tools. Each call becomes a tool span in Phoenix automatically.

The case-law tool is the grounding boundary: the model proposes neutral *search
topics*, this code fetches REAL opinions from CourtListener, and only real,
linkable cases reach the user. The model never invents citations — a hard rule
for a self-help legal app, and something we verify with an eval (see evals.py).
"""

from __future__ import annotations

import json
import os
from typing import Callable

import requests

# The agent's tool registry. Every @tool-decorated function lands here, so the
# agent picks them up automatically — definition, docstring-derived schema, and
# registration all live together in this file. ADK builds each tool's JSON schema
# from the function signature + docstring, so the contract can never drift.
TOOLS: list[Callable] = []


def tool(fn: Callable) -> Callable:
    """Register ``fn`` as an agent tool (keeps tools self-contained in this module)."""
    TOOLS.append(fn)
    return fn


@tool
def search_caselaw(query: str, jurisdiction: str = "") -> str:
    """Search real U.S. court opinions for a legal topic.

    Use this to ground any case-law reference. Pass a short, neutral search topic
    (e.g. "restraining order credible threat standard"), NOT a case name. Returns
    real opinions only — never invent citations.

    Args:
      query: A short, neutral legal search topic.
      jurisdiction: Optional state name to bias relevance (e.g. "California").

    Returns:
      A JSON string: a list of {caseName, citation, court, dateFiled, url}.
    """
    q = f"{query} {jurisdiction}".strip()
    url = (
        "https://www.courtlistener.com/api/rest/v4/search/"
        "?type=o&order_by=score+desc&q=" + requests.utils.quote(q)
    )
    headers = {"content-type": "application/json"}
    token = (os.environ.get("COURTLISTENER_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Token {token}"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return json.dumps([])
        results = (resp.json().get("results") or [])[:3]
        cases = [
            {
                "caseName": r.get("caseName") or r.get("caseNameFull") or "Unnamed opinion",
                "citation": (r.get("citation") or [""])[0]
                if isinstance(r.get("citation"), list)
                else (r.get("citation") or ""),
                "court": r.get("court") or r.get("court_id") or "",
                "dateFiled": r.get("dateFiled") or "",
                "url": (
                    f"https://www.courtlistener.com{r.get('absolute_url')}"
                    if r.get("absolute_url")
                    else "https://www.courtlistener.com/"
                ),
                "topic": query,
            }
            for r in results
        ]
        return json.dumps(cases)
    except Exception:
        return json.dumps([])
