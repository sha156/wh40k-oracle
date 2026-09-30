"""Public failure descriptions never serialize exception messages or bodies.

No credential lookup, pattern redaction, logging or provider retry occurs here.
This boundary describes failures; it does not sanitize arbitrary model prose.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable


class PublicActionError(ValueError):
    """Locally validated action failure; its payload is never made public."""


class PublicToolContractError(PublicActionError):
    """Locally rejected model capability; preserve its fixed useful reason."""


@dataclass(frozen=True)
class PublicFailure:
    category: str
    message: str
    retryable: bool = False
    status: int | None = None

    def describe(self) -> str:
        status = f"; status={self.status}" if self.status is not None else ""
        return (f"{self.message} [{self.category}{status}; "
                f"retryable={str(self.retryable).lower()}]")


def public_failure(error: Exception) -> PublicFailure:
    """Use typed SDK failures and integer HTTP status, never str/body/request."""
    if isinstance(error, PublicToolContractError):
        return PublicFailure("tool_contract", "工具调用不符合公开参数契约，未执行")
    if isinstance(error, PublicActionError):
        return PublicFailure("invalid_action", "模型动作格式无效，未执行")
    # The SDK remains optional for Python callers using injected LLM clients.
    try:
        from openai import APIConnectionError, APIStatusError, APITimeoutError
    except ImportError:  # pragma: no cover - optional deployment dependency
        pass
    else:
        if isinstance(error, APITimeoutError):
            return PublicFailure("provider_timeout", "上游服务超时，可稍后重试", True)
        if isinstance(error, APIConnectionError):
            return PublicFailure("provider_connection", "上游连接失败，可稍后重试", True)
        if isinstance(error, APIStatusError):
            code = error.status_code
            status = code if type(code) is int and 100 <= code <= 599 else None
            if status == 401:
                return PublicFailure("provider_authentication", "上游认证失败，请检查本地服务配置", status=status)
            if status == 403:
                return PublicFailure("provider_permission", "上游拒绝访问，请检查服务权限", status=status)
            if status == 429:
                return PublicFailure("provider_rate_limit", "上游请求限流，可稍后重试", True, status)
            if status in (408, 409) or status is not None and status >= 500:
                return PublicFailure("provider_unavailable", "上游服务暂时不可用，可稍后重试", True, status)
            return PublicFailure("provider_request", "上游请求未成功，请检查服务配置", status=status)
    if isinstance(error, TimeoutError):
        return PublicFailure("operation_timeout", "操作超时，可稍后重试", True)
    if isinstance(error, (ValueError, TypeError)):
        return PublicFailure("invalid_response", "响应或参数格式无效，未完成处理")
    return PublicFailure("internal_failure", "处理失败，本次未完成；请检查本地服务状态")


def public_tool_result(name: str, result: Any) -> Any:
    """Hide raw retrieval diagnostics before model feedback and API recording.

    rag_search currently converts caught exceptions into error/diagnostic fields.
    Normal evidence, citations and complete source notes remain untouched.
    """
    if name != "rag_search" or not isinstance(result, dict):
        return result
    if result.get("error") and not result.get("passages"):
        return {"found": False, "error": True, "passages": [],
                "note": PublicFailure("retrieval_unavailable", "检索管线不可用，不能据此判断语料是否存在").describe()}
    if result.get("retrieval_errors"):
        safe = dict(result)
        safe["retrieval_errors"] = ["召回通道故障"]
        safe["note"] = "部分召回通道故障，返回段落不完整；不能据此判断未召回的规则是否存在。"
        return safe
    return result


def public_tool_wrapper(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Apply returned-diagnostic boundary before TraceRecorder sees the result."""
    @wraps(fn)
    def safe(*args: Any, **kwargs: Any) -> Any:
        return public_tool_result(name, fn(*args, **kwargs))
    return safe
