# tests/test_simulator_dsl_pr10_payload.py
"""P7-PR10 千子编码落账：12 分队规则物化 + 57 战略 + 36 增强 = 105。

覆盖（spec 七-1 双验范式）：
  · DB 对账：faction='TS' 全部活跃 stratagems/enhancements 有 payload 条目、
    12 分队规则全物化；指纹全对
  · 三态计数：encoded 12 / partial 5 / not_modeled 88
  · 真源 payload 引擎级差分：巫视/焦烧翻焰远程无视掩体、利骨丛生近战 CLEAVE+AP、
    阿波米努斯法杖近战 SUSTAINED D3、附魔灌注载具 [PSYCHIC]+致伤、及守方向
    硫磺帷幕/岿然阵列/咒印甲胄/扭曲无常/坚定守护/代价赐福各至少一条
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
PAYLOAD = Path("dsl_payloads/thousandsons.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

TS_DET_RULE_IDS = ("000009653", "000009662", "000009671", "000009740",
                   "000010192", "000010196", "000010200", "000010204",
                   "000010208", "fp11e-ts-regen", "fp11e-ts-sekhetar",
                   "fp11e-ts-servants")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0):
    return WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=(), count=1)


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
        # 12 分队规则物化 + 57 战略 + 36 增强 = 105（12 encoded / 5 partial / 88 not_modeled）
        assert len(entries) == 105
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 12, "partial": 5, "not_modeled": 88}

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id

    def test_encoded_entries_have_fingerprint(self, entries):
        for e in entries:
            if e.status == "encoded":
                assert e.effects and e.provenance.get("text_sha256"), e.row_id


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_ts_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='TS' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_ts_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='TS' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_ts_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in TS_DET_RULE_IDS}

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
    def test_witchsight_ignores_cover_shooting_only(self, entries):
        # 巫视：远程 [IGNORES COVER]。BS3 打掩体目标：掩体 BS 恶化 1 → 4+（1/2），
        # 无视掩体后回到 3+（2/3）；近战不受掩体影响故不测
        w = _entry(entries, "det000009653")
        atk, mod, _ = inject_attacker(_attacker(_gun(bs=3)), [w], frozenset())
        assert mod  # 已施加
        base = _run(_attacker(_gun(bs=3)), _target(),
                    Stance(phase="shooting", target_in_cover=True))
        wit = _run(atk, _target(), Stance(phase="shooting", target_in_cover=True))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(wit.hits, wit.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_thicket_cleave_and_ap_melee_only(self, entries):
        # 利骨丛生：近战 [CLEAVE 1] + +1 AP。10 目标模型：攻击 1→3（每 5 +1）；
        # AP0→AP-1 打 Sv4：unsaved 1/2→2/3。射击阶段不生效
        th = _entry(entries, "fp11e-ts-servants-e2")
        atk, _, _ = inject_attacker(_attacker(_melee(ap=0)), [th], frozenset())
        m = _run(atk, _target(sv=4, models=10), Stance(phase="melee"))
        base = _run(_attacker(_melee(ap=0)), _target(sv=4, models=10),
                    Stance(phase="melee"))
        assert m.attacks.mean() == pytest.approx(3.0, abs=0.05)
        assert base.attacks.mean() == pytest.approx(1.0, abs=0.05)
        assert _ratio(m.unsaved, m.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_stave_abominus_sustained_d3_requires_bearer(self, entries):
        # 阿波米努斯法杖：近战 [SUSTAINED HITS D3]。WS4+ 命中 1/2，暴击 1/6 追加
        # D3(均2) → 1/2 + 1/6*2 = 5/6；开关未启用则不注入
        st = _entry(entries, "000010205005")
        atk, mod, _ = inject_attacker(_attacker(_melee()), [st],
                                      frozenset({"bearer_leading"}))
        assert mod
        r = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(5 / 6, abs=0.02)
        atk_off, mod_off, _ = inject_attacker(_attacker(_melee()), [st],
                                              frozenset())
        assert mod_off == []  # 开关未启用不注入

    def test_ensorcelled_infusion_wound_plus_one_shooting(self, entries):
        # 附魔灌注：载具远程武器致伤 +1 + [PSYCHIC]。S4 vs T4：4+→3+（1/2→2/3）
        ei = _entry(entries, "000010210006")
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [ei], frozenset())
        base = _run(_attacker(_gun(s=4)), _target(t=4), Stance(phase="shooting"))
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_lord_of_the_rubricae_hit_plus_one(self, entries):
        # 红骸之主：命中 +1（需 bearer_leading）。BS4+（1/2）→ 3+（2/3）
        lr = _entry(entries, "000010205004")
        atk, mod, _ = inject_attacker(_attacker(_gun(bs=4)), [lr],
                                      frozenset({"bearer_leading"}))
        assert mod
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)


class TestDefensiveFromPayload:
    def test_sulphurous_veil_hit_minus_one(self, entries):
        # 硫磺帷幕：攻击本单位命中 -1。BS3+（2/3）→ 4+（1/2）
        sv = _entry(entries, "000010198002")
        tgt, _, _ = inject_target(_target(), [sv], frozenset())
        r = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_warped_vicissitude_invuln_4(self, entries):
        # 扭曲无常：4+ 无效保护。AP-3 打 Sv7（护甲无效）→ 4++（unsaved 1/2）
        wv = _entry(entries, "000010202003")
        tgt, _, _ = inject_target(_target(sv=7), [wv], frozenset())
        r = _run(_attacker(_gun(ap=-3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_hex_marked_armour_ap_worsen(self, entries):
        # 咒印甲胄：攻击 AP 恶化 1。AP-1 打 Sv4（5+ 保，unsaved 2/3）→ AP0（4+，1/2）
        hm = _entry(entries, "000010210002")
        tgt, _, _ = inject_target(_target(sv=4), [hm], frozenset())
        r = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_unwavering_phalanx_wound_minus_one(self, entries):
        # 岿然阵列：攻击致伤 -1。S4 vs T4（4+，1/2）→ -1（5+，1/3）
        up = _entry(entries, "000010206007")
        tgt, _, _ = inject_target(_target(t=4), [up], frozenset())
        r = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_costly_blessing_invuln_melee_only(self, entries):
        # 代价赐福：3+ 无效保护（近战阶段）。AP-3 打 Sv7 近战 → 3++（unsaved 1/3）；
        # 射击阶段不生效（门控 phase_melee，护甲 7+ unsaved 1）
        cb = _entry(entries, "000009655002")
        tgt, _, _ = inject_target(_target(sv=7), [cb], frozenset())
        melee = _run(_attacker(_melee(ap=-3)), tgt, Stance(phase="melee"))
        shoot = _run(_attacker(_gun(ap=-3)), tgt, Stance(phase="shooting"))
        assert _ratio(melee.unsaved, melee.wounds) == pytest.approx(1 / 3,
                                                                    abs=0.02)
        assert _ratio(shoot.unsaved, shoot.wounds) == pytest.approx(1.0,
                                                                    abs=0.01)

    def test_kaleidoscopic_tempest_stealth_cover(self, entries):
        # 万花风暴：Stealth=对远程掩体收益（BS 恶化 1）：BS3+（2/3）→ 4+（1/2）
        kt = _entry(entries, "000009742007")
        tgt, _, _ = inject_target(_target(), [kt], frozenset())
        shoot = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(shoot.hits, shoot.attacks) == pytest.approx(1 / 2,
                                                                  abs=0.02)

    def test_implacable_guardians_damage_reduction(self, entries):
        # 坚定守护：伤害 -1（对方射击阶段）。D2 武器 → D1
        ig = _entry(entries, "000010206006")
        tgt, _, _ = inject_target(_target(sv=7, w=3), [ig], frozenset())
        base = _run(_attacker(_gun(ap=-3, damage=2)), _target(sv=7, w=3),
                    Stance(phase="shooting"))
        r = _run(_attacker(_gun(ap=-3, damage=2)), tgt, Stance(phase="shooting"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(1 / 2,
                                                                     abs=0.03)

    def test_flesh_change_fnp5(self, entries):
        # 血肉之变：FNP 5+ → 伤害通过率 2/3
        fc = _entry(entries, "000009664003")
        tgt, _, _ = inject_target(_target(sv=7), [fc], frozenset())
        base = _run(_attacker(_melee()), _target(sv=7), Stance(phase="melee"))
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert r.damage.mean() / base.damage.mean() == pytest.approx(2 / 3,
                                                                     abs=0.03)


@needs_db
class TestRealUnitSmoke:
    def test_ts_detachment_rule_materialized_in_db(self):
        con = sqlite3.connect(str(DB))
        row = con.execute(
            "SELECT dsl_status FROM abilities WHERE id='det000009653'").fetchone()
        con.close()
        assert row is not None and row[0] == "encoded"  # 巫视物化+编码
