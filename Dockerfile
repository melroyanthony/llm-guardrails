# ── Build stage ────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency metadata first for layer caching
COPY pyproject.toml ./

# Install runtime + api dependencies via uv
RUN uv pip install --system --no-cache ".[api]"

# Copy application code
COPY llm_guardrails/ llm_guardrails/
COPY api/ api/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
