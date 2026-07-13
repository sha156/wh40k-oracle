"""web_api/formatter.py — response_formatter：AgentResult + 工具证据 → Answer 契约。

分工（见 spec 第 1 节）：
- A 类槽位（trace/entityCard/cites/summary/traceWarn/cta/degraded）：确定性推导，零 LLM。
- B 类槽位（verdict/calc/sensitivity/followups）：一次结构化 LLM 调用产轻标记文本，
  再由 richtext tokenizer 转 RichText。结构化调用失败则 fail-closed 退化为「散文整段纯文本」。
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Protocol

from agent.loop import AgentLoop, AgentResult
from web_api.contract import (
    Answer, CalcStep, Cite, Cta, Sensitivity, TraceStep, Verdict,
)
from web_api.entity_card import build_entity_card
from web_api.richtext import to_richtext
from web_api.trace import TraceRecorder


class StructuringLLM(Protocol):
    """把散文答案重排成结构化槽位的 LLM 接口（与主循环 LLM 解耦）。"""

    def structure(
        self, question: str, prose: str, evidence: str, cites: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """返回 {summary?, verdict:{label,labelEn,lede}, calc:[str], sensitivity?, followups:[str]}。"""
        ...


# ── A 类槽位推导 ──────────────────────────────────────────────────

def _derive_cites(result: AgentResult, recorder: TraceRecorder) -> List[Cite]:
    """从工具证据与检索来源确定性抽引用；去重编号。诚实：无页码不编页码。"""
    cites: List[Cite] = []
    seen = set()

    def _add(book, page=None, section=None, term=None, wiki=""):
        key = (book, page, term)
        if key in seen or not book:
            return
        seen.add(key)
        cites.append(Cite(n=len(cites) + 1, book=book, page=page,
                          section=section, term=term, wiki=wiki))

    # 关键词定义页（核心规则术语）——provenance，非伪造页码
    kw_res = recorder.get_result("get_keyword_definition")
    if isinstance(kw_res, dict) and kw_res.get("found"):
        page = kw_res.get("page")
        term = getattr(getattr(page, "fm", None), "name_zh", None) if page else None
        wiki = "core-rules/" + (getattr(getattr(page, "fm", None), "name_en", "") or "")
        _add("核心规则术语", section="USR/关键词", term=term or "", wiki=wiki)

    # 结构库属性块
    ds_res = recorder.get_result("get_datasheet")
    if isinstance(ds_res, dict) and ds_res.get("found"):
        ds = ds_res.get("datasheet") or {}
        _add("L3 结构库 · " + str(ds.get("faction") or "未知"),
             term=str(ds.get("name_en") or ""), section="属性块")

    # 检索来源（真有 book/page 出处）
    for p in (result.sources or [])[:6]:
        if isinstance(p, dict) and p.get("book"):
            page = p.get("page")
            _add(str(p["book"]), page=int(page) if str(page).isdigit() else None,
                 wiki=str(p.get("wiki", "")))

    return cites


def _derive_cta(recorder: TraceRecorder, intent: str) -> Optional[Cta]:
    sim = recorder.get_result("simulate_combat")
    if isinstance(sim, dict):
        ready = bool(sim.get("ok") and sim.get("modeled"))
        return Cta(
            kind="simulator", ready=ready,
            label="⚔ 在模拟器中打开此对局",
            mini=None if ready else str(sim.get("note") or "未建模，当前为粗算"),
        )
    return None


def _derive_summary(trace: List[TraceStep], cites: List[Cite], degraded: bool) -> str:
    parts = ["检索 {} 步".format(len(trace)), "引用 {} 条".format(len(cites))]
    if degraded:
        parts.append("已降级兜底")
    return " · ".join(parts)


def _derive_trace_warn(trace: List[TraceStep]) -> Optional[str]:
    for st in trace:
        if st.status == "degraded":
            return "⚠ {} 降级".format(st.fn)
    return None


# ── B 类槽位（结构化 LLM 输出 → RichText）─────────────────────────

def _fallback_verdict(prose: str) -> Verdict:
    """结构化失败时：散文整段做 lede，标签中性。"""
    return Verdict(label="参谋回复", labelEn="Advisory", lede=to_richtext(prose))


def _build_verdict(structured: Dict[str, Any], prose: str) -> Verdict:
    v = structured.get("verdict") if isinstance(structured, dict) else None
    if not isinstance(v, dict) or not v.get("lede"):
        return _fallback_verdict(prose)
    return Verdict(
        label=str(v.get("label") or "参谋回复"),
        labelEn=str(v.get("labelEn") or "Advisory"),
        lede=to_richtext(str(v["lede"])),
    )


def _build_calc(structured: Dict[str, Any]) -> List[CalcStep]:
    raw = structured.get("calc") if isinstance(structured, dict) else None
    if not isinstance(raw, list):
        return []
    steps: List[CalcStep] = []
    for i, item in enumerate(raw, 1):
        text = item if isinstance(item, str) else str(item)
        if text.strip():
            steps.append(CalcStep(n=i, text=to_richtext(text)))
    return steps


def _build_sensitivity(structured: Dict[str, Any]) -> Optional[Sensitivity]:
    s = structured.get("sensitivity") if isinstance(structured, dict) else None
    if not isinstance(s, dict) or not s.get("text"):
        return None
    return Sensitivity(
        title=str(s.get("title") or "◭ 敏感性"),
        text=to_richtext(str(s["text"])),
    )


def _build_followups(structured: Dict[str, Any]) -> List[str]:
    raw = structured.get("followups") if isinstance(structured, dict) else None
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw if str(x).strip()][:4]


# ── 编排 ──────────────────────────────────────────────────────────

def format_answer(
    question: str,
    agent_result: AgentResult,
    recorder: TraceRecorder,
    structurer: Optional[StructuringLLM] = None,
    hot_weapon: Optional[str] = None,
) -> Answer:
    """把跑完的 AgentResult + 录制的工具证据组装成 Answer 契约。"""
    trace = list(recorder.steps)
    cites = _derive_cites(agent_result, recorder)
    entity_card = _derive_entity_card(recorder, hot_weapon)
    cta = _derive_cta(recorder, agent_result.intent)
    degraded = bool(agent_result.degraded)
    summary = _derive_summary(trace, cites, degraded)
    trace_warn = _derive_trace_warn(trace)

    structured: Dict[str, Any] = {}
    if structurer is not None:
        try:
            evidence = _evidence_digest(recorder)
            structured = structurer.structure(
                question, agent_result.answer, evidence,
                [c.model_dump() for c in cites],
            ) or {}
        except Exception:
            structured = {}   # fail-closed：退化为散文 lede

    return Answer(
        summary=summary,
        trace=trace,
        traceWarn=trace_warn,
        verdict=_build_verdict(structured, agent_result.answer),
        calc=_build_calc(structured),
        entityCard=entity_card,
        cites=cites,
        sensitivity=_build_sensitivity(structured),
        cta=cta,
        followups=_build_followups(structured),
        degraded=degraded,
    )


def _derive_entity_card(recorder: TraceRecorder, hot_weapon: Optional[str]):
    """E6 兵牌：优先走 codex.unit_card 完整装配（能力表/装备/受损档与图鉴一致）；
    codex 拿不到（DB 缺/测试注入的假 datasheet）再退回工具结果直映射。"""
    ds_res = recorder.get_result("get_datasheet") or {}
    ds = ds_res.get("datasheet") if isinstance(ds_res, dict) else None
    unit_id = str((ds or {}).get("unit_id") or "")
    if unit_id:
        try:
            from pathlib import Path

            from web_api import codex
            db_path = Path(__file__).resolve().parent.parent / "db" / "wh40k.sqlite"
            if db_path.exists():
                card = codex.unit_card(db_path, unit_id, hot_weapon=hot_weapon)
                if card is not None:
                    return card
        except Exception:
            pass  # 完整装配失败不挡答案，退回直映射
    return build_entity_card(ds_res, hot_weapon)


def _evidence_digest(recorder: TraceRecorder, limit: int = 2000) -> str:
    """把录到的工具返回压成给结构化 LLM 的证据摘要（截断防超长）。"""
    lines: List[str] = []
    for name, res in recorder.last_result.items():
        try:
            blob = json.dumps(res, ensure_ascii=False, default=str)
        except Exception:
            blob = str(res)
        lines.append("[{}] {}".format(name, blob[:600]))
    digest = "\n".join(lines)
    return digest[:limit]


def run_and_format(
    question: str,
    llm,
    structurer: Optional[StructuringLLM] = None,
    tools: Optional[Dict[str, Callable[..., Dict[str, Any]]]] = None,
    hot_weapon: Optional[str] = None,
) -> Answer:
    """跑 AgentLoop（工具用录制器包裹）并格式化为 Answer。"""
    from agent.tools import TOOLS
    recorder = TraceRecorder(tools if tools is not None else TOOLS)
    loop = AgentLoop(llm=llm, tools=recorder.wrapped_tools())
    result = loop.run(question)
    return format_answer(question, result, recorder, structurer, hot_weapon)
