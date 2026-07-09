"""P4-a 装配层单测：模型数解析 + loadout 组装 + 歧义/错误路径。

用真实库（db/wh40k.sqlite）跑端到端，验证 C1 装配缺口的补法：
  · parse_model_tiers 从 points desc 抽每档模型数
  · 未给 loadout → ambiguous + 武器池（P4 不猜默认装配）
  · 给 loadout → 组装 AttackerProfile，count 正确、同名武器按 phase 收窄
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engines.simulator.assembly import (
    assemble_attacker,
    default_model_count,
    parse_model_tiers,
)
from engines.simulator.profile import load_target, load_weapon_pool

DB = Path("db/wh40k.sqlite")
WARBOSS = "000000001"       # 单模型角色（武器池含互斥 choppa/klaw）
BOYZ = "000000016"          # 多模型：10/20 档，BOY+BOSS NOB 混编
INTERCESSOR = "000001157"   # 5/10 档，单 model 行

pytestmark = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")


# ---- 模型数解析（纯函数） ----
def test_parse_model_tiers_multi():
    pj = ('{"items":[{"desc":"10 models","cost":75},'
          '{"desc":"20 models","cost":150}]}')
    assert parse_model_tiers(pj) == [
        {"models": 10, "cost": 75}, {"models": 20, "cost": 150}]


def test_parse_model_tiers_single():
    assert parse_model_tiers('{"items":[{"desc":"1 model","cost":75}]}') == [
        {"models": 1, "cost": 75}]


def test_parse_model_tiers_sorts_and_skips_unparseable():
    pj = ('{"items":[{"desc":"20 models","cost":150},'
          '{"desc":"per model","cost":8},{"desc":"5 models","cost":80}]}')
    assert parse_model_tiers(pj) == [
        {"models": 5, "cost": 80}, {"models": 20, "cost": 150}]


def test_parse_model_tiers_empty():
    assert parse_model_tiers(None) == []
    assert parse_model_tiers("{}") == []


# ---- 真实库端到端 ----
def test_default_model_count_boyz():
    pool = load_weapon_pool(DB, BOYZ)
    assert len(pool) == 9                      # 实测 Boyz 武器池 9 把
    header_tiers = parse_model_tiers(
        '{"items":[{"desc":"10 models","cost":75},{"desc":"20 models","cost":150}]}')
    assert header_tiers[0]["models"] == 10


def test_assemble_no_loadout_is_ambiguous():
    res = assemble_attacker(DB, WARBOSS)
    assert res is not None
    assert res.ambiguous is True
    assert res.attacker is None
    assert len(res.weapon_pool) == 5           # Warboss 选项池 5 把
    assert res.models == 1                      # 单模型档


def test_assemble_with_loadout_builds_attacker():
    # 10 个 Boyz：全员 Shoota（近战另配 Choppa），BOSS NOB 拿 Power klaw
    res = assemble_attacker(
        DB, BOYZ, models=10,
        loadout=[("Shoota", 9), ("Slugga", 1)])
    assert res is not None and not res.ambiguous
    assert res.errors == []
    atk = res.attacker
    assert atk is not None and atk.models == 10
    names = {w.name_en: w.count for w in atk.loadout}
    assert names == {"Shoota": 9, "Slugga": 1}


def test_assemble_unknown_weapon_errors():
    res = assemble_attacker(DB, WARBOSS, loadout=[("Lasgun", 1)])
    assert res.ambiguous is True
    assert res.attacker is None
    assert any("不在该单位武器池" in e for e in res.errors)


def test_assemble_phase_narrows_same_name():
    # Intercessor 有近战 'Close combat weapon'；phase=melee 应能唯一匹配
    res = assemble_attacker(
        DB, INTERCESSOR, models=5,
        loadout=[("Bolt rifle", 5), ("Close combat weapon", 5)], phase="melee")
    assert not res.ambiguous, res.errors
    ccw = [w for w in res.attacker.loadout if w.name_en == "Close combat weapon"]
    assert len(ccw) == 1 and ccw[0].is_melee


def test_load_target_multimodel_uses_primary_and_keeps_rows():
    tgt = load_target(DB, BOYZ)
    assert tgt is not None
    assert tgt.t == 5 and tgt.w == 1          # 主行 BOY：T5 W1
    assert tgt.invuln is None                  # '-' → 无无效保护
    assert len(tgt.model_rows) == 2            # 混编两行保留供上层警示
    assert tgt.models == 10                     # 默认最小档


def test_load_target_unknown_returns_none():
    assert load_target(DB, "999999999") is None


def test_load_weapon_pool_parses_dice_and_keywords():
    pool = load_weapon_pool(DB, BOYZ)
    rokkit = next(w for w in pool if w.name_en == "Rokkit launcha")
    assert rokkit.attacks.faces == 3 and rokkit.attacks.n == 1   # A=D3
    assert rokkit.strength == 9 and rokkit.ap == -2 and rokkit.damage.k == 3
    assert any(k.name == "blast" for k in rokkit.raw_keywords)
