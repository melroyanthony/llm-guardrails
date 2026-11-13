# ── Rust build stage ──────────────────────────────────────────────────
# python:3.14-slim index digest. Dependabot's weekly docker group moves
# this digest. The tag stays 3.14-slim; versions >= 3.15 are ignored.
FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS builder

# rustup-init 1.29.3. The compiler channel stays stable, matching
# rust-toolchain.toml. These checksums change only when RUSTUP_VERSION is
# bumped on purpose. Dependabot does not refresh them.
ARG RUSTUP_VERSION=1.29.3
COPY scripts/verify_rustup_init.sh /usr/local/bin/verify_rustup_init.sh
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl build-essential \
    && arch="$(dpkg --print-architecture)" \
    && case "$arch" in \
         amd64) triple=x86_64-unknown-linux-gnu; expected=b1c8cb14e30889e7e2999e6b69e62d9e9b9ffc0f4df8180564d306d9680e6c55 ;; \
         arm64) triple=aarch64-unknown-linux-gnu; expected=9f608c142e0e38a78957d0661ba1dfaf0b6fb37184cfaa4b9a0aa57af6184282 ;; \
         *) echo "unsupported architecture: $arch" >&2; exit 1 ;; \
       esac \
    && curl -fsSL -o /tmp/rustup-init \
         "https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/${triple}/rustup-init" \
    && sh /usr/local/bin/verify_rustup_init.sh /tmp/rustup-init "$expected" \
    && chmod +x /tmp/rustup-init \
    && /tmp/rustup-init -y --default-toolchain stable --profile minimal \
    && rm -rf /var/lib/apt/lists/* /tmp/rustup-init

ENV PATH="/root/.cargo/bin:${PATH}"

# ghcr.io/astral-sh/uv:0.13.7 index digest. The same Dependabot docker
# group moves this digest.
COPY --from=ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 /uv /usr/local/bin/uv

WORKDIR /app

# Install maturin. The pin matches the release workflow.
RUN uv pip install --system --no-cache "maturin==1.16.0"

# Copy Rust + Python source
COPY Cargo.toml Cargo.lock ./
COPY src/ src/
COPY pyproject.toml README.md ./
COPY llm_guardrails/ llm_guardrails/
COPY api/ api/

# Build the wheel
RUN maturin build --release --out dist

# ── Runtime stage ─────────────────────────────────────────────────────
FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

COPY --from=ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 /uv /usr/local/bin/uv

WORKDIR /app

# Install the built wheel + API dependencies
COPY --from=builder /app/dist/*.whl /tmp/
RUN uv pip install --system --no-cache /tmp/*.whl && \
    uv pip install --system --no-cache "fastapi>=0.110,<1.0" "uvicorn[standard]>=0.54.0,<1.0" && \
    rm -rf /tmp/*.whl

COPY api/ api/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
