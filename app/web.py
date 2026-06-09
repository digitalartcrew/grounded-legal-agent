"""The web UI for the Case Review agent.

A single self-contained page (no external CDNs, no third-party assets) served at
``GET /`` by the FastAPI app. It posts a case to ``/readiness`` and renders the
Readiness Check. Kept as a Python string so it ships wherever the package does.
"""

from __future__ import annotations

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Grounded Legal Agent — Readiness Check</title>
<style>
  :root {
    --bg: #0f1115; --panel: #171a21; --panel-2: #1e222b; --line: #2a2f3a;
    --text: #e7e9ee; --muted: #9aa3b2; --accent: #6ea8fe;
    --good: #4ade80; --warn: #fbbf24; --bad: #f87171;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  a { color: var(--accent); }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 28px 20px 80px; }
  header h1 { margin: 0 0 4px; font-size: 24px; letter-spacing: -0.01em; }
  header p.tag { margin: 0; color: var(--muted); }
  .disclaimer {
    margin: 16px 0 24px; padding: 12px 14px; border: 1px solid var(--line);
    border-left: 3px solid var(--warn); border-radius: 8px; background: var(--panel);
    color: var(--muted); font-size: 13px;
  }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start; }
  @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }
  .card h2 { margin: 0 0 14px; font-size: 15px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
  label { display: block; font-size: 13px; color: var(--muted); margin: 12px 0 5px; }
  input, select, textarea {
    width: 100%; background: var(--panel-2); color: var(--text);
    border: 1px solid var(--line); border-radius: 8px; padding: 9px 11px; font: inherit;
  }
  textarea { resize: vertical; min-height: 70px; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .actions { display: flex; gap: 10px; margin-top: 18px; align-items: center; }
  button {
    background: var(--accent); color: #0b0e14; border: 0; border-radius: 8px;
    padding: 10px 18px; font: inherit; font-weight: 650; cursor: pointer;
  }
  button.secondary { background: transparent; color: var(--text); border: 1px solid var(--line); font-weight: 500; }
  button:disabled { opacity: .55; cursor: progress; }
  .hint { font-size: 12px; color: var(--muted); }
  #status { min-height: 18px; font-size: 13px; color: var(--muted); margin-top: 10px; }
  .spinner { display: inline-block; width: 13px; height: 13px; border: 2px solid var(--line);
    border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite; vertical-align: -2px; margin-right: 7px; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* results */
  #result { margin-top: 26px; display: none; }
  #result.show { display: block; }
  .summary { font-size: 16px; line-height: 1.6; }
  ul.clean { margin: 0; padding-left: 18px; }
  ul.clean li { margin: 6px 0; }
  .badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 650; }
  .badge.low { background: rgba(74,222,128,.15); color: var(--good); }
  .badge.medium { background: rgba(251,191,36,.15); color: var(--warn); }
  .badge.high { background: rgba(248,113,113,.15); color: var(--bad); }
  .badge.clear { background: rgba(74,222,128,.15); color: var(--good); }
  .badge.mixed { background: rgba(251,191,36,.15); color: var(--warn); }
  .badge.unclear { background: rgba(248,113,113,.15); color: var(--bad); }
  .case { border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; margin: 10px 0; background: var(--panel-2); }
  .case .name { font-weight: 650; }
  .case .meta { font-size: 12px; color: var(--muted); margin-top: 3px; }
  .case .cite { color: var(--text); }
  .full-span { grid-column: 1 / -1; }
  .error { border-left-color: var(--bad); color: #fecaca; }
  footer { margin-top: 40px; color: var(--muted); font-size: 12px; text-align: center; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>⚖️ Grounded Legal Agent</h1>
    <p class="tag">A safety-grounded case <strong>Readiness Check</strong> — powered by Gemini, grounded in real case law, traced &amp; evaluated with Arize Phoenix.</p>
  </header>

  <div class="disclaimer">
    This is automated self-help <strong>preparation</strong>, not legal advice, and does not predict any court
    outcome. This software is not a law firm. Consider consulting a licensed attorney in your jurisdiction.
  </div>

  <div class="grid">
    <!-- INPUT -->
    <form class="card" id="form">
      <h2>Your case</h2>
      <label for="matterLabel">Matter</label>
      <input id="matterLabel" placeholder="e.g. Restraining order" />
      <div class="row">
        <div>
          <label for="state">State</label>
          <input id="state" placeholder="e.g. California" />
        </div>
        <div>
          <label for="role">Your role</label>
          <select id="role">
            <option value="petitioner">Petitioner</option>
            <option value="respondent">Respondent</option>
            <option value="plaintiff">Plaintiff</option>
            <option value="defendant">Defendant</option>
          </select>
        </div>
      </div>
      <label for="summary">Case summary</label>
      <textarea id="summary" placeholder="Briefly describe what happened and what you are asking for."></textarea>
      <label for="relief">Relief sought</label>
      <input id="relief" placeholder="e.g. A two-year restraining order with stay-away provisions." />

      <label for="timeline">Timeline <span class="hint">— one per line, format: <code>YYYY-MM-DD | what happened</code></span></label>
      <textarea id="timeline" placeholder="2026-04-18 | Respondent appeared uninvited at workplace."></textarea>

      <label for="evidence">Evidence <span class="hint">— one per line, format: <code>type | description</code></span></label>
      <textarea id="evidence" placeholder="screenshots | Message thread showing the threat."></textarea>

      <div class="actions">
        <button type="submit" id="submit">Run Readiness Check</button>
        <button type="button" class="secondary" id="example">Load example</button>
      </div>
      <div id="status"></div>
    </form>

    <!-- WHY IT'S SAFE -->
    <div class="card">
      <h2>How this stays trustworthy</h2>
      <ul class="clean">
        <li><strong>Grounding boundary.</strong> The model proposes search topics; code fetches <strong>real</strong> opinions from CourtListener. Citations are never invented.</li>
        <li><strong>No legal advice, no outcome prediction.</strong> It produces preparation only, and recommends an attorney by case <em>complexity</em> — never odds of winning.</li>
        <li><strong>Measured safety.</strong> Four LLM-as-a-judge evals score every traced output in Arize Phoenix.</li>
        <li><strong>Fully inspectable.</strong> Every model and tool call is a span in Phoenix.</li>
      </ul>
      <p class="hint">Tip: the Readiness Check call runs a live Gemini turn plus real case-law lookups, so it typically takes ~15–30 seconds.</p>
    </div>
  </div>

  <!-- RESULT -->
  <div id="result"></div>

  <footer>
    Open source (Apache-2.0) · Running on Google Cloud Run · Not legal advice.
  </footer>
</div>

<script>
const EXAMPLE = {
  matterLabel: "Restraining order",
  state: "California",
  role: "petitioner",
  summary: "Petitioner seeks a restraining order against a former partner after repeated unwanted contact and one in-person threat. The parties share no children. Petitioner has moved to a new address.",
  relief: "A two-year restraining order with stay-away and no-contact provisions.",
  timeline: [
    "2026-03-02 | Relationship ended; petitioner moved out.",
    "2026-04-18 | Respondent appeared uninvited at petitioner's workplace.",
    "2026-04-25 | Respondent sent ~20 messages in one night, including 'you can't hide from me'.",
    "2026-05-01 | Petitioner filed a police report (report #2026-10482)."
  ].join("\n"),
  evidence: [
    "screenshots | Message thread from 2026-04-25 showing volume and the quoted threat.",
    "police_report | Filed 2026-05-01, documents the workplace visit and messages.",
    "witness | Coworker who saw the respondent at the workplace on 2026-04-18."
  ].join("\n")
};

const $ = (id) => document.getElementById(id);

$("example").addEventListener("click", () => {
  for (const k of ["matterLabel","state","role","summary","relief","timeline","evidence"]) $(k).value = EXAMPLE[k];
});

function parseLines(text, keys) {
  return text.split("\n").map(l => l.trim()).filter(Boolean).map(line => {
    const parts = line.split("|").map(s => s.trim());
    const obj = {};
    keys.forEach((k, i) => obj[k] = parts[i] || "");
    return obj;
  });
}

function buildPayload() {
  return {
    matterContext: ($("matterLabel").value || "") + ($("state").value ? " — " + $("state").value : ""),
    matterLabel: $("matterLabel").value,
    case: {
      state: $("state").value,
      role: $("role").value,
      summary: $("summary").value,
      reliefSought: $("relief").value
    },
    timeline: parseLines($("timeline").value, ["date", "event"]),
    evidence: parseLines($("evidence").value, ["type", "description"]),
    statementAnalyses: []
  };
}

function esc(s) { return String(s == null ? "" : s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function list(items) { return "<ul class='clean'>" + (items||[]).map(i => "<li>" + esc(i) + "</li>").join("") + "</ul>"; }

function render(r) {
  const ar = r.attorney_recommendation || {};
  const ea = r.evidence_assessment || {};
  const cases = (r.related_caselaw || []).map(c => `
    <div class="case">
      <div class="name"><a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.caseName)}</a></div>
      <div class="meta"><span class="cite">${esc(c.citation || "no reporter citation")}</span> · ${esc(c.court)} ${c.dateFiled ? "· " + esc(c.dateFiled) : ""}</div>
    </div>`).join("") || "<p class='hint'>No matching opinions returned.</p>";

  return `
    <div class="card full-span">
      <h2>Readiness summary</h2>
      <p class="summary">${esc(r.readiness_summary)}</p>
    </div>
    <div class="grid" style="margin-top:24px">
      <div class="card"><h2>Strengths</h2>${list(r.strengths)}</div>
      <div class="card"><h2>Gaps to address</h2>${list(r.gaps)}</div>
      <div class="card">
        <h2>Evidence assessment</h2>
        <p><span class="badge ${esc(ea.clarity)}">${esc(ea.clarity)}</span></p>
        <p>${esc(ea.notes)}</p>
      </div>
      <div class="card">
        <h2>Attorney recommendation <span class="hint">(by complexity, not odds)</span></h2>
        <p><span class="badge ${esc(ar.level)}">${esc(ar.level)}</span> &nbsp; confidence: ${esc(ar.confidence)}</p>
        ${list(ar.reasons)}
      </div>
      <div class="card"><h2>Suggested actions</h2>${list(r.suggested_actions)}</div>
      <div class="card"><h2>Real related case law</h2>${cases}</div>
    </div>
    <div class="disclaimer" style="margin-top:24px">${esc(r.disclaimer)}</div>
  `;
}

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("submit"), status = $("status"), result = $("result");
  btn.disabled = true;
  status.innerHTML = "<span class='spinner'></span>Reasoning with Gemini and fetching real case law… (~15–30s)";
  result.className = ""; result.innerHTML = "";
  try {
    const resp = await fetch("/readiness", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(buildPayload())
    });
    if (!resp.ok) throw new Error("Server returned " + resp.status);
    const data = await resp.json();
    result.innerHTML = render(data);
    result.className = "show";
    status.textContent = "Done.";
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    status.innerHTML = "";
    result.innerHTML = "<div class='card disclaimer error full-span'>Could not complete the readiness check: " + esc(err.message) + ". Make sure the server has a GOOGLE_API_KEY configured.</div>";
    result.className = "show";
  } finally {
    btn.disabled = false;
  }
});
</script>
</body>
</html>
"""
