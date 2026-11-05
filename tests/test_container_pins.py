"""The demo image pins published artifacts and checks the Rust installer."""

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
SECURITY = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
VERIFIER = ROOT / "scripts" / "verify_rustup_init.sh"

PYTHON_DIGEST = "sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54"
UV_DIGEST = "sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490"
RUSTUP_VERSION = "1.29.3"
RUSTUP_AMD64 = "b1c8cb14e30889e7e2999e6b69e62d9e9b9ffc0f4df8180564d306d9680e6c55"
RUSTUP_ARM64 = "9f608c142e0e38a78957d0661ba1dfaf0b6fb37184cfaa4b9a0aa57af6184282"
ACKNOWLEDGEMENT = (
    "We will acknowledge a report within 3 business days. We will keep you "
    "informed while we investigate and work on a fix. We will credit you in "
    "the release notes when the fix ships, unless you prefer to stay anonymous."
)


def test_base_images_and_uv_are_digest_pinned():
    assert DOCKERFILE.count(f"python:3.12-slim@{PYTHON_DIGEST}") == 2
    assert DOCKERFILE.count(f"ghcr.io/astral-sh/uv:0.13.7@{UV_DIGEST}") == 2
    assert "python:3.12-slim\n" not in DOCKERFILE
    assert "uv:0.13.7 /uv" not in DOCKERFILE


def test_rustup_installer_is_checksum_verified_and_channel_stays_stable():
    assert "https://sh.rustup.rs" not in DOCKERFILE
    assert f"ARG RUSTUP_VERSION={RUSTUP_VERSION}" in DOCKERFILE
    assert "rustup/archive/${RUSTUP_VERSION}/" in DOCKERFILE
    assert RUSTUP_AMD64 in DOCKERFILE
    assert RUSTUP_ARM64 in DOCKERFILE
    assert "verify_rustup_init.sh" in DOCKERFILE
    assert "--default-toolchain stable" in DOCKERFILE
    assert "/" + "tmp/rustup-init -y --default-toolchain stable" in DOCKERFILE
    script = VERIFIER.read_text(encoding="utf-8")
    assert "sha256sum" in script


def test_readme_documents_digest_updates_and_installer_refresh():
    assert "Dependabot" in README
    assert "docker" in README
    assert RUSTUP_VERSION in README


def test_security_policy_names_disclosure_without_a_new_contact_or_deadline():
    assert "disclosure" in SECURITY.lower()
    assert "https://github.com/melroyanthony/llm-guardrails/security/advisories/new" in SECURITY
    assert ACKNOWLEDGEMENT in SECURITY
    assert "@" not in SECURITY.split("https://", 1)[1]


def test_checksum_mismatch_fails_and_a_match_passes(tmp_path):
    blob = tmp_path / "rustup-init"
    blob.write_bytes(b"not-the-installer")
    mismatch = subprocess.run(  # noqa: S603
        ["/bin/sh", str(VERIFIER), str(blob), "a" * 64],
        check=False,
        capture_output=True,
        text=True,
    )
    assert mismatch.returncode != 0
    assert "checksum mismatch" in mismatch.stderr
    actual = hashlib.sha256(blob.read_bytes()).hexdigest()
    match = subprocess.run(  # noqa: S603
        ["/bin/sh", str(VERIFIER), str(blob), actual],
        check=False,
        capture_output=True,
        text=True,
    )
    assert match.returncode == 0
