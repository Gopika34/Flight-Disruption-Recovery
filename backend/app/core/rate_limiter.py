"""Bounded per-identity sliding-window limiter (single-process deployment)."""
from collections import defaultdict, deque
import threading, time

class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int = 60, max_keys: int = 20000):
        self.limit, self.window_seconds, self.max_keys = limit, window_seconds, max_keys
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, identity: str) -> bool:
        if self.limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            if identity not in self._hits and len(self._hits) >= self.max_keys:
                # Expire stale buckets before rejecting new identities.
                cutoff = now - self.window_seconds
                for key in list(self._hits.keys()):
                    q = self._hits[key]
                    while q and q[0] <= cutoff:
                        q.popleft()
                    if not q:
                        self._hits.pop(key, None)
                if len(self._hits) >= self.max_keys:
                    return False
            q = self._hits[identity]
            cutoff = now - self.window_seconds
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

limiter = SlidingWindowLimiter(limit=20)
