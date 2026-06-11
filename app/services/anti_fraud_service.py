from __future__ import annotations

import time
from collections import defaultdict, deque


class AntiFraudService:
    """
    Simple in-memory limiter for high-frequency actions.
    Replace with Redis in production for multi-instance deployment.
    """

    def __init__(self, max_events: int = 5, window_seconds: int = 20):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[int, deque[float]] = defaultdict(deque)

    def is_limited(self, user_id: int) -> bool:
        now = time.time()
        queue = self._events[user_id]
        while queue and now - queue[0] > self.window_seconds:
            queue.popleft()
        if len(queue) >= self.max_events:
            return True
        queue.append(now)
        return False
