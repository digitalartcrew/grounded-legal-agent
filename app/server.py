"""FastAPI server exposing the traced Case Review agent over HTTP.

A client POSTs a case JSON here (see CasePayload). Each request runs one ADK
agent turn; OpenInference traces it to Phoenix. We set a `session.id` so a
request's spans are groupable for the self-improvement loop.

Run:  uvicorn app.server:app --port 8080
"""

from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from app.agent import root_agent  # noqa: E402  (imports trigger setup_tracing)
from app.web import INDEX_HTML  # noqa: E402

app = FastAPI(title="Grounded Legal Agent — Case Review")

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

DISCLAIMER = (
    "This readiness check is automated self-help preparation, not legal advice, and does not "
    "predict any court outcome. This software is not a law firm. Consider consulting a licensed "
    "attorney in your jurisdiction."
)


class CasePayload(BaseModel):
    # The case shape a client sends — passed verbatim to the agent. Adapt freely.
    matterContext: str | None = ""
    matterLabel: str | None = ""
    case: dict = {}
    timeline: list = []
    evidence: list = []
    statementAnalyses: list = []


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of the agent's final message."""
    match = re.search(r"\{[\s\S]*\}", text or "")
    if not match:
        raise ValueError("agent did not return JSON")
    return json.loads(match.group(0))


async def _run_review(payload: CasePayload) -> dict:
    app_name, user_id = "case_review", "app_user"
    session_id = secrets.token_hex(8)  # groups this request's spans in Phoenix
    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    await runner.session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    prompt = "Review this case and return the JSON Readiness Check.\n\nCASE:\n" + json.dumps(
        payload.model_dump(), indent=2
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        if getattr(event, "content", None) and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final_text = part.text  # keep the latest model text

    return _extract_json(final_text)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")}


@app.post("/readiness")
async def readiness(payload: CasePayload) -> dict:
    review = await _run_review(payload)
    # Endpoint-level safety guarantee: every response carries a disclaimer and a
    # caselaw list, no matter how the review was produced.
    review.setdefault("disclaimer", DISCLAIMER)
    review.setdefault("related_caselaw", [])
    return review
