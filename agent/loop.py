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

# 必须先查证才能作答的意图：这些问题的答案是确定性事实（规则/属性/点数）或需跑模拟，
# 凭 LLM 参数记忆直接回答极易给出过时或编造的数字并伪造书页引用
# （gold 实测：16 题零工具直答错 9 道，而真正走工具的路径 0 真错）。
# 谋（模拟对战/谁能赢）自 P4-e 起 simulate_combat 已建模——LLM 不得凭直觉估「谁冲谁赢」，
# 必须先跑蒙特卡洛，故纳入门控（spec 第十节接线要求）。闲聊与规则无关，不在此列。
_MUST_VERIFY_INTENTS = ("查", "判", "算", "谋")

# 零工具直答被拦下时，先给模型一次纠偏机会，逼它改走工具查证。
_FORCE_TOOL_NUDGE = (
    "你还没有调用任何工具就想直接作答。属性/数值/规则/点数类问题必须先用工具查证："
    "数值属性走 get_datasheet，技能/背景/军表走 get_entity，USR 定义走 get_keyword_definition，"
    "都查不到再用 rag_search 兜底。不要凭记忆给出任何数字或书页引用，请先输出一个 tool_call。"
)

# 触发"空结果 → 降级 rag_search"的工具及判空规则。
# 未建模工具（simulate_combat 等）不在此列——它们的"未建模"提示本身就是诚实答案，
# rag_search 兜底对模拟/判定类问题没有意义，不应被此机制吞掉。
# ⚠️ ambiguous（同名多候选）不是空结果：它带 candidates/preview，是需要 LLM 按
# 提示词铁律重查消歧的实质性回复（评审 #25 通道）。此前判空谓词不区分 ambiguous，
# 在 LLM 看到候选之前就降级 classic——整条消歧路径成了死代码（gnhf 审查模块 5 HIGH）。
_EMPTY_CHECKS: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    "search_wiki": lambda r: not r.get("found"),
    # `suggestions` 非空 = 「名字没解析到，但库里有几个长得像的」（模糊匹配静默错配的
    # 修复通道）。这种返回**不是空手**：它带着「库里没有这个名字」这条实质信息 + 已标死
    # 为猜测的近似名，模型必须据此如实作答。判它空会立刻降级经典链，模型反而看不到
    # 这条信息、只能对着按相似词捞回来的片段自由发挥（与 #118 判空则丢失消歧信息同型）。
    # 注意这个键**只**出现在「一个候选都没解析到」的那条路径上：真拼错/简称仍照旧走
    # fuzzy/ambiguous，`_EMPTY_CHECKS` 对它们的判定逐字节不变。
    "get_entity": lambda r: (not r.get("found")
                             and not r.get("suggestions")
                             and (r.get("resolved_via") or {}).get("confidence")
                             != "ambiguous"),
    # `get_keyword_definition` **故意不在此列**（2026-07-27，基准 #117）。它和
    # `entity_resolver` 一样是纯映射工具（关键词 → 术语页），「这个词没有术语页」本身
    # 就是实质信息；而降级会把**此前已查到的兵牌/实体结果一并丢弃**，只留 PDF 片段。
    # 实测 tool_calls：`get_entity(战将泰坦)`→found ⇒ `get_keyword_definition(Frame)`
    # →not found ⇒ 当场降级 ⇒ 模型照 Faction Pack 原文答「Frame 在库中可查」，
    # 与库内事实（6 个关键词、无 Frame）相反，正是本题要考的诚实性反例。
    # 不降级并不等于够不到 PDF：rag_search 仍是模型手里的普通工具，
    # `_KEYWORD_NOT_FOUND_NOTE` 已明写「问规则含义就改用 rag_search」。
    "entity_resolver": lambda r: (not r.get("canonical_id")
                                  and not r.get("historical_record")
                                  and not r.get("candidates")
                                  and not r.get("suggestions")),
    # 数值题优先走 get_datasheet；但俗名/集合名解析不到时必须立即降级 classic 兜底，
    # 否则 LLM 会反复空查后直接宣布「档案缺失」，反而不如老链路（回归 7 题的根因）。
    # ⚠️ 这里**故意不看** `suggestions`（与上面两个工具相反）：2026-07-27 实测过让近似名
    # 抑制降级，#4（XV107 燃雨战斗服）与 #62（重武器小队）当场从 ✅ 掉成 ❌——两者都是
    # **真实存在**的单位，只是名字不在结构库的索引里，答案本来靠经典链从 PDF 语料捞回来。
    # 结构库 ≠ 全部语料，所以「结构库里没有这个名字」不足以支撑作答，必须让它去查语料；
    # 而 entity_resolver 是纯「名字 → id」映射工具，「这个名字解析不到 + 只有几个像的」
    # 本身就是它被问到的那个问题的实质答案，两者不可混为一谈。
    "get_datasheet": lambda r: (not r.get("found")
                                and r.get("reason") != "ambiguous"),
    # 一个名字都没解析到时降级兜底，别把「工具空手」留给模型自由发挥（基准 #109 硬错：
    # 四个中文名全查空后模型编出「泰坦军团不是 40K 阵营、无官方点数」的否定性断言）。
    # 只要有一个单位查到就不算空——「查到了但库里没点数」是诚实答案，不该被兜底吞掉。
    # `param_error` 例外（审查 R1-M1）：入参类型写错时 tools.calc_points 也返回
    # found=False，但那是**模型自己能改对**的错，不是「库里没有」。判空即降级会让它
    # 看不到「unit_list 应为列表」那句指路，白白丢掉一次恢复机会。
    "calc_points": lambda r: (not r.get("param_error")
                              and (not r.get("found")
                                   or bool(r.get("units"))
                                   and all(u.get("unresolved") for u in r["units"]))),
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


