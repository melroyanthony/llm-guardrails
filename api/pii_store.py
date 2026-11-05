"""Server-side PII mappings. Callers only receive an opaque id."""

from __future__ import annotations

import secrets
import threading
import time

# Live ids are not deleted to make room for a new one. Expired ids are
# dropped first. A map that does not fit is refused, so one PII-heavy
# text cannot fill the store and a flood of /guard/input cannot evict
# another caller's id.
DEFAULT_MAX_ENTRIES = 1_024
DEFAULT_MAX_BYTES = 256 * 1024
DEFAULT_MAX_ENTRY_BYTES = 64 * 1024


def mapping_nbytes(mapping: dict[str, str]) -> int:
    """UTF-8 size of every stored key and value."""
    return sum(
        len(key.encode("utf-8")) + len(value.encode("utf-8")) for key, value in mapping.items()
    )


class MappingStore:
    """Keep placeholder maps in memory until ``ttl_seconds`` elapses.

    The store is process-local. Ids are not shared across workers or replicas,
    and they disappear when the process restarts. ``max_entries`` caps how
    many maps are kept. ``max_bytes`` caps their combined UTF-8 size.
    ``max_entry_bytes`` caps one map. A map that does not fit is not stored.
    """

    def __init__(
        self,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_entry_bytes: int = DEFAULT_MAX_ENTRY_BYTES,
    ) -> None:
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.max_entry_bytes = max_entry_bytes
        self._items: dict[str, tuple[float, dict[str, str], int]] = {}
        self._bytes = 0
        self._lock = threading.Lock()

    def put(self, mapping: dict[str, str], ttl_seconds: float) -> str | None:
        """Store a non-empty map that fits. Otherwise return None."""
        if not mapping:
            return None
        stored = dict(mapping)
        size = mapping_nbytes(stored)
        if size > self.max_entry_bytes or size > self.max_bytes:
            return None
        token = secrets.token_urlsafe(32)
        now = time.monotonic()
        with self._lock:
            self._drop_expired(now, ttl_seconds)
            if len(self._items) >= self.max_entries or self._bytes + size > self.max_bytes:
                return None
            self._items[token] = (now, stored, size)
            self._bytes += size
        return token

    def pop(self, token: str, ttl_seconds: float) -> dict[str, str] | None:
        """Return the map and delete it. A second pop is a miss."""
        now = time.monotonic()
        with self._lock:
            self._drop_expired(now, ttl_seconds)
            item = self._items.pop(token, None)
            if item is None:
                return None
            self._bytes -= item[2]
            return dict(item[1])

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    @property
    def nbytes(self) -> int:
        with self._lock:
            return self._bytes

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._bytes = 0

    def _drop_expired(self, now: float, ttl_seconds: float) -> None:
        expired = [
            key for key, (created, _, _) in self._items.items() if now - created > ttl_seconds
        ]
        for key in expired:
            _, _, size = self._items.pop(key)
            self._bytes -= size
