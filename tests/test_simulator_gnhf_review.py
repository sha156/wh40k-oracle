# tests/test_simulator_gnhf_review.py
"""2026-07-20 GNHF 全库审查·模块1（engines/simulator）两处 HIGH 修复的成对回归。

HIGH-1：(hit, extra_hits) 多来源单值 last-write——DSL 授予 [SUSTAINED HITS 1] 会把
        武器自带 [SUSTAINED HITS 2] 降级；修复=同能力多实例按期望值取更优。
HIGH-2：(damage, modify) 多来源单值 last-write——melta X 与 DSL "+1 Damage" 互相
        覆盖（19 条 payload 条目走此通道）；修复=与 rf_exprs 同语义累加。
蒙特卡洛比率断言沿用 test_simulator_dsl_pr5_engine 范式，手算期望值写在断言旁。

模块 2（dsl_payloads 对照引擎语义）两处 HIGH 修复的成对回归（TestModule2PhaseGates）：
M2-HIGH-1：AoI DISPLACER FIELD（WHEN=对手射击阶段、持续至阶段末）漏 phase_shooting 门
           ——近战模拟也会拿到 4+ 无效保护（过度施加）；修复=补 phase_shooting。
M2-HIGH-2：WE DAEMONIC STRENGTH（WHEN=战斗阶段、持续至阶段末）用裸 target_has_keyword
           ——射击模拟对凶兽/载具也 D+1（过度施加，与 PR10-PR14 四次同型 HIGH 同类）；
           修复=改 melee_target_has_keyword 复合门。
"""
from pathlib import Path

import pytest

from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Effect,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.dsl import inject_attacker, inject_target, load_payload_file
from engines.simulator.effect_params import _gather_params
from engines.simulator.sequence import run_sequence

N = 60000
_SHOOT = Stance(phase="shooting")
_SHOOT_HALF = Stance(phase="shooting", half_range=True)


def _gun(effects=(), damage=DiceExpr(k=1)):
    return WeaponProfile(name_zh=None, name_en="test gun", range='24"',
                         attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                         damage=damage, effects=tuple(effects), count=1)


def _attacker(w):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=(w,))


def _target(t=4, sv=7, models=1, w=200):
    # 大 W 单模型：damage/unsaved 即每次未过保攻击的平均落伤（无溢出干扰）
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=None, w=w, oc=1)


def _sustained(x, source):
    return Effect("hit", "extra_hits", (DiceExpr(k=x),), (), source)


class TestSustainedBestOf:
    """HIGH-1：sustained 多来源取更优，不被后写入的低值降级。"""

    def test_dsl_lower_grant_does_not_downgrade(self):
        # 武器自带连击2，DSL 后注入连击1 → 应保留 2
        w = _gun(effects=[_sustained(2, "sustained hits 2"),
                          _sustained(1, "dsl grant 1")])
        p = _gather_params(w, _SHOOT, _target())
        assert p.sustained == DiceExpr(k=2)

    def test_dsl_higher_grant_wins_either_order(self):
        # 更优值在前/在后都胜出
        w1 = _gun(effects=[_sustained(1, "a"), _sustained(2, "b")])
        w2 = _gun(effects=[_sustained(2, "b"), _sustained(1, "a")])
        t = _target()
        assert _gather_params(w1, _SHOOT, t).sustained == DiceExpr(k=2)
        assert _gather_params(w2, _SHOOT, t).sustained == DiceExpr(k=2)

    def test_single_source_unchanged(self):
        # 负向：单来源行为不变
        w = _gun(effects=[_sustained(1, "sustained hits 1")])
        p = _gather_params(w, _SHOOT, _target())
        assert p.sustained == DiceExpr(k=1)

    def test_monte_carlo_ratio_keeps_better_value(self):
        # BS4+ 命中 1/2；连击2 暴击 1/6 每次 +2 命中 → hits/attacks = 1/2 + 2/6
        w = _gun(effects=[_sustained(2, "sustained hits 2"),
                          _sustained(1, "dsl grant 1")])
        r = run_sequence(_attacker(w), _target(), _SHOOT, n=N, seed=42)
        assert r.hits.mean() / r.attacks.mean() == pytest.approx(
            1 / 2 + 2 / 6, abs=0.02)


