"""Server-side PII mappings. Callers only receive an opaque id."""

from __future__ import annotations

import secrets
import threading
import time


class MappingStore:
    """Keep placeholder maps in memory until ``ttl_seconds`` elapses.

    The store is process-local. Ids are not shared across workers or replicas,
    and they disappear when the process restarts. ``max_entries`` caps the map;
    the oldest id is dropped first.
    """

    def __init__(self, max_entries: int = 10_000) -> None:
        self.max_entries = max_entries
        self._items: dict[str, tuple[float, dict[str, str]]] = {}
        self._lock = threading.Lock()

    def put(self, mapping: dict[str, str], ttl_seconds: float) -> str | None:
        """Store a non-empty map. An empty map is not stored and returns None."""
        if not mapping:
            return None
        token = secrets.token_urlsafe(32)
        now = time.monotonic()
        with self._lock:
            self._drop_expired(now, ttl_seconds)
            while len(self._items) >= self.max_entries:
                oldest = next(iter(self._items))
                del self._items[oldest]
            self._items[token] = (now, dict(mapping))
        return token

    def pop(self, token: str, ttl_seconds: float) -> dict[str, str] | None:
        """Return the map and delete it. A second pop is a miss."""
        now = time.monotonic()
        with self._lock:
            self._drop_expired(now, ttl_seconds)
            item = self._items.pop(token, None)
            if item is None:
                return None
            return dict(item[1])

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _drop_expired(self, now: float, ttl_seconds: float) -> None:
        expired = [key for key, (created, _) in self._items.items() if now - created > ttl_seconds]
        for key in expired:
            del self._items[key]
