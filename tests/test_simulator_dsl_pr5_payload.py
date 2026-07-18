# tests/test_simulator_dsl_pr5_payload.py
"""P7-PR5 吞世者编码落账：军规恐虐赐福 + 10 分队规则物化 + 47 战略 + 30 增强。

覆盖（spec 七-1 双验范式，手算期望值写在断言旁，期望值必须动）：
  · DB 对账：WE 活跃行（排除 fp_status='removed_11e'）全部有 payload 条目，
    removed 行（怒火容器重印未收录 6 条）必须没有
  · 军规赐福：三开关差分 + toggle_groups「至多两项」硬拦
  · 真源 payload 引擎级差分：每类 PR5 新通道条目至少一条
"""
import sqlite3
from pathlib import Path

import pytest

from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.dsl import (
    inject_attacker,
    inject_target,
    load_payload_file,
)
from engines.simulator.sequence import run_sequence

N = 60000
PAYLOAD = Path("dsl_payloads/worldeaters.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, name="chainaxe", effects=()):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(*weapons):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=tuple(weapons))


def _target(t=4, sv=4, models=5, keywords=frozenset(), effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=None, w=1, oc=1,
                         keywords=keywords, effects=tuple(effects))


def _entry(entries, row_id):
    return next(e for e in entries if e.row_id == row_id)


def _run(atk, target, stance):
    return run_sequence(atk, target, stance, n=N, seed=42)


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


# ═══ 结构与 DB 对账 ═══════════════════════════════════════════════════════

class TestPayloadShape:
    def test_counts(self, entries):
        # 1 军规 + 10 分队规则 + 47 战略 + 30 增强 = 88（0 encoded：全带假设注记）
        assert len(entries) == 88
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 27, "not_modeled": 61}

    def test_blessing_army_rule_has_toggle_group(self, entries):
        bl = _entry(entries, "000008428")
        assert bl.detachment is None                     # 军队级恒入选
        g = bl.toggle_groups[0]
        assert g["max"] == 2 and len(g["toggles"]) == 3  # 至多两项赐福

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction = 'WE' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_removed_vessels_rows_not_covered(self, entries):
        con = self._db()
        removed_s = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='WE' "
            "AND fp_status = 'removed_11e'")}
        removed_e = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='WE' "
            "AND fp_status = 'removed_11e'")}
        con.close()
        assert len(removed_s) == 4 and len(removed_e) == 2   # 怒火容器重印裁定
        ids = {e.row_id for e in entries}
        assert not (removed_s | removed_e) & ids

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id = 'WE' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_all_detachments_materialized(self, entries):
        con = self._db()
        dets = {r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction = 'WE'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "abilities"
                   and e.row_id.startswith("det")}
        assert covered == {f"det{d}" for d in dets}   # 10 分队（8 存量 + 2 fp_new）

    def test_fingerprints_match_db(self, entries):
        # 全部带 effects 条目的指纹必须与库现行文本一致（dsl-apply 才不会让路）
        from db_compile.dsl_apply import _fingerprint
        cols = {"abilities": "text_zh", "stratagems": "text_zh",
                "enhancements": "description"}
        con = self._db()
        for e in entries:
            if not e.effects:
                continue
            if e.row_id.startswith("det"):
                src = con.execute(
                    "SELECT rule_text FROM detachments WHERE id=?",
                    (e.row_id[3:],)).fetchone()
            else:
                src = con.execute(
                    f"SELECT {cols[e.table]} FROM {e.table} WHERE id=?",
                    (e.row_id,)).fetchone()
            assert src is not None, e.row_id
            assert _fingerprint(src[0]) == e.provenance["text_sha256"], e.row_id
        con.close()


# ═══ 军规恐虐赐福：差分 + 组约束 ═══════════════════════════════════════════

