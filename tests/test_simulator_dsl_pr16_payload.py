# tests/test_simulator_dsl_pr16_payload.py
"""P7-PR16 灰骑士（Grey Knights）编码落账：11 分队规则物化 + 53 战略 + 34 增强 = 98。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='GK' 全部活跃 stratagems/enhancements 有 payload 条目、
    11 分队规则全物化（含 3 全新 FP 分队）；指纹全对
  · 三态计数：encoded 14 / partial 10 / not_modeled 74（灵能/传送阵营可编率中等）
  · 真源 payload 引擎级差分：战场巨人近战 A+1 / 圣裁收割者近战 A+3 /
    戴摩斯恩赐远程 S+2 / 彼界之刃 [LANCE]（冲锋致伤+1）/ 聚焦焚烧 [SUSTAINED] /
    湮灭级目标对 MONSTER 致伤+1 / 灵能弹药 storm bolter AP 改善（weapon_filter）/
    装甲庇护守方 FNP4 / 预警闪避守方命中-1 / 训诫之盾守方近战命中-1 /
    永恒庇护守方 4++ 仅射击 / 深渊药瓶守方掩体仅射击
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
PAYLOAD = Path("dsl_payloads/greyknights.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

GK_DET_RULE_IDS = ("000009484", "000009492", "000009776", "000010347",
                   "000010351", "000010355", "000010359", "000010363",
                   "fp11e-gk-argent", "fp11e-gk-fires", "fp11e-gk-immaterial")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, name="nemesis force sword"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, damage=1, name="storm bolter"):
    return WeaponProfile(name_zh=None, name_en=name, range='24"',
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
        # 11 分队规则物化 + 53 战略 + 34 增强 = 98（14 encoded / 10 partial / 74 not_modeled）
        assert len(entries) == 98
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 14, "partial": 10, "not_modeled": 74}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id

    def test_encoded_entries_have_fingerprint(self, entries):
        for e in entries:
            if e.status == "encoded":
                assert e.effects and e.provenance.get("text_sha256"), e.row_id

    def test_not_modeled_have_reason(self, entries):
        for e in entries:
            if e.status == "not_modeled":
                assert not e.effects and e.not_modeled_notes_zh, e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_gk_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='GK' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_gk_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='GK' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_gk_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in GK_DET_RULE_IDS}

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
    def test_giants_of_the_battlefield_attacks(self, entries):
        # 战场巨人：终结者近战武器 A+1。1→2
        g = _entry(entries, "000010353002")
        atk, _, _ = inject_attacker(_attacker(_melee()), [g], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2.0, abs=0.05)

    def test_sanctic_reaper_attacks(self, entries):
        # 圣裁收割者：携带者近战武器 A+3。1→4
        sr = _entry(entries, "000010352004")
        atk, _, _ = inject_attacker(_attacker(_melee()), [sr], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(4.0, abs=0.05)

    def test_boons_of_deimos_ranged_strength(self, entries):
        # 戴摩斯恩赐：PURGATION 远程 +2 S。S4 vs T6（5+，1/3）→ S6（4+，1/2）
        bd = _entry(entries, "fp11e-gk-fires-e2")
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [bd], frozenset())
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)
        # 战斗阶段不生效（phase_shooting 门；近战武器 S 不变）
        rm = _run(_attacker(_melee(s=4)), _target(t=6), Stance(phase="melee"))
        atkm, _, _ = inject_attacker(_attacker(_melee(s=4)), [bd], frozenset())
        rm2 = _run(atkm, _target(t=6), Stance(phase="melee"))
        assert _ratio(rm2.wounds, rm2.hits) == pytest.approx(
            _ratio(rm.wounds, rm.hits), abs=0.02)

    def test_blades_from_beyond_lance_charge_only(self, entries):
        # 彼界之刃 [LANCE]：冲锋回合近战致伤+1。S4 vs T4 4+（1/2）冲锋→3+（2/3）
        bb = _entry(entries, "fp11e-gk-immaterial-s1")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [bb], frozenset())
        chg = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        noc = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(chg.wounds, chg.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(noc.wounds, noc.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_focused_immolation_sustained_shooting(self, entries):
        # 聚焦焚烧 [SUSTAINED HITS 1]：BS4（1/2）暴击6（1/6）→ hits/attacks≈2/3
        fi = _entry(entries, "fp11e-gk-fires-s2")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [fi], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_abominus_wound_vs_monster(self, entries):
        # 湮灭级目标：对 MONSTER/VEHICLE 致伤+1。S4 vs T4 4+（1/2）→ 对 MONSTER 3+（2/3）
        ab = _entry(entries, "000010361003")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ab], frozenset())
        mon = _run(atk, _target(t=4, keywords=frozenset({"monster"})),
                   Stance(phase="melee"))
        plain = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(mon.wounds, mon.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(plain.wounds, plain.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_psybolt_storm_bolter_ap_weapon_filter(self, entries):
        # 灵能弹药：仅 storm bolter AP 改善1。AP0 打 Sv4（4+，1/2 失败）→ AP-1（5+，2/3）
        pb = _entry(entries, "000009494005")
        atk, _, _ = inject_attacker(_attacker(_gun(ap=0, name="storm bolter")),
                                    [pb], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        # 非 storm bolter 武器不受影响（weapon_filter 未命中→显式披露）
        atk2, _, nm = inject_attacker(_attacker(_gun(ap=0, name="psilencer")),
                                      [pb], frozenset())
        r2 = _run(atk2, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r2.unsaved, r2.wounds) == pytest.approx(1 / 2, abs=0.02)
        assert any("storm bolter" in m for m in nm)


class TestDefensiveFromPayload:
    def test_armoured_aegis_fnp4(self, entries):
        # 装甲庇护：CHARACTER FNP 4+ → 伤害通过 1/2
        aa = _entry(entries, "000009494002")
        tgt, _, _ = inject_target(_target(sv=7), [aa], frozenset())
        base = _run(_attacker(_melee()), _target(sv=7), Stance(phase="melee"))
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(1 / 2, abs=0.03)

    def test_forewarned_evasion_hit_minus_one_both_phases(self, entries):
        # 预警闪避：针对本单位攻击命中-1（射击+战斗）。WS/BS4（1/2）→ 5+（1/3）
        fe = _entry(entries, "000010365004")
        tgt, _, _ = inject_target(_target(t=4), [fe], frozenset())
        melee = _run(_attacker(_melee(ws=4)), tgt, Stance(phase="melee"))
        shoot = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(melee.hits, melee.attacks) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(shoot.hits, shoot.attacks) == pytest.approx(1 / 3, abs=0.02)

    def test_shield_of_admonishment_melee_only(self, entries):
        # 训诫之盾：针对携带者的近战攻击命中-1；射击不生效
        sa = _entry(entries, "000009493002")
        tgt, _, _ = inject_target(_target(t=4), [sa], frozenset())
        melee = _run(_attacker(_melee(ws=4)), tgt, Stance(phase="melee"))
        shoot = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(melee.hits, melee.attacks) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(shoot.hits, shoot.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_aegis_eternal_invuln_shooting_only(self, entries):
        # 永恒庇护：4++ 仅对方射击阶段。AP-3 打 Sv2/无 invuln（5+，1/3 存）→ 4++（1/2 存）
        ae = _entry(entries, "000009778006")
        tgt, _, _ = inject_target(_target(sv=2, invuln=None), [ae], frozenset())
        shoot = _run(_attacker(_gun(ap=-3)), tgt, Stance(phase="shooting"))
        # 4++ 生效：失败保存 1/2（弱于 AP-3 后的 5+ 甲 1/3 通过→即 2/3 失败）
        assert _ratio(shoot.unsaved, shoot.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 近战阶段 invuln 不注入（phase_shooting 门）→ 仍走 AP-3 后的护甲 5+
        melee = _run(_attacker(_melee(ap=-3)), tgt, Stance(phase="melee"))
        assert _ratio(melee.unsaved, melee.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_phial_of_the_abyss_cover_shooting(self, entries):
        # 深渊药瓶：Stealth（掩体）仅射击 → BS4 掩体命中-1（1/2→1/3）
        ph = _entry(entries, "000009777004")
        tgt, _, _ = inject_target(_target(t=4), [ph], frozenset())
        shoot = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(shoot.hits, shoot.attacks) == pytest.approx(1 / 3, abs=0.02)
