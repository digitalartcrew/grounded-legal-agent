# Grounded Legal Agent

A small, readable **reference architecture** for safely grounding an LLM agent in
**real case law** — and proving it stayed safe. It's a code-owned **Gemini** agent
(Google ADK) that is **traced**, **evaluated**, and **self-improving** end-to-end via
**Arize Phoenix** (OpenInference).

The interesting part isn't "an LLM reviews a legal case." It's the scaffolding around
the model that most legal-AI demos skip:

- **A grounding boundary** so the model *cannot* invent citations — it proposes search
  topics, code fetches real opinions from CourtListener, only real cases reach the user.
- **Safety as a measured SLA** — four LLM-as-a-judge evals (*no legal advice, no outcome
  prediction, grounded citations, calm tone*) scored on every trace.
- **Full inspectability** — every model call and tool call is a span in Phoenix.
- **A closed loop** — the agent reads its own lowest-scoring traces and proposes a
  better prompt.

If you're building an LLM feature in *any* high-stakes domain, the patterns here
(grounding, evals-as-guardrails, self-improvement) are meant to be lifted and adapted.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the design and how to swap pieces.

> ## ⚠️ This is not legal advice, and not a law firm
>
> This software is a **developer reference**, provided **"as is" without warranty**
> (see [LICENSE](LICENSE)). Its output is automated self-help *preparation*, not legal
> advice, and it does **not** predict court outcomes. Deploying an LLM that interacts
> with the public about legal matters can implicate **unauthorized-practice-of-law
> (UPL)** rules and other regulations that vary by jurisdiction. **You** are responsible
> for legal review, appropriate disclaimers, and compliance before any production or
> public use. Nothing here creates an attorney–client relationship.

## What it does

A self-represented person's case (summary, timeline, evidence) is POSTed in. The agent:

1. Reasons about the case with **Gemini** (`gemini-2.5-flash` by default).
2. Calls the **`search_caselaw`** tool (CourtListener) for real, linkable opinions —
   the model never invents citations.
3. Returns a structured **Readiness Check**: strengths, gaps, an evidence-clarity
   assessment, an attorney-recommendation band (about case *complexity*, not odds),
   suggested actions, and real case law.

Every Gemini call and every tool call is a **span in Phoenix**.

## Quickstart

```bash
git clone <your-fork-url> grounded-legal-agent && cd grounded-legal-agent
uv sync                       # or: pip install -e .
cp .env.example .env          # fill in GOOGLE_API_KEY (Phoenix optional)
uvicorn app.server:app --port 8080
```

Then call it:

```bash
curl -s localhost:8080/health
curl -s -X POST localhost:8080/readiness \
  -H 'content-type: application/json' \
  --data @examples/sample_case.json | jq .
```

- **Gemini key:** an AI Studio `GOOGLE_API_KEY` (or the Vertex path in `.env.example`).
- **Phoenix (optional):** a free account at app.phoenix.arize.com → API key
  (`px_live_...`) + the Hostname (with `/s/<space>`) as `PHOENIX_COLLECTOR_ENDPOINT`.

The service is **degradable**: with no `PHOENIX_API_KEY` it still serves reviews, just
untraced. Without `GOOGLE_API_KEY` it won't run — that's the agent runtime.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET`  | `/health` | — | `{ "ok": true, "model": "..." }` |
| `POST` | `/readiness` | a case JSON (see [`examples/sample_case.json`](examples/sample_case.json)) | the Readiness Check JSON |

The request shape is defined by `CasePayload` in [`app/server.py`](app/server.py) and is
deliberately loose — adapt the fields to your own client. The agent reads the whole
payload as context.

## Evaluate

```bash
python -m app.evals      # LLM-as-a-judge over the traces, logged back to Phoenix
```

Four judges score the agent's hard rules on every traced output: **No Legal Advice**,
**No Outcome Prediction**, **Citation Grounding** (no hallucinated cites), **Calm
Factual Tone**. Scores appear on each trace in Phoenix. Edit the rubrics in
[`app/evals.py`](app/evals.py) alongside the agent's instruction in `app/agent.py`.

## Self-improve (the closed loop)

```bash
python -m app.improve    # traces -> evals -> a proposed better prompt
```

Pulls recent failing traces + eval explanations, asks Gemini to rewrite the agent's
system instruction to fix those exact failure modes, and writes the proposal to
`prompt_improvements.md` for **human review** before it ships into `app/agent.py`.

### Phoenix MCP — runtime self-introspection

[`.gemini/settings.json`](.gemini/settings.json) registers the Phoenix MCP server, so in
a Gemini CLI session you can ask the model to query its *own* traces, prompts, datasets,
and experiments:

> "Show my lowest-scoring traces this week and suggest prompt fixes."

Set `--baseUrl`/`--apiKey` (or export `PHOENIX_API_KEY`). This is the interactive twin of
`app/improve.py`.

## Deploy

The agent needs a public **HTTPS** URL for real clients to reach it. A `Dockerfile` is
included.

### Cloud Run

```bash
gcloud run deploy grounded-legal-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash,PHOENIX_PROJECT_NAME=grounded-legal-agent,ALLOWED_ORIGINS=https://your-client.example.com \
  --set-env-vars GOOGLE_API_KEY=...,PHOENIX_API_KEY=...,PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/<space>,COURTLISTENER_TOKEN=...
```

Cloud Run injects `$PORT` (the container binds to it). For production, prefer
`--set-secrets` (Secret Manager) over `--set-env-vars` for the keys, and set
`ALLOWED_ORIGINS` to your real client origin(s) rather than `*`.

### Render

Push to GitHub → Render → **New → Blueprint** → pick the repo
([`render.yaml`](render.yaml) is included). Set the `sync: false` secrets in the
dashboard. (Free tier cold-starts after idle.)

### Test against a real device without deploying

```bash
uvicorn app.server:app --port 8080
npx cloudflared tunnel --url http://localhost:8080   # gives an https URL
```

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Good first
contributions: a provider abstraction (Claude/OpenAI alongside Gemini), more eval
rubrics, tests, and additional grounded data sources.

## License

[Apache-2.0](LICENSE).
# grounded-legal-agent
