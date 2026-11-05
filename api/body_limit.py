"""Reject oversized HTTP bodies before the application reads them.

This is plain ASGI. It does not write Starlette's private request body.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


class LimitRequestBody:
    """Stop reading once ``max_bytes`` of request body has arrived."""

    def __init__(self, app: Callable, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = _content_length(scope)
        if declared is not None and declared > self.max_bytes:
            await _send_too_large(send, self.max_bytes)
            return
        buffered, too_large = await _buffer_body(receive, self.max_bytes)
        if too_large:
            await _send_too_large(send, self.max_bytes)
            return
        await self.app(scope, _replay(buffered, receive), send)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name.lower() != b"content-length":
            continue
        try:
            return int(value)
        except ValueError:
            return None
    return None


async def _buffer_body(receive: Receive, max_bytes: int) -> tuple[list[Message], bool]:
    received = 0
    buffered: list[Message] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            buffered.append(message)
            return buffered, False
        body = message.get("body") or b""
        received += len(body)
        if received > max_bytes:
            return buffered, True
        buffered.append(message)
        if not message.get("more_body", False):
            return buffered, False


def _replay(buffered: list[Message], receive: Receive) -> Receive:
    index = 0

    async def replay() -> Message:
        nonlocal index
        if index < len(buffered):
            message = buffered[index]
            index += 1
            return message
        return await receive()

    return replay


async def _send_too_large(send: Send, max_bytes: int) -> None:
    payload = json.dumps({"detail": f"Request body exceeds {max_bytes} bytes."}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload, "more_body": False})
