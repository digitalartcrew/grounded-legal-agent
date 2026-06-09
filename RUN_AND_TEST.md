# Run & Test Locally

Step-by-step instructions to run the Grounded Legal Agent on your machine and
verify it works. Every command below was run on macOS (Apple Silicon) and confirmed
working — see [Verified results](#verified-results) at the bottom.

> **TL;DR**
> ```bash
> uv sync                                            # install Python 3.12 + deps
> cp .env.example .env                               # then add GOOGLE_API_KEY
> uv run uvicorn app.server:app --port 8080          # start the server
> curl -s localhost:8080/health                      # smoke test
> ```

---

## 1. Prerequisites

- **`uv`** (recommended) — handles Python + dependencies in one step and auto-downloads
  a compatible interpreter. This matters: the project requires **Python 3.10–3.12**
  (`requires-python = ">=3.10,<3.13"` in `pyproject.toml`), so a system Python 3.13+
  will *not* work. `uv` sidesteps that by fetching its own 3.12.

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source $HOME/.local/bin/env            # add uv to PATH for this shell
  ```
  > Add `source $HOME/.local/bin/env` to your `~/.zshrc` so `uv` is on PATH in every
  > new terminal. Otherwise prefix commands with the full path or re-source it.

- **A Google Gemini API key** (required) — free from
  [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

- **`jq`** (optional) — pretty-prints JSON responses. Pre-installed on most macOS setups.

---

## 2. Install dependencies

```bash
uv sync
```

This creates a `.venv/` with Python 3.12 and installs everything from `pyproject.toml`
(Google ADK, FastAPI, Arize Phoenix, etc.).

---

## 3. Configure secrets

```bash
cp .env.example .env
```

Open `.env` and fill in the keys. **Only `GOOGLE_API_KEY` is required to run.**

| Variable | Required? | Notes |
|---|---|---|
| `GOOGLE_API_KEY` | ✅ **Required** | The agent runtime won't start without it. |
| `PHOENIX_API_KEY` + `PHOENIX_COLLECTOR_ENDPOINT` | Optional | Enables tracing & the eval/improve loops. Without it, reviews still work — just untraced. |
| `COURTLISTENER_TOKEN` | Optional | Case-law search works anonymously without a token. |
| `GEMINI_MODEL` | Optional | Defaults to `gemini-2.5-flash`. |
| `ALLOWED_ORIGINS` | Optional | CORS origins; `*` is fine for local dev. |

---

## 4. Run the server

```bash
uv run uvicorn app.server:app --port 8080
```

Leave this running. Open a **second terminal** for the test calls below.

---

## 5. Test it

### Health check (fast)
```bash
curl -s localhost:8080/health
```
Expected:
```json
{"ok":true,"model":"gemini-2.5-flash"}
```

### Readiness check (the real thing — calls Gemini + fetches real case law, ~20–30s)
```bash
curl -s -X POST localhost:8080/readiness \
  -H 'content-type: application/json' \
  --data @examples/sample_case.json | jq .
```

This POSTs the sample case in [`examples/sample_case.json`](examples/sample_case.json) and
returns a structured **Readiness Check**. A captured copy of a real response is saved at
[`examples/sample_readiness_output.json`](examples/sample_readiness_output.json) so you can
see the expected shape without running the agent.

To stop the server: `pkill -f "uvicorn app.server"`.

---

## 6. (Optional) Evaluate & self-improve — requires Phoenix

These read traces from Phoenix, so they need `PHOENIX_API_KEY` +
`PHOENIX_COLLECTOR_ENDPOINT` set in `.env`:

```bash
uv run python -m app.evals      # LLM-as-judge scores the 4 safety rules on each trace
uv run python -m app.improve    # reads failing traces -> proposes a better system prompt
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `zsh: command not found: uv` | Run `source $HOME/.local/bin/env` (or restart your shell). |
| Server exits immediately / agent errors on startup | `GOOGLE_API_KEY` is missing or empty in `.env`. |
| `uv sync` complains about Python version | Run `uv python install 3.12` first; `uv` will use it automatically. |
| `/readiness` returns case items with empty `citation` | Normal — not every real opinion has a reporter citation; the `url` always links to the real CourtListener opinion. |
| Port 8080 in use | Use `--port 8081` (and update the curl URL). |

---

## Verified results

The following was run end-to-end on macOS (Apple Silicon), Python 3.12.13:

```
GET  /health    -> 200  {"ok":true,"model":"gemini-2.5-flash"}
POST /readiness -> 200  in ~28s
```

The `/readiness` response returned a complete structured Readiness Check and — the key
safety property — **8 real case-law items grounded via the CourtListener tool**, each
with a verifiable opinion URL and, where available, a real reporter citation
(e.g. `594 U.S. 295`, `984 F.3d 744`, `249 Cal. Rptr. 3d 391`). The model did not invent
citations; the grounding boundary worked as designed.

See the full captured response in
[`examples/sample_readiness_output.json`](examples/sample_readiness_output.json).
