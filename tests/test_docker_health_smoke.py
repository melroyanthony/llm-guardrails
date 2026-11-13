"""The demo image is built in CI and /health must return 200."""

from __future__ import annotations

import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "docker_health_smoke.sh"
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1"


def _serve(status: int) -> tuple[ThreadingHTTPServer, int]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = b'{"status":"ok"}' if status == 200 else b'{"status":"bad"}'
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]


def _run(url: str, timeout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["/bin/sh", str(SCRIPT), url, timeout],
        check=False,
        capture_output=True,
        text=True,
    )


def test_http_200_is_accepted():
    server, port = _serve(200)
    try:
        result = _run(f"http://127.0.0.1:{port}/health", "5")
    finally:
        server.shutdown()
    assert result.returncode == 0, result.stderr


def test_other_http_status_fails_immediately():
    server, port = _serve(503)
    try:
        result = _run(f"http://127.0.0.1:{port}/health", "30")
    finally:
        server.shutdown()
    assert result.returncode == 1
    assert "HTTP 503" in result.stderr


def test_unreachable_url_hits_the_timeout():
    result = _run("http://127.0.0.1:9/health", "1")
    assert result.returncode == 1
    assert "timed out" in result.stderr


def test_ci_builds_the_image_and_does_not_push_it():
    start = CI.index("  docker:\n")
    job = CI[start:]
    assert "name: Docker smoke" in job
    assert "contents: read" in job.split("steps:", 1)[0]
    assert "docker build --tag llm-guardrails:ci ." in job
    assert "docker_health_smoke.sh" in job
    assert "docker push" not in CI
    assert "docker/login-action" not in CI
    assert CHECKOUT in job