def _has_usable_evidence(tool_name: str, result: Any) -> bool:
    """Whether a tool returned facts that can support at least part of an answer.

    Identity mappings alone do not qualify: knowing an id does not establish rules or
    points, so a later miss must still use the normal retrieval fallback. Historical
    facts qualify only while retaining their explicit non-current scope.
    """
    if not isinstance(result, dict):
        return False
    if tool_name == "calc_points":
        if not result.get("found"):
            return False
        return any(
            isinstance(unit, dict)
            and not unit.get("unresolved")
            and (unit.get("points") is not None
                 or unit.get("historical_points") is not None
                 or bool(unit.get("official_prices")))
            for unit in (result.get("units") or [])
        )
    if tool_name == "get_datasheet":
        return bool(result.get("found")
                    and (result.get("datasheet") is not None
                         or result.get("historical_record")))
    if tool_name == "get_entity":
        return bool(result.get("found")
                    and (result.get("page") is not None
                         or result.get("historical_record")))
    if tool_name == "search_wiki":
        if not result.get("found"):
            return False
        if result.get("page") is not None:
            return True
        return any(
            bool((entry.get("summary") or entry.get("text") or entry.get("content"))
                 if isinstance(entry, dict)
                 else (getattr(entry, "summary", None)
                       or getattr(entry, "text", None)
                       or getattr(entry, "content", None)))
            for entry in (result.get("results") or [])
        )
    if tool_name == "get_keyword_definition":
        return bool(result.get("found"))
    return False


