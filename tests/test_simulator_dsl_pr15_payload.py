# tests/test_simulator_dsl_pr15_payload.py
"""P7-PR15 圣血修女（Adepta Sororitas）编码落账：10 分队规则物化 + 44 战略 + 29 增强 = 83。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='AS' 全部活跃 stratagems/enhancements 有 payload 条目、
    10 分队规则全物化；指纹全对
  · 三态计数：encoded 0 / partial 27 / not_modeled 56（信仰/奇迹骰阵营可编率低）
  · 真源 payload 引擎级差分：神圣征途 WS/BS+1（bs_improve）/ 圣洁打击近战 +1 A/S /
    信仰与狂怒 [LANCE]（melee_charging 致伤+1）/ 帝皇庇佑守方 4++ / 回避之盾守方 AP 恶化 /
    蔑视死亡守方 S>T 被伤-1 / 信仰壁垒守方命中-1 仅近战（phase_melee 门）/ 受难之纯粹守方 FNP4+
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
PAYLOAD = Path("dsl_payloads/sororitas.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

AS_DET_RULE_IDS = ("000008468", "000009028", "000009032", "000009036",
                   "000009307", "000009315", "000009830",
                   "fp11e-sororitas-chorus", "fp11e-sororitas-orators",
                   "fp11e-sororitas-sacred")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0):
    return WeaponProfile(name_zh=None, name_en="power sword", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, damage=1):
    return WeaponProfile(name_zh=None, name_en="bolter", range='24"',
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
        # 10 分队规则物化 + 44 战略 + 29 增强 = 83（0 encoded / 25 partial / 58 not_modeled）
        # The Emperor Protects（排除 ARCO/REPENTIA）与 Fire and Fury（排除 Torrent 武器）
        # 均为负关键字/关键词筛选门无载体，审查后降 not_modeled（同 Devastating Reprise 先例）
        assert len(entries) == 83
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 25, "not_modeled": 58}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id

    def test_not_modeled_have_reason(self, entries):
        for e in entries:
            if e.status == "not_modeled":
                assert not e.effects and e.not_modeled_notes_zh, e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_as_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='AS' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_as_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='AS' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_as_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in AS_DET_RULE_IDS}

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
    def test_holy_quest_ws_bs_improve(self, entries):
        # 神圣征途：CELESTIAN SACRESANTS WS/BS +1。近战 WS4（4+，1/2）→ 3+（2/3）
        hq = _entry(entries, "detfp11e-sororitas-sacred")
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4)), [hq], frozenset())
        r = _run(atk, _target(t=8), Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_sanctified_blows_attacks_and_strength(self, entries):
        # 圣洁打击：Sacresants 近战 +1 A、+1 S。A：1→2；S：S4 vs T4 4+→3+（2/3）
        sb = _entry(entries, "fp11e-sororitas-sacred-s1")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [sb], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2.0, abs=0.05)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_faith_and_fury_lance_charge_only(self, entries):
        # 信仰与狂怒：[LANCE]=冲锋回合近战致伤+1。S4 vs T4 4+（1/2）冲锋→3+（2/3）；非冲锋维持 1/2
        ff = _entry(entries, "000009038004")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ff], frozenset())
        chg = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        noc = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(chg.wounds, chg.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(noc.wounds, noc.hits) == pytest.approx(1 / 2, abs=0.02)


class TestDefensiveFromPayload:
    def test_shield_of_aversion_ap_worsen(self, entries):
        # 回避之盾：针对本单位的攻击 AP 恶化 1。AP-1 打 Sv4（5+，2/3）→ AP0（4+，1/2）
        sa = _entry(entries, "000009034002")
        tgt, _, _ = inject_target(_target(sv=4), [sa], frozenset())
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_contempt_for_death_s_gt_t_only(self, entries):
        # 蔑视死亡：S>T 攻击致伤 -1。S8 vs T4（2+，5/6）→ -1（3+，2/3）
        cd = _entry(entries, "000009317003")
        tgt, _, _ = inject_target(_target(t=4), [cd], frozenset())
        r = _run(_attacker(_melee(s=8)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_bastion_of_faith_hit_minus_one_melee_only(self, entries):
        # 信仰壁垒：针对本单位的攻击命中 -1，仅近战（WHEN=战斗阶段）。
        # 近战 WS4（4+，1/2）→ 5+（1/3）；射击阶段不生效（BS4 维持 1/2）
        bf = _entry(entries, "000009832006")
        tgt, _, _ = inject_target(_target(t=4), [bf], frozenset())
        melee = _run(_attacker(_melee(ws=4)), tgt, Stance(phase="melee"))
        shoot = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(melee.hits, melee.attacks) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(shoot.hits, shoot.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_purity_of_suffering_fnp4(self, entries):
        # 受难之纯粹：PENITENT FNP 4+ → 伤害通过 1/2
        ps = _entry(entries, "000009030003")
        tgt, _, _ = inject_target(_target(sv=7), [ps], frozenset())
        base = _run(_attacker(_melee()), _target(sv=7), Stance(phase="melee"))
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(1 / 2,
                                                                     abs=0.03)
