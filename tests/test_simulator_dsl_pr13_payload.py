# tests/test_simulator_dsl_pr13_payload.py
"""P7-PR13 死灵编码落账：16 分队规则物化 + 79 战略 + 50 增强 = 145。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='NEC' 全部活跃 stratagems/enhancements 有 payload 条目、
    16 分队规则全物化；指纹全对
  · 三态计数：encoded 20 / partial 15 / not_modeled 110
  · 真源 payload 引擎级差分：脆弱之痕对低于满/半编 +命中致伤
    （target_below_starting/half）/ 不屈之躯守方 S>T 被伤-1（wound_s_gt_t）/
    宇宙风暴 tesla sphere AP+1（weapon_filter）/ 统御工具 [RAPID FIRE 1]（half_range）/
    亚表面量子织网守方 AP 恶化 / 指令协议 Character 率领 +1 命中 / 量子偏转守方
    4+ 无效保护 各至少一条
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
PAYLOAD = Path("dsl_payloads/necrons.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

NEC_DET_RULE_IDS = ("000008370", "000008542", "000008545", "000008549",
                    "000008553", "000009587", "000009595", "000009603",
                    "000009748", "000010663", "000010667", "000010671",
                    "000010734", "fp11e-nec-hand", "fp11e-nec-phaeron",
                    "fp11e-nec-skyshroud")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, damage=1, name="gauss"):
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
        # 16 分队规则物化 + 79 战略 + 50 增强 = 145（20 encoded / 15 partial / 110 not_modeled）
        assert len(entries) == 145
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 20, "partial": 15, "not_modeled": 110}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_nec_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='NEC' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_nec_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='NEC' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_nec_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in NEC_DET_RULE_IDS}

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
    def test_spoor_of_frailty_below_strength_tiers(self, entries):
        # 脆弱之痕：对低于满编 +1 命中，低于半编另 +1 致伤。BS4→3+（2/3）；S4vT4 4+→3+（2/3）
        sf = _entry(entries, "000008405003")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [sf], frozenset())
        r = _run(atk, _target(t=4),
                 Stance(phase="shooting", target_below_starting=True,
                        target_below_half=True))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 满编目标不触发
        full = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(full.hits, full.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_cosmic_storm_tesla_sphere_ap(self, entries):
        # 宇宙风暴：Tesla Sphere 武器 AP+1（限武器）。AP0 打 Sv4（4+，1/2）→ AP-1（5+，2/3）
        cs = _entry(entries, "fp11e-nec-phaeron-s3")
        atk, mod, _ = inject_attacker(
            _attacker(_gun(bs=3, ap=0, name="tesla sphere")), [cs], frozenset())
        assert mod
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_tools_of_dominion_rapid_fire(self, entries):
        # 统御工具：[RAPID FIRE 1]（半程 +1 攻击）。1→2
        td = _entry(entries, "fp11e-nec-hand-e2")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [td], frozenset())
        hr = _run(atk, _target(), Stance(phase="shooting", half_range=True))
        assert hr.attacks.mean() == pytest.approx(2.0, abs=0.05)

    def test_cold_fervour_strength_all_phases(self, entries):
        # 冷酷狂热：Destroyer Cult 武器 S +2（全阶段，远近皆适用——FP 原文「weapons」无限定）。
        # S4→S6 vs T6：射击与近战都从 5+（1/3）升到 4+（1/2）
        cf = _entry(entries, "det000010667")
        atk_g, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [cf], frozenset())
        sh = _run(atk_g, _target(t=6), Stance(phase="shooting"))
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [cf], frozenset())
        ml = _run(atk_m, _target(t=6), Stance(phase="melee"))
        assert _ratio(sh.wounds, sh.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(ml.wounds, ml.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_command_protocols_hit_requires_leading(self, entries):
        # 指令协议：Character 率领 +1 命中。BS4→3+（2/3）；开关未启用不注入
        cp = _entry(entries, "det000008370")
        atk, mod, _ = inject_attacker(_attacker(_gun(bs=4)), [cp],
                                      frozenset({"bearer_leading"}))
        assert mod
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        _, mod_off, _ = inject_attacker(_attacker(_gun(bs=4)), [cp], frozenset())
        assert mod_off == []


class TestDefensiveFromPayload:
    def test_unyielding_forms_s_gt_t_only(self, entries):
        # 不屈之躯：S>T 攻击致伤 -1。S8 vs T4（2+，5/6）→ -1（3+，2/3）
        uf = _entry(entries, "000009750003")
        tgt, _, _ = inject_target(_target(t=4), [uf], frozenset())
        r = _run(_attacker(_melee(s=8)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_subsurface_quantumweave_ap_worsen(self, entries):
        # 亚表面量子织网：攻击 AP 恶化 1。AP-1 打 Sv4（5+，2/3）→ AP0（4+，1/2）
        sq = _entry(entries, "fp11e-nec-phaeron-s1")
        tgt, _, _ = inject_target(_target(sv=4), [sq], frozenset())
        r = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_quantum_deflection_invuln(self, entries):
        # 量子偏转：4+ 无效保护。AP-3 打 Sv7 → 4++（unsaved 1/2）
        qd = _entry(entries, "000008555003")
        tgt, _, _ = inject_target(_target(sv=7), [qd], frozenset())
        r = _run(_attacker(_gun(ap=-3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_nanoassembly_damage_reduction(self, entries):
        # 纳米装配协议：伤害 -1。D2 → D1
        na = _entry(entries, "000008551004")
        tgt, _, _ = inject_target(_target(sv=7, w=3), [na], frozenset())
        base = _run(_attacker(_gun(ap=-3, damage=2)), _target(sv=7, w=3),
                    Stance(phase="shooting"))
        r = _run(_attacker(_gun(ap=-3, damage=2)), tgt, Stance(phase="shooting"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(1 / 2,
                                                                     abs=0.03)

    def test_enaegic_dermal_bond_fnp(self, entries):
        # 灵能真皮键结：FNP 4+（需 defender_bearer_leading）→ 伤害通过 1/2
        ed = _entry(entries, "000008372005")
        tgt, mod, _ = inject_target(_target(sv=7), [ed],
                                    frozenset({"defender_bearer_leading"}))
        assert mod
        base = _run(_attacker(_melee()), _target(sv=7), Stance(phase="melee"))
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(1 / 2,
                                                                     abs=0.03)
