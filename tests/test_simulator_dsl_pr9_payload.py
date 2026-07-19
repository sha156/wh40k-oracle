# tests/test_simulator_dsl_pr9_payload.py
"""P7-PR9 圣血天使编码落账：8 分队规则物化 + 39 战略 + 26 增强 = 73。

覆盖（spec 七-1 双验范式）：
  · DB 对账：BA 8 分队清单圈定的全部活跃行有 payload 条目（BT 子阵营口径）；
    指纹全对
  · 真源 payload 引擎级差分：猩红饥渴（冲锋 A+1/S+2）/ 蔑视甲胄（守方 AP 恶化）/
    无觉暴走 FNP5+ / 天使优雅光环 5++ / 天使之牙对人物连击 2 / 炫目复仇隐匿
    各至少一条
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
PAYLOAD = Path("dsl_payloads/bloodangels.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

BA_DETS = ("Liberator Assault Group", "The Lost Brethren", "The Angelic Host",
           "Angelic Inheritors", "Rage-cursed Onslaught", "Legacy of Grace",
           "Encarmine Speartip", "Wrath of the Doomed")
BA_DET_RULE_IDS = ("000008374", "000009185", "000009189", "000009834",
                   "000010644", "fp11e-ba-grace-det", "fp11e-ba-speartip-det",
                   "fp11e-ba-doomed-det")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, effects=()):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _gun(bs=4, s=4, ap=0, damage=1):
    return WeaponProfile(name_zh=None, name_en="gun", range='24"',
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=s, ap=ap,
                         damage=DiceExpr(k=damage), effects=(), count=1)


def _attacker(*weapons):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=tuple(weapons))


def _target(t=4, sv=7, models=5, w=1, invuln=None, keywords=frozenset(),
            effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=w, oc=1,
                         keywords=keywords, effects=tuple(effects))


def _entry(entries, row_id):
    return next(e for e in entries if e.row_id == row_id)


def _run(atk, target, stance):
    return run_sequence(atk, target, stance, n=N, seed=42)


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


class TestPayloadShape:
    def test_counts(self, entries):
        # 8 分队规则物化 + 39 战略 + 26 增强 = 73（28 partial / 45 not_modeled）
        assert len(entries) == 73
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 28, "not_modeled": 45}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_ba_stratagems_all_covered(self, entries):
        con = self._db()
        ph = ",".join("?" for _ in BA_DETS)
        active = {r[0] for r in con.execute(
            f"SELECT id FROM stratagems WHERE detachment IN ({ph}) "
            "AND COALESCE(fp_status, '') != 'removed_11e'", BA_DETS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_ba_enhancements_all_covered(self, entries):
        con = self._db()
        ph = ",".join("?" for _ in BA_DETS)
        active = {r[0] for r in con.execute(
            f"SELECT id FROM enhancements WHERE detachment_name IN ({ph}) "
            "AND COALESCE(fp_status, '') != 'removed_11e'", BA_DETS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_ba_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in BA_DET_RULE_IDS}

    def test_fingerprints_match_db(self, entries):
        from db_compile.dsl_apply import _fingerprint
        cols = {"stratagems": "text_zh", "enhancements": "description"}
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
    def test_red_thirst_charging_only(self, entries):
        # 猩红饥渴：冲锋回合近战 A+1 & S+2。S4→S6 vs T5：致伤 5+(1/3)→3+(2/3)；
        # 攻击数 1→2；非冲锋回合不生效
        rt = _entry(entries, "det000008374")
        atk, _, _ = inject_attacker(_attacker(_melee()), [rt], frozenset())
        chg = _run(atk, _target(t=5), Stance(phase="melee", charging=True))
        no_chg = _run(atk, _target(t=5), Stance(phase="melee"))
        assert chg.attacks.mean() == pytest.approx(2.0, abs=0.05)
        assert _ratio(chg.wounds, chg.hits) == pytest.approx(2 / 3, abs=0.02)
        assert no_chg.attacks.mean() == pytest.approx(1.0, abs=0.05)
        assert _ratio(no_chg.wounds, no_chg.hits) == pytest.approx(1 / 3,
                                                                   abs=0.02)

    def test_martial_paragon_sustained_both_phases(self, entries):
        # 武艺宗师（连击分支）：WS4+ 命中率 1/2 → 1/2 + 1/6（暴击追加 1）= 2/3
        mp = _entry(entries, "fp11e-ba-grace-s1")
        atk, _, _ = inject_attacker(_attacker(_melee()), [mp], frozenset())
        r = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_angels_fang_sustained_vs_character_only(self, entries):
        # 天使之牙：近战对人物 [SUSTAINED HITS 2]：1/2 + 2/6 = 5/6；对无关键词 1/2
        af = _entry(entries, "000010645005")
        atk, _, _ = inject_attacker(_attacker(_melee()), [af],
                                    frozenset({"bearer_leading"}))
        vs_char = _run(atk, _target(keywords=frozenset({"character"})),
                       Stance(phase="melee"))
        vs_line = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(vs_char.hits, vs_char.attacks) == pytest.approx(5 / 6,
                                                                      abs=0.02)
        assert _ratio(vs_line.hits, vs_line.attacks) == pytest.approx(1 / 2,
                                                                      abs=0.02)

    def test_archangels_shard_lance_when_charging(self, entries):
        # 大天使碎片 [LANCE] 分量：冲锋近战致伤 +1（S4 vs T4：4+→3+）
        shard = _entry(entries, "000009190004")
        atk, _, _ = inject_attacker(_attacker(_melee()), [shard],
                                    frozenset({"bearer_leading"}))
        chg = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        no_chg = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(chg.wounds, chg.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(no_chg.wounds, no_chg.hits) == pytest.approx(1 / 2,
                                                                   abs=0.02)


class TestDefensiveFromPayload:
    def test_armour_of_contempt_ap_worsen(self, entries):
        # 蔑视甲胄：AP-1 武器打 Sv4（5+ 保，unsaved 2/3）→ 恶化成 AP0（4+，1/2）
        aoc = _entry(entries, "000008375003")
        tgt, _, _ = inject_target(_target(sv=4), [aoc], frozenset())
        r = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_insensate_rampage_fnp5(self, entries):
        # 无觉暴走：FNP 5+ → 伤害通过率 2/3
        ir = _entry(entries, "000010646004")
        tgt, _, _ = inject_target(_target(sv=7), [ir], frozenset())
        base = _run(_attacker(_melee()), _target(sv=7), Stance(phase="melee"))
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(2 / 3,
                                                                     abs=0.03)

    def test_aura_of_angels_grace_invuln_shooting_only(self, entries):
        # 天使优雅光环：AP-3 打 Sv4（护甲 7+ 不可能）→ 射击 5++（unsaved 2/3）；
        # 近战不生效（unsaved 1）
        aura = _entry(entries, "fp11e-ba-grace-s3")
        tgt, _, _ = inject_target(_target(sv=4), [aura], frozenset())
        shoot = _run(_attacker(_gun(ap=-3)), tgt, Stance(phase="shooting"))
        melee = _run(_attacker(_melee(ap=-3)), tgt, Stance(phase="melee"))
        assert _ratio(shoot.unsaved, shoot.wounds) == pytest.approx(2 / 3,
                                                                    abs=0.02)
        assert _ratio(melee.unsaved, melee.wounds) == pytest.approx(1.0,
                                                                    abs=0.01)

    def test_blinding_blurs_stealth_cover(self, entries):
        # 炫目复仇：隐匿=掩体收益（BS 恶化 1）：BS3+（2/3）→ 4+（1/2）；近战不受影响
        bb = _entry(entries, "fp11e-ba-speartip-s3")
        tgt, _, _ = inject_target(_target(), [bb], frozenset())
        shoot = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(shoot.hits, shoot.attacks) == pytest.approx(1 / 2,
                                                                  abs=0.02)


@needs_db
class TestRealUnitSmoke:
    def test_sanguinary_guard_loads_ba_entries(self):
        from engines.simulator.profile import load_unit_dsl
        entries = load_unit_dsl(str(DB), "000000165")   # Sanguinary Guard
        ids = {e.row_id for e in entries}
        assert "det000008374" in ids             # 物化分队规则（猩红饥渴）
        assert "fp11e-ba-speartip-s3" in ids     # 补录战略（炫目复仇）
        assert "000010645005" in ids             # 增强（天使之牙）
