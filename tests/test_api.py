"""HTTP contract for the demo API."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

import api.main as main
from api.main import MAX_BODY_BYTES, MAX_TEXT_LENGTH


@pytest.fixture
def client():
    main.reset_for_tests()
    return TestClient(main.app)


def test_pipeline_is_not_built_at_import(monkeypatch):
    import llm_guardrails.pipeline as pipeline_mod

    constructed: list[object] = []
    real = pipeline_mod.GuardrailsPipeline

    class Spy(real):
        def __init__(self, *args, **kwargs):
            constructed.append(object())
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(pipeline_mod, "GuardrailsPipeline", Spy)
    importlib.reload(main)
    try:
        assert constructed == []
    finally:
        monkeypatch.undo()
        importlib.reload(main)


def test_health_uses_package_version(client: TestClient):
    from importlib.metadata import version

    response = client.get("/health")
    assert response.status_code == 200
    reported = response.json()["version"]
    assert reported == version("llm_guardrails")
    assert reported != "0.1.0"


def test_text_over_max_length_is_rejected(client: TestClient):
    response = client.post("/guard/input", json={"text": "a" * (MAX_TEXT_LENGTH + 1)})
    assert response.status_code == 422
    assert "text" in response.text


def test_request_body_over_limit_is_rejected(client: TestClient):
    payload = b'{"text":"' + (b"a" * (MAX_BODY_BYTES + 64)) + b'"}'
    response = client.post(
        "/guard/input",
        content=payload,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    detail = response.json()["detail"]
    assert "body" in detail.lower()
    assert str(MAX_BODY_BYTES) in detail


def test_input_keeps_pii_mapping_server_side(client: TestClient):
    response = client.post(
        "/guard/input",
        json={"text": "Email alice@example.com please."},
    )
    assert response.status_code == 200
    body = response.json()
    assert "pii_mapping" not in body
    assert "alice@example.com" not in response.text
    assert body["sanitised_text"].count("<<EMAIL_") == 1
    assert isinstance(body["pii_mapping_id"], str)
    assert body["pii_mapping_id"]


def test_output_restores_from_mapping_id(client: TestClient):
    created = client.post(
        "/guard/input",
        json={"text": "Email alice@example.com please."},
    )
    created_body = created.json()
    response = client.post(
        "/guard/output",
        json={
            "text": f"Reply to {created_body['sanitised_text']}",
            "pii_mapping_id": created_body["pii_mapping_id"],
        },
    )
    assert response.status_code == 200
    assert "alice@example.com" in response.json()["final_text"]


def test_output_rejects_client_supplied_mapping(client: TestClient):
    response = client.post(
        "/guard/output",
        json={
            "text": "hello",
            "pii_mapping": {"<<EMAIL_1>>": "alice@example.com"},
        },
    )
    assert response.status_code == 422


def test_unknown_mapping_id_is_not_found(client: TestClient):
    response = client.post(
        "/guard/output",
        json={"text": "hello", "pii_mapping_id": "missing"},
    )
    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "expired" in detail or "unknown" in detail


def test_expired_mapping_id_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    created = client.post(
        "/guard/input",
        json={"text": "Email alice@example.com please."},
    )
    mapping_id = created.json()["pii_mapping_id"]
    monkeypatch.setattr(main, "MAPPING_TTL_SECONDS", -1)
    response = client.post(
        "/guard/output",
        json={"text": "hello", "pii_mapping_id": mapping_id},
    )
    assert response.status_code == 404


def test_full_restores_without_returning_the_mapping(client: TestClient):
    response = client.post(
        "/guard/full",
        json={"text": "Email alice@example.com please."},
    )
    assert response.status_code == 200
    body = response.json()
    assert "pii_mapping" not in body["input_guard"]
    assert "alice@example.com" not in body["input_guard"]["sanitised_text"]
    assert "alice@example.com" in body["output_guard"]["final_text"]
