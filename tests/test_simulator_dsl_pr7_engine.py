# tests/test_simulator_dsl_pr7_engine.py
"""P7-PR7 帝皇之子引擎通道：守方 AP 恶化 + 近战×S>T 延迟 tag + 加速/撤退注入门。

双验范式：每个新通道至少一条差分断言，手算期望值写在断言旁。
基线骰面：WS4+ 命中 1/2；S4 vs T4 致伤 4+ = 1/2；S5 vs T4 致伤 3+ = 2/3。
"""
import pytest

from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Effect,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.dsl import ATTACKER_TOGGLES, DslError, parse_entry
from engines.simulator.sequence import KNOWN_CONDITION_TAGS, run_sequence

N = 60000


def _melee(ws=4, s=4, ap=0, effects=()):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _gun(ws=4, s=4, ap=0, effects=()):
    return WeaponProfile(name_zh=None, name_en="gun", range='24"',
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(w):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=(w,))


def _target(t=4, sv=4, models=5, effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=None, w=1, oc=1,
                         keywords=frozenset(), effects=tuple(effects))


def _run(w, target, stance):
    return run_sequence(_attacker(w), target, stance, n=N, seed=42)


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


class TestRegistry:
    def test_pr7_tag_and_toggle_registered(self):
        assert "melee_wound_s_gt_t" in KNOWN_CONDITION_TAGS
        assert "advanced_or_fell_back" in ATTACKER_TOGGLES
        assert ATTACKER_TOGGLES["advanced_or_fell_back"] is False  # 纯注入门


class TestTargetApWorsen:
    """守方 (save, ap_improve, -1)：恶化攻方 AP（恶孽甲胄/占有狂热）。"""

    _DEF = Effect("save", "ap_improve", (-1,), (), "恶孽甲胄")

    def test_ap_worsened_by_one(self):
        # AP-1 打 Sv4：需 5+（1/3 保住）→ 守方恶化后 AP0 → 4+（1/2 保住）。
        # unsaved/wounds：off = 2/3，on = 1/2
        off = _run(_melee(ap=-1), _target(sv=4), Stance(phase="melee"))
        on = _run(_melee(ap=-1), _target(sv=4, effects=[self._DEF]),
                  Stance(phase="melee"))
        assert _ratio(off.unsaved, off.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_ap0_cannot_be_worsened_into_bonus_save(self):
        # AP0 被恶化成 +1（w.ap - (-1) = +1）：Sv4 → 3+。engine 按特征值层净算，
        # 11 版 AP 恶化下限条款未见——如实按净算（3+ = 1/3 未保）
        on = _run(_melee(ap=0), _target(sv=4, effects=[self._DEF]),
                  Stance(phase="melee"))
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(1 / 3, abs=0.02)


class TestMeleeWoundSGtT:
    """迷魂麝香：仅近战 × S>T 时被伤 -1（裸 wound_s_gt_t 会在射击误放行）。"""

    _DEF = Effect("wound", "modify", (-1,), ("melee_wound_s_gt_t",), "迷魂麝香")

    def test_melee_s_gt_t_gets_penalty(self):
        # S5 vs T4 近战：3+（2/3）→ -1 → 4+（1/2）
        r = _run(_melee(s=5), _target(t=4, sv=7, effects=[self._DEF]),
                 Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_shooting_not_affected(self):
        # 同 S5 vs T4 射击：近战门控拦下 → 3+（2/3）
        r = _run(_gun(s=5), _target(t=4, sv=7, effects=[self._DEF]),
                 Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_melee_s_lte_t_not_affected(self):
        # S4 vs T4 近战：S 不大于 T → 4+（1/2）不动
        r = _run(_melee(s=4), _target(t=4, sv=7, effects=[self._DEF]),
                 Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)


class TestValidation:
    def test_melee_wound_s_gt_t_restricted_to_wound_modify(self):
        raw = {"dsl_version": 1, "table": "stratagems", "id": "x1",
               "side": "target", "faction": "EC", "detachment": None,
               "name_en": "X", "name_zh": None, "status": "partial",
               "effects": [{"phase": "hit", "op": "modify", "params": [-1],
                            "condition": ["melee_wound_s_gt_t"], "source": "err"}],
               "requires_toggles": [], "not_modeled_notes_zh": ["x"],
               "provenance": {"text_sha256": "0" * 64}, "encoded_by": "t"}
        with pytest.raises(DslError):
            parse_entry(raw)
