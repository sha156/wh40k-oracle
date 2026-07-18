# tests/test_simulator_dsl_pr4_engine.py
"""P7-PR4 引擎通道：s_improve / 守方 invuln·sv_improve / _target_effect_value 条件化 /
inject_target / weapon_filter / 开关注册表。

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
    TARGET_TOGGLES,
    DslError,
    attacker_toggles_from_options,
    inject_attacker,
    inject_target,
    parse_entry,
    select_entries,
    target_toggles_from_options,
)
from engines.simulator.sequence import (
    ATTACKER_CONSUMED,
    KNOWN_CONDITION_TAGS,
    TARGET_CONSUMED,
    run_sequence,
)

N = 60000


def _weapon(bs=4, s=4, ap=0, effects=()):
    return WeaponProfile(name_zh=None, name_en="test gun", range='24"',
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(*weapons):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=tuple(weapons))


def _target(t=4, sv=6, invuln=None, models=5, effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=1, oc=1,
                         effects=tuple(effects))


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


def _run(w, target, stance=None):
    return run_sequence(_attacker(w), target, stance or Stance(phase="shooting"),
                        n=N, seed=42)


class TestStrengthImproveChannel:
    def test_s_improve_shifts_wound_table(self):
        # S4 vs T4 → 4+（P=1/2）；s_improve+1 → S5>T4 → 3+（P=4/6）
        eff = Effect("wound", "s_improve", (1,), (), "bonded")
        base = _run(_weapon(), _target())
        on = _run(_weapon(effects=[eff]), _target())
        assert _ratio(base.wounds, base.hits) == pytest.approx(3 / 6, abs=0.02)
        assert _ratio(on.wounds, on.hits) == pytest.approx(4 / 6, abs=0.02)

    def test_s_improve_is_characteristic_not_roll_modifier(self):
        # 关键差分（禁止折算成 wound modify）：S4 vs T7 → 2S>T → 5+；
        # S5 vs T7 仍 S<T 且 2S>T → 5+ **不变**；而 wound modify +1 会错升成 4+
        eff = Effect("wound", "s_improve", (1,), (), "bonded")
        on = _run(_weapon(effects=[eff]), _target(t=7))
        mod = _run(_weapon(effects=[Effect("wound", "modify", (1,), (), "x")]),
                   _target(t=7))
        assert _ratio(on.wounds, on.hits) == pytest.approx(2 / 6, abs=0.02)
        assert _ratio(mod.wounds, mod.hits) == pytest.approx(3 / 6, abs=0.02)

    def test_registered_in_attacker_whitelist(self):
        assert ("wound", "s_improve") in ATTACKER_CONSUMED


class TestTargetSaveChannels:
    def test_dsl_invuln_grants_save(self):
        # Sv6+ AP-2 → 护甲 8+ 不可能；DSL invuln 5+ → P(save)=2/6，
        # unsaved/wounds 从 1.0 降到 4/6
        inv = Effect("save", "invuln", (5,), (), "skirmish fighters")
        base = _run(_weapon(ap=-2), _target())
        on = _run(_weapon(ap=-2), _target(effects=[inv]))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(1.0, abs=0.02)
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(4 / 6, abs=0.02)

    def test_dsl_invuln_takes_best_with_profile(self):
        # profile 自带 4++ 优于 DSL 6++ → 用 4++（P(unsaved)=1/2）
        inv = Effect("save", "invuln", (6,), (), "worse invuln")
        on = _run(_weapon(ap=-2), _target(invuln=4, effects=[inv]))
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(3 / 6, abs=0.02)

    def test_sv_improve_shifts_armor(self):
        # Sv4+ AP0 → P(unsaved)=1/2；+1 Sv → 3+ → P(unsaved)=2/6
        up = Effect("save", "sv_improve", (1,), (), "autoreactive")
        base = _run(_weapon(), _target(sv=4))
        on = _run(_weapon(), _target(sv=4, effects=[up]))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(3 / 6, abs=0.02)
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(2 / 6, abs=0.02)

    def test_sv_improve_floor_at_two(self):
        # Sv2+ 再 +1 → effective_save 夹到 2+（1+ 不存在）：数值不再变
        up = Effect("save", "sv_improve", (1,), (), "autoreactive")
        base = _run(_weapon(), _target(sv=2))
        on = _run(_weapon(), _target(sv=2, effects=[up]))
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(
            _ratio(base.unsaved, base.wounds), abs=0.02)

    def test_conditioned_invuln_by_phase(self):
        # Skirmish Fighters 形状：远程 5++ / 近战 6++ 两条条件效果并存，
        # 射击阶段只吃 5++（更优不受近战条目影响）
        inv_r = Effect("save", "invuln", (5,), ("phase_shooting",), "sf ranged")
        inv_m = Effect("save", "invuln", (6,), ("phase_melee",), "sf melee")
        tgt = _target(effects=[inv_r, inv_m])
        on = _run(_weapon(ap=-2), tgt)
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(4 / 6, abs=0.02)
        assert ("save", "invuln") in TARGET_CONSUMED
        assert ("save", "sv_improve") in TARGET_CONSUMED


class TestTargetEffectValueConditioned:
    def test_fnp_condition_respected(self):
        # 条件化 FNP（仅射击阶段）在近战模拟中不得生效——修复前首匹配无视 condition
        fnp = Effect("fnp", "fnp", (5,), ("phase_shooting",), "cond fnp")
        melee_w = WeaponProfile(name_zh=None, name_en="claw", range="Melee",
                                attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                                damage=DiceExpr(k=1), count=1)
        on = run_sequence(_attacker(melee_w), _target(effects=[fnp]),
                          Stance(phase="melee"), n=N, seed=42)
        base = run_sequence(_attacker(melee_w), _target(),
                            Stance(phase="melee"), n=N, seed=42)
        assert on.damage.mean() == pytest.approx(base.damage.mean(), rel=0.03)

    def test_fnp_best_of_multiple_sources(self):
        # 手动开关 fnp6 + DSL fnp5 → 取更优 5+（存活率 2/6）
        f6 = Effect("fnp", "fnp", (6,), (), "manual")
        f5 = Effect("fnp", "fnp", (5,), (), "dsl")
        both = _run(_weapon(), _target(effects=[f6, f5]))
        only5 = _run(_weapon(), _target(effects=[f5]))
        assert both.damage.mean() == pytest.approx(only5.damage.mean(), rel=0.03)

    def test_damage_reduction_best_of(self):
        # 减伤取大：1 与 2 并存 → 按 2 生效（D3 武器）
        d3 = WeaponProfile(name_zh=None, name_en="d3 gun", range='24"',
                           attacks=DiceExpr(k=1), bs_ws=4, strength=8, ap=-4,
                           damage=DiceExpr(n=1, faces=3, k=0), count=1)
        r1 = Effect("damage", "damage_reduction", (1,), (), "a")
        r2 = Effect("damage", "damage_reduction", (2,), (), "b")
        tgt_both = TargetProfile(canonical_id="t", name_en="T", name_zh=None,
                                 models=3, t=4, sv=6, invuln=None, w=6, oc=1,
                                 effects=(r1, r2))
        tgt_two = TargetProfile(canonical_id="t", name_en="T", name_zh=None,
                                models=3, t=4, sv=6, invuln=None, w=6, oc=1,
                                effects=(r2,))
        a, b = (run_sequence(_attacker(d3), t, Stance(phase="shooting"),
                             n=N, seed=42) for t in (tgt_both, tgt_two))
        assert a.damage.mean() == pytest.approx(b.damage.mean(), rel=0.03)


class TestModelsInRangeCondition:
    def test_sustained_by_target_size(self):
        # Arro'kon 形状：extra_hits 1 限 6-10 模型——5 模型目标不触发、6 模型触发
        eff = Effect("hit", "extra_hits", (DiceExpr(k=1),),
                     ("target_models_in_range", 6, 10), "arrokon")
        small = _run(_weapon(effects=[eff]), _target(models=5))
        big = _run(_weapon(effects=[eff]), _target(models=6))
        # BS4+：命中 0.5；触发后每暴击(1/6)+1 命中 → hits/attacks = 0.5+1/6
        assert _ratio(small.hits, small.attacks) == pytest.approx(0.5, abs=0.02)
        assert _ratio(big.hits, big.attacks) == pytest.approx(0.5 + 1 / 6, abs=0.02)


def _raw_entry(**over):
    raw = {
        "dsl_version": 1, "table": "stratagems", "id": "s-test",
        "side": "target", "faction": "TAU", "detachment": None,
        "name_en": "STIMM TEST", "name_zh": "测试", "status": "partial",
        "effects": [{"phase": "fnp", "op": "fnp", "params": [6],
                     "condition": [], "source": "stimm"}],
        "requires_toggles": [], "conflicts_with_toggles": [],
        "not_modeled_notes_zh": ["CP 不结算"],
        "provenance": {"text_sha256": "0" * 64},
    }
    raw.update(over)
    return raw


class TestInjectTarget:
    def test_injects_and_pairs_report_with_change(self):
        # F5 成对语义：注入 → modeled 注记出现 且 数值真的动
        entry = parse_entry(_raw_entry())
        tgt, modeled, notes = inject_target(_target(), [entry], frozenset())
        assert any("已施加（守方）" in m for m in modeled)
        base = _run(_weapon(), _target())
        on = _run(_weapon(), tgt)
        # FNP6+ → 伤害 ×5/6
        assert on.damage.mean() == pytest.approx(base.damage.mean() * 5 / 6, rel=0.05)

    def test_toggle_gate_blocks(self):
        entry = parse_entry(_raw_entry(requires_toggles=["defender_hidden"]))
        tgt, modeled, notes = inject_target(_target(), [entry], frozenset())
        assert not modeled and tgt.effects == ()
        assert any("未启用" in x for x in notes)
        tgt2, modeled2, _ = inject_target(
            _target(), [entry], frozenset({"defender_hidden"}))
        assert modeled2 and len(tgt2.effects) == 1

    def test_attacker_side_entry_disclosed_as_direction(self):
        # 守方阵营的攻方向条目（FTGG 等）→ 方向说明，不假装生效
        entry = parse_entry(_raw_entry(
            side="attacker", table="abilities",
            effects=[{"phase": "hit", "op": "bs_improve", "params": [1],
                      "condition": ["guided_vs_spotted"], "source": "ftgg"}]))
        tgt, modeled, notes = inject_target(_target(), [entry], frozenset())
        assert not modeled and tgt.effects == ()
        assert any("攻方向条目" in x for x in notes)

    def test_conflicts_gate(self):
        entry = parse_entry(_raw_entry(conflicts_with_toggles=["defender_hidden"]))
        _, modeled, notes = inject_target(
            _target(), [entry], frozenset({"defender_hidden"}))
        assert not modeled and any("互斥" in x for x in notes)


class TestWeaponFilter:
    def _entry(self, wf="flamer"):
        return parse_entry(_raw_entry(
            side="attacker", weapon_filter=wf,
            effects=[{"phase": "save", "op": "ap_improve", "params": [1],
                      "condition": [], "source": "epc"}]))

    def test_only_matching_weapon_gets_effects(self):
        flamer = WeaponProfile(name_zh=None, name_en="T'au flamer", range='12"',
                               attacks=DiceExpr(k=1), bs_ws=None, strength=4, ap=0,
                               damage=DiceExpr(k=1), count=1)
        rifle = _weapon()
        atk, modeled, _ = inject_attacker(
            AttackerProfile(canonical_id="a", name_en="A", name_zh=None, models=1,
                            loadout=(flamer, rifle)),
            [self._entry()], frozenset())
        by_name = {w.name_en: w for w in atk.loadout}
        assert len(by_name["T'au flamer"].effects) == 1
        assert len(by_name["test gun"].effects) == 0
        assert any("限武器" in m for m in modeled)

    def test_no_match_disclosed(self):
        atk, modeled, notes = inject_attacker(
            _attacker(_weapon()), [self._entry("plasma rifle")], frozenset())
        assert not modeled
        assert any("没有名字含" in x for x in notes)

    def test_target_side_weapon_filter_rejected(self):
        with pytest.raises(DslError, match="weapon_filter"):
            parse_entry(_raw_entry(weapon_filter="flamer"))


class TestToggleRegistry:
    def test_unknown_toggle_name_rejected(self):
        with pytest.raises(DslError, match="未注册的开关名"):
            parse_entry(_raw_entry(requires_toggles=["no_such_toggle"]))

    def test_options_normalization_implications(self):
        # 8" 蕴含 12"；低于半编蕴含低于满编
        on = attacker_toggles_from_options({"range_within_8": True})
        assert {"range_within_8", "range_within_12"} <= on
        on2 = attacker_toggles_from_options({"target_below_half": True})
        assert {"target_below_half", "target_below_starting"} <= on2

    def test_target_toggles_separate_namespace(self):
        on = target_toggles_from_options({"defender_hidden": True, "guided": True})
        assert on == frozenset({"defender_hidden"})

    def test_stance_backed_toggles_exist_as_fields(self):
        # 注册表标 True 的攻方开关必须真的是 Stance 字段（防注册表与引擎漂移）
        s = Stance()
        for name, stance_backed in ATTACKER_TOGGLES.items():
            if stance_backed:
                assert hasattr(s, name), f"Stance 缺字段 {name}"

    def test_no_namespace_overlap(self):
        assert not set(ATTACKER_TOGGLES) & set(TARGET_TOGGLES)


class TestFourWayToggleParity:
    """四路接线对拍（spec §四.6）：注册表是唯一真源，任一链路漏接开关即红。"""

    _LIST_KEYS = ("stratagems", "enhancements",
                  "defender_stratagems", "defender_enhancements")
    _STR_KEYS = ("detachment", "defender_detachment")

    def test_web_sanitize_passes_all_registry_toggles(self):
        from web_api.simulate import sanitize_options
        raw = {t: True for t in list(ATTACKER_TOGGLES) + list(TARGET_TOGGLES)}
        raw.update({k: ["X"] for k in self._LIST_KEYS})
        raw.update({k: "Kauyon" for k in self._STR_KEYS})
        out = sanitize_options(raw)
        for t in list(ATTACKER_TOGGLES) + list(TARGET_TOGGLES):
            assert out.get(t) is True, f"web sanitize 吞了开关 {t}"
        for k in self._LIST_KEYS:
            assert out.get(k) == ["X"], f"web sanitize 吞了 {k}"
        for k in self._STR_KEYS:
            assert out.get(k) == "Kauyon", f"web sanitize 吞了 {k}"

    def test_cli_has_flag_for_every_toggle(self):
        # CLI argparse 的 dest 覆盖全部注册表开关 + 点名/分队键
        import argparse
        from unittest import mock
        from engines.simulator import cli as sim_cli
        captured = {}
        orig = argparse.ArgumentParser.parse_args

        def fake_parse(self, argv=None):
            captured["dests"] = {a.dest for a in self._actions}
            raise SystemExit(0)          # 只收集不执行

        with mock.patch.object(argparse.ArgumentParser, "parse_args", fake_parse):
            with pytest.raises(SystemExit):
                sim_cli.main(["a", "b"])
        dests = captured["dests"]
        for t in list(ATTACKER_TOGGLES) + list(TARGET_TOGGLES):
            assert t in dests, f"CLI 缺开关旗标 {t}"
        for k in self._LIST_KEYS + self._STR_KEYS:
            assert k in dests, f"CLI 缺参数 {k}"

    def test_panel_emits_all_registry_toggles(self):
        # 面板 _options_from_inputs 覆盖全部开关与点名键（session_state 直灌）
        from types import SimpleNamespace
        from ui.simulator_panel import _options_from_inputs
        state = {
            "sim_guided": True, "sim_markerlight": True, "sim_det_rounds": True,
            "sim_r12": True, "sim_r8": True, "sim_tbs": True, "sim_tbh": True,
            "sim_ml_visible": True, "sim_bearer": True,
            "sim_def_hidden": True, "sim_def_bearer": True,
            "sim_detachment": "Kauyon", "sim_stratagems": "X",
            "sim_enhancements": "Y", "sim_def_detachment": "Kroot Hunting Pack",
            "sim_def_stratagems": "Z", "sim_def_enhancements": "W",
        }
        fake_st = SimpleNamespace(session_state=state)
        opts = _options_from_inputs(fake_st)
        for t in list(ATTACKER_TOGGLES) + list(TARGET_TOGGLES):
            assert opts.get(t) is True, f"面板漏发开关 {t}"
        assert opts["stratagems"] == ["X"] and opts["enhancements"] == ["Y"]
        assert opts["defender_stratagems"] == ["Z"]
        assert opts["defender_enhancements"] == ["W"]
        assert opts["detachment"] == "Kauyon"
        assert opts["defender_detachment"] == "Kroot Hunting Pack"

    def test_tools_consumes_every_toggle(self):
        # tools.py 的 Stance 构造 + toggles helper 覆盖：stance-backed 开关名必须
        # 出现在 simulate_combat_resolved 源码里（helper 化的经 *_from_options 免检）
        import inspect
        from agent import tools
        src = inspect.getsource(tools.simulate_combat_resolved)
        assert "attacker_toggles_from_options" in src
        assert "target_toggles_from_options" in src
        for name, stance_backed in ATTACKER_TOGGLES.items():
            if stance_backed:
                assert name in src, f"tools.py Stance 构造缺 {name}"
        for key in ("enhancements", "defender_detachment",
                    "defender_stratagems", "defender_enhancements"):
            assert key in src, f"tools.py 缺 {key} 接线"


class TestSelectEntriesEnhancements:
    def _enh_entry(self, **over):
        raw = _raw_entry(
            table="enhancements", id="e-test", side="attacker",
            name_en="Borthrod Gland", name_zh="博斯罗德腺体",
            detachment="Kroot Hunting Pack",
            effects=[{"phase": "hit", "op": "crit_threshold", "params": [5],
                      "condition": ["phase_melee"], "source": "borthrod"}])
        raw.update(over)
        return parse_entry(raw)

    def test_enhancement_is_opt_in_not_auto(self):
        # 增强与战略同为 opt-in：选了分队但没点名 → 不入选
        entry = self._enh_entry()
        sel, notes = select_entries([entry], detachment="Kroot Hunting Pack")
        assert sel == []
        sel2, _ = select_entries([entry], detachment="Kroot Hunting Pack",
                                 enhancements=("Borthrod Gland",))
        assert sel2 == [entry]

    def test_enhancement_wrong_detachment_disclosed(self):
        entry = self._enh_entry()
        sel, notes = select_entries([entry], detachment="Kauyon",
                                    enhancements=("Borthrod Gland",))
        assert sel == [] and any("不符" in x for x in notes)

    def test_unmatched_enhancement_token_disclosed(self):
        sel, notes = select_entries([], enhancements=("No Such Thing",))
        assert any("增强点名" in x for x in notes)