def _evidence_facts(tool_name: str, result: Any) -> List[str]:
    """Bounded facts for the rare case where the final synthesis step also fails."""
    if not isinstance(result, dict):
        return []
    facts: List[str] = []

    def page_fact(page: Any, fallback: str) -> None:
        if page is None:
            return
        fm = getattr(page, "fm", None)
        if isinstance(page, dict):
            fm = page.get("fm") or fm
            body = page.get("body") or page.get("text") or page.get("content")
        else:
            body = getattr(page, "body", None)
        if isinstance(fm, dict):
            title = fm.get("name_zh") or fm.get("name_en") or fallback
        else:
            title = (getattr(fm, "name_zh", None) or getattr(fm, "name_en", None)
                     or fallback)
        excerpt = " ".join(str(body or "").split())[:500]
        if excerpt:
            facts.append(f"{title}：{excerpt}")

    def cross_faction_facts(unit: Dict[str, Any]) -> bool:
        siblings = unit.get("same_name_other_factions") or []
        rendered = False
        for sibling in siblings:
            if not isinstance(sibling, dict) or sibling.get("points") is None:
                continue
            label = (sibling.get("candidate") or sibling.get("name_en")
                     or sibling.get("faction") or "同名候选")
            facts.append(f"{label}：点数 {sibling['points']}（同名跨阵营候选，必须消歧）")
            rendered = True
        return rendered

    if tool_name == "calc_points":
        for unit in result.get("units") or []:
            if not isinstance(unit, dict) or unit.get("unresolved"):
                continue
            # A single unqualified price is actively misleading when the same
            # English name has independent faction rows. Render every candidate.
            ambiguous = cross_faction_facts(unit)
            canonical = str(unit.get("name_en") or unit.get("unit_id") or "单位")
            query = str(unit.get("query") or "")
            confidence = ((unit.get("resolved_via") or {}).get("confidence")
                          if isinstance(unit.get("resolved_via"), dict) else None)
            label = canonical
            if confidence == "fuzzy":
                label += f"（由查询“{query}”模糊匹配，需核对身份）"
            elif query and query != canonical:
                label += f"（查询：{query}）"
            if unit.get("points") is not None and not ambiguous:
                facts.append(f"{label}：点数 {unit['points']}")
            if unit.get("historical_points") is not None:
                facts.append(f"{label}：历史缓存点数 {unit['historical_points']}（非现行）")
            if unit.get("points") is None:
                for price in unit.get("official_prices") or []:
                    if not isinstance(price, dict) or price.get("cost") is None:
                        continue
                    price_label = " / ".join(str(value) for value in (
                        price.get("faction_slug"), price.get("unit_name"), price.get("models"))
                        if value)
                    facts.append(f"{price_label or label}：官方点数 {price['cost']}（未消歧）")
    elif tool_name == "get_datasheet":
        historical = result.get("historical_record") or {}
        if isinstance(historical, dict) and historical.get("historical_points") is not None:
            label = historical.get("name_zh") or historical.get("name_en") or "历史兵牌"
            facts.append(f"{label}：历史缓存点数 {historical['historical_points']}（非现行）")
        datasheet = result.get("datasheet") or {}
        ambiguous = cross_faction_facts(result)
        if (isinstance(datasheet, dict) and datasheet.get("points") is not None
                and not ambiguous):
            label = datasheet.get("name_zh") or datasheet.get("name_en") or "兵牌"
            facts.append(f"{label}：点数 {datasheet['points']}")
    elif tool_name in ("get_entity", "get_keyword_definition"):
        page_fact(result.get("page"), "规则条目")
    elif tool_name == "search_wiki":
        page_fact(result.get("page"), "Wiki 条目")
        for entry in result.get("results") or []:
            if isinstance(entry, dict):
                title = entry.get("title_zh") or entry.get("title_en") or entry.get("title")
                summary = entry.get("summary") or entry.get("text") or entry.get("content")
            else:
                title = (getattr(entry, "title_zh", None)
                         or getattr(entry, "title_en", None)
                         or getattr(entry, "title", None))
                summary = (getattr(entry, "summary", None)
                           or getattr(entry, "text", None)
                           or getattr(entry, "content", None))
            excerpt = " ".join(str(summary or "").split())[:500]
            if excerpt:
                facts.append(f"{title or 'Wiki 检索结果'}：{excerpt}")
    # Keep the emergency answer readable and bounded; normal successful synthesis
    # still receives the complete structured tool results in messages.
    return facts[:12]


_PRESERVE_EVIDENCE_NUDGE = (
    "这次补充查询没有命中，但前面的工具已经查到可用的规则或点数证据。"
    "不得丢弃、否定或用兜底片段覆盖此前已查到的证据；请据其回答能够确定的部分，"
    "并把本次未解析的名字单独标为未确认。若仍需补充原文，可主动调用 rag_search，"
    "但不能把已查到的当前点数改写成“不可用”。"
)

