# tests/test_simulator_dsl_pr5_engine.py
"""P7-PR5 引擎通道：恐虐赐福条件 tag / melee_charging / toggle_groups 组约束 /
attacks-modify 累加 / 守方 (wound, modify) 消费点。

蒙特卡洛比率断言沿用 test_simulator_dsl 范式：N=60000，手算期望值写在断言旁。
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
    inject_attacker,
    parse_entry,
)
from engines.simulator.sequence import (
    KNOWN_CONDITION_TAGS,
    TARGET_CONSUMED,
    _cond_true,
    run_sequence,
)

N = 60000


def _melee_weapon(ws=4, s=4, ap=0, attacks=1, effects=()):
    return WeaponProfile(name_zh=None, name_en="chainaxe", range="Melee",
                         attacks=DiceExpr(k=attacks), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _gun(bs=4, effects=()):
    return WeaponProfile(name_zh=None, name_en="test gun", range='24"',
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=4, ap=0,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(*weapons):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=tuple(weapons))


def _target(t=4, sv=6, models=5, keywords=frozenset(), effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=None, w=1, oc=1,
                         keywords=keywords, effects=tuple(effects))


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


def _run(w, target, stance):
    return run_sequence(_attacker(w), target, stance, n=N, seed=42)


_MELEE = Stance(phase="melee")


class TestBlessingConditionTags:
    def test_tags_registered(self):
        for tag in ("melee_charging", "blessing_martial_excellence",
                    "blessing_warp_blades",
                    "blessing_decapitating_strikes_vs_infantry"):
            assert tag in KNOWN_CONDITION_TAGS

    def test_martial_excellence_sustained_only_when_toggle_and_melee(self):
        # WS4+ 命中 1/2；[连击1] 暴击 1/6 每次 +1 命中 → hits/attacks = 1/2 + 1/6
        eff = Effect("hit", "extra_hits", (DiceExpr(k=1),),
                     ("blessing_martial_excellence",), "卓越武艺")
        w = _melee_weapon(effects=[eff])
        off = _run(w, _target(), _MELEE)
        on = _run(w, _target(), Stance(phase="melee",
                                       blessing_martial_excellence=True))
        assert _ratio(off.hits, off.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(on.hits, on.attacks) == pytest.approx(1 / 2 + 1 / 6, abs=0.02)

    def test_blessing_tag_does_not_fire_in_shooting(self):
        # 赐福 tag 自含近战门控：远程武器带同 tag 的效果在射击阶段不生效
        eff = Effect("hit", "extra_hits", (DiceExpr(k=1),),
                     ("blessing_martial_excellence",), "卓越武艺")
        r = _run(_gun(effects=[eff]), _target(),
                 Stance(phase="shooting", blessing_martial_excellence=True))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_warp_blades_lethal_hits(self):
        # [致命一击]：暴击命中自动致伤。S4vsT4 → 4+；
        # wounds/attacks = 命中非暴击×1/2 + 暴击×1 = (1/2-1/6)/2 + 1/6·1 = 1/3+...
        # 直接对拍开关差分：off = 1/2×1/2 = 1/4；on = (1/3)×(1/2) + (1/6)×1 = 1/3
        eff = Effect("hit", "auto_wound", (), ("blessing_warp_blades",), "次元邪刃")
        w = _melee_weapon(effects=[eff])
        off = _run(w, _target(), _MELEE)
        on = _run(w, _target(), Stance(phase="melee", blessing_warp_blades=True))
        assert _ratio(off.wounds, off.attacks) == pytest.approx(1 / 4, abs=0.02)
        assert _ratio(on.wounds, on.attacks) == pytest.approx(1 / 3, abs=0.02)

    def test_decapitating_strikes_requires_infantry(self):
        # [毁灭伤害] 对步兵：暴击致伤入致命池；非步兵目标不触发
        eff = Effect("wound", "mortal_pool", (),
                     ("blessing_decapitating_strikes_vs_infantry",), "斩首一击")
        w = _melee_weapon(effects=[eff])
        st = Stance(phase="melee", blessing_decapitating_strikes=True)
        inf = _run(w, _target(keywords=frozenset({"infantry"})), st)
        veh = _run(w, _target(keywords=frozenset({"vehicle"})), st)
        assert inf.mortals.mean() > 0
        assert veh.mortals.mean() == 0

    def test_melee_target_has_keyword_composite(self):
        # (tag, kw)：近战 × 目标关键词；射击阶段不放行；缺参 raise
        cond = ("melee_target_has_keyword", "monster")
        assert _cond_true(cond, _MELEE, _target(keywords=frozenset({"monster"})))
        assert not _cond_true(cond, _MELEE, _target(keywords=frozenset({"vehicle"})))
        assert not _cond_true(cond, Stance(phase="shooting"),
                              _target(keywords=frozenset({"monster"})))
        with pytest.raises(ValueError):
            _cond_true(("melee_target_has_keyword",), _MELEE, _target())

    def test_keyword_tag_args_validated_at_parse(self):
        # 关键词 tag 大写/缺参在录入期就炸（大写会静默永不匹配）
        def _entry(cond):
            return _blessing_entry(effects=[
                {"phase": "wound", "op": "modify", "params": [1],
                 "condition": cond, "source": "trophy"}], toggle_groups=[])
        parse_entry(_entry(["melee_target_has_keyword", "monster"]))   # 合法
        with pytest.raises(DslError):
            parse_entry(_entry(["melee_target_has_keyword", "MONSTER"]))
        with pytest.raises(DslError):
            parse_entry(_entry(["melee_target_has_keyword"]))
        with pytest.raises(DslError):
            parse_entry(_entry(["target_has_keyword", "Vehicle"]))

    def test_melee_charging_composite(self):
        assert _cond_true(("melee_charging",),
                          Stance(phase="melee", charging=True), _target())
        assert not _cond_true(("melee_charging",),
                              Stance(phase="melee", charging=False), _target())
        # 关键差分：射击阶段即使 charging 开着也不放行（PR3-H1：软提示不是防线）
        assert not _cond_true(("melee_charging",),
                              Stance(phase="shooting", charging=True), _target())

    def test_toggles_registered_and_stance_backed(self):
        for t in ("blessing_martial_excellence", "blessing_warp_blades",
                  "blessing_decapitating_strikes"):
            assert ATTACKER_TOGGLES.get(t) is True
            assert hasattr(Stance(), t)


class TestAttacksModifyAccumulates:
    def test_two_sources_stack(self):
        # 基础 A1 + 两个 +1 A 效果（分队规则 + 战略同阶段叠加）→ 每次激活 3 攻击骰。
        # PR5 前 rf_expr 是 last-write，会静默吞掉一层
        e1 = Effect("attacks", "modify", (DiceExpr(k=1),), ("phase_melee",), "det")
        e2 = Effect("attacks", "modify", (DiceExpr(k=1),), ("phase_melee",), "strat")
        base = _run(_melee_weapon(), _target(), _MELEE)
        both = _run(_melee_weapon(effects=[e1, e2]), _target(), _MELEE)
        assert base.attacks.mean() == pytest.approx(1.0, abs=0.02)
        assert both.attacks.mean() == pytest.approx(3.0, abs=0.05)

    def test_rapid_fire_semantics_unchanged(self):
        # 既有 rapid fire（半射程条件单效果）行为不变：半射程时 A1+1
        rf = Effect("attacks", "modify", (DiceExpr(k=1),), ("half_range",), "rf1")
        far = _run(_gun(effects=[rf]), _target(), Stance(phase="shooting"))
        near = _run(_gun(effects=[rf]), _target(),
                    Stance(phase="shooting", half_range=True))
        assert far.attacks.mean() == pytest.approx(1.0, abs=0.02)
        assert near.attacks.mean() == pytest.approx(2.0, abs=0.02)


class TestTargetWoundModify:
    def test_registered_in_target_whitelist(self):
        assert ("wound", "modify") in TARGET_CONSUMED

    def test_minus_one_shifts_wound_ratio(self):
        # S4vsT4 → 4+（1/2）；守方 -1 致伤 → 5+（1/3）
        eff = Effect("wound", "modify", (-1,), (), "daemonic resistance")
        base = _run(_melee_weapon(), _target(), _MELEE)
        on = _run(_melee_weapon(), _target(effects=[eff]), _MELEE)
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(on.wounds, on.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_clamps_with_attacker_bonus(self):
        # 攻方 +1 与守方 -1 同在 → 净 0（统一夹取通道，非各夹各的）
        up = Effect("wound", "modify", (1,), (), "trophy")
        down = Effect("wound", "modify", (-1,), (), "resistance")
        r = _run(_melee_weapon(effects=[up]), _target(effects=[down]), _MELEE)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)


def _blessing_entry(**over):
    raw = {
        "dsl_version": 1, "table": "abilities", "id": "000008428",
        "side": "attacker", "faction": "WE", "detachment": None,
        "name_en": "Blessings of Khorne", "name_zh": "恐虐赐福",
        "status": "partial",
        "effects": [
            {"phase": "hit", "op": "extra_hits", "params": [1],
             "condition": ["blessing_martial_excellence"], "source": "卓越武艺"},
            {"phase": "hit", "op": "auto_wound", "params": [],
             "condition": ["blessing_warp_blades"], "source": "次元邪刃"},
        ],
        "requires_toggles": [],
        "toggle_groups": [{"toggles": ["blessing_martial_excellence",
                                       "blessing_warp_blades",
                                       "blessing_decapitating_strikes"],
                           "max": 2, "label_zh": "恐虐赐福"}],
        "not_modeled_notes_zh": ["测试残量"],
        "provenance": {"text_sha256": "0" * 64},
        "encoded_by": "test",
    }
    raw.update(over)
    return raw


class TestToggleGroups:
    def test_parse_valid_group(self):
        entry = parse_entry(_blessing_entry())
        assert entry.toggle_groups[0]["max"] == 2

    def test_reject_bad_shapes(self):
        with pytest.raises(DslError):
            parse_entry(_blessing_entry(toggle_groups=[{"max": 2}]))          # 缺 toggles
        with pytest.raises(DslError):
            parse_entry(_blessing_entry(toggle_groups=[
                {"toggles": ["blessing_warp_blades"], "max": 1}]))            # max ≥ 组大小
        with pytest.raises(DslError):
            parse_entry(_blessing_entry(toggle_groups=[
                {"toggles": ["no_such_toggle", "guided"], "max": 1}]))        # 未注册开关
        with pytest.raises(DslError):
            parse_entry(_blessing_entry(toggle_groups=[
                {"toggles": ["guided", "markerlight_observer"], "max": 0}]))  # max<1

    def test_over_limit_refused_with_note(self):
        # 三项赐福全开 → 超军规上限，整条拒注入 + ⚠ 披露（不静默保留前两个）
        entry = parse_entry(_blessing_entry())
        atk = _attacker(_melee_weapon())
        toggles = frozenset({"blessing_martial_excellence", "blessing_warp_blades",
                             "blessing_decapitating_strikes"})
        out, modeled, not_modeled = inject_attacker(atk, [entry], toggles)
        assert not modeled
        assert any("⚠" in n and "至多" in n for n in not_modeled)
        assert out.loadout[0].effects == ()                  # 未注入

    def test_within_limit_injected(self):
        entry = parse_entry(_blessing_entry())
        atk = _attacker(_melee_weapon())
        toggles = frozenset({"blessing_martial_excellence", "blessing_warp_blades"})
        out, modeled, _ = inject_attacker(atk, [entry], toggles)
        assert modeled
        assert len(out.loadout[0].effects) == 2