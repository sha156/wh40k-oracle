"""P5-a 技能分类器黄金用例：FNP 条件陷阱 + Stealth 端到端 + 零丢分桶对账。

分类器不自动施加任何效果（见 abilities.py 裁决）——它只分桶 + 为可建模防守 USR
产出"若启用则施加"的 Effect。这里断言：条件式 FNP 必进 toggle 不误判无条件、
Stealth（11版24.33=掩体收益）端到端让射击过保变难而命中不变、近战不受影响、
各桶之和 == 原始条数（不静默丢）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from engines.simulator.abilities import (
    CAT_NM_AURA_LEADER,
    CAT_NM_DEPLOYMENT,
    CAT_NM_MORALE,
    CAT_NM_ONDEATH,
    CAT_NM_OTHER,
    CAT_NM_TARGETING,
    CAT_TOGGLE_DEF,
    classify_ability,
    classify_records,
    clean_text,
)
from engines.simulator.contracts import (
    AbilityRecord,
    AttackerProfile,
    DiceExpr,
    Effect,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.sequence import run_sequence

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "db" / "wh40k.sqlite"


def _rec(name, text=""):
    return AbilityRecord(name_en=name, text=text)


# ── clean_text ───────────────────────────────────────────────
def test_clean_text_strips_html_and_unescapes():
    raw = '<b>WHEN:</b> Feel&nbsp;No Pain 5+<br><span class="x">ability</span>'
    out = clean_text(raw)
    assert "<" not in out and ">" not in out
    assert "&nbsp;" not in out and "Feel" in out and "ability" in out


def test_clean_text_none_empty():
    assert clean_text(None) == ""
    assert clean_text("") == ""


# ── 🔴 T1 陷阱：条件式 FNP 必须进 toggle 且标 conditional ───────────
def test_fnp_while_condition_is_conditional_not_unconditional():
    # Meganobz 原文：While the Waaagh! is active … Feel No Pain 5+
    rec = _rec("Krumpin' Time",
               "While the Waaagh! is active for your army, models in this unit "
               "have the Feel No Pain 5+ ability.")
    ca = classify_ability(rec)
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.conditional is True          # "While" 必须被识别为条件
    assert ca.params == (5,)
    assert ca.effect is not None and ca.effect.phase == "fnp"


def test_fnp_against_condition_is_conditional():
    rec = _rec("Psychic Hood",
               "Models in this unit have the Feel No Pain 4+ ability against "
               "Psychic Attacks.")
    ca = classify_ability(rec)
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.conditional is True
    assert ca.params == (4,)


def test_fnp_unconditional_self_parses_value_not_conditional():
    rec = _rec("Helix Gauntlet",
               "Models in this unit have the Feel No Pain 6+ ability.")
    ca = classify_ability(rec)
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.conditional is False
    assert ca.params == (6,)


def test_fnp_no_value_still_toggle_no_fake_default():
    rec = _rec("Feel No Pain",
               "Some models have the 'Feel No Pain x+' ability listed.")
    ca = classify_ability(rec)
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.params == ()                 # 抽不到值不猜默认
    assert ca.effect is None


# ── Stealth ──────────────────────────────────────────────────
def test_stealth_by_name_grants_cover_effect():
    # 11版 24.33：Stealth = 被远程攻击选中获掩体收益（不再是命中减值）
    ca = classify_ability(_rec("Stealth", ""))
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.conditional is False
    assert ca.effect == Effect("save", "cover", (), ("phase_shooting",), "stealth")
    assert "掩体" in ca.detail and "命中 -1" not in ca.detail


def test_hit_penalty_ability_by_text_pattern_keeps_hit_channel():
    # 单位专属减命中技能（原文明说 subtract 1 from Hit roll）≠ Stealth USR：
    # 按原文保留 hit+modify 通道，不随 24.33 掩体化
    ca = classify_ability(_rec(
        "Camouflage",
        "Each time a ranged attack is made against this unit, subtract 1 from "
        "that attack's Hit roll."))
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.effect is not None and ca.effect.phase == "hit"


# ── 减伤 ─────────────────────────────────────────────────────
def test_damage_reduction_detected():
    ca = classify_ability(_rec(
        "Duty and Honour",
        "Each time an attack is allocated to this model, reduce the Damage "
        "characteristic of that attack by 1."))
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.effect is not None and ca.effect.op == "damage_reduction"


# ── 评审 HIGH#2：伤害减半 ≠ 加法 -1，必须归未建模，不产 damage_reduction Effect ──
def test_halve_damage_is_not_flat_reduction():
    ca = classify_ability(_rec(
        "Molten Form",
        "Each time an attack is allocated to this model, halve the Damage "
        "characteristic of that attack."))
    assert ca.effect is None                         # 绝不塌成 (1,) 的加法减伤
    assert ca.category != CAT_TOGGLE_DEF
    assert "减半" in ca.detail


# ── 评审 LOW#8：裸 " 1" 不再触发减伤（需显式 by 1/one）──
def test_damage_reduction_not_triggered_by_bare_space_one():
    ca = classify_ability(_rec(
        "Minimum Wound",
        "This model's Damage is reduced to a minimum of 1 wound remaining."))
    assert ca.effect is None or ca.effect.op != "damage_reduction"


# ── 评审 HIGH#3：进攻型敌方压制（含 enemy）不得误判为本单位 Stealth ──
def test_offensive_enemy_suppression_not_classified_as_stealth():
    ca = classify_ability(_rec(
        "Rivetin' Dakka",
        "In your Shooting phase, after this model has shot, select one enemy "
        "unit hit. That enemy unit is suppressed. While a unit is suppressed, "
        "each time a model in that unit makes a ranged attack, subtract 1 from "
        "the Hit roll."))
    # 不能产出让攻方命中 -1 的 Stealth Effect
    assert not (ca.effect is not None and ca.effect.phase == "hit")


def test_core_stealth_with_legacy_text_still_detected_as_cover():
    # name 精确命中「Stealth」时按 11版 USR 处理（即使正文还是十版 -1 措辞）
    ca = classify_ability(_rec(
        "Stealth",
        "Each time a ranged attack is made against it, subtract 1 from that "
        "attack's Hit roll."))
    assert ca.effect is not None
    assert ca.effect.phase == "save" and ca.effect.op == "cover"


# ── 评审 M#4："whilst" 英式变体必须识别为条件式 ──
def test_whilst_fnp_is_conditional():
    ca = classify_ability(_rec(
        "Medicae Medi-packs",
        "Whilst this unit contains one or more Medicae Servitors, models in "
        "this unit have the Feel No Pain 5+ ability."))
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.conditional is True                     # 不能被当成无条件


# ── not_modeled 精确分桶 ──────────────────────────────────────
@pytest.mark.parametrize("name,text,expect", [
    ("Lone Operative",
     "This model can only be selected as the target of a ranged attack if the "
     "attacking model is within 12\".", CAT_NM_TARGETING),
    ("Scouts 6\"", "...", CAT_NM_DEPLOYMENT),
    ("Synapse", "...", CAT_NM_MORALE),
    ("Deadly Demise 1", "...", CAT_NM_ONDEATH),
    ("Aura of Command", "While a friendly unit is within 6\" of this model...",
     CAT_NM_AURA_LEADER),
    ("Weird Bespoke Thing", "does something unclassifiable and unique",
     CAT_NM_OTHER),
])
def test_not_modeled_buckets(name, text, expect):
    assert classify_ability(_rec(name, text)).category == expect


# ── 零丢分桶对账 ─────────────────────────────────────────────
def test_classify_records_no_silent_drop():
    recs = (
        _rec("Stealth"),
        _rec("Krumpin' Time", "While the Waaagh! ... Feel No Pain 5+ ability."),
        _rec("Lone Operative", "can only be selected as the target ... within 12\""),
        _rec("Synapse"),
        _rec("Mystery", "unique"),
    )
    cls = classify_records(recs)
    assert cls.total == len(recs)
    assert cls.bucket_count() == len(recs)          # 各桶之和 == 原始条数
    assert len(cls.toggle_defensive) == 2           # Stealth + FNP
    assert len(cls.not_modeled) == 3


def test_classification_reporting_lines_nonempty():
    cls = classify_records((
        _rec("Krumpin' Time", "While the Waaagh! ... Feel No Pain 5+ ability."),
        _rec("Lone Operative", "can only be selected as the target ... within 12\""),
    ))
    assert any("无痛" in s for s in [t[1] for t in cls.toggle_summaries()])
    assert any("未建模·" in line for line in cls.not_modeled_by_category())


# ── Stealth 端到端（11版24.33）：射击获掩体过保变难、命中不变、近战不变 ──
N = 60_000
SEED = 20260709


def _atk(range_, bs_ws, effects=()):
    w = WeaponProfile(
        name_zh=None, name_en="probe", range=range_,
        attacks=DiceExpr(k=1), bs_ws=bs_ws, strength=4, ap=0,
        damage=DiceExpr(k=1), effects=tuple(effects), count=10)
    return AttackerProfile(canonical_id="a", name_en="A", name_zh=None,
                           models=10, loadout=(w,))


def _tgt(effects=()):
    return TargetProfile(canonical_id="t", name_en="T", name_zh=None, models=10,
                         t=4, sv=6, invuln=None, w=1, oc=1, effects=effects)


STEALTH = Effect("save", "cover", (), ("phase_shooting",), "stealth")


def _raw(attacker, target, stance):
    return run_sequence(attacker, target, stance, n=N, seed=SEED)


def test_stealth_grants_cover_in_shooting():
    atk = _atk("24\"", bs_ws=3)                     # 3+ 命中，AP0
    base = _raw(atk, _tgt(), Stance(phase="shooting"))
    stl = _raw(atk, _tgt((STEALTH,)), Stance(phase="shooting"))
    # 命中不变（11版 Stealth 不再减命中）
    assert float(stl.hits.mean()) == pytest.approx(float(base.hits.mean()), abs=0.15)
    # Sv6+ AP0 → 掩体后有效 5+：过保失败率 5/6 → 4/6（unsaved 约降 20%）
    ratio = float(stl.unsaved.mean()) / float(base.unsaved.mean())
    assert ratio == pytest.approx(0.8, abs=0.05)


def test_stealth_cancelled_by_ignores_cover():
    # 攻方带 [IGNORES COVER]（24.18）→ Stealth 的掩体收益被抵消，与无 Stealth 一致
    ign = (Effect("save", "ignores_cover", (), (), "ignores cover"),)
    atk = _atk("24\"", bs_ws=3, effects=ign)
    base = _raw(atk, _tgt(), Stance(phase="shooting"))
    stl = _raw(atk, _tgt((STEALTH,)), Stance(phase="shooting"))
    assert float(stl.unsaved.mean()) == pytest.approx(
        float(base.unsaved.mean()), rel=0.03)


def test_stealth_does_not_affect_melee():
    atk = _atk("Melee", bs_ws=3)
    base = _raw(atk, _tgt(), Stance(phase="melee"))
    stl = _raw(atk, _tgt((STEALTH,)), Stance(phase="melee"))
    # 近战不受 Stealth 影响：命中与过保均不变
    assert abs(float(base.hits.mean()) - float(stl.hits.mean())) < 0.05
    assert float(stl.unsaved.mean()) == pytest.approx(
        float(base.unsaved.mean()), rel=0.03)


# ── DB 集成：全库挂载技能零丢分桶（裸调对账，spec 验证 #4）──────────
@pytest.mark.skipif(not DB.exists(), reason="wh40k.sqlite 不存在")
def test_full_library_no_silent_drop():
    from engines.simulator.abilities import clean_text as _clean
    conn = sqlite3.connect(str(DB))
    try:
        rows = conn.execute(
            "SELECT name_en, text_zh FROM abilities "
            "WHERE owner_id IS NOT NULL AND owner_id != ''").fetchall()
    finally:
        conn.close()
    recs = tuple(AbilityRecord(name_en=(r[0] or ""), text=_clean(r[1])) for r in rows)
    cls = classify_records(recs)
    assert cls.total == len(recs)
    assert cls.bucket_count() == len(recs)          # 3607 条一条不丢
    assert len(recs) > 3000                          # sanity：确实扫到全库
