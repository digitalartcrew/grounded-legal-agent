"""Phoenix tracing for the Case Review agent.

Uses ``phoenix.otel.register(..., auto_instrument=True)``, which auto-loads the
installed OpenInference instrumentors (here: google-adk). Every Gemini call and
every tool span is exported to Phoenix Cloud over OTLP.

Docs: https://arize.com/docs/phoenix/integrations/python/google-adk/google-adk-tracing
Env: PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT, optional PHOENIX_PROJECT_NAME.
"""

from __future__ import annotations

import os
from typing import Any, Optional

_provider: Optional[Any] = None


def setup_tracing() -> Optional[Any]:
    """Register Phoenix tracing once. Returns the provider, or None if unconfigured.

    The app stays fully functional with no Phoenix key — it simply won't trace.
    """
    global _provider
    if _provider is not None:
        return _provider
    if not (os.environ.get("PHOENIX_API_KEY") or "").strip():
        return None

    from phoenix.otel import register

    _provider = register(
        project_name=os.environ.get("PHOENIX_PROJECT_NAME", "grounded-legal-agent"),
        batch=True,           # batch spans for a low-latency request path
        auto_instrument=True,  # picks up openinference-instrumentation-google-adk
        verbose=False,
    )
    return _provider
