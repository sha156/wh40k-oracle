# tests/test_simulator_dsl_pr14_payload.py
"""P7-PR14 兽人编码落账：15 分队规则物化 + 77 战略 + 50 增强 = 142。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='ORK' 全部活跃 stratagems/enhancements 有 payload 条目、
    15 分队规则全物化；指纹全对
  · 三态计数：encoded 23 / partial 13 / not_modeled 106
  · 真源 payload 引擎级差分：深陷苦战近战 [SUSTAINED HITS 1] / 好战登舰者守方
    S>T 被伤-1（wound_s_gt_t）/ 群体心理 BOYZ 6+ 无效保护 / 毁灭漂移冲锋近战
    [CLEAVE 1]（melee_charging）/ 全速前进近战 +1 致伤 / 闪亮射手 [RAPID FIRE 1]
    （half_range）/ 巨兽蛮汉守方 AP 恶化 各至少一条
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
PAYLOAD = Path("dsl_payloads/orks.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

ORK_DET_RULE_IDS = ("000008365", "000008867", "000008871", "000008875",
                    "000008876", "000008880", "000008884", "000009614",
                    "000009622", "000009794", "000009990", "000010711",
                    "000010794", "000010798", "fp11e-ork-rollin")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0):
    return WeaponProfile(name_zh=None, name_en="choppa", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, damage=1):
    return WeaponProfile(name_zh=None, name_en="shoota", range='24"',
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
        # 15 分队规则物化 + 77 战略 + 50 增强 = 142（23 encoded / 13 partial / 106 not_modeled）
        assert len(entries) == 142
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 23, "partial": 13, "not_modeled": 106}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_ork_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='ORK' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_ork_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='ORK' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_ork_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in ORK_DET_RULE_IDS}

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
    def test_get_stuck_in_sustained_melee(self, entries):
        # 深陷苦战：ORKS 近战 [SUSTAINED HITS 1]。WS4 命中 1/2，暴击 1/6 追加 1 → 2/3
        gs = _entry(entries, "det000008365")
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4)), [gs], frozenset())
        r = _run(atk, _target(t=8), Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_devastating_drift_cleave_charge_only(self, entries):
        # 毁灭漂移：冲锋回合近战 [CLEAVE 1]。10 目标模型：冲锋攻击 1→3；非冲锋不生效
        dd = _entry(entries, "fp11e-ork-rollin-s3")
        atk, _, _ = inject_attacker(_attacker(_melee()), [dd], frozenset())
        chg = _run(atk, _target(models=10), Stance(phase="melee", charging=True))
        noc = _run(atk, _target(models=10), Stance(phase="melee"))
        assert chg.attacks.mean() == pytest.approx(3.0, abs=0.05)
        assert noc.attacks.mean() == pytest.approx(1.0, abs=0.05)

    def test_full_throttle_wound_plus_one(self, entries):
        # 全速前进：近战致伤 +1。S4 vs T4 4+→3+（2/3）
        ft = _entry(entries, "000008873006")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ft], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_dead_shiny_shootas_rapid_fire(self, entries):
        # 闪亮射手：[RAPID FIRE 1]（需 bearer_leading，半程 +1 攻击）。1→2
        ds = _entry(entries, "000009991003")
        atk, mod, _ = inject_attacker(_attacker(_gun(bs=4)), [ds],
                                      frozenset({"bearer_leading"}))
        assert mod
        hr = _run(atk, _target(), Stance(phase="shooting", half_range=True))
        assert hr.attacks.mean() == pytest.approx(2.0, abs=0.05)


class TestDefensiveFromPayload:
    def test_belligerent_boarders_s_gt_t_only(self, entries):
        # 好战登舰者：S>T 攻击致伤 -1。S8 vs T4（2+，5/6）→ -1（3+，2/3）
        bb = _entry(entries, "det000009614")
        tgt, _, _ = inject_target(_target(t=4), [bb], frozenset())
        r = _run(_attacker(_melee(s=8)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_mob_mentality_invuln6(self, entries):
        # 群体心理：BOYZ 6+ 无效保护。AP-3 打 Sv7 → 6++（unsaved 5/6）
        mm = _entry(entries, "det000008880")
        tgt, _, _ = inject_target(_target(sv=7), [mm], frozenset())
        r = _run(_attacker(_gun(ap=-3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(5 / 6, abs=0.02)

    def test_hulking_brutes_ap_worsen_shooting_only(self, entries):
        # 巨兽蛮汉：攻击 AP 恶化 1（仅对方射击阶段）。射击 AP-1 打 Sv4（5+，2/3）→
        # AP0（4+，1/2）；近战阶段不生效（AP-1 维持 2/3）
        hb = _entry(entries, "000008886007")
        tgt, _, _ = inject_target(_target(sv=4), [hb], frozenset())
        shoot = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        melee = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(shoot.unsaved, shoot.wounds) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(melee.unsaved, melee.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_ard_as_nails_wound_minus_one(self, entries):
        # 坚如磐石：攻击本单位致伤 -1。S4 vs T4（4+，1/2）→ 5+（1/3）
        an = _entry(entries, "000008366005")
        tgt, _, _ = inject_target(_target(t=4), [an], frozenset())
        r = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_supa_cybork_body_fnp4(self, entries):
        # 超级赛博兽人身躯：FNP 4+（需 defender_bearer_leading）→ 伤害通过 1/2
        sc = _entry(entries, "000008367005")
        tgt, mod, _ = inject_target(_target(sv=7), [sc],
                                    frozenset({"defender_bearer_leading"}))
        assert mod
        base = _run(_attacker(_melee()), _target(sv=7), Stance(phase="melee"))
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(1 / 2,
                                                                     abs=0.03)
