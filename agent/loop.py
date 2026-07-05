"""agent/loop.py — L5 Agent 循环（spec 第七节「Agent 循环」）。

意图分类 → function-calling 循环（max_steps=6）→ 答案合成；
工具异常或返回空结果时静默降级到 rag_search，走老链路兜底回答。

LLMClient 是本模块与具体 LLM 供应商之间的边界：真实实现（deepseek/glm 兼容接口）
留待接线到 app.py 之前的下一迭代；本迭代的测试与骨架验证一律用实现了该 Protocol
的 Fake 对象，不真调 API。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from agent.context import SessionContext
from agent.tools import TOOL_SPECS, TOOLS

MAX_STEPS = 6
INTENTS = ("查", "判", "算", "谋", "闲聊")
DEFAULT_INTENT = "查"

# 触发"空结果 → 降级 rag_search"的工具及判空规则。
# 未建模工具（simulate_combat 等）不在此列——它们的"未建模"提示本身就是诚实答案，
# rag_search 兜底对模拟/判定类问题没有意义，不应被此机制吞掉。
_EMPTY_CHECKS: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    "search_wiki": lambda r: not r.get("found"),
    "get_entity": lambda r: not r.get("found"),
    "get_keyword_definition": lambda r: not r.get("found"),
    "entity_resolver": lambda r: not r.get("canonical_id"),
}


class LLMClient(Protocol):
    """Agent 循环依赖的最小 LLM 接口。"""

    def classify_intent(self, user_input: str) -> str:
        """返回 查/判/算/谋/闲聊 之一。"""
        ...

    def next_step(
        self, messages: List[Dict[str, Any]], tool_specs: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """返回下一步动作：
        {"type": "tool_call", "tool": "<工具名>", "args": {...}}
        或
        {"type": "final", "content": "<结论+数字+引用+未建模提示>", "sources": [...]}
        """
        ...


@dataclass(frozen=True)
class AgentResult:
    answer: str
    intent: str
    tool_calls: List[str] = field(default_factory=list)
    degraded: bool = False
    sources: List[Dict[str, Any]] = field(default_factory=list)


def _is_empty_result(tool_name: str, result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    check = _EMPTY_CHECKS.get(tool_name)
    return bool(check and check(result))


class AgentLoop:
    """查/判/算/谋/闲聊 意图路由 + 工具调用循环。"""

    def __init__(
        self,
        llm: LLMClient,
        tools: Optional[Dict[str, Callable[..., Dict[str, Any]]]] = None,
        max_steps: int = MAX_STEPS,
    ):
        self.llm = llm
        self.tools = tools if tools is not None else TOOLS
        self.max_steps = max_steps

    def run(self, user_input: str, session: Optional[SessionContext] = None) -> AgentResult:
        session = session if session is not None else SessionContext()
        intent = self._classify(user_input)

        try:
            result = self._run_tool_loop(user_input, intent)
        except Exception as exc:
            result = self._fallback(user_input, intent, tool_calls=[], reason=f"异常: {exc}")

        session.append_turn("user", user_input)
        session.append_turn("assistant", result.answer)
        return result

    def _classify(self, user_input: str) -> str:
        try:
            intent = self.llm.classify_intent(user_input)
        except Exception:
            return DEFAULT_INTENT
        return intent if intent in INTENTS else DEFAULT_INTENT

    def _run_tool_loop(self, user_input: str, intent: str) -> AgentResult:
        messages: List[Dict[str, Any]] = [{"role": "user", "content": user_input}]
        tool_calls: List[str] = []

        for _ in range(self.max_steps):
            step = self.llm.next_step(messages, TOOL_SPECS)

            if step.get("type") == "final":
                return AgentResult(
                    answer=step.get("content", ""),
                    intent=intent,
                    tool_calls=tool_calls,
                    degraded=False,
                    sources=step.get("sources", []),
                )

            tool_name = step.get("tool")
            args = step.get("args") or {}
            tool_fn = self.tools.get(tool_name)

            if tool_fn is None:
                messages.append({
                    "role": "tool", "name": tool_name,
                    "content": {"error": f"未知工具: {tool_name}"},
                })
                continue

            try:
                result = tool_fn(**args)
            except Exception as exc:
                return self._fallback(
                    user_input, intent, tool_calls + [tool_name],
                    reason=f"{tool_name} 异常: {exc}",
                )

            tool_calls.append(tool_name)

            if tool_name != "rag_search" and _is_empty_result(tool_name, result):
                return self._fallback(user_input, intent, tool_calls, reason=f"{tool_name} 空结果")

            messages.append({"role": "tool", "name": tool_name, "content": result})

        return self._fallback(user_input, intent, tool_calls, reason="超过 max_steps 仍未得出结论")

    def _fallback(
        self, user_input: str, intent: str, tool_calls: List[str], reason: str,
    ) -> AgentResult:
        rag_fn = self.tools.get("rag_search")
        passages: List[Dict[str, Any]] = []
        note = reason

        if rag_fn is not None:
            try:
                rag_result = rag_fn(user_input)
                passages = rag_result.get("passages", [])
                if not passages:
                    note = f"{reason}；rag_search 兜底也未检索到相关内容"
            except Exception as exc:
                note = f"{reason}；rag_search 兜底异常: {exc}"
            tool_calls = tool_calls + ["rag_search"]

        return AgentResult(
            answer=self._synthesize_fallback_answer(passages, note),
            intent=intent,
            tool_calls=tool_calls,
            degraded=True,
            sources=passages,
        )

    @staticmethod
    def _synthesize_fallback_answer(passages: List[Dict[str, Any]], note: str) -> str:
        if not passages:
            return f"⚠️ 已降级到兜底检索，但仍未找到相关内容（{note}）。"
        lines = [f"⚠️ 已降级到兜底检索（{note}），供参考的原文片段："]
        for p in passages[:3]:
            text = (p.get("text") or "")[:120]
            lines.append(f"- 《{p.get('book', '未知')}》第{p.get('page', '?')}页：{text}")
        return "\n".join(lines)
