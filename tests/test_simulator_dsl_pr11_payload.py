# tests/test_simulator_dsl_pr11_payload.py
"""P7-PR11 卡斯托迪斯编码落账：11 分队规则物化 + 53 战略 + 34 增强 = 98。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='AC' 全部活跃 stratagems/enhancements 有 payload 条目、
    11 分队规则全物化；指纹全对
  · 三态计数：encoded 15 / partial 16 / not_modeled 67（精英近战阵营高可编率）
  · 真源 payload 引擎级差分：无瑕造物守方 S>T 被伤-1（wound_s_gt_t）/ 坚毅决心
    +1T（t_improve）/ 帝皇的处刑者对低于满编敌 +1 致伤（target_below_starting）/
    死歌之镰 LANCE+对 PSYKER +1A / 暗影追诉 boltgun RAPID FIRE+AP / 湮灭骑士
    +1 命中+对 PSYKER +1 致伤 / 聚焦恐惧守方 AP 恶化 各至少一条
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
PAYLOAD = Path("dsl_payloads/custodes.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

AC_DET_RULE_IDS = ("000008393", "000008920", "000008924", "000008929",
                   "000009263", "000009272", "000009752", "000009986",
                   "fp11e-ac-moritoi", "fp11e-ac-silent", "fp11e-ac-tharanatoi")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, damage=1, name="boltgun"):
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
        # 11 分队规则物化 + 53 战略 + 34 增强 = 98（15 encoded / 16 partial / 67 not_modeled）
        assert len(entries) == 98
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 15, "partial": 16, "not_modeled": 67}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_ac_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='AC' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_ac_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='AC' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_ac_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in AC_DET_RULE_IDS}

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


class TestDefensiveFromPayload:
    def test_flawless_construction_s_gt_t_only(self, entries):
        # 无瑕造物：S>T 攻击致伤 -1。S8 vs T4（2+，5/6）→ -1（3+，2/3）；S4=T4 不触发
        fc = _entry(entries, "fp11e-ac-moritoi-s1")
        tgt, _, _ = inject_target(_target(t=4), [fc], frozenset())
        hi = _run(_attacker(_melee(s=8)), tgt, Stance(phase="melee"))
        lo = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(hi.wounds, hi.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(lo.wounds, lo.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_hardened_resolve_toughness_plus_one(self, entries):
        # 坚毅决心：+1 T。S4 vs T4（4+，1/2）→ T5（5+，1/3）
        hr = _entry(entries, "fp11e-ac-tharanatoi-s1")
        tgt, _, _ = inject_target(_target(t=4), [hr], frozenset())
        r = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_focused_fear_ap_worsen(self, entries):
        # 聚焦恐惧：攻击 AP 恶化 1。AP-1 打 Sv4（5+，2/3）→ AP0（4+，1/2）
        ff = _entry(entries, "000009274003")
        tgt, _, _ = inject_target(_target(sv=4), [ff], frozenset())
        r = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_augury_uplink_fnp5(self, entries):
        # 预警上行链路：FNP 5+（需 defender_bearer_leading）→ 伤害通过 2/3
        au = _entry(entries, "000009753003")
        tgt, mod, _ = inject_target(_target(sv=7), [au],
                                    frozenset({"defender_bearer_leading"}))
        assert mod
        base = _run(_attacker(_melee()), _target(sv=7), Stance(phase="melee"))
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(2 / 3,
                                                                     abs=0.03)


class TestAttackerFromPayload:
    def test_emperors_executioners_below_starting_only(self, entries):
        # 帝皇的处刑者：对低于满编敌 +1 致伤。S4 vs T4：满编 4+（1/2）→ 低于满编 3+（2/3）
        ee = _entry(entries, "000008922005")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ee], frozenset())
        on = _run(atk, _target(t=4), Stance(phase="melee", target_below_starting=True))
        off = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(on.wounds, on.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(off.wounds, off.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_deathsong_lance_and_psyker_attacks(self, entries):
        # 死歌之镰：[LANCE] 冲锋致伤 +1 + 对 PSYKER +1 A。冲锋打 psyker：攻击 1→2，
        # S4 vs T4 冲锋 4+→3+（2/3）；非冲锋非 psyker 无增益
        ds = _entry(entries, "fp11e-ac-silent-s1")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ds], frozenset())
        chg = _run(atk, _target(t=4, keywords=frozenset({"psyker"})),
                   Stance(phase="melee", charging=True))
        assert chg.attacks.mean() == pytest.approx(2.0, abs=0.05)
        assert _ratio(chg.wounds, chg.hits) == pytest.approx(2 / 3, abs=0.02)
        plain = _run(atk, _target(t=4), Stance(phase="melee"))
        assert plain.attacks.mean() == pytest.approx(1.0, abs=0.05)
        assert _ratio(plain.wounds, plain.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_umbral_prosecution_boltgun_rapid_fire_and_ap(self, entries):
        # 暗影追诉：Boltgun [RAPID FIRE 2] + +1 AP（限 boltgun）。半程攻击 1→3；
        # AP0→-1 打 Sv4：unsaved 1/2→2/3
        up = _entry(entries, "fp11e-ac-silent-s2")
        atk, mod, _ = inject_attacker(
            _attacker(_gun(bs=3, s=4, ap=0, name="boltgun")), [up], frozenset())
        assert mod
        hr = _run(atk, _target(sv=4), Stance(phase="shooting", half_range=True))
        assert hr.attacks.mean() == pytest.approx(3.0, abs=0.05)
        assert _ratio(hr.unsaved, hr.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_oblivion_knight_hit_and_psyker_wound(self, entries):
        # 湮灭骑士：+1 命中 + 对 PSYKER +1 致伤（需 bearer_leading）。BS4→3+（2/3）；
        # 对 psyker S4vT4 4+→3+（2/3）；非 psyker 致伤不加
        ok = _entry(entries, "000008926004")
        atk, mod, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [ok],
                                      frozenset({"bearer_leading"}))
        assert mod
        vs_psy = _run(atk, _target(t=4, keywords=frozenset({"psyker"})),
                      Stance(phase="shooting"))
        vs_plain = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(vs_psy.hits, vs_psy.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(vs_psy.wounds, vs_psy.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(vs_plain.wounds, vs_plain.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_punishment_inescapable_ignores_cover_and_hit_mods(self, entries):
        # 无可逃脱的惩罚：远程 [IGNORES COVER] + 无视命中不利修正。掩体目标 BS3：
        # 掩体 4+（1/2）被无视 → 回 3+（2/3）
        pi = _entry(entries, "000009754007")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [pi], frozenset())
        r = _run(atk, _target(), Stance(phase="shooting", target_in_cover=True))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
