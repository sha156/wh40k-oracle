"""P5-a 技能分类器黄金用例：FNP 条件陷阱 + Stealth 端到端 + 零丢分桶对账。

分类器不自动施加任何效果（见 abilities.py 裁决）——它只分桶 + 为可建模防守 USR
产出"若启用则施加"的 Effect。这里断言：条件式 FNP 必进 toggle 不误判无条件、
Stealth 端到端让射击命中降一档而近战不变、各桶之和 == 原始条数（不静默丢）。
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
def test_stealth_by_name_makes_ranged_hit_penalty_effect():
    ca = classify_ability(_rec("Stealth", ""))
    assert ca.category == CAT_TOGGLE_DEF
    assert ca.conditional is False
    assert ca.effect == Effect("hit", "modify", (-1,), ("phase_shooting",), "stealth")


def test_stealth_by_text_pattern():
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


# ── Stealth 端到端：射击命中降一档、近战不变 ─────────────────────
N = 60_000
SEED = 20260709


def _atk(range_, bs_ws):
    w = WeaponProfile(
        name_zh=None, name_en="probe", range=range_,
        attacks=DiceExpr(k=1), bs_ws=bs_ws, strength=4, ap=0,
        damage=DiceExpr(k=1), effects=(), count=10)
    return AttackerProfile(canonical_id="a", name_en="A", name_zh=None,
                           models=10, loadout=(w,))


def _tgt(effects=()):
    return TargetProfile(canonical_id="t", name_en="T", name_zh=None, models=10,
                         t=4, sv=6, invuln=None, w=1, oc=1, effects=effects)


STEALTH = Effect("hit", "modify", (-1,), ("phase_shooting",), "stealth")


def _hits_mean(attacker, target, stance):
    raw = run_sequence(attacker, target, stance, n=N, seed=SEED)
    return float(raw.hits.mean())


def test_stealth_lowers_shooting_hits():
    atk = _atk("24\"", bs_ws=3)                     # 3+ 命中
    base = _hits_mean(atk, _tgt(), Stance(phase="shooting"))
    stealth = _hits_mean(atk, _tgt((STEALTH,)), Stance(phase="shooting"))
    # 3+ 命中 → Stealth 有效 4+：10 攻击命中期望 6.67 → 5.0（降幅 ~10*(1/6)≈1.67）
    assert base == pytest.approx(6.667, abs=0.15)
    assert stealth == pytest.approx(5.0, abs=0.15)
    assert base - stealth == pytest.approx(1.667, abs=0.2)


def test_stealth_does_not_affect_melee():
    atk = _atk("Melee", bs_ws=3)
    base = _hits_mean(atk, _tgt(), Stance(phase="melee"))
    stealth = _hits_mean(atk, _tgt((STEALTH,)), Stance(phase="melee"))
    assert abs(base - stealth) < 0.05               # 近战不受 Stealth 影响


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
