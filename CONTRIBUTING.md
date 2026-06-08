# Contributing

Thanks for your interest! This project is a reference architecture, so contributions
that make the patterns clearer, safer, or more portable are especially welcome.

## Ground rules

- **Keep it safe.** This agent gives legal-adjacent guidance to vulnerable people. Any
  change must preserve the four hard rules (no legal advice, no outcome prediction,
  grounded citations only, calm factual tone). If you touch the system instruction in
  [`app/agent.py`](app/agent.py), update the matching rubric in
  [`app/evals.py`](app/evals.py) in the same PR.
- **The grounding boundary is sacred.** The model must never be able to emit a citation
  that didn't come from a real tool result. Don't add code paths that let it.
- **Stay readable.** This is teaching code. Prefer clarity over cleverness, and keep the
  module docstrings accurate.

## Dev setup

```bash
uv sync                # or: pip install -e .
cp .env.example .env   # GOOGLE_API_KEY required; Phoenix optional
uvicorn app.server:app --port 8080
```

## Good first issues

- A **provider abstraction** so the agent and the eval judge can run on Claude or
  OpenAI alongside Gemini.
- More **eval rubrics** (e.g. jurisdiction-appropriateness, reading level).
- **Tests** — a smoke test for `search_caselaw` parsing and `_extract_json`, and a
  mocked end-to-end `/readiness` test.
- Additional **grounded data sources** (statutes, court forms) behind the same
  "model picks the query, code owns the fetch" boundary.

## PRs

1. Fork and branch off `main`.
2. Make the change; note any change to the safety rules or eval rubrics explicitly.
3. Open a PR describing *what* changed and *why it stays safe*.

By contributing, you agree your contributions are licensed under the project's
[Apache-2.0](LICENSE) license.
