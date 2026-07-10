"""P4-c 词条→Effect 黄金用例：每词条单独 + 关键组合（lethal+dev、anti+dev）。

走完整链路 parse.tokenize_keywords → keywords.build_weapon_effects → sequence 生效，
每例把受词条影响的漏斗均值与解析期望对拍（容差 <3%）。
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Effect,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.keywords import build_weapon_effects, keyword_to_effects
from engines.simulator.parse import tokenize_keywords
from engines.simulator.sequence import run_sequence

N = 120_000
SEED = 20260709


def const(k):
    return DiceExpr(n=0, faces=0, k=k)


def kw(s):
    """词条串 → effects（走真实 parse+mapping 链）。"""
    parsed, _ = tokenize_keywords('["' + s + '"]')
    effects, _mod, _ann, _unp = build_weapon_effects(tuple(parsed))
    return effects


def weapon(attacks, bs_ws, strength, ap, damage, effects=(), melee=False, count=1):
    return WeaponProfile(
        name_zh=None, name_en="W", range="Melee" if melee else "24",
        attacks=attacks, bs_ws=bs_ws, strength=strength, ap=ap,
        damage=damage, effects=tuple(effects), count=count)


def atk(w):
    return AttackerProfile(canonical_id="A", name_en="A", name_zh=None,
                           models=1, loadout=(w,), keywords=frozenset())


def tgt(t, sv, w, models, invuln=None, keywords=(), effects=()):
    return TargetProfile(canonical_id="T", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=w, oc=1,
                         keywords=frozenset(keywords), effects=tuple(effects))


def st(phase="shooting", cover=False, charging=False, stationary=False,
       half=False, long_range=False, indirect=False):
    return Stance(phase=phase, charging=charging, stationary=stationary,
                  half_range=half, target_in_cover=cover,
                  long_range=long_range, indirect=indirect)


def run(w, t, s):
    return run_sequence(atk(w), t, s, n=N, seed=SEED)


def close(got, exp, rel=0.02, absol=0.03):
    return abs(got - exp) <= max(absol, abs(exp) * rel)


# ===================== 映射层单测 =====================
def test_mapping_basic():
    (e,), mod, ann = keyword_to_effects(tokenize_keywords('["rapid fire 2"]')[0][0])
    assert e.phase == "attacks" and e.op == "modify"
    assert e.params[0].is_constant and e.params[0].k == 2   # 常量存 DiceExpr(k=2)
    assert e.condition == ("half_range",)


def test_mapping_anti_carries_keyword_and_threshold():
    pk = tokenize_keywords('["anti-vehicle 4+"]')[0][0]
    (e,), mod, ann = keyword_to_effects(pk)
    assert e.phase == "wound" and e.op == "crit_threshold"
    assert e.params == (4,) and e.condition == ("target_has_keyword", "vehicle")


def test_mapping_precision_is_annotation_not_math():
    pk = tokenize_keywords('["precision"]')[0][0]
    e, mod, ann = keyword_to_effects(pk)
    assert e == [] and mod == [] and ann and "precision" in ann[0]


def test_build_collects_unparsed():
    parsed, _ = tokenize_keywords('["rapid fire 1, bubblechukka"]')
    eff, mod, ann, unp = build_weapon_effects(tuple(parsed))
    assert "rapid fire 1" in mod
    assert any("bubblechukka" in u for u in unp)


# ===================== 攻击数 =====================
def test_rapid_fire_adds_at_half_range():
    w = weapon(const(2), 3, 4, 0, const(1), effects=kw("rapid fire 1"))
    t = tgt(4, 7, 1, 500)
    assert close(run(w, t, st(half=True)).attacks.mean(), 3)
    assert close(run(w, t, st(half=False)).attacks.mean(), 2)


def test_blast_scales_with_target_models():
    w = weapon(const(2), 3, 4, 0, const(1), effects=kw("blast"))
    assert close(run(w, tgt(4, 7, 1, 20), st()).attacks.mean(), 2 + 4)     # +floor(20/5)
    assert close(run(w, tgt(4, 7, 1, 12), st()).attacks.mean(), 2 + 2)     # +floor(12/5)


def test_rapid_fire_dice_value_not_collapsed_to_one():
    # 回归：rapid fire D3 曾被 _as_int 塌成常量 1；应按 D3 采样（半射程 +E[D3]=2）
    w = weapon(const(2), 3, 4, 0, const(1), effects=kw("rapid fire d3"))
    t = tgt(4, 7, 1, 500)
    assert close(run(w, t, st(half=True)).attacks.mean(), 2 + 2, rel=0.02)
    assert close(run(w, t, st(half=False)).attacks.mean(), 2)          # 远距无加成


def test_rapid_fire_d6plus3_full_bonus():
    # 回归：Rapid-fire battle cannon 'rapid fire d6+3'，曾只加 +1（低估 85%），应 +6.5
    w = weapon(const(2), 3, 4, 0, const(1), effects=kw("rapid fire d6+3"))
    assert close(run(w, tgt(4, 7, 1, 500), st(half=True)).attacks.mean(),
                 2 + 6.5, rel=0.02)


def test_rapid_fire_dice_label_readable():
    e, mod, ann = keyword_to_effects(tokenize_keywords('["rapid fire d6+3"]')[0][0])
    assert mod == ["rapid fire D6+3"]                                  # 非 'rapid fire None'


# ===================== 命中 =====================
def test_sustained_hits_adds_extra_on_crit():
    w = weapon(const(60), 2, 4, 0, const(1), effects=kw("sustained hits 2"))
    t = tgt(4, 7, 1, 800)
    hits = run(w, t, st()).hits.mean()
    assert close(hits, 60 * 5 / 6 + 60 * (1 / 6) * 2, rel=0.02)            # 50 + 20


def test_sustained_hits_dice_param():
    w = weapon(const(60), 2, 4, 0, const(1), effects=kw("sustained hits d3"))
    hits = run(w, tgt(4, 7, 1, 800), st()).hits.mean()
    assert close(hits, 50 + 60 * (1 / 6) * 2, rel=0.03)                    # E[d3]=2


def test_lethal_hits_auto_wounds_on_crit():
    # S4 vs T8 → 致伤需 6+；lethal 让暴击命中跳致伤直接成功
    w = weapon(const(60), 2, 4, 0, const(1), effects=kw("lethal hits"))
    t = tgt(8, 7, 1, 800)
    wounds = run(w, t, st()).wounds.mean()
    exp = 10 + 40 * (1 / 6)          # 暴击命中10自动致伤 + 非暴击40按6+致伤
    assert close(wounds, exp, rel=0.03)


def test_torrent_auto_hits():
    w = weapon(const(20), 4, 4, 0, const(1), effects=kw("torrent"))
    assert close(run(w, tgt(4, 7, 1, 500), st()).hits.mean(), 20)


def test_na_bs_auto_hits():
    w = weapon(const(20), None, 4, 0, const(1))       # bs_ws=N/A → None
    assert close(run(w, tgt(4, 7, 1, 500), st()).hits.mean(), 20)


def test_heavy_plus1_when_stationary():
    # 11版 24.16：数值不变（+1 命中）；stance.stationary 承载放宽后的 Heavy 条件
    # （未交战+本回合未上场+全员移动≤3"），字段名沿用十版
    w = weapon(const(60), 4, 4, 0, const(1), effects=kw("heavy"))
    t = tgt(4, 7, 1, 800)
    assert close(run(w, t, st(stationary=True)).hits.mean(), 60 * 4 / 6, rel=0.02)   # 3+
    assert close(run(w, t, st(stationary=False)).hits.mean(), 60 * 3 / 6, rel=0.02)  # 4+


def test_conversion_lowers_crit_hit_at_long_range():
    w = weapon(const(60), 5, 4, 0, const(1), effects=kw("conversion"))
    t = tgt(4, 7, 1, 800)
    assert close(run(w, t, st(long_range=True)).hits.mean(), 60 * 3 / 6, rel=0.02)   # 暴击4+→4+命中
    assert close(run(w, t, st(long_range=False)).hits.mean(), 60 * 2 / 6, rel=0.02)  # 仅5+


def test_indirect_fixed_6up_hit_and_grants_cover():
    # 11版 24.19+10.07：间接开火命中与 BS 无关——未修正仅 6 命中；目标获掩体（保留）
    w = weapon(const(60), 3, 8, 0, const(1), effects=kw("indirect fire"))
    t = tgt(4, 4, 1, 800)
    r_ind = run(w, t, st(indirect=True))
    r_dir = run(w, t, st(indirect=False))
    assert close(r_ind.hits.mean(), 60 * 1 / 6, rel=0.03)      # 6+，与 BS3+ 无关
    assert close(r_dir.hits.mean(), 60 * 4 / 6, rel=0.02)      # 直射按 BS 3+
    # 掩体：indirect 目标获掩体 → 过保率更低
    assert r_ind.unsaved.mean() / r_ind.wounds.mean() < r_dir.unsaved.mean() / r_dir.wounds.mean()


# ===================== 致伤 =====================
def test_anti_lowers_crit_wound_for_matching_keyword():
    w = weapon(const(60), 2, 4, 0, const(1), effects=kw("anti-vehicle 4+"))
    veh = tgt(10, 7, 1, 800, keywords=("vehicle",))
    inf = tgt(10, 7, 1, 800, keywords=("infantry",))
    # 对载具：致伤 = 暴击4+ ∪ 正常6+ = roll≥4 = 3/6
    assert close(run(w, veh, st()).wounds.mean(), 50 * 3 / 6, rel=0.02)
    # 对步兵：anti 不触发，仅正常 6+
    assert close(run(w, inf, st()).wounds.mean(), 50 * (1 / 6), rel=0.03)


def test_twin_linked_rerolls_failed_wounds():
    w = weapon(const(60), 2, 4, 0, const(1), effects=kw("twin-linked"))
    t = tgt(8, 7, 1, 800)      # 致伤 6+，P=1/6
    wounds = run(w, t, st()).wounds.mean()
    assert close(wounds, 50 * (1 - (5 / 6) ** 2), rel=0.03)   # 11/36


def test_lance_plus1_wound_on_charge():
    w = weapon(const(60), 3, 4, 0, const(1), effects=kw("lance"), melee=True)
    t = tgt(5, 7, 1, 800)      # S4 vs T5 → 致伤 5+
    hits = 60 * 4 / 6
    assert close(run(w, t, st(phase="melee", charging=True)).wounds.mean(),
                 hits * 3 / 6, rel=0.03)                        # +1 → 4+
    assert close(run(w, t, st(phase="melee", charging=False)).wounds.mean(),
                 hits * 2 / 6, rel=0.03)                        # 5+


# ===================== 伤害 =====================
def test_melta_adds_damage_at_half_range():
    # 单巨兽 W50 不团灭，量有效伤害 = E[未过保] × D
    w = weapon(const(4), 2, 10, 0, const(1), effects=kw("melta 2"))
    t = tgt(4, 7, 50, 1)       # wt2, sv7
    exp_unsaved = 4 * (5 / 6) * (5 / 6)
    assert close(run(w, t, st(half=False)).damage.mean(), exp_unsaved * 1, rel=0.03)
    assert close(run(w, t, st(half=True)).damage.mean(), exp_unsaved * 3, rel=0.03)


# ===================== 保存 =====================
def test_ignores_cover_denies_cover_benefit():
    plain = weapon(const(60), 2, 8, 0, const(1))
    ignore = weapon(const(60), 2, 8, 0, const(1), effects=kw("ignores cover"))
    t = tgt(4, 4, 1, 800)      # Sv4+
    r_plain = run(plain, t, st(cover=True))    # 掩体 → 3+
    r_ignore = run(ignore, t, st(cover=True))  # 无视掩体 → 4+
    assert r_ignore.unsaved.mean() > r_plain.unsaved.mean() * 1.2


# ===================== 关键组合 =====================
def test_lethal_plus_dev_lethal_does_not_trigger_dev():
    # lethal 暴击命中 → 自动致伤（走保存、非致命池）；dev 只作用于真正的暴击致伤
    w = weapon(const(60), 2, 10, 0, const(1),
               effects=kw("lethal hits, devastating wounds"))
    t = tgt(4, 2, 1, 800)      # S10 vs T4 → 致伤2+；Sv2+
    r = run(w, t, st())
    # 致命池只来自非暴击命中(40)里的暴击致伤(roll6)=40/6≈6.67；lethal 的 10 不进池
    assert close(r.mortals.mean(), 40 * (1 / 6), rel=0.04)


def test_anti_plus_dev_crit_wounds_become_mortals():
    w = weapon(const(60), 2, 4, 0, const(1),
               effects=kw("anti-vehicle 4+, devastating wounds"))
    veh = tgt(10, 2, 1, 800, keywords=("vehicle",), invuln=2)   # 2++ 也挡不住致命池
    r = run(w, veh, st())
    # anti 把暴击致伤阈值降到 4+ → 命中里 roll≥4 全成致命池 = 50×3/6 = 25
    assert close(r.mortals.mean(), 50 * 3 / 6, rel=0.02)
