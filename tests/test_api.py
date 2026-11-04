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
    assert reported == version("ferroguard")
    assert reported != "0.1.0"


def test_text_over_max_length_is_rejected(client: TestClient):
    response = client.post("/guard/input", json={"text": "a" * (MAX_TEXT_LENGTH + 1)})
    assert response.status_code == 422
    assert "text" in response.text


def test_chunked_body_without_content_length_stops_early():
    import asyncio

    chunk = b"a" * 4096
    offered = (MAX_BODY_BYTES // len(chunk)) + 12
    pulled = 0

    async def receive():
        nonlocal pulled
        pulled += 1
        if pulled > offered:
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": chunk, "more_body": True}

    async def run():
        messages: list[dict] = []
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/guard/input",
            "raw_path": b"/guard/input",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }

        async def send(message):
            messages.append(message)

        await main.app(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        assert start["status"] == 413
        assert pulled <= (MAX_BODY_BYTES // len(chunk)) + 2

    asyncio.run(run())


def test_small_chunked_body_without_content_length_is_accepted():
    import asyncio

    parts = [b'{"text":', b'"hello"', b"}"]
    index = 0

    async def receive():
        nonlocal index
        if index >= len(parts):
            return {"type": "http.disconnect"}
        body = parts[index]
        index += 1
        return {"type": "http.request", "body": body, "more_body": index < len(parts)}

    async def run():
        messages: list[dict] = []
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/guard/input",
            "raw_path": b"/guard/input",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }

        async def send(message):
            messages.append(message)

        await main.app(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        assert start["status"] == 200

    main.reset_for_tests()
    asyncio.run(run())


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


def test_mapping_id_is_single_use(client: TestClient):
    created = client.post(
        "/guard/input",
        json={"text": "Email alice@example.com please."},
    )
    created_body = created.json()
    first = client.post(
        "/guard/output",
        json={
            "text": created_body["sanitised_text"],
            "pii_mapping_id": created_body["pii_mapping_id"],
        },
    )
    assert first.status_code == 200
    assert "alice@example.com" in first.json()["final_text"]
    second = client.post(
        "/guard/output",
        json={
            "text": created_body["sanitised_text"],
            "pii_mapping_id": created_body["pii_mapping_id"],
        },
    )
    assert second.status_code == 404


def test_empty_mapping_is_not_stored(client: TestClient):
    before = len(main._store)
    response = client.post("/guard/input", json={"text": "Hello there."})
    assert response.status_code == 200
    assert response.json()["pii_mapping_id"] is None
    assert len(main._store) == before


def test_full_does_not_store_a_mapping(client: TestClient):
    before = len(main._store)
    response = client.post(
        "/guard/full",
        json={"text": "Email alice@example.com please."},
    )
    assert response.status_code == 200
    assert response.json()["input_guard"]["pii_mapping_id"] is None
    assert len(main._store) == before
    assert "alice@example.com" in response.json()["output_guard"]["final_text"]


def test_store_cap_evicts_oldest():
    from api.pii_store import MappingStore

    store = MappingStore(max_entries=2)
    first = store.put({"n": "1"}, 60)
    second = store.put({"n": "2"}, 60)
    third = store.put({"n": "3"}, 60)
    assert store.pop(first, 60) is None
    assert store.pop(second, 60) == {"n": "2"}
    assert store.pop(third, 60) == {"n": "3"}
    assert MappingStore().max_entries == 10_000


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
