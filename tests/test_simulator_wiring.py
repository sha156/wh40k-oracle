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
    assert any("abilities" in nm.lower() for nm in rep["not_modeled"])


@pytestmark_db
def test_simulate_combat_multimodel_needs_loadout():
    from agent.tools import simulate_combat
    res = simulate_combat("Boyz", "Intercessor Squad")   # 未给 loadout
    assert res["ok"] is False and res["reason"] == "loadout_required"
    assert res["weapon_pool"]                             # 返回武器池供指定
