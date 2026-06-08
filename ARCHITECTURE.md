# Architecture

One code-owned Gemini agent, callable by any client, traced end-to-end.

```
 your client(s) ──▶  grounded-legal-agent  ──┬─ Gemini (gemini-2.5-flash)
 (web / mobile /     (Google ADK, FastAPI)   ├─ search_caselaw tool (CourtListener)
  CLI / anything)            │               └─ OpenInference → Phoenix Cloud
                             │
                             ├─ traces every Gemini + tool call
                             ├─ evals.py   → LLM-as-a-judge scores on each trace
                             ├─ improve.py → traces + evals → a proposed better prompt
                             └─ .gemini/settings.json → Phoenix MCP (self-introspection)
```

## Why this shape

The interesting part of an LLM in a high-stakes domain isn't the model call — it's
the scaffolding that keeps it safe and lets you *prove* it stayed safe. This repo is
a small, readable reference for four pieces of that scaffolding:

1. **A grounding boundary** so the model cannot fabricate facts.
   In [`app/tools.py`](app/tools.py) the model proposes neutral *search topics*; the
   code fetches real opinions from CourtListener; only real, linkable cases reach the
   user. Fabricated citations are the failure mode that has gotten real lawyers
   sanctioned — here it's structurally prevented, not just discouraged.

2. **Safety as a measured SLA, not a hope.**
   [`app/evals.py`](app/evals.py) turns the agent's hard rules — *no legal advice, no
   outcome prediction, grounded citations, calm tone* — into LLM-as-a-judge scores on
   every trace. A regression becomes a visible metric instead of a user complaint.

3. **Full inspectability.**
   OpenInference auto-instrumentation ([`app/instrumentation.py`](app/instrumentation.py))
   makes every Gemini decision and every tool lookup a span in Phoenix, so you can
   show the agent followed a real tool result rather than inventing one.

4. **A closed evaluate → iterate loop.**
   [`app/improve.py`](app/improve.py) reads the lowest-scoring traces and asks the
   model to rewrite its own system instruction to fix those exact failures — written
   to `prompt_improvements.md` for human review before anything ships.

## Files

| File | Role |
|---|---|
| [`app/agent.py`](app/agent.py) | The ADK agent: model, system instruction (safety rules + JSON contract), tool wiring. |
| [`app/tools.py`](app/tools.py) | `search_caselaw` — the grounding boundary (CourtListener). |
| [`app/server.py`](app/server.py) | FastAPI: `POST /readiness`, `GET /health`. One request = one traced agent turn. |
| [`app/instrumentation.py`](app/instrumentation.py) | Phoenix tracing setup (degradable — no key = no tracing, app still runs). |
| [`app/evals.py`](app/evals.py) | Four LLM-as-a-judge evals, logged back onto each trace. |
| [`app/improve.py`](app/improve.py) | Traces + evals → a proposed improved prompt. |

## Swapping pieces

- **Different data source.** Replace `search_caselaw` with any retrieval that returns
  real records (a statute API, an internal document store). The pattern — *model picks
  the query, code owns the fetch* — is what generalizes.
- **Different model/provider.** The agent is Google ADK + Gemini today. The grounding,
  eval, and self-improvement patterns are provider-agnostic; porting means swapping the
  `Agent`/judge construction.
- **Different domain.** The same scaffolding fits any domain where the model must not
  fabricate and must obey hard rules — edit the instruction in `agent.py` and the
  rubrics in `evals.py` together.
