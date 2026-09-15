"""Bounded, expiring in-memory conversations; serialize turns within a session."""
from contextlib import contextmanager
from dataclasses import dataclass, field
import threading
import time

from agent.context import SessionContext


@dataclass
class _Entry:
    context: SessionContext = field(default_factory=SessionContext)
    lock: object = field(default_factory=threading.Lock)
    last_used: float = 0
    users: int = 0


class SessionStore:
    def __init__(self, capacity=128, ttl=3600, clock=time.monotonic):
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self._entries = {}
        self._lock = threading.Lock()

    @contextmanager
    def session(self, sid):
        if not sid:
            yield SessionContext()
            return
        with self._lock:
            now = self.clock()
            for key, entry in list(self._entries.items()):
                if not entry.users and now - entry.last_used >= self.ttl:
                    del self._entries[key]
            if sid not in self._entries:
                if len(self._entries) >= self.capacity:
                    idle = [(e.last_used, k) for k, e in self._entries.items() if not e.users]
                    if not idle:
                        raise RuntimeError("会话服务繁忙，请稍后重试")
                    del self._entries[min(idle)[1]]
                self._entries[sid] = _Entry(last_used=now)
            entry = self._entries[sid]
            entry.users += 1
        try:
            with entry.lock:
                yield entry.context
        finally:
            with self._lock:
                entry.users -= 1
                entry.last_used = self.clock()
