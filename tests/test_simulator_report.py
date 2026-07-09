"""P4-d 报告层 + 编排单测：聚合正确性、诚实清单、串行幸存反打。"""
from __future__ import annotations

import numpy as np

from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Effect,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.context import STANDARD_BIAS
from engines.simulator.engine import simulate, simulate_matchup
from engines.simulator.parse import tokenize_keywords
from engines.simulator.keywords import build_weapon_effects


def const(k):
    return DiceExpr(n=0, faces=0, k=k)


def kw(s):
    parsed, _ = tokenize_keywords('["' + s + '"]')
    eff, _m, _a, _u = build_weapon_effects(tuple(parsed))
    return eff, parsed


def weapon(a, bs, s, ap, d, s_kw="", melee=False, count=1):
    eff, parsed = kw(s_kw) if s_kw else ((), ())
    return WeaponProfile(name_zh=None, name_en="W", range="Melee" if melee else "24",
                         attacks=a, bs_ws=bs, strength=s, ap=ap, damage=d,
                         effects=tuple(eff), raw_keywords=tuple(parsed), count=count)


def attacker(w, models=1):
    return AttackerProfile(canonical_id="A", name_en="A", name_zh=None,
                           models=models, loadout=(w,), keywords=frozenset())


def target(t, sv, w, models, invuln=None, rows=()):
    return TargetProfile(canonical_id="T", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=w, oc=1,
                         keywords=frozenset(), model_rows=rows)


def test_report_aggregates_and_distribution():
    w = weapon(const(20), 3, 5, -1, const(2))
    rep = simulate(attacker(w), target(4, 4, 2, 40), Stance(), n=50000, seed=1, points=100)
    assert rep.iterations == 50000
    assert rep.expected_damage > 0 and rep.expected_kills > 0
    # 直方图是概率、和≈1
    assert abs(sum(rep.distribution["histogram"].values()) - 1.0) < 1e-6
    assert rep.distribution["p10"] <= rep.distribution["p50"] <= rep.distribution["p90"]
    # 漏斗单调递减：攻击≥命中≥致伤≥未过保
    f = rep.funnel
    assert f["attacks"] >= f["hits"] >= f["wounds"] >= f["unsaved"]
    # 性价比 = 伤害/点数×100
    assert abs(rep.efficiency["damage_per_100"] - rep.expected_damage / 100 * 100) < 0.01


def test_report_honest_declarations():
    # precision（标注类）应进 not_modeled；rapid fire 进 modeled_effects
    w = weapon(const(10), 3, 5, -1, const(1), s_kw="rapid fire 1, precision")
    rep = simulate(attacker(w), target(4, 4, 1, 20), Stance(half_range=True), n=20000, seed=2)
    assert any("rapid fire" in m for m in rep.modeled_effects)
    assert any("precision" in nm for nm in rep.not_modeled)
    assert "abilities" in " ".join(rep.not_modeled).lower() or any(
        "abilities" in nm.lower() for nm in rep.not_modeled)
    # 标准偏差声明必须真实存在（禁止空列表糊弄）
    assert len(rep.bias_notes) >= len(STANDARD_BIAS)


def test_not_modeled_flags_mixed_unit():
    rows = ({"name": "boy", "t": 5, "sv": 6, "w": 1},
            {"name": "nob", "t": 5, "sv": 6, "w": 2})
    w = weapon(const(10), 3, 5, 0, const(1))
    rep = simulate(attacker(w), target(5, 6, 1, 10, rows=rows), Stance(), n=10000, seed=3)
    assert any("混编" in nm for nm in rep.not_modeled)


def test_matchup_attaches_survivor_reverse():
    # A：强火力射击队；B：多模型近战队。A→B 打掉一部分，B 幸存者反打 A
    a_gun = weapon(const(40), 3, 5, -1, const(1))
    a_atk = attacker(a_gun, models=10)
    a_as_target = target(4, 3, 2, 10)          # A 自身作靶

    b_fist = weapon(const(3), 3, 8, -2, const(2), melee=True, count=20)
    b_atk = AttackerProfile(canonical_id="B", name_en="B", name_zh=None,
                            models=20, loadout=(b_fist,), keywords=frozenset())
    b_as_target = target(4, 6, 1, 20)          # B 作靶（20 模型 W1）

    rep = simulate_matchup(
        a_atk, b_as_target, b_atk, a_as_target,
        stance_forward=Stance(phase="shooting"),
        stance_reverse=Stance(phase="melee"),
        n=20000, seed=5, points_a=150, points_b=180)

    assert rep.expected_kills > 0
    assert rep.reverse is not None                      # B 有幸存者 → 反打存在
    assert rep.reverse.expected_damage >= 0
    assert any("反打基于 B 期望幸存" in b for b in rep.bias_notes)


def test_matchup_no_reverse_when_wiped():
    # A 火力碾压把 B（少量脆皮）打光 → 无幸存者反打
    a_gun = weapon(const(60), 2, 10, -3, const(3))
    a_atk = attacker(a_gun, models=10)
    b_as_target = target(3, 6, 1, 3)                    # 3 个 W1 脆皮
    b_fist = weapon(const(2), 4, 4, 0, const(1), melee=True, count=3)
    b_atk = AttackerProfile(canonical_id="B", name_en="B", name_zh=None,
                            models=3, loadout=(b_fist,), keywords=frozenset())
    rep = simulate_matchup(a_atk, b_as_target, b_atk, target(4, 3, 2, 10),
                           Stance(phase="shooting"), Stance(phase="melee"),
                           n=20000, seed=6)
    assert rep.wipe_probability > 0.9
    assert rep.reverse is None                          # 团灭 → 反打为空
