# tests/test_simulator_dsl_pr12_payload.py
"""P7-PR12 德鲁卡里编码落账：13 分队规则物化 + 61 战略 + 38 增强 = 112。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='DRU' 全部活跃 stratagems/enhancements 有 payload 条目、
    13 分队规则全物化；指纹全对
  · 三态计数：encoded 21 / partial 13 / not_modeled 78
  · 真源 payload 引擎级差分：残酷之雨下车 [IGNORES COVER]+[LANCE]
    （disembarked_this_turn + melee_charging）/ 缝肉憎恶守方 S>T 被伤-1
    （wound_s_gt_t）/ 窃船者 [ANTI-INFANTRY 3+]（crit_threshold）/ 甲板清扫者
    splinter 武器 AP+1（weapon_filter）/ 预谋打击 [LETHAL HITS] / 麻木无痛减伤 /
    杂技表演守方 5+ 无效保护 各至少一条
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
PAYLOAD = Path("dsl_payloads/drukhari.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

DRU_DET_RULE_IDS = ("000008714", "000009424", "000009432", "000009440",
                    "000009449", "000009780", "000010572", "000010579",
                    "000010583", "000010587", "fp11e-dru-agonysts",
                    "fp11e-dru-exhibition", "fp11e-dru-torment")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, damage=1, name="splinter rifle"):
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
        # 13 分队规则物化 + 61 战略 + 38 增强 = 112（21 encoded / 13 partial / 78 not_modeled）
        assert len(entries) == 112
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 21, "partial": 13, "not_modeled": 78}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_dru_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='DRU' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_dru_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='DRU' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_dru_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in DRU_DET_RULE_IDS}

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
    def test_rain_of_cruelty_disembark_gated(self, entries):
        # 残酷之雨：下车后远程 [IGNORES COVER] + 近战 [LANCE]（冲锋致伤+1）。
        # 需 disembarked_this_turn 开关；掩体 BS3 4+→无视 3+；冲锋 S4vT4 4+→3+
        rc = _entry(entries, "det000008714")
        atk, mod, _ = inject_attacker(
            _attacker(_gun(bs=3), _melee(s=4)), [rc],
            frozenset({"disembarked_this_turn"}))
        assert mod
        sh = _run(atk, _target(sv=7),
                  Stance(phase="shooting", target_in_cover=True,
                         disembarked_this_turn=True))
        assert _ratio(sh.hits, sh.attacks) == pytest.approx(2 / 3, abs=0.02)
        ml = _run(atk, _target(t=4),
                  Stance(phase="melee", charging=True, disembarked_this_turn=True))
        assert _ratio(ml.wounds, ml.hits) == pytest.approx(2 / 3, abs=0.02)
        # 未下车 → 不注入
        _, mod_off, _ = inject_attacker(_attacker(_melee()), [rc], frozenset())
        assert mod_off == []

    def test_planned_strikes_lethal_hits(self, entries):
        # 预谋打击：近战 [LETHAL HITS]（暴击命中自动致伤）。S4 vs T8 正常 6+ 致伤（1/6），
        # LETHAL 使暴击命中（1/6）自动致伤 → 致伤率上升
        ps = _entry(entries, "fp11e-dru-exhibition-s1")
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4, s=4)), [ps], frozenset())
        lethal = _run(atk, _target(t=8), Stance(phase="melee"))
        base = _run(_attacker(_melee(s=4)), _target(t=8), Stance(phase="melee"))
        assert _ratio(lethal.wounds, lethal.hits) > _ratio(base.wounds, base.hits) + 0.15

    def test_deckplate_sweepers_splinter_ap(self, entries):
        # 甲板清扫者：splinter 武器 AP+1（限武器）。AP0 打 Sv4（4+，1/2）→ AP-1（5+，2/3）
        ds = _entry(entries, "000009434003")
        atk, mod, _ = inject_attacker(
            _attacker(_gun(bs=3, ap=0, name="splinter rifle")), [ds], frozenset())
        assert mod
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_making_a_point_bs_and_ap(self, entries):
        # 证明观点：远程 BS+1 + AP+1。BS4→3+（2/3）；AP0→-1 打 Sv4（4+→5+，2/3）
        mp = _entry(entries, "000010589006")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4, ap=0)), [mp], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)


class TestDefensiveFromPayload:
    def test_stitchflesh_s_gt_t_only(self, entries):
        # 缝肉憎恶：S>T 攻击致伤 -1。S8 vs T4（2+，5/6）→ -1（3+，2/3）
        st = _entry(entries, "det000010583")
        tgt, _, _ = inject_target(_target(t=4), [st], frozenset())
        r = _run(_attacker(_melee(s=8)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_insensible_to_pain_damage_reduction(self, entries):
        # 麻木无痛：伤害 -1。D2 → D1
        ip = _entry(entries, "000010575002")
        tgt, _, _ = inject_target(_target(sv=7, w=3), [ip], frozenset())
        base = _run(_attacker(_gun(ap=-3, damage=2)), _target(sv=7, w=3),
                    Stance(phase="shooting"))
        r = _run(_attacker(_gun(ap=-3, damage=2)), tgt, Stance(phase="shooting"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(1 / 2,
                                                                     abs=0.03)

    def test_hyperagility_hit_and_wound_minus_one(self, entries):
        # 超敏捷：攻击本单位命中 -1 + 致伤 -1。BS3 命中 2/3→1/2；S4vT4 致伤 1/2→1/3
        hy = _entry(entries, "000009442002")
        tgt, _, _ = inject_target(_target(t=4), [hy], frozenset())
        r = _run(_attacker(_gun(bs=3, s=4)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_night_shield_invuln_shooting(self, entries):
        # 夜幕护盾：4+ 无效保护（对方射击）。AP-3 打 Sv7 → 4++（unsaved 1/2）
        ns = _entry(entries, "000010577007")
        tgt, _, _ = inject_target(_target(sv=7), [ns], frozenset())
        r = _run(_attacker(_gun(ap=-3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_hyperstimm_trafficker_toughness(self, entries):
        # 超刺激贩子：+1 T（需 defender_bearer_leading）。S4 vs T4（4+）→ T5（5+，1/3）
        ht = _entry(entries, "fp11e-dru-exhibition-e2")
        tgt, mod, _ = inject_target(_target(t=4), [ht],
                                    frozenset({"defender_bearer_leading"}))
        assert mod
        r = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)