class TestDamageModStacking:
    """HIGH-2：melta 与 DSL "+1 Damage" 等 (damage, modify) 多来源累加。"""

    def test_both_sources_collected_in_half_range(self):
        w = _gun(effects=[
            Effect("damage", "modify", (DiceExpr(k=3),), ("half_range",), "melta 3"),
            Effect("damage", "modify", (DiceExpr(k=1),), (), "dsl +1 damage")])
        p = _gather_params(w, _SHOOT_HALF, _target())
        assert p.dmg_mod_exprs == (DiceExpr(k=3), DiceExpr(k=1))

    def test_melta_gated_out_beyond_half_range(self):
        # 负向：半射程外 melta 不进桶，只剩 DSL +1
        w = _gun(effects=[
            Effect("damage", "modify", (DiceExpr(k=3),), ("half_range",), "melta 3"),
            Effect("damage", "modify", (DiceExpr(k=1),), (), "dsl +1 damage")])
        p = _gather_params(w, _SHOOT, _target())
        assert p.dmg_mod_exprs == (DiceExpr(k=1),)

    def test_monte_carlo_damage_per_unsaved_stacks(self):
        # D1 + melta3 + DSL+1 = 每未过保攻击落伤 5（大 W 单模型无溢出）
        w = _gun(effects=[
            Effect("damage", "modify", (DiceExpr(k=3),), ("half_range",), "melta 3"),
            Effect("damage", "modify", (DiceExpr(k=1),), (), "dsl +1 damage")])
        r = run_sequence(_attacker(w), _target(), _SHOOT_HALF, n=N, seed=42)
        assert r.unsaved.sum() > 0
        assert r.damage.sum() / r.unsaved.sum() == pytest.approx(5.0, abs=0.01)

    def test_monte_carlo_single_melta_unchanged(self):
        # 负向：单 melta 行为不变——D1 + melta3 = 每未过保落伤 4
        w = _gun(effects=[
            Effect("damage", "modify", (DiceExpr(k=3),), ("half_range",), "melta 3")])
        r = run_sequence(_attacker(w), _target(), _SHOOT_HALF, n=N, seed=42)
        assert r.unsaved.sum() > 0
        assert r.damage.sum() / r.unsaved.sum() == pytest.approx(4.0, abs=0.01)


# ═══ 模块 2：payload 相位门修复的成对回归（真载荷条目直载） ═══════════════
_MELEE = Stance(phase="melee")


def _entry_by_id(path, row_id):
    for e in load_payload_file(Path(path)):
        if e.row_id == row_id:
            return e
    raise AssertionError(f"{path} 中找不到条目 {row_id}")


def _keyword_target(kw=(), sv=7, t=4):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=1, t=t, sv=sv, invuln=None, w=200, oc=1,
                         keywords=frozenset(kw))


