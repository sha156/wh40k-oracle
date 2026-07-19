# tests/test_simulator_dsl_pr8_engine.py
"""P7-PR8 引擎通道：T 特征值净算（攻方 t_worsen / 守方 t_improve）+ 骨疽疟条件 tag。

关键语义（手算注释均为精确概率）：
  · T-1 与 S+1 在 2T 边界不等价：S6 打 T4 基线 3+（S>T）；t_worsen 1 → T3，
    S6 ≥ 2×3 升 2+（5/6）；而 s_improve 1 → S7 vs T4 仍只是 S>T → 3+（2/3）
  · 特征值下限：T 不得低于 1（核心规则），t_worsen 溢出钳住
  · S/T 延迟分量（wound_mod_s_gt_t 等）比较基准同为最终 T
"""
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
from engines.simulator.dsl import (
    ATTACKER_TOGGLES,
    DslError,
    parse_entry,
)
from engines.simulator.effect_params import KNOWN_CONDITION_TAGS
from engines.simulator.sequence import run_sequence

N = 60000


def _melee(ws=4, s=4, ap=0, effects=()):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(*weapons):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=tuple(weapons))


def _target(t=4, sv=7, models=5, effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=None, w=1, oc=1,
                         keywords=frozenset(), effects=tuple(effects))


def _run(atk, target, stance=None):
    return run_sequence(atk, target, stance or Stance(phase="melee"),
                        n=N, seed=42)


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


class TestRegistry:
    def test_pr8_tag_and_toggles_registered(self):
        assert "plague_rattlejoint" in KNOWN_CONDITION_TAGS
        assert ATTACKER_TOGGLES["target_afflicted"] is False      # 纯注入门
        assert ATTACKER_TOGGLES["plague_rattlejoint"] is True     # Stance 字段
        assert hasattr(Stance(), "plague_rattlejoint")


class TestTWorsen:
    """攻方 (wound, t_worsen, 1)：目标 T 特征值恶化。"""

    def test_2t_boundary_not_equivalent_to_s_improve(self):
        # S6 vs T4 基线 3+（2/3）。t_worsen 1 → T3，S≥2T 升 2+（5/6）；
        # s_improve 1 → S7 vs T4 仍 3+（2/3）——两通道在 2T 边界必须分道
        tw = Effect(phase="wound", op="t_worsen", params=(1,))
        si = Effect(phase="wound", op="s_improve", params=(1,))
        base = _run(_attacker(_melee(s=6)), _target(t=4))
        worsen = _run(_attacker(_melee(s=6, effects=(tw,))), _target(t=4))
        stronger = _run(_attacker(_melee(s=6, effects=(si,))), _target(t=4))
        assert _ratio(base.wounds, base.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(worsen.wounds, worsen.hits) == pytest.approx(5 / 6, abs=0.02)
        assert _ratio(stronger.wounds, stronger.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_t_floor_clamped_at_1(self):
        # T1 目标：S4 vs T1 已是 2+（S≥2T）；t_worsen 1 钳在 T1，比率不再变化
        tw = Effect(phase="wound", op="t_worsen", params=(1,))
        base = _run(_attacker(_melee(s=4)), _target(t=1))
        worsen = _run(_attacker(_melee(s=4, effects=(tw,))), _target(t=1))
        assert _ratio(base.wounds, base.hits) == pytest.approx(5 / 6, abs=0.02)
        assert _ratio(worsen.wounds, worsen.hits) == pytest.approx(5 / 6, abs=0.02)


class TestTImprove:
    """守方 (wound, t_improve, X)：T 特征值改善，与 t_worsen 同一 t_final 净算。"""

    def test_plus_2_t_shifts_wound_band(self):
        # S4 vs T4 → 4+（1/2）；+2 T → T6（T>S 且 <2S）→ 5+（1/3）
        ti = Effect(phase="wound", op="t_improve", params=(2,))
        base = _run(_attacker(_melee()), _target(t=4))
        buffed = _run(_attacker(_melee()), _target(t=4, effects=(ti,)))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(buffed.wounds, buffed.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_net_with_t_worsen(self):
        # t_worsen 1 + t_improve 2 → 净 T5：S4 vs T5 → 5+（1/3）
        tw = Effect(phase="wound", op="t_worsen", params=(1,))
        ti = Effect(phase="wound", op="t_improve", params=(2,))
        r = _run(_attacker(_melee(effects=(tw,))), _target(t=4, effects=(ti,)))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_deferred_s_gt_t_compares_final_t(self):
        # 守方 S>T 延迟分量（被伤-1）基准=最终 T：
        # S5 vs T4（S>T）→ 分量生效：3+ → 4+（1/2）；
        # 再加 t_improve 2 → T6，S<T → 分量不生效：致伤 5+（1/3，纯 T 档位移动）
        sgt = Effect(phase="wound", op="modify", params=(-1,),
                     condition=("wound_s_gt_t",))
        ti = Effect(phase="wound", op="t_improve", params=(2,))
        with_mod = _run(_attacker(_melee(s=5)), _target(t=4, effects=(sgt,)))
        buffed = _run(_attacker(_melee(s=5)), _target(t=4, effects=(sgt, ti)))
        assert _ratio(with_mod.wounds, with_mod.hits) == pytest.approx(1 / 2,
                                                                       abs=0.02)
        assert _ratio(buffed.wounds, buffed.hits) == pytest.approx(1 / 3,
                                                                   abs=0.02)


class TestPlagueRattlejoint:
    def test_condition_gates_on_stance(self):
        # (save, ap_improve, 1) cond plague_rattlejoint：开关关无差分、开 AP 恶化 1 档
        ap = Effect(phase="save", op="ap_improve", params=(1,),
                    condition=("plague_rattlejoint",))
        atk = _attacker(_melee(effects=(ap,)))
        off = _run(atk, _target(sv=4))
        on = _run(atk, _target(sv=4), Stance(phase="melee",
                                             plague_rattlejoint=True))
        # sv4 ap0：save 4+ → unsaved 1/2；AP-1 → 5+ → 2/3
        assert _ratio(off.unsaved, off.wounds) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(2 / 3, abs=0.02)


class TestDslValidation:
    def _raw(self, side, phase, op, params):
        return {
            "dsl_version": 1, "table": "stratagems", "id": "x1",
            "side": side, "faction": "DG", "name_en": "X", "status": "partial",
            "effects": [{"phase": phase, "op": op, "params": params,
                         "condition": [], "source": "t"}],
            "not_modeled_notes_zh": ["r"],
            "provenance": {"text_sha256": "00"},
        }

    def test_t_worsen_attacker_only(self):
        parse_entry(self._raw("attacker", "wound", "t_worsen", [1]))
        with pytest.raises(DslError):
            parse_entry(self._raw("target", "wound", "t_worsen", [1]))

    def test_t_improve_target_only(self):
        parse_entry(self._raw("target", "wound", "t_improve", [2]))
        with pytest.raises(DslError):
            parse_entry(self._raw("attacker", "wound", "t_improve", [2]))

    def test_t_worsen_param_shape(self):
        with pytest.raises(DslError):
            parse_entry(self._raw("attacker", "wound", "t_worsen", []))
        with pytest.raises(DslError):
            parse_entry(self._raw("attacker", "wound", "t_worsen", ["1"]))