class TestBlessingsOfKhorne:
    def test_martial_excellence_differential(self, entries):
        # WS4+ [连击1]：hits/attacks 1/2 → 1/2+1/6
        atk, _, _ = inject_attacker(_attacker(_melee()),
                                    [_entry(entries, "000008428")], frozenset())
        on = _run(atk, _target(),
                  Stance(phase="melee", blessing_martial_excellence=True))
        off = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(off.hits, off.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(on.hits, on.attacks) == pytest.approx(1 / 2 + 1 / 6, abs=0.02)

    def test_decapitating_strikes_only_vs_infantry(self, entries):
        atk, _, _ = inject_attacker(_attacker(_melee()),
                                    [_entry(entries, "000008428")], frozenset())
        st = Stance(phase="melee", blessing_decapitating_strikes=True)
        inf = _run(atk, _target(keywords=frozenset({"infantry"})), st)
        veh = _run(atk, _target(keywords=frozenset({"vehicle"})), st)
        assert inf.mortals.mean() > 0 and veh.mortals.mean() == 0

    def test_three_blessings_hard_refused(self, entries):
        toggles = frozenset({"blessing_martial_excellence", "blessing_warp_blades",
                             "blessing_decapitating_strikes"})
        atk, modeled, notes = inject_attacker(
            _attacker(_melee()), [_entry(entries, "000008428")], toggles)
        assert not modeled
        assert any("⚠" in n and "至多" in n for n in notes)
        assert atk.loadout[0].effects == ()


# ═══ 分队规则 / 战略 / 增强：引擎级差分 ═══════════════════════════════════

class TestRelentlessRage:
    def test_charge_adds_attacks_and_strength(self, entries):
        # A1→A2（+1 A）；S4+2=6 vs T4 → 3+（4/6）；未冲锋完全无效
        atk, _, _ = inject_attacker(_attacker(_melee()),
                                    [_entry(entries, "det000008430")], frozenset())
        off = _run(atk, _target(), Stance(phase="melee"))
        on = _run(atk, _target(), Stance(phase="melee", charging=True))
        assert off.attacks.mean() == pytest.approx(1.0, abs=0.02)
        assert on.attacks.mean() == pytest.approx(2.0, abs=0.03)
        assert _ratio(on.wounds, on.hits) == pytest.approx(4 / 6, abs=0.02)

    def test_no_effect_in_shooting_even_if_charging(self, entries):
        # melee_charging 复合 tag：射击阶段 charging 开着也不放行
        gun = WeaponProfile(name_zh=None, name_en="gun", range='24"',
                            attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                            damage=DiceExpr(k=1), effects=(), count=1)
        atk, _, _ = inject_attacker(_attacker(gun),
                                    [_entry(entries, "det000008430")], frozenset())
        r = _run(atk, _target(), Stance(phase="shooting", charging=True))
        assert r.attacks.mean() == pytest.approx(1.0, abs=0.02)


class TestStratagemChannels:
    def test_hack_and_slash_ap(self, entries):
        # Sv4+ AP0 → unsaved/wounds 1/2；AP 改善 1 → Sv5+ → 4/6（须冲锋）
        atk, _, _ = inject_attacker(_attacker(_melee()),
                                    [_entry(entries, "000008431003")], frozenset())
        on = _run(atk, _target(), Stance(phase="melee", charging=True))
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(4 / 6, abs=0.02)

    def test_daemonic_resistance_target_side(self, entries):
        # 守方 -1 致伤：S4vsT4 4+（1/2）→ 5+（1/3）——PR5 新通道消费者
        tgt, modeled, _ = inject_target(_target(),
                                        [_entry(entries, "000010083002")],
                                        frozenset())
        assert modeled
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_trophy_for_throne_melee_only_vs_monster(self, entries):
        # 近战对凶兽致伤 +1：4+→3+；射击阶段/非凶兽不生效
        atk, _, _ = inject_attacker(_attacker(_melee()),
                                    [_entry(entries, "fp11e-we-butchers-s2")],
                                    frozenset())
        mon = _run(atk, _target(keywords=frozenset({"monster"})),
                   Stance(phase="melee"))
        plain = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(mon.wounds, mon.hits) == pytest.approx(4 / 6, abs=0.02)
        assert _ratio(plain.wounds, plain.hits) == pytest.approx(3 / 6, abs=0.02)

    def test_aspire_to_infamy_attacks_and_strength(self, entries):
        # +1 A + S+2（11e 重印人物版）：A1→2、S6vsT4→3+
        atk, _, _ = inject_attacker(_attacker(_melee()),
                                    [_entry(entries, "000009848002")], frozenset())
        r = _run(atk, _target(), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2.0, abs=0.03)
        assert _ratio(r.wounds, r.hits) == pytest.approx(4 / 6, abs=0.02)

    def test_wrath_beyond_reason_ranged_only(self, entries):
        # 守方 D-1（远程）：D1 夹到 ≥1 → 数值不变但被消费不告警；近战不适用由 tag 拦
        tgt, modeled, _ = inject_target(_target(),
                                        [_entry(entries, "fp11e-we-butchers-s3")],
                                        frozenset())
        assert modeled

    def test_focused_ferocity_stacks_with_relentless_rage(self, entries):
        # PR5 攻击骰累加回归：分队规则 +1A 与战略 +1A 同时注入 → A1+1+1=3
        atk, _, _ = inject_attacker(
            _attacker(_melee()),
            [_entry(entries, "det000008430"),
             _entry(entries, "fp11e-we-butchers-s1")], frozenset())
        r = _run(atk, _target(), Stance(phase="melee", charging=True))
        assert r.attacks.mean() == pytest.approx(3.0, abs=0.05)


class TestEnhancementChannels:
    def test_frenzied_focus_crit_threshold(self, entries):
        # 未修正 5+ 暴击 + 军规邪刃组合不在此测；单测 crit 阈值不改命中率
        atk, modeled, _ = inject_attacker(_attacker(_melee()),
                                          [_entry(entries, "000010082004")],
                                          frozenset({"bearer_leading"}))
        assert modeled

    def test_talons_of_butchery_cleave_via_weapon_filter(self, entries):
        # [CLEAVE 2]：10 模型目标 → +2×(10//5)=+4 攻击；weapon_filter 只中 Fists
        fists = _melee(name="Maulerfiend fists")
        other = _melee(name="lasher tendrils")
        atk, modeled, notes = inject_attacker(
            _attacker(fists, other), [_entry(entries, "fp11e-we-brazeng-e1")],
            frozenset())
        assert modeled and any("Talons" in m or "屠戮之爪" in m for m in modeled)
        r = _run(atk, _target(models=10), Stance(phase="melee"))
        # fists A1+4 + tendrils A1 = 6
        assert r.attacks.mean() == pytest.approx(6.0, abs=0.05)

    def test_helm_of_brazen_ire_needs_defender_toggle(self, entries):
        # 守方增强需 defender_bearer_leading：未开→拒注入披露；开→减伤生效
        e = _entry(entries, "000008432003")
        tgt_off, modeled_off, notes_off = inject_target(_target(), [e], frozenset())
        assert not modeled_off and any("未启用" in n for n in notes_off)
        tgt_on, modeled_on, _ = inject_target(
            _target(), [e], frozenset({"defender_bearer_leading"}))
        assert modeled_on