def _sword(effects=()):
    return WeaponProfile(name_zh=None, name_en="test sword", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


class TestModule2PhaseGates:
    """M2-HIGH-1/M2-HIGH-2：射击/近战相位门修复后，正向照常生效、错相位不再施加。"""

    def test_displacer_field_applies_in_shooting(self):
        # 正向：射击相位 4+ invuln 生效——sv=7 无甲，未保存/致伤 ≈ 1/2
        df = _entry_by_id("dsl_payloads/imperialagents.json", "000009139006")
        tgt, _, _ = inject_target(_keyword_target(), [df], frozenset())
        r = run_sequence(_attacker(_gun()), tgt, _SHOOT, n=N, seed=42)
        assert r.unsaved.sum() / r.wounds.sum() == pytest.approx(1 / 2, abs=0.03)

    def test_displacer_field_not_applied_in_melee(self):
        # 负向（修复点）：WHEN=对手射击阶段——近战模拟不得再拿 4+ invuln，
        # sv=7 无甲无保护，未保存/致伤 ≈ 1
        df = _entry_by_id("dsl_payloads/imperialagents.json", "000009139006")
        tgt, _, _ = inject_target(_keyword_target(), [df], frozenset())
        r = run_sequence(_attacker(_sword()), tgt, _MELEE, n=N, seed=42)
        assert r.wounds.sum() > 0
        assert r.unsaved.sum() / r.wounds.sum() == pytest.approx(1.0, abs=0.02)

    def test_daemonic_strength_melee_vs_monster_plus1(self):
        # 正向：近战对 MONSTER 目标 D1+1=2（每未过保落伤 ≈ 2，大 W 无溢出）
        ds = _entry_by_id("dsl_payloads/worldeaters.json", "000010083003")
        atk, _, _ = inject_attacker(_attacker(_sword()), [ds], frozenset())
        r = run_sequence(atk, _keyword_target(kw=("monster",)), _MELEE, n=N, seed=42)
        assert r.unsaved.sum() > 0
        assert r.damage.sum() / r.unsaved.sum() == pytest.approx(2.0, abs=0.01)

    def test_daemonic_strength_not_applied_in_shooting(self):
        # 负向（修复点）：WHEN=战斗阶段——射击模拟对 MONSTER 不得再 D+1
        ds = _entry_by_id("dsl_payloads/worldeaters.json", "000010083003")
        atk, _, _ = inject_attacker(_attacker(_gun()), [ds], frozenset())
        r = run_sequence(atk, _keyword_target(kw=("monster",)), _SHOOT, n=N, seed=42)
        assert r.unsaved.sum() > 0
        assert r.damage.sum() / r.unsaved.sum() == pytest.approx(1.0, abs=0.01)

    def test_daemonic_strength_melee_vs_non_monster_unchanged(self):
        # 负向：近战对非凶兽/载具目标不加伤（神尊八缚分支关键词门）
        ds = _entry_by_id("dsl_payloads/worldeaters.json", "000010083003")
        atk, _, _ = inject_attacker(_attacker(_sword()), [ds], frozenset())
        r = run_sequence(atk, _keyword_target(kw=("infantry",)), _MELEE, n=N, seed=42)
        assert r.unsaved.sum() > 0
        assert r.damage.sum() / r.unsaved.sum() == pytest.approx(1.0, abs=0.01)


class TestModule2StealthChannel:
    """M2-HIGH-3（家族修复）：授予 Stealth 的条目按十版语义编成 hit-1，而 11 版
    STEALTH 24.33 的全部效果=授予掩体收益 13.08（BS 恶化 1 的二元状态）。
    错通道的三个可观测差异：①与地形掩体开关叠加成双重惩罚（应去重）；
    ②不被 [IGNORES COVER]（24.18 点名含 Stealth）抵消；③BLIND SCREEN 同条目
    hit-1+cover 双编=基线即双重计费。修复=统一改单份 (save, cover)。"""

    def test_blind_screen_single_cover_penalty(self):
        # 正向（双编修复点）：BS4+ 只掉一档 → hits/attacks ≈ 1/3（修复前 hit-1+cover ≈ 1/6）
        bs = _entry_by_id("dsl_payloads/spacemarines.json", "000010681006")
        tgt, _, _ = inject_target(_keyword_target(), [bs], frozenset())
        r = run_sequence(_attacker(_gun()), tgt, _SHOOT, n=N, seed=42)
        assert r.hits.sum() / r.attacks.sum() == pytest.approx(1 / 3, abs=0.02)

    def test_blind_screen_negated_by_ignores_cover(self):
        # 负向：[IGNORES COVER]（24.18 点名含 Stealth）整体抵消 → 无惩罚 ≈ 1/2
        bs = _entry_by_id("dsl_payloads/spacemarines.json", "000010681006")
        tgt, _, _ = inject_target(_keyword_target(), [bs], frozenset())
        gun = _gun(effects=[Effect("save", "ignores_cover", (), (), "ignores cover")])
        r = run_sequence(_attacker(gun), tgt, _SHOOT, n=N, seed=42)
        assert r.hits.sum() / r.attacks.sum() == pytest.approx(1 / 2, abs=0.02)

    def test_dispersed_formation_dedupes_with_terrain_cover(self):
        # 正向（二元去重修复点）：地形掩体开关已开时再上分散阵型不叠加 → ≈ 1/3
        # （修复前 hit-1 与掩体 BS 惩罚双算 ≈ 1/6）
        df = _entry_by_id("dsl_payloads/votann.json", "000010440007")
        tgt, _, _ = inject_target(_keyword_target(), [df], frozenset())
        r = run_sequence(_attacker(_gun()), tgt,
                         Stance(phase="shooting", target_in_cover=True), n=N, seed=42)
        assert r.hits.sum() / r.attacks.sum() == pytest.approx(1 / 3, abs=0.02)

    def test_dispersed_formation_negated_by_ignores_cover(self):
        # 负向：修复前 hit_mod -1 不吃 24.18 抵消（≈1/3），修复后整体抵消 ≈ 1/2
        df = _entry_by_id("dsl_payloads/votann.json", "000010440007")
        tgt, _, _ = inject_target(_keyword_target(), [df], frozenset())
        gun = _gun(effects=[Effect("save", "ignores_cover", (), (), "ignores cover")])
        r = run_sequence(_attacker(gun), tgt, _SHOOT, n=N, seed=42)
        assert r.hits.sum() / r.attacks.sum() == pytest.approx(1 / 2, abs=0.02)

    def test_wings_of_shadow_cover_penalty_and_negation(self):
        # DA 家族成员成对：无抵消掉一档 ≈ 1/3；[IGNORES COVER] 抵消 ≈ 1/2
        ws = _entry_by_id("dsl_payloads/darkangels.json", "fp11e-da-darkflight-s2")
        tgt, _, _ = inject_target(_keyword_target(), [ws], frozenset())
        r = run_sequence(_attacker(_gun()), tgt, _SHOOT, n=N, seed=42)
        assert r.hits.sum() / r.attacks.sum() == pytest.approx(1 / 3, abs=0.02)
        gun = _gun(effects=[Effect("save", "ignores_cover", (), (), "ignores cover")])
        r2 = run_sequence(_attacker(gun), tgt, _SHOOT, n=N, seed=42)
        assert r2.hits.sum() / r2.attacks.sum() == pytest.approx(1 / 2, abs=0.02)

    def test_umbral_raptor_toggle_gated_cover(self):
        # SM 增强（requires defender_bearer_leading）成对：开关点亮 ≈ 1/3 / 未点亮不注入 ≈ 1/2
        # （Shroud Field 同文件同形，家族口径由本条覆盖）
        ur = _entry_by_id("dsl_payloads/spacemarines.json", "000010466004")
        tgt_on, _, _ = inject_target(_keyword_target(), [ur],
                                     frozenset({"defender_bearer_leading"}))
        r_on = run_sequence(_attacker(_gun()), tgt_on, _SHOOT, n=N, seed=42)
        assert r_on.hits.sum() / r_on.attacks.sum() == pytest.approx(1 / 3, abs=0.02)
        tgt_off, _, _ = inject_target(_keyword_target(), [ur], frozenset())
        r_off = run_sequence(_attacker(_gun()), tgt_off, _SHOOT, n=N, seed=42)
        assert r_off.hits.sum() / r_off.attacks.sum() == pytest.approx(1 / 2, abs=0.02)
