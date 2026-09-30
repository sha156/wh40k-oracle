"""web_api/formatter.py — response_formatter：AgentResult + 工具证据 → Answer 契约。

分工（见 spec 第 1 节）：
- A 类槽位（trace/entityCard/cites/summary/traceWarn/cta/degraded）：确定性推导，零 LLM。
- B 类槽位（verdict/calc/sensitivity/followups）：一次结构化 LLM 调用产轻标记文本，
  再由 richtext tokenizer 转 RichText。结构化调用失败则 fail-closed 退化为「散文整段纯文本」。
"""
from __future__ import annotations

import json
import re
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

def _historical_records(recorder: TraceRecorder) -> List[Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    for tool in ("get_datasheet", "get_entity", "entity_resolver", "calc_points"):
        for result in recorder.get_results(tool):
            if not isinstance(result, dict):
                continue
            for item in [result] + (result.get("units") or []):
                record = item.get("historical_record") if isinstance(item, dict) else None
                if isinstance(record, dict) and record.get("archive_id"):
                    records[record["archive_id"]] = record
    return list(records.values())


def _derive_cites(result: AgentResult, recorder: TraceRecorder) -> List[Cite]:
    """从工具证据与检索来源确定性抽引用；去重编号。诚实：无页码不编页码。"""
    cites: List[Cite] = []
    seen = set()

    def _add(book, page=None, section=None, term=None, wiki="", url=None):
        page = page if isinstance(page, int) and page > 0 else None
        key = (book, page, term, url)
        if key in seen or not book:
            return
        seen.add(key)
        cites.append(Cite(n=len(cites) + 1, book=book, page=page,
                          section=section, term=term, wiki=wiki, url=url))

    # 关键词定义页（核心规则术语）——provenance，非伪造页码
    for kw_res in recorder.get_results("get_keyword_definition"):
        if isinstance(kw_res, dict) and kw_res.get("found"):
            page = kw_res.get("page")
            term = getattr(getattr(page, "fm", None), "name_zh", None) if page else None
            wiki = "core-rules/" + (getattr(getattr(page, "fm", None), "name_en", "") or "")
            _add("核心规则术语", section="USR/关键词", term=term or "", wiki=wiki)

    # 结构库属性块
    for ds_res in recorder.get_results("get_datasheet"):
        if isinstance(ds_res, dict) and ds_res.get("found") and ds_res.get("datasheet"):
            ds = ds_res["datasheet"]
            _add("L3 结构库 · " + str(ds.get("faction") or "未知"),
                 term=str(ds.get("name_en") or ""), section="属性块")

    # A merged wiki card is also structured evidence. Without its own citation
    # the structurer can only attach unrelated PDF pages to card-specific facts.
    # Do not promote its frontmatter references to per-field PDF provenance.
    for entity in recorder.get_results("get_entity"):
        if isinstance(entity, dict) and entity.get("found"):
            fm = getattr(entity.get("page"), "fm", None)
            if fm is not None and (fm.version or {}).get("source") == "official-db":
                _add("L3 结构库 · " + str(fm.faction or "未知"),
                     term=str(fm.name_en or fm.name_zh or fm.id), section="合并兵牌")

    # 检索来源（真有 book/page 出处）
    for evidence in recorder.get_results("calc_points") + recorder.get_results("get_datasheet"):
        if isinstance(evidence, dict):
            for source in evidence.get("official_sources", []):
                _add("Munitorum Field Manual", section="官方当前点数",
                     url=source.get("url"))
    for record in _historical_records(recorder):
        # The cached POST endpoint is provenance, not a navigable card URL.
        _add("黑图书馆 · 历史缓存（第三方，已删除）", section="历史资料，非当前点数",
             term="{} · 源记录 {}".format(record.get("name_en", ""), record.get("source_id", "")))
    sources = result.sources if isinstance(result.sources, list) else []
    for p in sources[:6]:
        if isinstance(p, dict) and isinstance(p.get("book"), str) and p["book"].strip():
            page = p.get("page")
            valid_page = re.fullmatch(r"[0-9]{1,7}", str(page))
            _add(str(p["book"]), page=int(page) if valid_page else None,
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

def _validate_layout(structured: Dict[str, Any]) -> None:
    """Malformed but parseable JSON must not silently discard verified prose."""
    if not isinstance(structured, dict):
        raise ValueError("Answer layout must be an object")
    verdict = structured.get("verdict")
    if not isinstance(verdict, dict) or not isinstance(verdict.get("lede"), str) or not verdict["lede"].strip():
        raise ValueError("Answer layout requires a text verdict")
    if {"calc", "sensitivity", "followups"}.intersection(verdict):
        raise ValueError("Answer content is nested in the wrong slot")
    for field in ("label", "labelEn"):
        if field in verdict and not isinstance(verdict[field], str):
            raise ValueError("Verdict labels must be text")
    for field in ("calc", "followups"):
        value = structured.get(field, [])
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError("Answer {} must be a list of text".format(field))
    sensitivity = structured.get("sensitivity")
    if sensitivity is not None:
        if not isinstance(sensitivity, dict) or not isinstance(sensitivity.get("text"), str):
            raise ValueError("Answer sensitivity must contain text")
        if "title" in sensitivity and not isinstance(sensitivity["title"], str):
            raise ValueError("Sensitivity title must be text")


def _missing_table_labels(prose: str, structured: Dict[str, Any]) -> List[str]:
    """Reject lossy formatting of named Markdown rows; fall back to full prose.

    A table can contain the actual answer (e.g. six order effects). A valid JSON
    response is not sufficient if the layout model drops that entire table.
    Numeric-only labels are excluded; conservative false positives retain prose.
    """
    def normalized(text: str) -> str:
        return re.sub(r"\W+", "", text, flags=re.UNICODE).casefold()

    labels: List[tuple[str, str]] = []
    in_table = False
    for line in prose.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?", stripped):
            in_table = True
            continue
        if not stripped.startswith("|") or "\\|" in stripped:
            in_table = False
            continue
        if in_table:
            raw_label = stripped.strip("|").split("|", 1)[0].strip()
            label = normalized(raw_label)
            if label and any(ch.isalpha() for ch in label):
                labels.append((raw_label, label))
    if len(labels) < 2:
        return []
    verdict = structured.get("verdict") or {}
    sensitivity = structured.get("sensitivity") or {}
    visible = normalized(" ".join([
        str(verdict.get("lede", "")),
        *[str(item) for item in (structured.get("calc") or [])],
        str(sensitivity.get("text", "")),
    ]))
    # The layout pass may use a natural short form of a dotted Chinese personal
    # name ("罗伯特·基里曼" -> "基里曼").  Treat that as the same row only when
    # the short form uniquely identifies one row in this table.  This keeps the
    # original loss guard fail-closed for tables containing two people with the
    # same final name, and does not authorize arbitrary fuzzy abbreviations.
    aliases: List[List[str]] = []
    for raw_label, label in labels:
        raw_name = re.split(r"[（(]", raw_label, maxsplit=1)[0]
        candidates: List[str] = []
        dotted = re.split(r"[·•・]", raw_name)
        if len(dotted) > 1:
            short = normalized(dotted[-1])
            if len(short) >= 3 and all("\u3400" <= ch <= "\u9fff" for ch in short):
                candidates.append(short)
        aliases.append(candidates)

    # A short form must not occur anywhere in another row's full label.  Counting
    # only equal dotted suffixes misses collisions such as ordinary "卡尔加"
    # versus a non-dotted "卡尔加（安提洛库斯之铠版）" row.
    short_counts = {
        alias: sum(alias in other_label for _raw, other_label in labels)
        for candidates in aliases for alias in candidates
    }

    missing: List[str] = []
    for (_raw_label, label), candidates in zip(labels, aliases):
        if label in visible or any(
            alias in visible
            for alias in candidates
            if short_counts.get(alias, 0) == 1
        ):
            continue
        missing.append(label)
    return missing


_HISTORICAL_ABSENCE = re.compile(
    r"(?:无|没有|不存在|未有|并无)(?:任何|可用|对应|相关|已知)?的?"
    r"历史(?:缓存)?(?:点数|记录|资料|数据)"
)
_ABSENCE_NEGATION = re.compile(
    r"(?:不得|不能|不可|禁止|不要|不应|并非|不代表|不等于|未证实|未确认|"
    r"无法确认|不能据此断言)"
)
_DOTTED_ZH_NAME = re.compile(
    r"[\u3400-\u9fff]{1,20}(?:[·•・][\u3400-\u9fff]{1,20})+"
)


def _structured_body(structured: Dict[str, Any], *, followups: bool = False) -> str:
    verdict = structured.get("verdict") or {}
    sensitivity = structured.get("sensitivity") or {}
    parts = [str(verdict.get("lede", "")),
             *[str(item) for item in (structured.get("calc") or [])],
             str(sensitivity.get("text", ""))]
    if followups:
        parts.extend(str(item) for item in (structured.get("followups") or []))
    return "\n".join(parts)


def _unsupported_grounding_claims(
    question: str, prose: str, evidence: str, text: str,
) -> List[str]:
    """Find two high-confidence ways a layout pass can invent new facts.

    The structurer may paraphrase, so broad token-diff validation is unsafe. These
    checks target concrete regressions: asserting that historical data does not
    exist merely because no field was returned, and introducing a newly named
    Chinese variant. The original prose/evidence remains the authority.
    """
    problems: List[str] = []
    factual_grounding = prose + "\n" + evidence

    def affirmative_absence_subjects(value: str) -> set[str]:
        subjects: set[str] = set()
        for clause in re.split(r"[，。；！？\n]", value):
            for match in _HISTORICAL_ABSENCE.finditer(clause):
                prefix = clause[:match.start()]
                # "Do not claim there is no history" is a caution, not evidence
                # that the historical record is absent.
                if _ABSENCE_NEGATION.search(prefix):
                    continue
                labels = [part for part in re.split(r"[:：]", prefix) if part.strip()]
                subject = labels[-1] if labels else prefix
                subject = re.sub(r"[^\u3400-\u9fffA-Za-z0-9·•・.]+", "", subject)
                subjects.add(subject or "*")
        return subjects

    claimed_absences = affirmative_absence_subjects(text)
    grounded_absences = affirmative_absence_subjects(factual_grounding)
    if any(subject not in grounded_absences for subject in claimed_absences):
        problems.append("unsupported historical-absence claim")

    entity_grounding = question + "\n" + factual_grounding
    for candidate in _DOTTED_ZH_NAME.findall(text):
        # The regex intentionally captures contiguous Chinese, including nearby
        # grammar. Strip a small set of relation/predicate words, then compare the
        # complete dotted identity; accepting arbitrary substrings would let
        # `卡尔加·安提洛库斯` incorrectly authorize `卡尔加·无畏机甲`.
        name = re.sub(r"^(?:关于|至于|其中|而|相对于)+", "", candidate)
        name = re.sub(
            r"(?:当前|现在|此时|等版本|版本|等|的|是|为|可以|能够|点数)+$", "", name)
        if name not in entity_grounding:
            problems.append("unsupported named variant: " + name)
    return problems

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
            _validate_layout(structured)
            if _missing_table_labels(agent_result.answer, structured):
                raise ValueError("Answer formatting omitted named table rows")
            if _unsupported_grounding_claims(
                    question, agent_result.answer, evidence, _structured_body(structured)):
                raise ValueError("Answer formatting added unsupported factual claims")
            # Follow-up suggestions are optional. Drop only unsupported ones rather
            # than degrading an otherwise grounded answer layout.
            if structured.get("followups"):
                structured["followups"] = [
                    item for item in structured["followups"]
                    if not _unsupported_grounding_claims(
                        question, agent_result.answer, evidence, str(item))
                ]
        except Exception:
            structured = {}
            degraded = True
            trace_warn = "回答排版失败，以下保留原始回复与已查证来源。"
            summary = _derive_summary(trace, cites, degraded)

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
    for record in _historical_records(recorder):
        summary = {key: record.get(key) for key in (
            "archive_id", "name_en", "historical_points", "is_current", "source_scope",
            "identity_scope")}
        lines.append("[历史来源] " + json.dumps(summary, ensure_ascii=False))
    scopes = set()
    for entity in recorder.get_results("get_entity"):
        if isinstance(entity, dict) and entity.get("found") and entity.get("source_scope"):
            fm = getattr(entity.get("page"), "fm", None)
            # Name each comparison subject before bulk text. Shared scope
            # warnings need only be included once in the bounded digest.
            scope = str(entity["source_scope"])
            lines.append("[合并兵牌出处] {} · {}：{}".format(
                getattr(fm, "faction", ""), getattr(fm, "name_en", ""),
                scope if scope not in scopes else "同上来源边界",
            ))
            scopes.add(scope)
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