_FINALIZE_EVIDENCE_NUDGE = (
    "工具步数已经用尽。前面的工具结果含有可用证据；现在必须直接返回 final，"
    "用这些证据回答能确定的部分，并把剩余缺口明确标为未确认。不要再调用工具，"
    "不要声称已经查到的事实不可用。"
)


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
            result = self._run_tool_loop(user_input, intent, session.history)
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

    def _run_tool_loop(self, user_input: str, intent: str, history=None) -> AgentResult:
        # Past answers resolve references; the existing fresh-tool gate still
        # requires current evidence for every rules/points question.
        messages: List[Dict[str, Any]] = [dict(m) for m in (history or [])[-12:]]
        messages.append({"role": "user", "content": user_input})
        tool_calls: List[str] = []
        nudged_for_tools = False
        nudged_for_empty = False       # 空 final 只给一次重答机会（评审 M#5）
        last_exception_tool: Optional[str] = None  # 连续异常检测（评审 M#6）
        has_usable_evidence = False
        evidence_facts: List[str] = []

        for _ in range(self.max_steps):
            step = self.llm.next_step(messages, TOOL_SPECS)

            if step.get("type") == "final":
                # 零工具直答门控：查/判/算 类问题若一次工具都没调就想给最终答案，
                # 先强制纠偏一次；仍不查证则视同降级转 classic 兜底，而非放行凭记忆作答。
                if intent in _MUST_VERIFY_INTENTS and not tool_calls:
                    if not nudged_for_tools:
                        nudged_for_tools = True
                        messages.append({"role": "user", "content": _FORCE_TOOL_NUDGE})
                        continue
                    return self._fallback(
                        user_input, intent, tool_calls,
                        reason="零工具直答已拒绝（查/判/算 类须先查证）",
                    )
                # 空内容 final 不算成功（评审 M#5）：先写回提示再给模型一次机会，
                # 仍为空才降级——不把空字符串当作有效回答返回给用户。
                answer = str(step.get("content") or "")
                if not answer.strip():
                    if not nudged_for_empty:
                        nudged_for_empty = True
                        messages.append({
                            "role": "user",
                            "content": "上一步返回了空内容。请给出实际的中文回答"
                                       "（final 的 content 不能为空）。",
                        })
                        continue
                    return self._fallback(
                        user_input, intent, tool_calls,
                        reason="final 步骤 content 连续为空",
                    )
                return AgentResult(
                    answer=answer,
                    intent=intent,
                    tool_calls=tool_calls,
                    degraded=False,
                    sources=([source for source in step["sources"] if isinstance(source, dict)]
                             if isinstance(step.get("sources"), list) else []),
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
                # 与未知工具的恢复策略一致（评审 M#6）：错误写回 messages 让模型
                # 修正参数重试或换工具；同一工具**连续第二次**异常才降级 classic
                # （达到 max_steps 时由循环末尾的兜底降级）。
                if last_exception_tool == tool_name:
                    return self._fallback(
                        user_input, intent, tool_calls + [tool_name],
                        reason=f"{tool_name} 连续两次异常: {exc}",
                    )
                last_exception_tool = tool_name
                messages.append({
                    "role": "tool", "name": tool_name,
                    "content": {"error": f"{tool_name} 执行异常: {exc}。"
                                         "请修正参数后重试，或改用其他工具。"},
                })
                continue

            last_exception_tool = None
            tool_calls.append(tool_name)

            if tool_name != "rag_search" and _is_empty_result(tool_name, result):
                if has_usable_evidence:
                    messages.append({"role": "tool", "name": tool_name, "content": result})
                    messages.append({"role": "user", "content": _PRESERVE_EVIDENCE_NUDGE})
                    continue
                return self._fallback(user_input, intent, tool_calls, reason=f"{tool_name} 空结果")

            if _has_usable_evidence(tool_name, result):
                has_usable_evidence = True
                for fact in _evidence_facts(tool_name, result):
                    if fact not in evidence_facts:
                        evidence_facts.append(fact)
            messages.append({"role": "tool", "name": tool_name, "content": result})

        if has_usable_evidence:
            # A protected late miss can consume the last normal step. Give the
            # model one synthesis-only turn rather than throwing all accumulated
            # evidence away through the legacy RAG fallback.
            messages.append({"role": "user", "content": _FINALIZE_EVIDENCE_NUDGE})
            try:
                step = self.llm.next_step(messages, TOOL_SPECS)
            except Exception:
                step = {}
            if not isinstance(step, dict):
                step = {}
            answer = str(step.get("content") or "")
            if step.get("type") == "final" and answer.strip():
                return AgentResult(
                    answer=answer,
                    intent=intent,
                    tool_calls=tool_calls,
                    degraded=False,
                    sources=([source for source in step["sources"]
                              if isinstance(source, dict)]
                             if isinstance(step.get("sources"), list) else []),
                )
            if evidence_facts:
                detail = ("已经确定的证据如下；不能据此否定这些事实，"
                          "其余内容暂列为未确认。\n"
                          + "\n".join(f"- {fact}" for fact in evidence_facts))
            else:
                detail = ("工具曾返回可用证据，但安全降级路径无法展开其内容；"
                          "请重试整理，当前不能据此下结论。")
            return AgentResult(
                answer="⚠️ 模型在工具步数用尽后仍未完成整理。" + detail,
                intent=intent,
                tool_calls=tool_calls,
                degraded=True,
                sources=[],
            )
        return self._fallback(user_input, intent, tool_calls, reason="超过 max_steps 仍未得出结论")

    def _fallback(
        self, user_input: str, intent: str, tool_calls: List[str], reason: str,
    ) -> AgentResult:
        rag_fn = self.tools.get("rag_search")
        passages: List[Dict[str, Any]] = []
        note = reason
        unavailable = False

        if rag_fn is not None:
            try:
                rag_result = rag_fn(user_input)
                passages = rag_result.get("passages", [])
                if not passages:
                    # 审查 H1：rag_search 的 error=True 表示**检索管线/环境不可用**，
                    # 与「语料里没有」是两回事。降级答案是这条链路的最后一句话——
                    # 一律写「未找到相关内容」等于把环境故障说成内容结论。
                    if rag_result.get("error"):
                        unavailable = True
                        note = (f"{reason}；rag_search 兜底不可用："
                                f"{rag_result.get('note') or '检索侧环境故障'}")
                    else:
                        note = f"{reason}；rag_search 兜底也未检索到相关内容"
            except Exception as exc:
                unavailable = True
                note = f"{reason}；rag_search 兜底异常: {exc}"
            tool_calls = tool_calls + ["rag_search"]

        return AgentResult(
            answer=self._synthesize_fallback_answer(passages, note, unavailable),
            intent=intent,
            tool_calls=tool_calls,
            degraded=True,
            sources=passages,
        )

    @staticmethod
    def _synthesize_fallback_answer(passages: List[Dict[str, Any]], note: str,
                                    unavailable: bool = False) -> str:
        if not passages:
            if unavailable:
                # 检索没跑成，不是语料里没有——这句话是用户/模型看到的最后一句，
                # 不许在这里把环境故障收敛成「找不到」（审查 H1）。
                return (f"⚠️ 本次检索**不可用**（{note}）。"
                        "这是检索侧环境故障，不能据此判断相关规则/单位是否存在，"
                        "请修复检索环境后重试，或查阅原始规则书。")
            return f"⚠️ 已降级到兜底检索，但仍未找到相关内容（{note}）。"
        lines = [f"⚠️ 已降级到兜底检索（{note}），供参考的原文片段："]
        for p in passages[:3]:
            text = (p.get("text") or "")[:120]
            lines.append(f"- 《{p.get('book', '未知')}》第{p.get('page', '?')}页：{text}")
        return "\n".join(lines)
