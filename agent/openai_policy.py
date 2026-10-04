"""Shared transport bounds and narrowly identified JSON-mode compatibility."""
from __future__ import annotations

import re
from typing import Any


def create_openai_client(api_key: str, base_url: str) -> Any:
    from httpx import Timeout
    from openai import OpenAI

    # Application recovery owns retries. Allow normal 3200-token generation
    # (observed live answers exceed 50s), while bounding each stalled I/O phase.
    # HTTPX timeouts are inactivity/phase bounds, not a total operation deadline.
    return OpenAI(api_key=api_key, base_url=base_url, max_retries=0,
                  timeout=Timeout(connect=15.0, read=180.0, write=30.0, pool=10.0))


def rejects_response_format(error: Exception) -> bool:
    """Recognize a capability rejection, never a generic 400 or internal error."""
    if isinstance(error, TypeError):
        # The exact Python signature rejection supports older injected clients.
        return bool(re.search(
            r"got an unexpected keyword argument ['\"]response_format['\"]", str(error)))

    try:
        from openai import BadRequestError
    except ImportError:  # pragma: no cover - SDK is optional for injected clients
        return False
    if not isinstance(error, BadRequestError):
        return False
    body = error.body
    if isinstance(body, dict):
        body = body.get("error", body)
    if not isinstance(body, dict):
        return False
    param = body.get("param")
    if param is not None and param not in ("response_format", "response_format.type"):
        return False
    code = body.get("code")
    if code not in (None, "invalid_request_error", "unsupported_parameter", "unknown_parameter",
                    "unsupported_value", "unsupported_response_format", "not_supported"):
        return False
    if param is not None and code in ("unsupported_parameter", "unknown_parameter"):
        return True
    # Providers also return invalid_request_error without a param. Require a
    # direct unsupported/unknown signature naming the format, not mere mention.
    message = body.get("message")
    if not isinstance(message, str):
        return False
    target = r"(?<![\w.])['\"]?response_format(?:\.type)?['\"]?(?![\w.])"
    return any(re.search(pattern, message, re.IGNORECASE) for pattern in (
        r"\b(?:unsupported|unknown|unrecognized) (?:parameter|argument)\s*:\s*" + target,
        target + r"\s+(?:is\s+)?(?:not supported|unsupported)\b",
        r"\b(?:does not|doesn't|cannot) support\s+" + target,
    ))
