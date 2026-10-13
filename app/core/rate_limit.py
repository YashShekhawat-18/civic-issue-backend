"""A very small in-memory rate limiter (sliding window).

Good for one server process. If you later run several server processes, move the counters
to Redis. The rest of the code would not change.
"""
import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = {}

    def check(self, key: str, limit: int, window_seconds: int, now: float | None = None) -> tuple[bool, int]:
        """Counts this attempt. Returns (allowed, seconds_until_the_next_attempt_is_allowed)."""
        now = time.monotonic() if now is None else now
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()  # forget attempts older than the window

        if len(hits) >= limit:
            retry_after = int(hits[0] + window_seconds - now) + 1
            return False, max(retry_after, 1)

        hits.append(now)
        if len(self._hits) > 10_000:  # keep memory small: drop keys that have gone quiet
            self._purge(now, window_seconds)
        return True, 0

    def _purge(self, now: float, window_seconds: int) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - window_seconds]:
            del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()


limiter = SlidingWindowLimiter()
