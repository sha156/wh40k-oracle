"""web_api/trace.py — 工具调用录制器（E3 机魂运转记录）。

用录制代理包住 TOOLS 里的每个工具，AgentLoop 照常调用（loop.py 零改动），
把 (fn, args, 结果摘要, ok/degraded, note) 逐条录进 TraceStep 列表。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from web_api.contract import TraceStep


def _fmt_args(kwargs: Dict[str, Any]) -> str:
    """kwargs → 紧凑展示串。单参数只显其值，多参数显 k=v。"""
    if not kwargs:
        return "()"
    if len(kwargs) == 1:
        (v,) = kwargs.values()
        return "({!r})".format(v)
    parts = ["{}={!r}".format(k, v) for k, v in kwargs.items()]
    return "(" + ", ".join(parts) + ")"


def _summarize(result: Any) -> str:
    """工具结果 dict → 一行摘要（供 trace 右侧展示）。"""
    if not isinstance(result, dict):
        return str(result)[:80]
    for key in ("canonical_id", "name_en"):
        if result.get(key):
            return str(result[key])
    if result.get("found") is True:
        return "已命中"
    if "report" in result:
        return "模拟报告"
    note = result.get("note")
    if note:
        return str(note)[:80]
    if result.get("found") is False:
        return "未命中"
    return "ok"


def _status(result: Any) -> str:
    """degraded：未建模（modeled:false）或显式失败（ok:false）；否则 ok。"""
    if isinstance(result, dict):
        if result.get("modeled") is False or result.get("ok") is False:
            return "degraded"
    return "ok"


class TraceRecorder:
    """包住 TOOLS，录制每次调用；`steps` 是有序 TraceStep 列表。"""

    def __init__(self, tools: Dict[str, Callable[..., Dict[str, Any]]]):
        self._tools = tools
        self.steps: List[TraceStep] = []
        # 每个工具最近一次的完整返回（供 entityCard 等取结构化数据）+ 入参
        self.last_result: Dict[str, Any] = {}
        self.last_args: Dict[str, Dict[str, Any]] = {}

    def _wrap(self, name: str, fn: Callable[..., Dict[str, Any]]):
        def recorded(**kwargs: Any) -> Dict[str, Any]:
            result = fn(**kwargs)
            self.last_result[name] = result
            self.last_args[name] = dict(kwargs)
            self.steps.append(TraceStep(
                fn=name,
                args=_fmt_args(kwargs),
                result=_summarize(result),
                status=_status(result),
                note=(result.get("note") if isinstance(result, dict) else None),
            ))
            return result
        return recorded

    def wrapped_tools(self) -> Dict[str, Callable[..., Dict[str, Any]]]:
        return {name: self._wrap(name, fn) for name, fn in self._tools.items()}

    def get_result(self, fn_name: str) -> Any:
        """取某工具最近一次的完整返回（未调用过返回 None）。"""
        return self.last_result.get(fn_name)
