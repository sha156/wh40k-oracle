# tests/test_simulator_dsl_pr7_payload.py
"""P7-PR7 帝皇之子编码落账：1 军规 + 12 分队规则物化 + 55 战略 + 36 增强 = 104。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='EC' 全部活跃行有 payload 条目（含库内 Sublime Strike）；
    指纹全对
  · 真源 payload 引擎级差分：守方 AP 恶化 / 近战×S>T / 加速撤退门 /
    傲然凌人对 CHARACTER 重骰 各至少一条
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
PAYLOAD = Path("dsl_payloads/emperorschildren.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, effects=()):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
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


class TestPayloadShape:
    def test_counts(self, entries):
        # 1 军规 + 12 分队规则 + 55 战略 + 36 增强 = 104（0 encoded）
        assert len(entries) == 104
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 37, "not_modeled": 67}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_ec_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='EC' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_ec_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='EC' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_ec_detachments_materialized(self, entries):
        con = self._db()
        dets = {r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='EC'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "abilities"
                   and e.row_id.startswith("det")}
        assert covered == {f"det{d}" for d in dets}   # 12（9 存量 + 3 fp_new）

    def test_fingerprints_match_db(self, entries):
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


class TestAttackerFromPayload:
    def test_prideful_superiority_rerolls_vs_character(self, entries):
        # 傲然凌人：近战对 CHARACTER 命中+致伤全重骰。
        # WS4+ S4vsT4：hits/attacks 1/2→3/4；wounds/hits 1/2→3/4（重骰失败）；
        # 对非人物目标不生效（1/2）
        ps = _entry(entries, "000010655003")
        atk, _, _ = inject_attacker(_attacker(_melee()), [ps], frozenset())
        vs_char = _run(atk, _target(sv=7, keywords=frozenset({"character"})),
                       Stance(phase="melee"))
        vs_line = _run(atk, _target(sv=7), Stance(phase="melee"))
        assert _ratio(vs_char.hits, vs_char.attacks) == pytest.approx(3 / 4,
                                                                      abs=0.02)
        assert _ratio(vs_char.wounds, vs_char.hits) == pytest.approx(3 / 4,
                                                                     abs=0.02)
        assert _ratio(vs_line.hits, vs_line.attacks) == pytest.approx(1 / 2,
                                                                      abs=0.02)

    def test_frantic_focus_needs_toggle(self, entries):
        # 狂乱专注：开关关 → 不注入并披露；开 → S4→S5 vs T5（1/3→1/2）
        ff = _entry(entries, "detfp11e-ec-host-det")
        atk_off, _, notes = inject_attacker(_attacker(_melee()), [ff],
                                            frozenset())
        assert any("advanced_or_fell_back" in n for n in notes)
        atk_on, _, _ = inject_attacker(_attacker(_melee()), [ff],
                                       frozenset({"advanced_or_fell_back"}))
        off = _run(atk_off, _target(t=5, sv=7), Stance(phase="melee"))
        on = _run(atk_on, _target(t=5, sv=7), Stance(phase="melee"))
        assert _ratio(off.wounds, off.hits) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(on.wounds, on.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_sensational_performance_charging_only(self, entries):
        # 惊艳献演：冲锋回合近战 S+1 & AP 改善 1。S4→S5 vs T5：1/3→1/2；
        # 非冲锋回合不生效
        sp = _entry(entries, "det000010652")
        atk, _, _ = inject_attacker(_attacker(_melee()), [sp], frozenset())
        chg = _run(atk, _target(t=5, sv=7),
                   Stance(phase="melee", charging=True))
        no_chg = _run(atk, _target(t=5, sv=7), Stance(phase="melee"))
        assert _ratio(chg.wounds, chg.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(no_chg.wounds, no_chg.hits) == pytest.approx(1 / 3,
                                                                   abs=0.02)


class TestDefensiveFromPayload:
    def test_armour_of_abhorrence_ap_worsen(self, entries):
        # 恶孽甲胄：AP-1 打 Sv4（5+ 保，unsaved 2/3）→ 恶化成 AP0（4+ 保，1/2）
        aa = _entry(entries, "000010015007")
        tgt, _, _ = inject_target(_target(sv=4), [aa], frozenset())
        r = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_intoxicating_musk_melee_only_s_gt_t(self, entries):
        # 迷魂麝香：近战 S5vsT4 被伤 3+→4+；射击不受影响
        musk = _entry(entries, "000009998003")
        tgt, _, _ = inject_target(_target(t=4, sv=7), [musk],
                                  frozenset({"defender_bearer_leading"}))
        melee = _run(_attacker(_melee(s=5)), tgt, Stance(phase="melee"))
        gun = WeaponProfile(name_zh=None, name_en="gun", range='24"',
                            attacks=DiceExpr(k=1), bs_ws=4, strength=5, ap=0,
                            damage=DiceExpr(k=1), effects=(), count=1)
        shoot = _run(_attacker(gun), tgt, Stance(phase="shooting"))
        assert _ratio(melee.wounds, melee.hits) == pytest.approx(1 / 2,
                                                                 abs=0.02)
        assert _ratio(shoot.wounds, shoot.hits) == pytest.approx(2 / 3,
                                                                 abs=0.02)

    def test_protection_of_dark_prince_fnp6(self, entries):
        # 黑暗王子庇佑：FNP 6+ → 伤害通过率 5/6
        pp = _entry(entries, "000010015002")
        tgt, _, _ = inject_target(_target(sv=7), [pp], frozenset())
        base = _run(_attacker(_melee()), _target(sv=7), Stance(phase="melee"))
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(5 / 6,
                                                                     abs=0.03)


@needs_db
class TestRealUnitSmoke:
    def test_flawless_blades_loads_ec_entries(self):
        from engines.simulator.profile import load_unit_dsl
        entries = load_unit_dsl(str(DB), "000004089")   # Flawless Blades
        ids = {e.row_id for e in entries}
        assert "000009994" in ids                # 军规
        assert "fp11e-ec-spectacle-s1" in ids    # 补录战略
        assert "det000010652" in ids             # 物化分队规则
        assert "000010654005" in ids             # Court 增强（Spiritsliver）
