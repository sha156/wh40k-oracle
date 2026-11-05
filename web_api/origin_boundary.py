"""Reject supplied foreign Origins before handlers; retain local no-Origin clients.

CORS controls browser response access, not whether a simple POST executes.
This exact allowlist gate is an execution boundary, not client authentication.
"""
from collections.abc import Sequence

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class OriginBoundaryMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: Sequence[str]) -> None:
        self.app = app
        # Special CORS values must never turn into accepted request Origins.
        self.allowed_origins = frozenset(allowed_origins) - {"null", "*", ""}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            origins = [value for name, value in scope.get("headers", [])
                       if name.lower() == b"origin"]
            if origins and (len(origins) != 1 or
                            origins[0].decode("latin-1") not in self.allowed_origins):
                # Do not consume the body, invoke handlers, or reflect header input.
                response = JSONResponse(status_code=403, content={"detail": "Origin not allowed"})
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
