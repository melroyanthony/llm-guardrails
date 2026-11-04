"""Server-side PII mappings. Callers only receive an opaque id."""

from __future__ import annotations

import secrets
import threading
import time


class MappingStore:
    """Keep placeholder maps in memory until ``ttl_seconds`` elapses."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[float, dict[str, str]]] = {}
        self._lock = threading.Lock()

    def put(self, mapping: dict[str, str], ttl_seconds: float) -> str:
        token = secrets.token_urlsafe(32)
        now = time.monotonic()
        with self._lock:
            self._drop_expired(now, ttl_seconds)
            self._items[token] = (now, dict(mapping))
        return token

    def get(self, token: str, ttl_seconds: float) -> dict[str, str] | None:
        now = time.monotonic()
        with self._lock:
            self._drop_expired(now, ttl_seconds)
            item = self._items.get(token)
            if item is None:
                return None
            return dict(item[1])

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _drop_expired(self, now: float, ttl_seconds: float) -> None:
        expired = [key for key, (created, _) in self._items.items() if now - created > ttl_seconds]
        for key in expired:
            del self._items[key]
