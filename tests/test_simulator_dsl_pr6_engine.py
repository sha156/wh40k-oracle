# tests/test_simulator_dsl_pr6_engine.py
"""P7-PR6 黑色圣堂引擎通道：下车态 tag + S/T 延迟判定致伤修正 + 指引圣兆 tag。

双验范式（spec 七-1）：每个新通道至少一条差分断言，手算期望值写在断言旁。
基线骰面：WS4+ 命中 1/2；S4 vs T4 致伤 4+ = 1/2；S4 vs T5 致伤 5+ = 1/3。
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
from engines.simulator.dsl import (
    ATTACKER_TOGGLES,
    DslError,
    attacker_toggles_from_options,
    parse_entry,
)
from engines.simulator.sequence import KNOWN_CONDITION_TAGS, run_sequence

N = 60000


def _melee_weapon(ws=4, s=4, ap=0, attacks=1, effects=()):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                         attacks=DiceExpr(k=attacks), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(w):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=(w,))


def _target(t=4, sv=7, models=5, keywords=frozenset(), effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=None, w=1, oc=1,
                         keywords=keywords, effects=tuple(effects))


def _run(w, target, stance):
    return run_sequence(_attacker(w), target, stance, n=N, seed=42)


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


_MELEE = Stance(phase="melee")


class TestTagsRegistered:
    def test_pr6_tags_registered(self):
        for tag in ("melee_disembarked", "melee_s_lte_t", "wound_s_gt_t",
                    "omen_instrument_vs_character", "omen_momentous_brutality"):
            assert tag in KNOWN_CONDITION_TAGS

    def test_pr6_toggles_registered(self):
        for t in ("disembarked_this_turn", "disembarked_from_land_raider",
                  "vow_accept_any_challenge", "omen_instrument",
                  "omen_momentous_brutality"):
            assert t in ATTACKER_TOGGLES

    def test_land_raider_implies_disembarked(self):
        on = attacker_toggles_from_options({"disembarked_from_land_raider": True})
        assert "disembarked_this_turn" in on


class TestMeleeDisembarked:
    def test_hit_bonus_only_when_melee_and_disembarked(self):
        # Shock and Awe：下车回合近战命中+1。WS4+ → off 1/2，on 3+ = 2/3
        eff = Effect("hit", "modify", (1,), ("melee_disembarked",), "震慑突袭")
        w = _melee_weapon(effects=[eff])
        off = _run(w, _target(), _MELEE)
        on = _run(w, _target(), Stance(phase="melee", disembarked_this_turn=True))
        assert _ratio(off.hits, off.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(on.hits, on.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_land_raider_stance_field_also_fires_tag(self):
        # LR 档 Stance 字段独立点亮时 tag 亦成立（蕴含语义在 tag 内）
        eff = Effect("hit", "modify", (1,), ("melee_disembarked",), "震慑突袭")
        w = _melee_weapon(effects=[eff])
        on = _run(w, _target(),
                  Stance(phase="melee", disembarked_from_land_raider=True))
        assert _ratio(on.hits, on.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_no_bonus_in_shooting(self):
        gun = WeaponProfile(name_zh=None, name_en="gun", range='24"',
                            attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                            damage=DiceExpr(k=1),
                            effects=(Effect("hit", "modify", (1,),
                                            ("melee_disembarked",), "震慑突袭"),),
                            count=1)
        r = _run(gun, _target(), Stance(phase="shooting",
                                        disembarked_this_turn=True))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)


class TestVowSLteT:
    """圣堂誓言·接受一切挑战：近战 S≤T 时致伤+1——延迟到最终 S 判定。"""

    _EFF = Effect("wound", "modify", (1,), ("melee_s_lte_t",), "接受一切挑战")

    def test_bonus_when_s_lte_t(self):
        # S4 vs T5：2S>T → 5+（1/3）；+1 → 4+（1/2）。wounds/hits 差分
        w = _melee_weapon(s=4, effects=[self._EFF])
        off = _run(_melee_weapon(s=4), _target(t=5), _MELEE)
        on = _run(w, _target(t=5), _MELEE)
        assert _ratio(off.wounds, off.hits) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(on.wounds, on.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_no_bonus_when_s_gt_t(self):
        # S5 vs T4：S>T → 3+（2/3），誓言不适用——比值与无效果基线一致
        w = _melee_weapon(s=5, effects=[self._EFF])
        r = _run(w, _target(t=4), _MELEE)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_s_improve_can_push_past_t_and_cancel_vow(self):
        # RAW 特征值先改后比：S4 + s_improve 2 = S6 打 T5 → S>T，誓言失效。
        # wt(6,5)=3+ → 2/3；若误用基础 S 判定会错给 +1 → 2+（5/6）
        s_up = Effect("wound", "s_improve", (2,), ("phase_melee",), "屠灭邪物")
        w = _melee_weapon(s=4, effects=[self._EFF, s_up])
        r = _run(w, _target(t=5), _MELEE)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_deferred_merges_into_unified_clamp(self):
        # 基础 +1（另一来源）+ 誓言 +1 → 合并夹取到 +1（不是 +2）。
        # S4 vs T4：4+ 基线 1/2；夹后 +1 → 3+ = 2/3（若错叠 +2 会成 2+ = 5/6）
        base = Effect("wound", "modify", (1,), ("phase_melee",), "另一来源")
        w = _melee_weapon(s=4, effects=[self._EFF, base])
        r = _run(w, _target(t=4), _MELEE)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_not_in_shooting(self):
        gun = WeaponProfile(name_zh=None, name_en="gun", range='24"',
                            attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                            damage=DiceExpr(k=1), effects=(self._EFF,), count=1)
        r = _run(gun, _target(t=5), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)


class TestTargetWoundSGtT:
    """净化！圣化！守方向：攻方最终 S>T 时被伤-1（延迟判定）。"""

    _DEF = Effect("wound", "modify", (-1,), ("wound_s_gt_t",), "净化！圣化！")

    def test_minus_one_when_s_gt_t(self):
        # S5 vs T4：3+（2/3）→ -1 → 4+（1/2）
        r = _run(_melee_weapon(s=5), _target(t=4, effects=[self._DEF]), _MELEE)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_no_effect_when_s_lte_t(self):
        # S4 vs T4：4+（1/2）不受影响
        r = _run(_melee_weapon(s=4), _target(t=4, effects=[self._DEF]), _MELEE)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)


class TestGuidingOmens:
    def test_momentous_brutality_adds_attacks(self):
        # 凶暴神视：近战 A+2 → 每模型 1+2=3 攻击
        eff = Effect("attacks", "modify", (DiceExpr(k=2),),
                     ("omen_momentous_brutality",), "凶暴神视")
        w = _melee_weapon(effects=[eff])
        off = _run(w, _target(), _MELEE)
        on = _run(w, _target(), Stance(phase="melee",
                                       omen_momentous_brutality=True))
        assert off.attacks.mean() == pytest.approx(1.0, abs=0.02)
        assert on.attacks.mean() == pytest.approx(3.0, abs=0.02)

    def test_instrument_dev_wounds_needs_character(self):
        # 神皇之器：近战接战 CHARACTER 时 [毁灭伤害]——暴击致伤入致命池
        eff = Effect("wound", "mortal_pool", (),
                     ("omen_instrument_vs_character",), "神皇之器")
        w = _melee_weapon(effects=[eff])
        st = Stance(phase="melee", omen_instrument=True)
        vs_char = _run(w, _target(keywords=frozenset({"character"})), st)
        vs_line = _run(w, _target(), st)
        no_toggle = _run(w, _target(keywords=frozenset({"character"})), _MELEE)
        assert vs_char.mortals.mean() > 0
        assert vs_line.mortals.mean() == 0
        assert no_toggle.mortals.mean() == 0


class TestDeferredTagValidation:
    def test_s_tags_only_allowed_on_wound_modify(self):
        raw = {"dsl_version": 1, "table": "stratagems", "id": "x1",
               "side": "attacker", "faction": "SM", "detachment": None,
               "name_en": "X", "name_zh": None, "status": "partial",
               "effects": [{"phase": "hit", "op": "modify", "params": [1],
                            "condition": ["melee_s_lte_t"], "source": "err"}],
               "requires_toggles": [], "not_modeled_notes_zh": ["x"],
               "provenance": {"text_sha256": "0" * 64}, "encoded_by": "t"}
        with pytest.raises(DslError):
            parse_entry(raw)
