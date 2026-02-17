# ── Rust build stage ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install maturin
RUN uv pip install --system --no-cache maturin

# Copy Rust + Python source
COPY Cargo.toml Cargo.lock ./
COPY src/ src/
COPY pyproject.toml README.md ./
COPY llm_guardrails/ llm_guardrails/
COPY api/ api/

# Build the wheel
RUN maturin build --release --out dist

# ── Runtime stage ─────────────────────────────────────────────────────
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install the built wheel + API dependencies
COPY --from=builder /app/dist/*.whl /tmp/
RUN uv pip install --system --no-cache /tmp/*.whl && \
    uv pip install --system --no-cache "fastapi>=0.110,<1.0" "uvicorn[standard]>=0.29,<1.0" && \
    rm -rf /tmp/*.whl

COPY api/ api/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
