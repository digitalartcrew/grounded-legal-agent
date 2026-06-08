"""Self-improvement loop: traces -> evals -> a better prompt.

Run:  python -m app.improve

This closes the evaluate→iterate loop. It:
  1. Pulls the agent's recent LLM spans from Phoenix (its own operational data),
  2. Judges them against the agent's rules to find FAILURES,
  3. Asks Gemini to rewrite the agent's system instruction to fix those failure
     modes, citing the concrete failing outputs,
  4. Writes the proposal to prompt_improvements.md for human review before it
     ships into app/agent.py.

You can also do this interactively in Gemini CLI with the Phoenix MCP server:
  "Find my lowest-scoring traces this week and suggest prompt fixes."
The MCP server exposes traces/prompts/datasets/experiments as tools, so the model
introspects its own runs without any custom glue. This script is the headless
version of that loop.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import phoenix as px
from phoenix.evals import GeminiModel, llm_classify
from phoenix.trace.dsl import SpanQuery

from app.agent import INSTRUCTION
from app.evals import EVALS, RAILS

PROJECT = os.environ.get("PHOENIX_PROJECT_NAME", "grounded-legal-agent")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def collect_failures(limit: int = 25) -> list[dict]:
    client = px.Client()
    query = (
        SpanQuery()
        .where("span_kind == 'LLM'")
        .select(input="input.value", output="output.value")
    )
    df = client.query_spans(query, project_name=PROJECT)
    if df is None or df.empty:
        return []
    df = df.tail(limit)

    judge = GeminiModel(model=MODEL)
    failures: list[dict] = []
    for eval_name, template in EVALS.items():
        res = llm_classify(dataframe=df, template=template, model=judge, rails=RAILS, provide_explanation=True)
        for idx, row in res.iterrows():
            if row.get("label") == "fail":
                failures.append(
                    {
                        "eval": eval_name,
                        "why": str(row.get("explanation", ""))[:400],
                        "output": str(df.loc[idx, "output"])[:600] if idx in df.index else "",
                    }
                )
    return failures


def propose_prompt(failures: list[dict]) -> str:
    from google import genai

    client = genai.Client()
    failure_text = "\n\n".join(
        f"- FAILED [{f['eval']}]: {f['why']}\n  Offending output: {f['output']}" for f in failures
    ) or "(no failures found in the sampled traces)"

    meta_prompt = f"""You are improving the system instruction for a self-help legal app's Case Review agent.
Here is the CURRENT instruction:
---
{INSTRUCTION}
---
Here are real failures from production traces (judged by LLM evals):
{failure_text}

Propose a REVISED system instruction that fixes these failure modes without weakening the JSON output
contract or the safety rules. Output: (1) a short bulleted list of the specific changes and WHY each
addresses a failure, then (2) the full revised instruction in a code block."""

    resp = client.models.generate_content(model=MODEL, contents=meta_prompt)
    return resp.text or ""


def main() -> None:
    if not (os.environ.get("PHOENIX_API_KEY") or "").strip():
        raise SystemExit("Set PHOENIX_API_KEY + PHOENIX_COLLECTOR_ENDPOINT first.")
    failures = collect_failures()
    print(f"Found {len(failures)} failing eval(s) across recent traces.")
    proposal = propose_prompt(failures)
    out = Path(__file__).resolve().parents[1] / "prompt_improvements.md"
    out.write_text(f"# Proposed prompt improvements\n\n{proposal}\n")
    print(f"Wrote {out}. Review it, then fold accepted changes into app/agent.py INSTRUCTION.")


if __name__ == "__main__":
    main()
