"""P4-b 裸攻击序列黄金用例：S-T 查表 / 保存修正 / dev 致命池 / 掩体（11版BS惩罚）/ FNP。

策略：用**可解析期望**的合成 profile，把 hit/wound/save 三阶段的漏斗均值与解析概率
对拍（容差 <1%），再对规则订正项（dev 跳 invuln、11版掩体=恶化攻方 BS 而非护甲+1、FNP 对
致命池生效、不溢出）做定向断言。分配核本身已由 _spike_allocation 精确对拍过。
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
from engines.simulator.sequence import (
    effective_save,
    run_sequence,
    wound_target,
)

N = 100_000
SEED = 20260709


# ---------- 构造器 ----------
def const(k: int) -> DiceExpr:
    return DiceExpr(n=0, faces=0, k=k)


def d6() -> DiceExpr:
    return DiceExpr(n=1, faces=6, k=0)


def weapon(attacks, bs_ws, strength, ap, damage, effects=(), melee=False, count=1):
    return WeaponProfile(
        name_zh=None, name_en="W", range="Melee" if melee else "24",
        attacks=attacks, bs_ws=bs_ws, strength=strength, ap=ap,
        damage=damage, effects=tuple(effects), count=count)


def attacker(w):
    return AttackerProfile(canonical_id="A", name_en="A", name_zh=None,
                           models=1, loadout=(w,), keywords=frozenset())


def target(t, sv, w, models, invuln=None, effects=()):
    return TargetProfile(canonical_id="T", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=w, oc=1,
                         keywords=frozenset(), effects=tuple(effects))


def stance(phase="shooting", cover=False, charging=False, half=False):
    return Stance(phase=phase, charging=charging, stationary=False,
                  half_range=half, target_in_cover=cover)


# ---------- 解析概率 ----------
def p_hit(bs):
    return 1.0 if bs is None else (7 - bs) / 6.0


def p_wound(wt):
    return (7 - wt) / 6.0


def p_fail_save(need):
    return 1.0 - ((7 - need) / 6.0 if need <= 6 else 0.0)


def close(got, exp, rel=0.01, absol=0.02):
    return abs(got - exp) <= max(absol, abs(exp) * rel)


# ---------- S-T 查表五档边界 ----------
def test_wound_target_boundaries_exact():
    assert wound_target(8, 4) == 2
    assert wound_target(9, 4) == 2
    assert wound_target(5, 4) == 3
    assert wound_target(4, 4) == 4
    assert wound_target(3, 4) == 5
    assert wound_target(2, 4) == 6      # 2S=4=T → 2S≤T → 6
    assert wound_target(2, 5) == 6


# ---------- 保存修正（11版：effective_save 只管 AP+invuln，掩体已移出保存侧）----------
def test_effective_save_ap_worsens():
    assert effective_save(3, 0, None) == 3
    assert effective_save(3, -1, None) == 4
    assert effective_save(2, -3, None) == 5


def test_effective_save_invuln_caps():
    # 6+ 甲被 AP-2 打成 8+（救不到），invuln 4++ 兜底
    assert effective_save(6, -2, 4) == 4


def test_effective_save_double_comparison_takes_favorable():
    # 11版 05.04：单次保存骰同时对照 InSv 与 AP 后 Sv，取更优（数学=取更小阈值）
    assert effective_save(2, 0, 4) == 2        # 护甲 2+ 优于 invuln 4+ → 2+
    assert effective_save(6, -2, 4) == 4        # 护甲 8+ 救不到，invuln 4+ 接管 → 4+
    assert effective_save(3, -1, 5) == 4        # 护甲 4+ 优于 invuln 5+ → 4+


# ---------- 漏斗均值 vs 解析期望（<1%）----------
def test_funnel_matches_analytic_shooting():
    # 20 发、BS3+、S4 vs T4(wt4)、Sv5+ AP0、D1、W1、100 模型（不团灭）
    w = weapon(const(20), bs_ws=3, strength=4, ap=0, damage=const(1))
    tgt = target(t=4, sv=5, w=1, models=100)
    raw = run_sequence(attacker(w), tgt, stance(), n=N, seed=SEED)

    exp_hits = 20 * p_hit(3)
    exp_wounds = exp_hits * p_wound(wound_target(4, 4))
    exp_unsaved = exp_wounds * p_fail_save(5)
    assert close(raw.attacks.mean(), 20)
    assert close(raw.hits.mean(), exp_hits), (raw.hits.mean(), exp_hits)
    assert close(raw.wounds.mean(), exp_wounds), (raw.wounds.mean(), exp_wounds)
    assert close(raw.unsaved.mean(), exp_unsaved), (raw.unsaved.mean(), exp_unsaved)
    # D1/W1 无溢出：有效伤害 = 击杀 = unsaved
    assert close(raw.damage.mean(), exp_unsaved)
    assert close(raw.kills.mean(), exp_unsaved)


def test_variable_attacks_and_damage_expected():
    # A=D6（期望3.5）、BS2+、S8 vs T4(wt2)、Sv6+ AP-1(→7+ 救不到)、D=D6、W3、20 模型
    w = weapon(d6(), bs_ws=2, strength=8, ap=-1, damage=d6())
    tgt = target(t=4, sv=6, w=3, models=20)
    raw = run_sequence(attacker(w), tgt, stance(), n=N, seed=SEED)
    exp_attacks = 3.5
    exp_hits = exp_attacks * p_hit(2)
    exp_wounds = exp_hits * p_wound(2)
    exp_unsaved = exp_wounds * p_fail_save(7)     # 7+ → 必不过保
    assert close(raw.attacks.mean(), exp_attacks)
    assert close(raw.hits.mean(), exp_hits)
    assert close(raw.unsaved.mean(), exp_unsaved, rel=0.02)


# ---------- dev 致命池：暴击造伤跳 invuln ----------
def test_dev_wounds_crit_bypasses_invuln():
    dev = [Effect(phase="wound", op="mortal_pool", source="devastating wounds")]
    # 60 发、BS2+、S10 vs T4(wt2)、目标 2++ invuln、Sv6、D1、W1、200 模型
    w = weapon(const(60), bs_ws=2, strength=10, ap=0, damage=const(1), effects=dev)
    tgt = target(t=4, sv=6, w=1, models=200, invuln=2)
    raw = run_sequence(attacker(w), tgt, stance(), n=N, seed=SEED)

    exp_hits = 60 * p_hit(2)
    exp_mortals = exp_hits * (1 / 6)              # 暴击造伤 = 命中里自然 6 致伤
    assert close(raw.mortals.mean(), exp_mortals, rel=0.02), (raw.mortals.mean(), exp_mortals)
    # 致命池全穿 2++（否则会被 invuln 挡掉）：mortals 都进了有效伤害
    # 对照无 dev：暴击造伤改走 2++ 保存，总伤害显著更低
    w_nodev = weapon(const(60), bs_ws=2, strength=10, ap=0, damage=const(1))
    raw2 = run_sequence(attacker(w_nodev), tgt, stance(), n=N, seed=SEED)
    assert raw.damage.mean() > raw2.damage.mean() * 1.3


def test_dev_non_spillover_caps_at_models():
    # dev、D=D6、W1、只有 5 个模型：每份致命最多杀 1，团灭后封顶
    dev = [Effect(phase="wound", op="mortal_pool", source="devastating wounds")]
    w = weapon(const(40), bs_ws=2, strength=10, ap=0, damage=d6(), effects=dev)
    tgt = target(t=4, sv=7, w=1, models=5, invuln=None)
    raw = run_sequence(attacker(w), tgt, stance(), n=N, seed=SEED)
    assert raw.kills.max() <= 5                    # 绝不超出模型数
    assert raw.wiped.mean() > 0.9                   # 火力过剩几乎必团灭


# ---------- FNP 对致命池同样逐点生效 ----------
def test_fnp_reduces_mortal_damage():
    dev = [Effect(phase="wound", op="mortal_pool", source="devastating wounds")]
    fnp5 = [Effect(phase="fnp", op="fnp", params=(5,), source="feel no pain 5+")]
    w = weapon(const(60), bs_ws=2, strength=10, ap=-4, damage=const(1), effects=dev)
    tgt_no = target(t=4, sv=6, w=1, models=300)
    tgt_fnp = target(t=4, sv=6, w=1, models=300, effects=fnp5)
    raw_no = run_sequence(attacker(w), tgt_no, stance(), n=N, seed=SEED)
    raw_fnp = run_sequence(attacker(w), tgt_fnp, stance(), n=N, seed=SEED)
    # FNP5+ 免掉约 1/3 伤害（含致命池）
    ratio = raw_fnp.damage.mean() / raw_no.damage.mean()
    assert close(ratio, 2 / 3, rel=0.03), ratio


# ---------- 掩体在完整序列里的效果（11版 13.08：恶化攻方 BS 1，射击专属）----------
def test_cover_worsens_hit_not_save_in_sequence():
    # BS2+ 攻方，目标进掩体 → BS3+：命中 5/6→4/6（降 20%）。掩体不再碰保存骰，
    # 因此每发命中的过保失败率不变，unsaved 与 hits 同比例下降（≈0.8）。
    w = weapon(const(60), bs_ws=2, strength=8, ap=0, damage=const(1))
    tgt = target(t=4, sv=5, w=1, models=300)
    raw_open = run_sequence(attacker(w), tgt, stance(cover=False), n=N, seed=SEED)
    raw_cover = run_sequence(attacker(w), tgt, stance(cover=True), n=N, seed=SEED)
    assert close(raw_cover.hits.mean(), raw_open.hits.mean() * 4 / 5, rel=0.02)
    # 每发命中的过保失败率不变（掩体不作用于保存）：unsaved/hits 两态一致
    assert close(raw_cover.unsaved.mean() / raw_cover.hits.mean(),
                 raw_open.unsaved.mean() / raw_open.hits.mean(), rel=0.02)


def test_cover_benefit_applies_regardless_of_sv_ap_in_sequence():
    # 11版取消十版"Sv3+ 对 AP0 不享受掩体"例外：Sv3+ AP0 目标进掩体同样受益，
    # 命中随 BS 惩罚下降（十版此处 unsaved 与无掩体一致，现应显著下降）。
    w = weapon(const(60), bs_ws=2, strength=8, ap=0, damage=const(1))
    tgt = target(t=4, sv=3, w=1, models=300)
    raw_open = run_sequence(attacker(w), tgt, stance(cover=False), n=N, seed=SEED)
    raw_cover = run_sequence(attacker(w), tgt, stance(cover=True), n=N, seed=SEED)
    assert close(raw_cover.hits.mean(), raw_open.hits.mean() * 4 / 5, rel=0.02)
    assert raw_cover.unsaved.mean() < raw_open.unsaved.mean() * 0.85


def test_cover_not_applied_in_melee():
    # 掩体只对远程攻击生效（13.08）：近战下 cover 开关不改变命中
    w = weapon(const(60), bs_ws=2, strength=8, ap=0, damage=const(1), melee=True)
    tgt = target(t=4, sv=5, w=1, models=300)
    raw_open = run_sequence(attacker(w), tgt,
                            stance(phase="melee", cover=False), n=N, seed=SEED)
    raw_cover = run_sequence(attacker(w), tgt,
                             stance(phase="melee", cover=True), n=N, seed=SEED)
    assert close(raw_cover.hits.mean(), raw_open.hits.mean(), rel=0.02)


# ---------- 退化输入不静默夹取（审查发现的两个 HIGH/LOW） ----------
def test_count_zero_weapon_does_not_fire():
    # 回归：count=0（0 模型持此武器）曾被 max(count,1) 夹成 1 而幽灵开火
    w = weapon(const(5), 2, 8, -2, const(2), count=0)
    raw = run_sequence(attacker(w), target(4, 4, 2, 10), stance(), n=5000, seed=1)
    assert raw.attacks.mean() == 0
    assert raw.damage.mean() == 0 and raw.kills.mean() == 0


def test_degenerate_target_zero_models_zero_kills():
    # 回归：models=0 曾被 max(models,1) 夹成打一个幽灵模型
    w = weapon(const(20), 2, 8, -2, const(2))
    raw = run_sequence(attacker(w), target(4, 4, 1, 0), stance(), n=2000, seed=1)
    assert raw.kills.mean() == 0 and raw.damage.mean() == 0 and raw.wiped.mean() == 0


# ---------- 近战 phase 过滤 ----------
def test_melee_phase_selects_melee_weapon():
    gun = weapon(const(10), bs_ws=3, strength=4, ap=0, damage=const(1), melee=False)
    fist = weapon(const(10), bs_ws=3, strength=8, ap=-2, damage=const(2), melee=True)
    atk = AttackerProfile(canonical_id="A", name_en="A", name_zh=None,
                          models=1, loadout=(gun, fist), keywords=frozenset())
    tgt = target(t=4, sv=4, w=2, models=50)
    raw_shoot = run_sequence(atk, tgt, stance(phase="shooting"), n=N, seed=SEED)
    raw_melee = run_sequence(atk, tgt, stance(phase="melee"), n=N, seed=SEED)
    # 射击只用 gun（S4 D1），近战只用 fist（S8 AP-2 D2）
    assert close(raw_shoot.attacks.mean(), 10)
    assert close(raw_melee.attacks.mean(), 10)
    assert raw_melee.damage.mean() > raw_shoot.damage.mean()   # 拳头更狠
