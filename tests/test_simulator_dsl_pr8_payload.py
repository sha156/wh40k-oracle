# tests/test_simulator_dsl_pr8_payload.py
"""P7-PR8 死亡守卫编码落账：1 军规 + 12 分队规则物化 + 57 战略 + 36 增强 = 106。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='DG' 全部活跃行有 payload 条目（removed_11e 零覆盖）；指纹全对
  · 真源 payload 引擎级差分：军规 T-1（target_afflicted 门）/ 骨疽疟 AP 等价 /
    怪诞坚韧 +2 T（t_improve 首连）/ 活化蝇群 S>T 被伤-1 / 可憎坚韧减伤 /
    原体教诲 [HEAVY] 各至少一条
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
PAYLOAD = Path("dsl_payloads/deathguard.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")


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


def _target(t=4, sv=7, models=5, w=1, effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=None, w=w, oc=1,
                         keywords=frozenset(), effects=tuple(effects))


def _entry(entries, row_id):
    return next(e for e in entries if e.row_id == row_id)


def _run(atk, target, stance):
    return run_sequence(atk, target, stance, n=N, seed=42)


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


class TestPayloadShape:
    def test_counts(self, entries):
        # 1 军规 + 12 分队规则 + 57 战略 + 36 增强 = 106（24 partial / 82 not_modeled）
        assert len(entries) == 106
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 24, "not_modeled": 82}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_dg_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='DG' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_dg_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='DG' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_dg_detachments_materialized(self, entries):
        con = self._db()
        dets = {r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='DG'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "abilities"
                   and e.row_id.startswith("det")}
        assert covered == {f"det{d}" for d in dets}   # 12（10 存量 + 2 fp_new）

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


class TestArmyRuleFromPayload:
    def test_nurgles_gift_t_worsen_needs_toggle(self, entries):
        # 纳垢赐福：开关关 → 不注入并披露；开 → S6 vs T4 变 T3（3+ → 2+）
        ng = _entry(entries, "000008396")
        atk_off, _, notes = inject_attacker(_attacker(_melee(s=6)), [ng],
                                            frozenset())
        assert any("target_afflicted" in n for n in notes)
        atk_on, modeled, _ = inject_attacker(_attacker(_melee(s=6)), [ng],
                                             frozenset({"target_afflicted"}))
        assert modeled
        off = _run(atk_off, _target(t=4), Stance(phase="melee"))
        on = _run(atk_on, _target(t=4), Stance(phase="melee"))
        assert _ratio(off.wounds, off.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(on.wounds, on.hits) == pytest.approx(5 / 6, abs=0.02)

    def test_rattlejoint_ap_via_stance(self, entries):
        # 骨疽疟：afflicted 开 + 瘟疫开关 → 在 T-1 之外再恶化护甲 1 档。
        # S4 ap0 vs T4 sv4：仅 afflicted → T3（wound 3+）save 4+ unsaved 1/2；
        # + rattlejoint → save 5+ unsaved 2/3
        ng = _entry(entries, "000008396")
        atk, _, _ = inject_attacker(_attacker(_melee()), [ng],
                                    frozenset({"target_afflicted",
                                               "plague_rattlejoint"}))
        no_plague = _run(atk, _target(t=4, sv=4), Stance(phase="melee"))
        plague = _run(atk, _target(t=4, sv=4),
                      Stance(phase="melee", plague_rattlejoint=True))
        assert _ratio(no_plague.unsaved, no_plague.wounds) == pytest.approx(
            1 / 2, abs=0.02)
        assert _ratio(plague.unsaved, plague.wounds) == pytest.approx(
            2 / 3, abs=0.02)


class TestAttackerFromPayload:
    def test_mortarions_teachings_heavy_needs_stationary(self, entries):
        # 原体教诲：[HEAVY] 驻停 BS4+ → 3+（2/3）；移动过 → 1/2
        mt = _entry(entries, "000010144006")
        atk, _, _ = inject_attacker(_attacker(_gun()), [mt], frozenset())
        stat = _run(atk, _target(), Stance(phase="shooting", stationary=True))
        moved = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(stat.hits, stat.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(moved.hits, moved.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_fell_harvester_two_extra_melee_attacks(self, entries):
        # 残暴收割：A1 → 3（需 bearer_leading 开关）
        fh = _entry(entries, "000010135003")
        _, _, notes = inject_attacker(_attacker(_melee()), [fh], frozenset())
        assert any("bearer_leading" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_melee()), [fh],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(3.0, abs=0.05)


class TestDefensiveFromPayload:
    def test_grotesque_fortitude_plus_2_t(self, entries):
        # 怪诞坚韧：S4 vs T4 4+（1/2）→ T6 5+（1/3）
        gf = _entry(entries, "000010132004")
        tgt, _, _ = inject_target(_target(t=4), [gf], frozenset())
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_rejuvenating_swarm_s_gt_t_minus_1(self, entries):
        # 活化蝇群（11 版新效果）：S5 vs T4（S>T）被伤 3+ → 4+；S4 vs T4 不受影响
        rs = _entry(entries, "fp11e-dg-paragons-e1")
        tgt, _, _ = inject_target(_target(t=4), [rs],
                                  frozenset({"defender_bearer_leading"}))
        strong = _run(_attacker(_melee(s=5)), tgt, Stance(phase="melee"))
        equal = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(strong.wounds, strong.hits) == pytest.approx(1 / 2,
                                                                   abs=0.02)
        assert _ratio(equal.wounds, equal.hits) == pytest.approx(1 / 2,
                                                                 abs=0.02)

    def test_disgustingly_resilient_damage_reduction(self, entries):
        # 可憎坚韧：W2 目标吃 D2 武器（每发灭一模型）→ 减伤到 D1（半伤；
        # W1 目标会被溢出封顶掩盖差分，故用 W2）
        dr = _entry(entries, "000010124003")
        tgt, _, _ = inject_target(_target(sv=7, w=2), [dr], frozenset())
        atk = _attacker(_gun(damage=2))
        base = _run(atk, _target(sv=7, w=2), Stance(phase="shooting"))
        red = _run(atk, tgt, Stance(phase="shooting"))
        assert red.damage.mean() / base.damage.mean() == pytest.approx(
            1 / 2, abs=0.03)

    def test_cloud_of_flies_hit_minus_1(self, entries):
        # 蝇群蔽体：WS4+ 命中 1/2 → 5+ 1/3
        cf = _entry(entries, "000009417005")
        tgt, _, _ = inject_target(_target(), [cf], frozenset())
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)


@needs_db
class TestRealUnitSmoke:
    def test_plague_marines_load_dg_entries(self):
        from engines.simulator.profile import load_unit_dsl
        con = sqlite3.connect(str(DB))
        row = con.execute(
            "SELECT id FROM units WHERE faction_id='DG' "
            "AND name_en='Plague Marines'").fetchone()
        con.close()
        assert row is not None
        entries = load_unit_dsl(str(DB), row[0])
        ids = {e.row_id for e in entries}
        assert "000008396" in ids                   # 军规
        assert "fp11e-dg-paragons-s1" in ids        # 补录战略
        assert "det000009728" in ids                # 物化分队规则（重印后）
        assert "000010123005" in ids                # 增强（可怖再生）
