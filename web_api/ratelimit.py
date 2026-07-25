"""web_api/ratelimit.py — Stage 5 既定的「限流」这一半（CORS 那一半在 main.py）。

为什么需要：本服务的重活是 CPU 密集且没有天然上限的——`/chat` 会拉起 bge-m3 做
嵌入检索并调外部 LLM（花钱），`/simulate`、`/roster/critique` 跑蒙特卡洛。
既有的信号量只挡「同时」打满线程池，挡不住「持续」高频灌请求。

实现取固定窗口计数：进程内、无外部依赖（不引 redis），线程安全，时钟可注入以便
确定性测试。单实例自用够了；将来横向扩多副本时这层要换成共享存储的实现——
届时别以为它还在生效。
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

# 重活端点前缀：命中则走更严的 heavy 配额。/roster/validate 不在内（纯查表实时重算，
# 前端每次编辑都调，限死了体验就废了）。
HEAVY_PREFIXES: Tuple[str, ...] = ("/chat", "/simulate", "/roster/critique")

# 探针不限流：限流器把健康检查也拒了会让编排系统误判服务已死。
EXEMPT_PATHS: Tuple[str, ...] = ("/healthz",)

# 键上限：防被伪造 IP 刷爆内存。到顶时清掉过期键，仍到顶就拒绝新键的请求
# （宁可误伤也不给人把进程内存撑爆的机会）。
_MAX_KEYS = 4096


@dataclass(frozen=True)
class RateLimitConfig:
    """两档配额，单位「次/窗口」；任一档 ≤0 表示该档不限。"""

    default_per_window: int
    heavy_per_window: int
    window_s: float = 60.0

    @staticmethod
    def from_env() -> "RateLimitConfig":
        return RateLimitConfig(
            default_per_window=_int_env("WEB_API_RATE_LIMIT_PER_MIN", 120),
            heavy_per_window=_int_env("WEB_API_HEAVY_RATE_LIMIT_PER_MIN", 20),
            window_s=60.0,
        )


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        print("[ratelimit] 环境变量 {}={!r} 不是整数，回退默认 {}".format(
            name, raw, default), flush=True)
        return default


def bucket_of(path: str) -> str:
    return "heavy" if path.startswith(HEAVY_PREFIXES) else "default"


class FixedWindowLimiter:
    """(客户端, 档位) → 当前窗口计数。`check` 返回 None 放行，否则返回需等待秒数。"""

    def __init__(self, config: RateLimitConfig,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self._cfg = config
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        # key → (窗口起点, 该窗口内计数)
        self._hits: Dict[Tuple[str, str], Tuple[float, int]] = {}

    @property
    def config(self) -> RateLimitConfig:
        return self._cfg

    def _limit_for(self, bucket: str) -> int:
        return (self._cfg.heavy_per_window if bucket == "heavy"
                else self._cfg.default_per_window)

    def check(self, client: str, bucket: str) -> Optional[float]:
        limit = self._limit_for(bucket)
        if limit <= 0:
            return None
        now = self._clock()
        key = (client, bucket)
        with self._lock:
            if len(self._hits) >= _MAX_KEYS:
                self._evict_expired(now)
                if len(self._hits) >= _MAX_KEYS and key not in self._hits:
                    return self._cfg.window_s
            start, count = self._hits.get(key, (now, 0))
            if now - start >= self._cfg.window_s:
                start, count = now, 0
            if count >= limit:
                return max(0.0, self._cfg.window_s - (now - start))
            self._hits[key] = (start, count + 1)
            return None

    def _evict_expired(self, now: float) -> None:
        """调用方须持锁。"""
        dead = [k for k, (start, _) in self._hits.items()
                if now - start >= self._cfg.window_s]
        for k in dead:
            del self._hits[k]


def client_key(client_host: Optional[str], forwarded_for: Optional[str],
               trust_forwarded: bool) -> str:
    """取限流身份。

    默认**不信** X-Forwarded-For——它是客户端可随手伪造的头，信了等于把限流关掉。
    只有显式 `WEB_API_TRUST_FORWARDED=1`（确实架在自己的反代后面）才取其首段。
    """
    if trust_forwarded and forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    return client_host or "unknown"


def trust_forwarded_from_env() -> bool:
    return os.environ.get("WEB_API_TRUST_FORWARDED", "") == "1"


def install(app, config: Optional[RateLimitConfig] = None,
            clock: Optional[Callable[[], float]] = None) -> FixedWindowLimiter:
    """把限流挂进 FastAPI 并返回限流器本体（测试可直接操作）。

    ⚠ 挂载顺序：本函数必须在 `add_middleware(CORSMiddleware)` **之前**调用。
    Starlette 后加的中间件在外层，CORS 在外才能给 429 响应补上跨域头、
    并让浏览器的 OPTIONS 预检不被计入配额。
    """
    from starlette.responses import JSONResponse

    limiter = FixedWindowLimiter(config or RateLimitConfig.from_env(), clock)
    trust_forwarded = trust_forwarded_from_env()

    @app.middleware("http")
    async def _rate_limit(request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        if path in EXEMPT_PATHS:
            return await call_next(request)
        key = client_key(
            request.client.host if request.client else None,
            request.headers.get("x-forwarded-for"),
            trust_forwarded,
        )
        retry_after = limiter.check(key, bucket_of(path))
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试"},
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
        return await call_next(request)

    return limiter
