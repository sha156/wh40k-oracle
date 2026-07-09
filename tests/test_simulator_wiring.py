"""P4-e 接线单测：三失败路径、CLI 解析、意图门控、真实库端到端。"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent import loop as agent_loop


# ---- 意图门控：谋已纳入零工具必查证 ----
def test_scheme_intent_now_gated():
    assert "谋" in agent_loop._MUST_VERIFY_INTENTS
    # 原有三档不丢
    for i in ("查", "判", "算"):
        assert i in agent_loop._MUST_VERIFY_INTENTS


# ---- P5-e：judge_fight_order 工具接线（替换 P5 桩）----
def test_judge_fight_order_charger_first():
    from agent.tools import judge_fight_order
    r = judge_fight_order({"attacker": "Warboss", "defender": "Terminators",
                           "attacker_charged": True})
    assert r["ok"] is True and r["modeled"] is True
    assert r["first_striker"] == "Warboss"
    assert r["rationale"] and r["rule_refs"]


def test_judge_fight_order_defender_fights_first():
    from agent.tools import judge_fight_order
    # 攻方未冲锋 + 守方 Fights First → 守方先打
    r = judge_fight_order({"attacker": "A", "defender": "B",
                           "attacker_charged": False, "defender_fights_first": True})
    assert r["first_striker"] == "B"


def test_judge_fight_order_no_longer_a_stub():
    from agent.tools import judge_fight_order
    r = judge_fight_order({"attacker": "A", "defender": "B"})
    # P4 桩返回 modeled=False + "未建模"；P5-e 起必须是真实判定
    assert r.get("modeled") is True
    assert "未建模" not in r.get("note", "")
    assert "first_striker" in r


def test_judge_fight_order_in_tool_registry():
    from agent.tools import TOOL_SPECS
    spec = next(s for s in TOOL_SPECS if s["name"] == "judge_fight_order")
    assert "未建模" not in spec["description"]


# ---- CLI loadout 解析 ----
def test_cli_parse_loadout():
    from engines.simulator.cli import _parse_loadout
    assert _parse_loadout("Shoota:9,Slugga:1") == [("Shoota", 9), ("Slugga", 1)]
    assert _parse_loadout("Choppa") == [("Choppa", 1)]
    assert _parse_loadout(None) is None
    assert _parse_loadout("") is None


# ---- 三失败路径（假 resolver，不碰库） ----
class _Res:
    def __init__(self, cid, name_en, conf, cands):
        self.canonical_id, self.name_en, self.confidence, self.candidates = (
            cid, name_en, conf, cands)


class _FakeResolver:
    def __init__(self, mapping):
        self._m = mapping

    def resolve(self, name):
        return self._m.get(name, _Res(None, None, "none", []))


def test_resolve_unit_ambiguous():
    from agent.tools import _resolve_unit
    rv = _FakeResolver({"终结者": _Res(None, None, "ambiguous", ["A 小队", "B 领主"])})
    out = _resolve_unit("终结者", resolver=rv)
    assert out["ok"] is False and out["reason"] == "ambiguous"
    assert "A 小队" in out["candidates"]


def test_resolve_unit_not_found():
    from agent.tools import _resolve_unit
    out = _resolve_unit("不存在的单位", resolver=_FakeResolver({}))
    assert out["ok"] is False and out["reason"] == "not_found"


def test_resolve_unit_fuzzy_warns_but_proceeds():
    from agent.tools import _resolve_unit
    rv = _FakeResolver({"歪名": _Res("000000001", "Warboss", "fuzzy", [])})
    out = _resolve_unit("歪名", resolver=rv)
    assert out["ok"] is True and "warning" in out


# ---- 真实库端到端 ----
DB = Path("db/wh40k.sqlite")
pytestmark_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")


@pytestmark_db
def test_simulate_combat_end_to_end():
    from agent.tools import simulate_combat
    res = simulate_combat("Boyz", "Intercessor Squad",
                          {"loadout": [["Shoota", 10]], "defender_models": 5, "n": 4000})
    assert res["ok"] is True and res["modeled"] is True
    rep = res["report"]
    assert rep["funnel"]["attacks"] == 20.0            # 10 Shoota × A2
    assert rep["expected_damage"] >= 0
    assert rep["bias_notes"]                            # 诚实声明非空
    # P5-a：not_modeled 由笼统一行升级为逐条精确分类（"未建模·<类别>：技能名"）
    assert any("未建模·" in nm for nm in rep["not_modeled"])
    assert "defender_toggles" in res                     # 守方可 opt-in 开关列名（可为空）


@pytestmark_db
def test_simulate_combat_multimodel_needs_loadout():
    from agent.tools import simulate_combat
    res = simulate_combat("Boyz", "Intercessor Squad")   # 未给 loadout
    assert res["ok"] is False and res["reason"] == "loadout_required"
    assert res["weapon_pool"]                             # 返回武器池供指定


# ---- P5-c：Go to Ground / Smokescreen 手工核验开关（评审 E1）----
@pytestmark_db
def test_go_to_ground_is_not_stealth():
    """E1：Go to Ground = 掩体 + 6+ 无效保护，**不**改命中（不是 Stealth）。"""
    from agent.tools import simulate_combat
    opt = lambda **k: {"loadout": [["Shoota", 10]], "phase": "shooting",
                       "n": 8000, "seed": 9, **k}
    base = simulate_combat("Boyz", "Intercessor Squad", opt())
    gtg = simulate_combat("Boyz", "Intercessor Squad", opt(go_to_ground=True))
    # 命中不受 Go to Ground 影响（它不给命中惩罚）
    assert gtg["report"]["funnel"]["hits"] == pytest.approx(
        base["report"]["funnel"]["hits"], rel=0.03)


@pytestmark_db
def test_smokescreen_lowers_hits():
    """E1：Smokescreen = 掩体 + Stealth → 射击命中下降。"""
    from agent.tools import simulate_combat
    opt = lambda **k: {"loadout": [["Shoota", 10]], "phase": "shooting",
                       "n": 8000, "seed": 9, **k}
    base = simulate_combat("Boyz", "Intercessor Squad", opt())
    smk = simulate_combat("Boyz", "Intercessor Squad", opt(smokescreen=True))
    assert smk["report"]["funnel"]["hits"] < base["report"]["funnel"]["hits"] * 0.8


@pytestmark_db
def test_faction_options_surfaced():
    """P5-c：守方阵营分队名 surface（诚实披露未建模的分队规则）。"""
    from agent.tools import simulate_combat
    res = simulate_combat("Boyz", "Intercessor Squad",
                          {"loadout": [["Shoota", 10]], "n": 1000})
    fo = res["faction_options"]
    assert fo["faction_id"] == "SM"
    assert isinstance(fo["detachments"], list) and len(fo["detachments"]) > 0
    assert "KEYWORDS" not in fo["detachments"]           # 噪声名已剔除
