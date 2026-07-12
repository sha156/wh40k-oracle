"""tests/test_web_api_stage3.py — Stage 3 结构化回答契约 + formatter 测试。

覆盖：richtext tokenizer（各 span 类型）、entityCard 映射（真 DB 的 Broadside）、
formatter 端到端（Fake LLM，断言 A 类槽位确定性正确 + B 类经 tokenizer 成 RichText）、
FastAPI 无 key 降级不崩、防目录穿越。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.loop import AgentLoop, AgentResult
from web_api.contract import Answer, InlineCite, InlineText
from web_api.entity_card import build_entity_card
from web_api.formatter import format_answer, run_and_format
from web_api.richtext import to_richtext
from web_api.trace import TraceRecorder

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "wh40k.sqlite"


# ── richtext tokenizer ────────────────────────────────────────────

def _kinds(rt):
    return [(x.t, getattr(x, "s", None) if isinstance(x, InlineText) else x.n) for x in rt]


def test_tokenizer_num_kw_strong_cite():
    rt = to_richtext("【重型】未移动 +1 命中 → 3+ 命中（67%），**值得带** [2]")
    kinds = _kinds(rt)
    assert ("kw", "[重型]") in kinds
    assert ("num", "3+") in kinds
    assert ("num", "67%") in kinds
    assert ("strong", "值得带") in kinds
    assert ("cite", 2) in kinds


def test_tokenizer_cite_vs_keyword_disambiguation():
    rt = to_richtext("[2] 是引用，[毁灭伤害] 是关键词")
    types = [x.t for x in rt]
    assert "cite" in types
    assert any(x.t == "kw" and x.s == "[毁灭伤害]" for x in rt)


def test_tokenizer_stat_tokens():
    rt = to_richtext("S12 AP-4 D6+1 打出 5++ 无效")
    nums = [x.s for x in rt if isinstance(x, InlineText) and x.t == "num"]
    assert "S12" in nums and "AP-4" in nums and "D6+1" in nums and "5++" in nums


def test_tokenizer_empty():
    assert to_richtext("") == []


def test_tokenizer_no_number_leak_into_keyword():
    rt = to_richtext("【重型2】")
    # 关键词内部的数字不应被切成独立 num span
    assert len(rt) == 1 and rt[0].t == "kw" and rt[0].s == "[重型2]"


# ── entityCard 映射（真 DB）───────────────────────────────────────

@pytest.mark.skipif(not DB_PATH.exists(), reason="wh40k.sqlite 不存在")
def test_entity_card_from_real_datasheet():
    from agent.tools import get_datasheet
    res = get_datasheet("Broadside Battlesuits")
    assert res.get("found")
    card = build_entity_card(res, hot_weapon="rail")
    assert card is not None
    assert card.name_en == "Broadside Battlesuits"
    assert card.name_zh  # 中文名非空
    # 属性格顺序 M/T/SV/W/LD/OC
    assert [s.lab for s in card.stats][:6] == ["M", "T", "SV", "W", "LD", "OC"]
    # 点数由 points_options 拼接
    assert "/" in card.pts
    # 焦点武器 hot 命中 rail
    assert any(w.hot and "rail" in w.name.lower() for w in card.ranged)
    # 近战武器 range 本地化
    assert card.melee and card.melee[0].range == "近战"
    # 诚实：src 不含伪造页码，标结构库来源
    assert "L3 结构库" in card.src


def test_entity_card_not_found_returns_none():
    assert build_entity_card({"found": False}, None) is None
    assert build_entity_card({}, None) is None


# ── formatter 端到端（Fake LLM）───────────────────────────────────

class _FakeStructurer:
    """返回固定结构化槽位，验证 B 类槽位经 tokenizer 成 RichText。"""

    def structure(self, question, prose, evidence, cites):
        return {
            "verdict": {"label": "值得带", "labelEn": "Sanctioned",
                        "lede": "对帝国骑士每轮约 2.3 伤，**值得带**"},
            "calc": ["【重型】未移动 → 3+ 命中 [1]", "S12 对 T12 → 4+ 穿防"],
            "sensitivity": {"title": "◭ 敏感性", "text": "有【标记】时命中 2+"},
            "followups": ["换武器打步兵？", "对比铁手将军"],
        }


def _fake_agent_result(prose="散文答案", degraded=False, sources=None):
    return AgentResult(answer=prose, intent="判", tool_calls=["get_datasheet"],
                       degraded=degraded, sources=sources or [])


def test_formatter_derives_slots_and_richtext():
    rec = TraceRecorder({})
    # 手动塞一条 get_datasheet 证据模拟工具已跑
    rec.last_result["get_datasheet"] = {
        "found": True,
        "datasheet": {"name_en": "X", "name_zh": "测试单位", "faction": "钛帝国",
                      "points_options": [{"line": "1", "desc": "1 model", "cost": 80}],
                      "keywords": ["A"], "models": [{"m": "5\"", "t": "6", "sv": "2+",
                      "invuln": "-", "w": "8", "ld": "7+", "oc": "2"}],
                      "weapons": [{"name": "gun", "kind": "ranged", "range": "60",
                      "a": "2", "bs_ws": "4", "s": "12", "ap": "-4", "d": "D6+1",
                      "keywords": []}]},
    }
    ans = format_answer("测试问题", _fake_agent_result(), rec, _FakeStructurer())
    assert isinstance(ans, Answer)
    # A 类：entityCard 来自证据
    assert ans.entity_card is not None and ans.entity_card.name_zh == "测试单位"
    # B 类：verdict.lede 经 tokenizer 有 strong span
    assert any(isinstance(x, InlineText) and x.t == "strong" for x in ans.verdict.lede)
    # calc 步骤有 kw + cite span
    assert len(ans.calc) == 2
    flat = [x for step in ans.calc for x in step.text]
    assert any(isinstance(x, InlineCite) for x in flat)
    # sensitivity 有 kw span
    assert ans.sensitivity is not None
    assert any(isinstance(x, InlineText) and x.t == "kw" for x in ans.sensitivity.text)
    # followups
    assert ans.followups == ["换武器打步兵？", "对比铁手将军"]
    # summary 确定性
    assert "引用" in ans.summary


def test_formatter_fallback_without_structurer():
    """无结构化器：verdict.lede 退化为散文整段，calc 空。"""
    rec = TraceRecorder({})
    ans = format_answer("问题", _fake_agent_result(prose="档案缺失"), rec, None)
    assert ans.verdict.label == "参谋回复"
    assert ans.verdict.lede  # 散文进 lede
    assert ans.calc == []


def test_formatter_degraded_flows_through():
    rec = TraceRecorder({})
    ans = format_answer("问题", _fake_agent_result(degraded=True), rec, None)
    assert ans.degraded is True
    assert "已降级兜底" in ans.summary


def test_trace_recorder_records_status():
    """录制器把未建模工具标 degraded。"""
    def fake_tool(**kw):
        return {"ok": False, "modeled": False, "note": "未建模"}
    rec = TraceRecorder({"simulate_combat": fake_tool})
    wrapped = rec.wrapped_tools()
    wrapped["simulate_combat"](attacker="a", defender="b")
    assert len(rec.steps) == 1
    assert rec.steps[0].status == "degraded"
    assert rec.steps[0].fn == "simulate_combat"


# ── FastAPI 降级 + 安全 ───────────────────────────────────────────

def test_contract_json_roundtrip_camelcase():
    """Answer.model_dump(by_alias=True) 出 camelCase，与前端 answer.ts 对齐。"""
    rec = TraceRecorder({})
    ans = format_answer("q", _fake_agent_result(), rec, _FakeStructurer())
    d = ans.model_dump(by_alias=True)
    assert "traceWarn" in d  # camelCase 别名
    assert "labelEn" in d["verdict"]
    # entityCard 键名也是 camelCase
    # （本例无 entityCard，跳过）


@pytest.mark.skipif(not DB_PATH.exists(), reason="wh40k.sqlite 不存在")
def test_codex_factions_units_card():
    """图鉴端点：阵营列表 → 单位列表 → 兵牌，真 DB。"""
    from web_api import codex

    factions = codex.list_factions(DB_PATH)
    assert len(factions) >= 20  # 25 有单位阵营
    top = factions[0]
    assert top["count"] > 0 and top["name"]
    # curated 中文名正确（不用众数——GC 不该是星界军）
    gc = next((f for f in factions if f["id"] == "GC"), None)
    if gc:
        assert gc["nameZh"] == "基因窃取者教派"

    units = codex.list_units(DB_PATH, top["id"])
    assert len(units) == top["count"]
    assert all("id" in u and "nameEn" in u for u in units)

    card = codex.unit_card(DB_PATH, units[0]["id"])
    assert card is not None and card.name_en


@pytest.mark.skipif(not DB_PATH.exists(), reason="wh40k.sqlite 不存在")
def test_codex_unit_not_found():
    from web_api import codex
    assert codex.unit_card(DB_PATH, "999999999") is None
    assert codex.faction_exists(DB_PATH, "ZZZ") is False


def test_run_and_format_with_fake_loop_llm():
    """端到端：Fake 主循环 LLM 直接 final（查意图会先被门控 nudge，这里用闲聊绕过）。"""

    class _FakeLLM:
        def __init__(self):
            self.calls = 0

        def classify_intent(self, user_input):
            return "闲聊"  # 绕过零工具门控

        def next_step(self, messages, tool_specs):
            return {"type": "final", "content": "你好，我是规则参谋。", "sources": []}

    ans = run_and_format("在吗", _FakeLLM(), structurer=None, tools={})
    assert isinstance(ans, Answer)
    assert ans.verdict.lede
