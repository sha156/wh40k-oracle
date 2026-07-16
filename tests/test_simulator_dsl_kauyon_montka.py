# tests/test_simulator_dsl_kauyon_montka.py
"""P7-PR3：Kauyon/Mont'ka 分队规则 + 12 战略的 DSL 编码与引擎新通道。

覆盖（spec 七-1 双验范式，手算期望值写在断言旁，期望值必须动）：
  · 引擎新通道：hit reroll(fail) / ap_improve / 条件化 extra_hits·auto_wound·wound reroll
  · 新 condition tag：detachment_rounds_shooting / detachment_rounds_guided / markerlight_observer
  · select_entries 选择层：分队匹配 / 战略点名 / 弯撇号归一 / 未匹配显式披露
  · 真源 payload 逐条引擎级差分（Patient Hunter / Killing Blow / 6 条带效果战略）
  · 三态对账：payload 计数与判据
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
from engines.simulator.dsl import inject_attacker, load_payload_file, select_entries
from engines.simulator.sequence import run_sequence

N = 60000
PAYLOAD = Path("dsl_payloads/tau.json")


def _weapon(bs=4, s=4, ap=0, effects=()):
    return WeaponProfile(name_zh=None, name_en="test gun", range='24"',
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(w):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=(w,))


def _target(sv=6, t=4):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None, models=5,
                         t=t, sv=sv, invuln=None, w=1, oc=1)


def _raw(w, stance, target=None, seed=42):
    return run_sequence(_attacker(w), target or _target(), stance, n=N, seed=seed)


def _hit_ratio(w, stance, target=None):
    raw = _raw(w, stance, target)
    return raw.hits.mean() / raw.attacks.mean()


def _wound_per_attack(w, stance, target=None):
    raw = _raw(w, stance, target)
    return raw.wounds.mean() / raw.attacks.mean()


_SHOOT = Stance(phase="shooting")


# ── 引擎新通道 ───────────────────────────────────────────────────────────────

class TestHitRerollChannel:
    def test_reroll_fail_moves_hit_ratio(self):
        # BS4+：0.5 → 0.5 + 0.5×0.5 = 0.75（只重骰失败）
        eff = Effect("hit", "reroll", ("fail",), (), "pinpoint")
        assert _hit_ratio(_weapon(), _SHOOT) == pytest.approx(0.5, abs=0.02)
        assert _hit_ratio(_weapon(effects=[eff]), _SHOOT) == pytest.approx(0.75, abs=0.02)

    def test_reroll_respects_condition(self):
        # condition=phase_shooting 在近战不放行（近战 WS4+ 仍 0.5）
        eff = Effect("hit", "reroll", ("fail",), ("phase_shooting",), "x")
        w = WeaponProfile(name_zh=None, name_en="fist", range="Melee",
                          attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                          damage=DiceExpr(k=1), effects=(eff,), count=1)
        assert _hit_ratio(w, Stance(phase="melee")) == pytest.approx(0.5, abs=0.02)

    def test_reroll_can_yield_crit(self):
        # 重骰出的 6 照常暴击：带 sustained 1 + reroll，
        # hits/attacks = P(hit)+P(crit) = 0.75 + (1/6 + 0.5×1/6) = 0.75 + 0.25 = 1.0
        effs = [Effect("hit", "reroll", ("fail",), (), "x"),
                Effect("hit", "extra_hits", (DiceExpr(k=1),), (), "sustained")]
        assert _hit_ratio(_weapon(effects=effs), _SHOOT) == pytest.approx(1.0, abs=0.03)


class TestApImproveChannel:
    def test_ap_improve_moves_damage(self):
        # Sv3+ AP0：save 3+（过保 4/6）→ ap_improve 1 = AP-1 → save 4+（过保 3/6）
        # 未过保率 1/3 → 1/2，期望伤害 ×1.5
        eff = Effect("save", "ap_improve", (1,), ("phase_shooting",), "focused fire")
        base = _raw(_weapon(), _SHOOT, _target(sv=3)).damage.mean()
        on = _raw(_weapon(effects=[eff]), _SHOOT, _target(sv=3)).damage.mean()
        assert on / base == pytest.approx(1.5, abs=0.05)

    def test_ap_improve_condition_gates(self):
        # 近战阶段 phase_shooting 条件不放行 → 伤害不动
        eff = Effect("save", "ap_improve", (1,), ("phase_shooting",), "x")
        w_base = WeaponProfile(name_zh=None, name_en="fist", range="Melee",
                               attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                               damage=DiceExpr(k=1), effects=(), count=1)
        w_on = WeaponProfile(name_zh=None, name_en="fist", range="Melee",
                             attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                             damage=DiceExpr(k=1), effects=(eff,), count=1)
        st = Stance(phase="melee")
        assert (_raw(w_on, st, _target(sv=3)).damage.mean()
                == pytest.approx(_raw(w_base, st, _target(sv=3)).damage.mean(), rel=0.03))


class TestConditionalKeywordChannels:
    """P7-PR3：extra_hits / auto_wound / wound reroll 补 ok 门控——条件假不放行。"""

    def test_conditional_sustained_gated(self):
        eff = Effect("hit", "extra_hits", (DiceExpr(k=1),),
                     ("detachment_rounds_shooting",), "patient hunter")
        # 开关关：0.5；开关开：0.5 + 1/6
        assert _hit_ratio(_weapon(effects=[eff]), _SHOOT) == pytest.approx(0.5, abs=0.02)
        on = _hit_ratio(_weapon(effects=[eff]),
                        Stance(phase="shooting", detachment_rounds=True))
        assert on == pytest.approx(0.5 + 1 / 6, abs=0.02)

    def test_conditional_lethal_gated(self):
        eff = Effect("hit", "auto_wound", (), ("detachment_rounds_guided",), "killing blow")
        # S4 vs T4 致伤 4+：无 lethal wounds/attack = 0.5×0.5 = 0.25
        # lethal：暴击 1/6 自动致伤 + 普通命中 2/6×0.5 = 1/6+1/6 = 1/3
        off = _wound_per_attack(_weapon(effects=[eff]),
                                Stance(phase="shooting", detachment_rounds=True))
        assert off == pytest.approx(0.25, abs=0.02)   # 缺 guided 不放行
        on = _wound_per_attack(_weapon(effects=[eff]),
                               Stance(phase="shooting", detachment_rounds=True, guided=True))
        assert on == pytest.approx(1 / 3, abs=0.02)

    def test_conditional_wound_reroll_gated(self):
        eff = Effect("wound", "reroll", ("fail",), ("phase_shooting",), "debarkation")
        # S4 vs T4：wounds/attack = 0.5×0.5=0.25 → 重骰失败 0.5×0.75=0.375
        on = _wound_per_attack(_weapon(effects=[eff]), _SHOOT)
        assert on == pytest.approx(0.375, abs=0.02)
        w_melee = WeaponProfile(name_zh=None, name_en="fist", range="Melee",
                                attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                                damage=DiceExpr(k=1), effects=(eff,), count=1)
        off = _wound_per_attack(w_melee, Stance(phase="melee"))
        assert off == pytest.approx(0.25, abs=0.02)   # 近战不放行


class TestMarkerlightObserverTag:
    def test_ignores_cover_via_markerlight_self(self):
        # CTE 第二条款：本单位（观察员）带标记光 → [IGNORES COVER]，不要求 guided。
        # 掩体=BS 恶化 1（BS4+→5+ 命中 1/3）；ignores_cover 抵消回 0.5
        eff = Effect("save", "ignores_cover", (), ("markerlight_observer",), "cte")
        st_cover = Stance(phase="shooting", target_in_cover=True)
        assert _hit_ratio(_weapon(effects=[eff]), st_cover) == pytest.approx(1 / 3, abs=0.02)
        st_ml = Stance(phase="shooting", target_in_cover=True, markerlight_observer=True)
        assert _hit_ratio(_weapon(effects=[eff]), st_ml) == pytest.approx(0.5, abs=0.02)


# ── 选择层 ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


class TestSelectEntries:
    def test_army_rule_always_selected(self, entries):
        sel, _ = select_entries(list(entries))
        assert [e.row_id for e in sel] == ["000008439"]   # 只有军队级 FTGG

    def test_detachment_apostrophe_normalized(self, entries):
        # 用户输直撇号 Mont'ka，DB 拼写弯撇号 Mont’ka——必须匹配
        sel, _ = select_entries(list(entries), detachment="mont'ka")
        assert {e.row_id for e in sel} == {"000008439", "det000008810"}

    def test_stratagem_requires_naming(self, entries):
        # 战略不点名不入选（一次性 opt-in）
        sel, _ = select_entries(list(entries), detachment="Kauyon")
        assert all(e.table != "stratagems" for e in sel)

    def test_stratagem_by_zh_name(self, entries):
        sel, notes = select_entries(list(entries), stratagems=("集中火力",))
        assert any(e.row_id == "000008812004" for e in sel)
        assert any("假设" in x for x in notes)   # 未指定分队 → 假设披露

    def test_stratagem_detachment_mismatch_disclosed(self, entries):
        sel, notes = select_entries(list(entries), detachment="Kauyon",
                                    stratagems=("集中火力",))
        assert all(e.row_id != "000008812004" for e in sel)
        assert any("不符" in x for x in notes)

    def test_unknown_token_disclosed(self, entries):
        _, notes = select_entries(list(entries), stratagems=("不存在的战略",))
        assert any("无匹配" in x for x in notes)

    def test_wrong_detachment_rule_excluded(self, entries):
        sel, _ = select_entries(list(entries), detachment="Kauyon")
        assert all(e.row_id != "det000008810" for e in sel)


# ── 真源 payload 三态对账 ────────────────────────────────────────────────────

class TestPayloadReconciliation:
    def test_counts(self, entries):
        # 军规 1 + 分队规则 2 + 战略 12 = 15；三态：partial 9 / not_modeled 6 / encoded 0
        assert len(entries) == 15
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 9, "not_modeled": 6}

    def test_kauyon_montka_stratagems_all_present(self, entries):
        ids = {e.row_id for e in entries if e.table == "stratagems"}
        assert ids == {f"00000844300{i}" for i in range(2, 8)} | {
            f"00000881200{i}" for i in range(2, 8)}

    def test_counterfire_is_target_side_not_modeled(self, entries):
        cf = next(e for e in entries if e.row_id == "000008812007")
        assert cf.side == "target" and cf.status == "not_modeled" and not cf.effects
        assert any("inject_target" in n for n in cf.not_modeled_notes_zh)


# ── 真源 payload 引擎级差分（每条带效果条目期望值必须动，评审 F7）─────────────

def _inject(entries, row_id, toggles):
    entry = next(e for e in entries if e.row_id == row_id)
    atk, modeled, notes = inject_attacker(_attacker(_weapon()), [entry],
                                          frozenset(toggles))
    return atk, modeled, notes


class TestPatientHunter:
    def test_sustained_clause(self, entries):
        # 3-5轮远程 [SUSTAINED HITS 1]：hits/attacks 0.5 → 0.5+1/6
        atk, modeled, _ = _inject(entries, "det000008441", {"detachment_rounds"})
        assert any("已施加" in x for x in modeled)
        st = Stance(phase="shooting", detachment_rounds=True)
        raw = run_sequence(atk, _target(), st, n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(0.5 + 1 / 6, abs=0.02)

    def test_toggle_off_disclosed_no_change(self, entries):
        atk, modeled, notes = _inject(entries, "det000008441", set())
        assert not modeled and any("未启用" in x for x in notes)
        assert atk.loadout[0].effects == ()

    def test_ignore_mods_clause_needs_guided(self, entries):
        # 第二条款：受引导时可无视修正——掩体 BS 惩罚被清（0.5 恢复），不开 guided 不清
        atk, _, _ = _inject(entries, "det000008441", {"detachment_rounds"})
        st_cover = Stance(phase="shooting", detachment_rounds=True, target_in_cover=True)
        raw = run_sequence(atk, _target(), st_cover, n=N, seed=7)
        # 掩体 BS4+→5+：命中 1/3；sustained 额外命中按自然骰暴击（1/6，不吃 BS 恶化）
        # → 1/3 + 1/6 = 0.5（若掩体被错误无视会是 0.5+1/6=0.667，两值可区分）
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(0.5, abs=0.02)
        st_guided = Stance(phase="shooting", detachment_rounds=True,
                           target_in_cover=True, guided=True)
        raw2 = run_sequence(atk, _target(), st_guided, n=N, seed=7)
        assert raw2.hits.mean() / raw2.attacks.mean() == pytest.approx(0.5 + 1 / 6, abs=0.02)


class TestKillingBlow:
    def test_lethal_clause(self, entries):
        # 1-3轮受引导 [LETHAL HITS]：S4 vs T4 wounds/attack 0.25 → 1/3
        atk, _, _ = _inject(entries, "det000008810", {"detachment_rounds"})
        st = Stance(phase="shooting", detachment_rounds=True, guided=True)
        raw = run_sequence(atk, _target(), st, n=N, seed=7)
        assert raw.wounds.mean() / raw.attacks.mean() == pytest.approx(1 / 3, abs=0.02)

    def test_without_guided_no_lethal(self, entries):
        atk, _, _ = _inject(entries, "det000008810", {"detachment_rounds"})
        st = Stance(phase="shooting", detachment_rounds=True)
        raw = run_sequence(atk, _target(), st, n=N, seed=7)
        assert raw.wounds.mean() / raw.attacks.mean() == pytest.approx(0.25, abs=0.02)

    def test_assault_disclosed_not_modeled(self, entries):
        kb = next(e for e in entries if e.row_id == "det000008810")
        assert any("ASSAULT" in n for n in kb.not_modeled_notes_zh)


class TestStratagemEffects:
    def test_tempting_trap_wound_plus_one(self, entries):
        # +1 致伤：S4 vs T4 致伤 4+ → 实效 3+，wounds/attack 0.25 → 0.5×(4/6)=1/3
        atk, _, _ = _inject(entries, "000008443002", set())
        raw = run_sequence(atk, _target(), _SHOOT, n=N, seed=7)
        assert raw.wounds.mean() / raw.attacks.mean() == pytest.approx(1 / 3, abs=0.02)

    def test_point_blank_ambush_ap(self, entries):
        # AP 改善 1：Sv3+ 过保 4/6→3/6，期望伤害 ×1.5
        base = _raw(_weapon(), _SHOOT, _target(sv=3)).damage.mean()
        atk, _, _ = _inject(entries, "000008443003", set())
        raw = run_sequence(atk, _target(sv=3), _SHOOT, n=N, seed=7)
        assert raw.damage.mean() / base == pytest.approx(1.5, abs=0.05)

    def test_focused_fire_ap(self, entries):
        base = _raw(_weapon(), _SHOOT, _target(sv=3)).damage.mean()
        atk, _, _ = _inject(entries, "000008812004", set())
        raw = run_sequence(atk, _target(sv=3), _SHOOT, n=N, seed=7)
        assert raw.damage.mean() / base == pytest.approx(1.5, abs=0.05)

    def test_coordinate_to_engage(self, entries):
        # BS 特征值改善 1：BS4+→3+（4/6）；掩体场景 + 标记光 → [IGNORES COVER] 抵消
        atk, _, _ = _inject(entries, "000008443004", set())
        raw = run_sequence(atk, _target(), _SHOOT, n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(4 / 6, abs=0.02)
        st_cover = Stance(phase="shooting", target_in_cover=True)
        raw2 = run_sequence(atk, _target(), st_cover, n=N, seed=7)
        assert raw2.hits.mean() / raw2.attacks.mean() == pytest.approx(0.5, abs=0.02)
        st_ml = Stance(phase="shooting", target_in_cover=True, markerlight_observer=True)
        raw3 = run_sequence(atk, _target(), st_ml, n=N, seed=7)
        assert raw3.hits.mean() / raw3.attacks.mean() == pytest.approx(4 / 6, abs=0.02)

    def test_pinpoint_counter_offensive(self, entries):
        # 命中重骰失败：0.5 → 0.75（近战同样生效——条件为空）
        atk, _, _ = _inject(entries, "000008812002", set())
        raw = run_sequence(atk, _target(), _SHOOT, n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(0.75, abs=0.02)

    def test_combat_debarkation_wound_reroll(self, entries):
        # 致伤重骰失败：wounds/attack 0.25 → 0.375
        atk, _, _ = _inject(entries, "000008812005", set())
        raw = run_sequence(atk, _target(), _SHOOT, n=N, seed=7)
        assert raw.wounds.mean() / raw.attacks.mean() == pytest.approx(0.375, abs=0.02)
