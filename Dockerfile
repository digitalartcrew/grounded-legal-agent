# Grounded Legal Agent — container for Cloud Run / Render / any host.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /srv

# Install dependencies via the project's pyproject (hatchling build).
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install .

EXPOSE 8080

# Cloud Run / Render inject $PORT; bind to it. Falls back to 8080 locally.
CMD ["sh", "-c", "uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
