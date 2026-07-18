# tests/test_simulator_dsl_pr6_payload.py
"""P7-PR6 黑色圣堂编码落账：军规誓言 + 6 分队规则物化 + 24 战略 + 17 增强。

覆盖（spec 七-1 双验范式，手算期望值写在断言旁）：
  · DB 对账：BT 范围活跃行（6 分队的战略/增强 + 军规，排除 removed_11e）全部有
    payload 条目，removed 行（怒火巡游队重印未收录 7 条）必须没有
  · 真源 payload 引擎级差分：誓言 S≤T / 圣兆 / 谴责音阵 LR 门 / 屠灭邪物 s_improve /
    守方不朽忠诚祷言 invuln 各至少一条
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
PAYLOAD = Path("dsl_payloads/blacktemplars.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# BT 分队清单（子阵营挂 SM 无独立阵营行——覆盖口径按分队名圈定，见工作单）
BT_DETS = ("Companions of Vehemence", "Vindication Task Force",
           "Godhammer Assault Force", "Wrathful Procession",
           "Marshal’s Household", "The Living Miracle")
BT_DET_RULE_IDS = ("000010391", "000010395", "000010399", "000009842",
                   "fp11e-bt-marshals-det", "fp11e-bt-miracle-det")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, name="blade", effects=()):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
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


# ═══ 结构与 DB 对账 ═══════════════════════════════════════════════════════

class TestPayloadShape:
    def test_counts(self, entries):
        # 1 军规 + 6 分队规则 + 24 战略 + 17 增强 = 48（0 encoded：全带假设注记）
        assert len(entries) == 48
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 20, "not_modeled": 28}

    def test_faction_is_sm_subfaction(self, entries):
        assert all(e.faction == "SM" for e in entries)

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id

    def test_vow_entry_gated_by_toggle(self, entries):
        vow = _entry(entries, "000008526")
        assert vow.detachment is None                    # 军队级
        assert "vow_accept_any_challenge" in vow.requires_toggles

    def test_target_side_entries(self, entries):
        target_ids = {e.row_id for e in entries if e.side == "target"}
        assert target_ids == {"det000010395", "det000009842", "000010401007",
                              "000010397006", "000009844002", "000010396003"}


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_bt_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN "
            f"({','.join('?' * len(BT_DETS))}) "
            "AND COALESCE(fp_status, '') != 'removed_11e'", BT_DETS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_removed_wrathful_rows_not_covered(self, entries):
        con = self._db()
        removed_s = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment='Wrathful Procession' "
            "AND fp_status = 'removed_11e'")}
        removed_e = {r[0] for r in con.execute(
            "SELECT id FROM enhancements "
            "WHERE detachment_name='Wrathful Procession' "
            "AND fp_status = 'removed_11e'")}
        con.close()
        assert len(removed_s) == 4 and len(removed_e) == 3   # 重印裁定
        ids = {e.row_id for e in entries}
        assert not (removed_s | removed_e) & ids

    def test_active_bt_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN "
            f"({','.join('?' * len(BT_DETS))}) "
            "AND COALESCE(fp_status, '') != 'removed_11e'", BT_DETS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_bt_detachments_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"
                   and e.row_id.startswith("det")}
        assert covered == {f"det{d}" for d in BT_DET_RULE_IDS}

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


# ═══ 真源 payload 引擎级差分 ═══════════════════════════════════════════════

class TestVowFromPayload:
    def test_accept_any_challenge_differential(self, entries):
        # S4 vs T5：5+（1/3）→ 誓言 +1 → 4+（1/2）；开关关时不注入
        vow = _entry(entries, "000008526")
        atk_on, _, _ = inject_attacker(
            _attacker(_melee()), [vow],
            frozenset({"vow_accept_any_challenge"}))
        atk_off, _, notes_off = inject_attacker(_attacker(_melee()), [vow],
                                                frozenset())
        on = _run(atk_on, _target(t=5), Stance(phase="melee"))
        off = _run(atk_off, _target(t=5), Stance(phase="melee"))
        assert _ratio(on.wounds, on.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(off.wounds, off.hits) == pytest.approx(1 / 3, abs=0.02)
        assert any("vow_accept_any_challenge" in n for n in notes_off)  # 开关门披露

    def test_vow_yields_nothing_vs_lower_t(self, entries):
        # S5 vs T4：S>T 誓言不适用——3+（2/3）与基线一致
        vow = _entry(entries, "000008526")
        atk, _, _ = inject_attacker(
            _attacker(_melee(s=5)), [vow],
            frozenset({"vow_accept_any_challenge"}))
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)


class TestStratagemsFromPayload:
    def test_slayers_s_improve_vs_monster(self, entries):
        # 屠灭邪物：S4 vs T5 巨兽——+2 S → S6>T5 → 3+（2/3）；非巨兽仍 5+（1/3）
        sl = _entry(entries, "fp11e-bt-marshals-s1")
        atk, _, _ = inject_attacker(_attacker(_melee()), [sl], frozenset())
        vs_monster = _run(atk, _target(t=5, keywords=frozenset({"monster"})),
                          Stance(phase="melee"))
        vs_line = _run(atk, _target(t=5), Stance(phase="melee"))
        assert _ratio(vs_monster.wounds, vs_monster.hits) == pytest.approx(
            2 / 3, abs=0.02)
        assert _ratio(vs_line.wounds, vs_line.hits) == pytest.approx(
            1 / 3, abs=0.02)

    def test_condemnatory_requires_land_raider_toggle(self, entries):
        # 谴责音阵：LR 开关关 → 不注入并披露；开 → 近战致伤重骰
        # S4vsT4 4+：off wounds/hits = 1/2；重骰失败 → 1/2 + 1/2×1/2 = 3/4
        ci = _entry(entries, "000010401006")
        atk_off, _, notes = inject_attacker(_attacker(_melee()), [ci],
                                            frozenset())
        assert any("disembarked_from_land_raider" in n for n in notes)
        toggles = frozenset({"disembarked_from_land_raider",
                             "disembarked_this_turn"})
        atk_on, _, _ = inject_attacker(_attacker(_melee()), [ci], toggles)
        off = _run(atk_off, _target(), Stance(phase="melee"))
        on = _run(atk_on, _target(),
                  Stance(phase="melee", disembarked_from_land_raider=True))
        assert _ratio(off.wounds, off.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(on.wounds, on.hits) == pytest.approx(3 / 4, abs=0.02)

    def test_rite_of_perfervid_wrath_s_improve(self, entries):
        # 极端怒火仪式：S4→S5 vs T5——5+（1/3）升 4+（1/2）
        rite = _entry(entries, "fp11e-bt-wrathful-s1")
        atk, _, _ = inject_attacker(_attacker(_melee()), [rite], frozenset())
        r = _run(atk, _target(t=5), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)


class TestOmensFromPayload:
    def test_momentous_brutality_attacks(self, entries):
        # 凶暴神视开：A1+2=3；圣兆全关：A1
        omens = _entry(entries, "fp11e-bt-miracle-e1")
        atk, _, _ = inject_attacker(_attacker(_melee()), [omens], frozenset())
        on = _run(atk, _target(), Stance(phase="melee",
                                         omen_momentous_brutality=True))
        off = _run(atk, _target(), Stance(phase="melee"))
        assert on.attacks.mean() == pytest.approx(3.0, abs=0.02)
        assert off.attacks.mean() == pytest.approx(1.0, abs=0.02)

    def test_instrument_mortals_only_vs_character(self, entries):
        omens = _entry(entries, "fp11e-bt-miracle-e1")
        atk, _, _ = inject_attacker(_attacker(_melee()), [omens], frozenset())
        st = Stance(phase="melee", omen_instrument=True)
        vs_char = _run(atk, _target(keywords=frozenset({"character"})), st)
        vs_line = _run(atk, _target(), st)
        assert vs_char.mortals.mean() > 0
        assert vs_line.mortals.mean() == 0


class TestDefensiveFromPayload:
    def test_chant_invuln_vs_shooting_only(self, entries):
        # 不朽忠诚祷言：AP-3 打 Sv4（穿甲后 7+ 失效）——射击时 5+ InSv 挡 1/3；
        # 近战不生效。gun WS4+ S4 vs T4：wounds 相同，unsaved 差分
        chant = _entry(entries, "det000009842")
        tgt, _, _ = inject_target(_target(sv=4), [chant], frozenset())
        gun = WeaponProfile(name_zh=None, name_en="gun", range='24"',
                            attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=-3,
                            damage=DiceExpr(k=1), effects=(), count=1)
        shoot = _run(_attacker(gun), tgt, Stance(phase="shooting"))
        melee = _run(_attacker(_melee(ap=-3)), tgt, Stance(phase="melee"))
        # 射击：5+ InSv → unsaved/wounds = 2/3；近战：无保存（7+）→ 1
        assert _ratio(shoot.unsaved, shoot.wounds) == pytest.approx(2 / 3,
                                                                    abs=0.02)
        assert _ratio(melee.unsaved, melee.wounds) == pytest.approx(1.0,
                                                                    abs=0.02)

    def test_purge_and_sanctify_wound_penalty_needs_s_gt_t(self, entries):
        # 净化！圣化！：S5 vs T4（S>T）3+ → -1 → 4+（1/2）；S4 vs T4 不受影响 1/2
        ps = _entry(entries, "det000010395")
        tgt, _, _ = inject_target(_target(t=4, sv=7), [ps], frozenset())
        high_s = _run(_attacker(_melee(s=5)), tgt, Stance(phase="melee"))
        even_s = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(high_s.wounds, high_s.hits) == pytest.approx(1 / 2,
                                                                   abs=0.02)
        assert _ratio(even_s.wounds, even_s.hits) == pytest.approx(1 / 2,
                                                                   abs=0.02)

    def test_consecrating_aura_needs_defender_bearer_toggle(self, entries):
        # 守护圣环：defender_bearer_leading 关 → 不注入（AP-3 无保存）；开 → 5+ InSv
        aura = _entry(entries, "000010396003")
        tgt_off, _, notes = inject_target(_target(sv=4), [aura], frozenset())
        tgt_on, _, _ = inject_target(_target(sv=4), [aura],
                                  frozenset({"defender_bearer_leading"}))
        assert any("defender_bearer_leading" in n for n in notes)
        gun = WeaponProfile(name_zh=None, name_en="gun", range='24"',
                            attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=-3,
                            damage=DiceExpr(k=1), effects=(), count=1)
        off = _run(_attacker(gun), tgt_off, Stance(phase="shooting"))
        on = _run(_attacker(gun), tgt_on, Stance(phase="shooting"))
        assert _ratio(off.unsaved, off.wounds) == pytest.approx(1.0, abs=0.02)
        assert _ratio(on.unsaved, on.wounds) == pytest.approx(2 / 3, abs=0.02)


@needs_db
class TestRealUnitSmoke:
    def test_sword_brethren_loads_bt_entries(self):
        # 真单位冒烟（PR4 教训：单测全绿也逮不到 load_unit_dsl 漏扫某表）
        from engines.simulator.profile import load_unit_dsl
        entries = load_unit_dsl(str(DB), "000002798")   # Sword Brethren Squad
        ids = {e.row_id for e in entries}
        assert "000008526" in ids            # 军规誓言
        assert "fp11e-bt-marshals-s1" in ids  # 补录战略
        assert "fp11e-bt-miracle-e1" in ids   # 补录增强（enhancements 表投影）
        assert "det000009842" in ids          # 物化分队规则
