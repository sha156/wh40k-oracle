# tests/test_simulator_dsl_pr26_payload.py
"""P7-PR26 Chaos Daemons（混沌恶魔，faction='CD'）全量 DSL 编码落账：13 个分队容器
（6 个 Index/Codex + 4 个登舰行动 + 3 个 fp_new）的分队规则 + 战略 + 增强 = 122
（1 encoded / 25 partial / 96 not_modeled）——零新引擎通道、零新态势开关。

混沌恶魔是「区域态 + 战栗 + 召唤/预备队」气质阵营：军规 Shadow of Chaos、Daemonic
Manifestation/Terror、Flux token、Surge move、深入打击落点、复活/治疗、致命伤池均无
引擎载体，故可编率低。可编子集集中在 AP 改善 / S 特征值 / 命中·致伤骰修正 / 暴击阈值 /
FNP / [LANCE]（melee_charging）/ [IGNORES COVER] / [LETHAL HITS] / 重投命中。

fp_new 三全新分队 Cavalcade of Chaos / Lords of the Warp / Warptide
（fp11e-chaosdaemons-*）由 db_compile/fp_rules_patches.json inserts 补录；
5 条 text_patch（Warp Rifts 9"→8"、First Prince of Chaos 两分支、Murdercall、
SHADE PATH、FOOLS' FLIGHT）同批落账。CD 无 removed_11e 行（FP 对现有分队均为重印）。
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
PAYLOAD = Path("dsl_payloads/chaosdaemons.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 13 个混沌恶魔分队容器名（stratagems.detachment / enhancements.detachment_name）
CD_DETACHMENTS = (
    "Daemonic Incursion", "Shadow Legion", "Blood Legion", "Scintillating Legion",
    "Plague Legion", "Legion of Excess", "Dread Carnival", "Infernal Onslaught",
    "Pandaemoniac Inferno", "Rotten and Rusted",
    "Cavalcade of Chaos", "Lords of the Warp", "Warptide",
)


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="hellblade"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="warpflame", rng='18"'):
    return WeaponProfile(name_zh=None, name_en=name, range=rng,
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _attacker(*weapons):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=tuple(weapons))


def _target(t=4, sv=7, models=5, w=1, invuln=None, keywords=frozenset(), effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=w, oc=1,
                         keywords=keywords, effects=tuple(effects))


def _entry(entries, row_id):
    return next(e for e in entries if e.row_id == row_id)


def _run(atk, target, stance):
    return run_sequence(atk, target, stance, n=N, seed=42)


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


# ══ 结构与 DB 对账 ═══════════════════════════════════════════════════════
class TestPayloadShape:
    def test_counts(self, entries):
        assert len(entries) == 122
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 1, "partial": 25, "not_modeled": 96}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        # 14 库内分队规则 + 3 fp_new；56 库内战略 + 10 fp_new；34 库内增强 + 5 fp_new
        assert by == {"abilities": 17, "stratagems": 66, "enhancements": 39}

    def test_faction_is_cd(self, entries):
        assert all(e.faction == "CD" for e in entries)

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id

    def test_encoded_entries_have_effects_and_no_notes(self, entries):
        # encoded = 原文全部从句落地且无未建模限制；有残量注记的一律降 partial
        for e in entries:
            if e.status == "encoded":
                assert e.effects and not e.not_modeled_notes_zh, e.row_id

    def test_not_modeled_have_reason(self, entries):
        for e in entries:
            if e.status == "not_modeled":
                assert not e.effects and e.not_modeled_notes_zh, e.row_id

    def test_bearer_limited_entries_gated_by_toggle(self, entries):
        # 携带者限定 / 光环范围假设的条目不得无条件注入——必须挂 bearer 开关
        for rid, tog in (("000008438002", "bearer_leading"),        # A'rgath
                         ("000008438004", "defender_bearer_leading"),  # Endless Gift
                         ("000008438005", "bearer_leading"),        # Everstave
                         ("000009815002", "bearer_leading"),        # Slaughterthirst
                         ("000009815003", "bearer_leading"),        # Fury's Cage
                         ("000009806002", "bearer_leading"),        # False Majesty
                         ("000009806003", "bearer_leading"),        # Dreaming Crown
                         ("000009819005", "bearer_leading"),        # Font of Spores
                         ("000009810004", "bearer_leading"),        # Neverblade
                         ("000009572002", "bearer_leading"),        # Fatal Caress
                         ("000009580002", "defender_bearer_leading")):  # Fulgurating
            assert tog in _entry(entries, rid).requires_toggles, rid

    def test_upgrade_scope_entries_have_no_bearer_toggle(self, entries):
        # 反面：原文是 UPGRADE「This unit's ...」整单位生效的，不得挂 bearer 开关
        assert not _entry(entries, "fp11e-chaosdaemons-warptide-e1").requires_toggles

    def test_no_new_engine_channel(self, entries):
        # 纯编码 PR：所有 (phase, op) 必须是既有通道
        known = {
            ("save", "ap_improve"), ("save", "ignores_cover"),
            ("fnp", "fnp"), ("hit", "modify"), ("hit", "reroll"),
            ("hit", "crit_threshold"), ("hit", "auto_wound"),
            ("wound", "modify"), ("wound", "s_improve"), ("wound", "reroll"),
            ("wound", "crit_threshold"), ("attacks", "modify"),
        }
        for e in entries:
            for f in e.effects:
                assert (f.phase, f.op) in known, (e.row_id, f.phase, f.op)

    def test_no_new_toggle(self, entries):
        # 零新态势开关：只复用 PR4/PR6 既有的两个 bearer 通用假设
        used = {t for e in entries for t in e.requires_toggles}
        assert used == {"bearer_leading", "defender_bearer_leading"}


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(CD_DETACHMENTS)), CD_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(CD_DETACHMENTS)), CD_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        rule_ids = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='CD'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == rule_ids

    def test_cd_has_no_removed_11e_rows(self, entries):
        # FP 对 6 个现有分队均为重印且逐条一致（除 5 条 text_patch），零删减
        con = self._db()
        dead = con.execute(
            "SELECT COUNT(*) FROM stratagems WHERE faction='CD' "
            "AND fp_status='removed_11e'").fetchone()[0]
        dead += con.execute(
            "SELECT COUNT(*) FROM enhancements WHERE faction_id='CD' "
            "AND fp_status='removed_11e'").fetchone()[0]
        con.close()
        assert dead == 0

    def test_fp_new_rows_marked_added_11e(self):
        con = self._db()
        added = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-chaosdaemons-%'")}
        added |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-chaosdaemons-%'")}
        con.close()
        assert len(added) == 15          # 10 战略 + 5 增强（分队行不带 fp_status 列）

    def test_11e_text_patches_landed(self):
        # 5 条 A/B 真漂移必须已落库（fp-rules 先于 dsl-apply）
        con = self._db()
        wr = con.execute("SELECT rule_text FROM detachments "
                         "WHERE id='000008436'").fetchone()[0]
        assert 'instead of more than 8".' in wr and 'more than 9"' not in wr
        fpc = con.execute("SELECT rule_text FROM detachments "
                          "WHERE id='000009978'").fetchone()[0]
        assert "Each time a melee attack targets this unit" in fpc
        assert "snap shooting attacks" in fpc
        assert "Fire</span> <span class=\"tt kwbu\">Overwatch" not in fpc
        mc = con.execute("SELECT rule_text FROM detachments "
                         "WHERE id='000009813'").fetchone()[0]
        assert mc.startswith("In your opponent’s Movement phase,")
        assert 'ends a move within 8"' in mc
        sp = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009979006'").fetchone()[0]
        assert "Start of your opponent’s Charge phase." in sp
        assert "-1 to Charge rolls" in sp
        ff = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009816006'").fetchone()[0]
        assert "unengaged" in ff and "Charge bonus" not in ff
        con.close()

    def test_fingerprints_match_db(self, entries):
        from db_compile.dsl_apply import _fingerprint
        con = self._db()
        for e in entries:
            if not e.effects:
                continue
            if e.table == "abilities":
                src = con.execute("SELECT rule_text FROM detachments WHERE id=?",
                                  (e.row_id[3:],)).fetchone()
            elif e.table == "stratagems":
                src = con.execute("SELECT text_zh FROM stratagems WHERE id=?",
                                  (e.row_id,)).fetchone()
            else:
                src = con.execute("SELECT description FROM enhancements WHERE id=?",
                                  (e.row_id,)).fetchone()
            assert src is not None, e.row_id
            assert _fingerprint(src[0]) == e.provenance["text_sha256"], e.row_id
        con.close()


# ══ 守方向：真源 payload 引擎级差别 ════════════════════════════════════
class TestDefensiveFromPayload:
    def test_incorporeal_terrors_hit_minus1_shooting_only(self, entries):
        # 无形恐怖（Daemonic Incursion 登舰战略，本 PR 唯一 encoded）：
        # WHEN=对手射击阶段 → 只在射击注入
        it = _entry(entries, "000009548005")
        assert it.status == "encoded"
        tgt, _, _ = inject_target(_target(), [it], frozenset())
        base = _run(_attacker(_gun(bs=3)), _target(), Stance(phase="shooting"))
        r = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)
        # 近战阶段不放行
        bm = _run(_attacker(_melee(ws=3)), _target(), Stance(phase="melee"))
        rm = _run(_attacker(_melee(ws=3)), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(
            _ratio(bm.hits, bm.attacks), abs=0.02)

    def test_overwhelming_excess_hit_minus1_both_phases(self, entries):
        # 过度泛滥（Legion of Excess 战略）：WHEN=对手射击阶段**或**战斗阶段 → 两相位
        oe = _entry(entries, "000009807007")
        assert all(not f.condition for f in oe.effects)
        tgt, _, _ = inject_target(_target(), [oe], frozenset())
        for phase, wpn in (("shooting", _gun(bs=3)), ("melee", _melee(ws=3))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_seductive_whispers_melee_only(self, entries):
        # 魅惑低语（Dread Carnival 登舰战略）：WHEN=战斗阶段 → 只在近战注入
        sw = _entry(entries, "000009573002")
        assert all(f.condition == ("phase_melee",) for f in sw.effects)
        tgt, _, _ = inject_target(_target(), [sw], frozenset())
        rm = _run(_attacker(_melee(ws=3)), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)
        rs = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_foul_resilience_fnp5_both_phases(self, entries):
        # 污秽韧性（Rotten and Rusted 登舰战略）：WHEN=两相位 → 不加相位门
        fr = _entry(entries, "000009565002")
        assert all(not f.condition for f in fr.effects)
        tgt, _, _ = inject_target(_target(w=1), [fr], frozenset())
        for phase, wpn in (("shooting", _gun(ap=-6)), ("melee", _melee(ap=-6))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.damage, r.unsaved) == pytest.approx(2 / 3, abs=0.03)

    def test_endless_gift_fnp5_needs_bearer_toggle(self, entries):
        # 无尽馈赠（Daemonic Incursion 增强）：只给携带者模型 → 必须挂守方携带者开关
        eg = _entry(entries, "000008438004")
        _, _, notes = inject_target(_target(), [eg], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(w=1), [eg],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_melee(ap=-6)), tgt, Stance(phase="melee"))
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2 / 3, abs=0.03)

    def test_fulgurating_presence_hit_minus1_needs_bearer_toggle(self, entries):
        # 闪耀存在（Pandaemoniac Inferno 登舰增强）：只针对瞄准携带者的攻击，两相位
        fp = _entry(entries, "000009580002")
        _, _, notes = inject_target(_target(), [fp], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(), [fp],
                                  frozenset({"defender_bearer_leading"}))
        for phase, wpn in (("shooting", _gun(bs=3)), ("melee", _melee(ws=3))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)


# ══ 攻方向：真源 payload 引擎级差别 ════════════════════════════════════
class TestOffensiveFromPayload:
    def test_draught_of_terror_ap_improve_both_phases(self, entries):
        # 恐惧之饮（Daemonic Incursion 战略）：AP 改善 1，射击/近战两相位
        dt = _entry(entries, "000008437004")
        assert all(not f.condition for f in dt.effects)
        for phase, wpn in (("shooting", _gun(ap=0)), ("melee", _melee(ap=0))):
            atk, _, _ = inject_attacker(_attacker(wpn), [dt], frozenset())
            base = _run(_attacker(wpn), _target(sv=4), Stance(phase=phase))
            r = _run(atk, _target(sv=4), Stance(phase=phase))
            # AP0 vs Sv4+（1/2 过）→ AP-1 → 5+（1/3 过）
            assert _ratio(base.unsaved, base.wounds) == pytest.approx(1 / 2, abs=0.02)
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_pyrogenesis_s_improve_both_phases(self, entries):
        # 烈焰创生（Scintillating Legion 战略）：S +2，两相位
        pg = _entry(entries, "000009811003")
        for phase, wpn in (("shooting", _gun(s=4)), ("melee", _melee(s=4))):
            atk, _, _ = inject_attacker(_attacker(wpn), [pg], frozenset())
            base = _run(_attacker(wpn), _target(t=4), Stance(phase=phase))
            r = _run(atk, _target(t=4), Stance(phase=phase))
            # S4 vs T4 → 4+（1/2）；S6 vs T4 → 3+（2/3）
            assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
            assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_fever_visions_hit_plus1_both_phases(self, entries):
        # 热病幻象（Plague Legion 战略）：命中 +1，两相位
        fv = _entry(entries, "000009820003")
        assert all(not f.condition for f in fv.effects)
        for phase, wpn in (("shooting", _gun(bs=4)), ("melee", _melee(ws=4))):
            atk, _, _ = inject_attacker(_attacker(wpn), [fv], frozenset())
            r = _run(atk, _target(), Stance(phase=phase))
            assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_archagonists_wound_plus1_melee_only(self, entries):
        # 极致痛师（Legion of Excess 战略）：WHEN=战斗阶段 → 致伤 +1 仅近战
        ag = _entry(entries, "000009807003")
        assert all(f.condition == ("phase_melee",) for f in ag.effects)
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ag], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [ag], frozenset())
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_channelled_wrath_lance_is_melee_charging(self, entries):
        # 引导之怒（Shadow Legion 战略）：[LANCE] ＝ 冲锋回合近战致伤 +1
        cw = _entry(entries, "000009979003")
        assert all(f.condition == ("melee_charging",) for f in cw.effects)
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [cw], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 非冲锋回合不生效
        rn = _run(atk, _target(t=4), Stance(phase="melee", charging=False))
        assert _ratio(rn.wounds, rn.hits) == pytest.approx(1 / 2, abs=0.02)
        # 射击阶段不生效（即便本回合冲锋过）
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [cw], frozenset())
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting", charging=True))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_seductive_gambit_reroll_hits_melee_charging(self, entries):
        # 诱敌之赌（Legion of Excess 分队规则）：冲锋结束后声明 → 本回合只剩战斗阶段
        sg = _entry(entries, "det000009805")
        assert all(f.condition == ("melee_charging",) for f in sg.effects)
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4)), [sg], frozenset())
        base = _run(_attacker(_melee(ws=4)), _target(),
                    Stance(phase="melee", charging=True))
        r = _run(atk, _target(), Stance(phase="melee", charging=True))
        # WS4+ 重投失败 → 1/2 + 1/2*1/2 = 3/4
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(3 / 4, abs=0.02)
        # 非冲锋回合与射击阶段均不放行
        rn = _run(atk, _target(), Stance(phase="melee", charging=False))
        assert _ratio(rn.hits, rn.attacks) == pytest.approx(1 / 2, abs=0.02)
        atk_s, _, _ = inject_attacker(_attacker(_gun(bs=4)), [sg], frozenset())
        rs = _run(atk_s, _target(), Stance(phase="shooting", charging=True))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_skirling_magicks_lethal_hits_shooting_only(self, entries):
        # 尖啸魔法（Lords of the Warp fp_new 战略）：远程 [LETHAL HITS]
        sm = _entry(entries, "fp11e-chaosdaemons-lordswarp-s4")
        assert all(f.condition == ("phase_shooting",) for f in sm.effects)
        # S3 vs T6 → 需 5+；[LETHAL HITS] 让暴击命中直接致伤
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3, s=3)), [sm], frozenset())
        base = _run(_attacker(_gun(bs=3, s=3)), _target(t=6), Stance(phase="shooting"))
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) > _ratio(base.wounds, base.hits)
        # 近战不放行
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=3, s=3)), [sm], frozenset())
        bm = _run(_attacker(_melee(ws=3, s=3)), _target(t=6), Stance(phase="melee"))
        rm = _run(atk_m, _target(t=6), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(
            _ratio(bm.wounds, bm.hits), abs=0.02)

    def test_call_to_murder_attacks_plus1_melee_charging(self, entries):
        # 屠戮号令（Lords of the Warp fp_new 战略）：WHEN 要求本回合冲锋过才出手
        cm = _entry(entries, "fp11e-chaosdaemons-lordswarp-s2")
        assert all(f.condition == ("melee_charging",) for f in cm.effects)
        atk, _, _ = inject_attacker(_attacker(_melee()), [cm], frozenset())
        base = _run(_attacker(_melee()), _target(), Stance(phase="melee", charging=True))
        r = _run(atk, _target(), Stance(phase="melee", charging=True))
        assert r.attacks.mean() == pytest.approx(2 * base.attacks.mean(), rel=0.02)
        # 非冲锋回合不生效
        rn = _run(atk, _target(), Stance(phase="melee", charging=False))
        assert rn.attacks.mean() == pytest.approx(base.attacks.mean(), rel=0.02)

    def test_encroaching_darkness_ignores_cover_shooting_only(self, entries):
        # 逼近黑暗（Shadow Legion 战略）：武器获 [IGNORES COVER]
        ed = _entry(entries, "000009979005")
        assert all(f.condition == ("phase_shooting",) for f in ed.effects)
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [ed], frozenset())
        cover = Stance(phase="shooting", target_in_cover=True)
        base = _run(_attacker(_gun(bs=3)), _target(sv=4), cover)
        r = _run(atk, _target(sv=4), cover)
        assert _ratio(r.hits, base.hits) > 1.0

    def test_seeping_virulence_crit_threshold_melee_only(self, entries):
        # 渗漏毒性（Plague Legion 战略）：近战未修正命中 5+ 即暴击。
        # 暴击命中恒算命中（11版 24.14），故对 WS6+ 武器可直接观测命中率变化。
        sv = _entry(entries, "000009820002")
        assert all(f.condition == ("phase_melee",) for f in sv.effects)
        atk, _, _ = inject_attacker(_attacker(_melee(ws=6)), [sv], frozenset())
        base = _run(_attacker(_melee(ws=6)), _target(), Stance(phase="melee"))
        r = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 6, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        # 射击阶段不放行
        atk_s, _, _ = inject_attacker(_attacker(_gun(bs=6)), [sv], frozenset())
        rs = _run(atk_s, _target(), Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 6, abs=0.02)

    def test_argath_attacks_and_strength_melee_only(self, entries):
        # 阿尔加斯（Daemonic Incursion 增强）：携带者近战武器 A+1 与 S+1
        ag = _entry(entries, "000008438002")
        _, _, notes = inject_attacker(_attacker(_melee()), [ag], frozenset())
        assert any("bearer_leading" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ag],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(_melee(s=4)), _target(t=5), Stance(phase="melee"))
        r = _run(atk, _target(t=5), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2 * base.attacks.mean(), rel=0.02)
        # S4 vs T5 → 5+（1/3）；S5 vs T5 → 4+（1/2）
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)
        # 射击阶段不放行
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [ag],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(t=5), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_everstave_strength_shooting_only(self, entries):
        # 永恒法杖（Daemonic Incursion 增强）：携带者远程武器 S+1，近战不放行
        es = _entry(entries, "000008438005")
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [es],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=5), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [es],
                                      frozenset({"bearer_leading"}))
        rm = _run(atk_m, _target(t=5), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_slaughterthirst_aura_lance_melee_charging(self, entries):
        # 嗜血渴望（Blood Legion 增强，光环授 [LANCE]）：冲锋回合近战致伤 +1
        st = _entry(entries, "000009815002")
        _, _, notes = inject_attacker(_attacker(_melee()), [st], frozenset())
        assert any("bearer_leading" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [st],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        rn = _run(atk, _target(t=4), Stance(phase="melee", charging=False))
        assert _ratio(rn.wounds, rn.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_furys_cage_double_reroll_melee_only(self, entries):
        # 怒火之笼（Blood Legion 增强）：携带者出手时重投命中与致伤（近战门）
        fc = _entry(entries, "000009815003")
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4, s=4)), [fc],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(3 / 4, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(3 / 4, abs=0.02)
        # 射击阶段不放行
        atk_s, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [fc],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_dreaming_crown_and_false_majesty_melee_only(self, entries):
        # 梦寐之冠（命中 +1）与虚妄威仪（致伤 +1）：均为近战光环
        dc = _entry(entries, "000009806003")
        fm = _entry(entries, "000009806002")
        for e in (dc, fm):
            assert all(f.condition == ("phase_melee",) for f in e.effects)
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4, s=4)), [dc, fm],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk_s, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [dc, fm],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_font_of_spores_ap_improve_both_phases(self, entries):
        # 孢子之泉（Plague Legion 增强光环）：AP 改善 1，原文无相位措辞 → 两相位
        fs = _entry(entries, "000009819005")
        assert all(not f.condition for f in fs.effects)
        for phase, wpn in (("shooting", _gun(ap=0)), ("melee", _melee(ap=0))):
            atk, _, _ = inject_attacker(_attacker(wpn), [fs],
                                        frozenset({"bearer_leading"}))
            r = _run(atk, _target(sv=4), Stance(phase=phase))
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_neverblade_four_clause_melee_only(self, entries):
        # 永恒之刃（Scintillating Legion 增强）：S+2 / A+1 / AP 改善 1 / 命中 +1，全近战
        nb = _entry(entries, "000009810004")
        assert len(nb.effects) == 4
        assert all(f.condition == ("phase_melee",) for f in nb.effects)
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4, s=4, ap=0)), [nb],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(_melee(ws=4, s=4, ap=0)), _target(t=4, sv=4),
                    Stance(phase="melee"))
        r = _run(atk, _target(t=4, sv=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2 * base.attacks.mean(), rel=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)   # S6 vs T4
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)  # AP-1

    def test_fatal_caress_wound_crit_threshold_melee_only(self, entries):
        # 致命爱抚（Dread Carnival 登舰增强）：近战未修正致伤 5+ 即暴击。
        # 致伤暴击阈值本身不改致伤率，用 AP-6 + 3+ 甲下的「暴击不吃暴击专属效果」不可观测，
        # 故改以「阈值 ≤ 致伤所需骰面时暴击放宽会让 S<T 场景致伤率上升」验证。
        fc = _entry(entries, "000009572002")
        assert all(f.condition == ("phase_melee",) for f in fc.effects)
        atk, _, _ = inject_attacker(_attacker(_melee(s=3)), [fc],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(_melee(s=3)), _target(t=6), Stance(phase="melee"))
        r = _run(atk, _target(t=6), Stance(phase="melee"))
        # S3 vs T6（2S=T）→ 需 6+（1/6）；暴击阈值 5+ → 5、6 均致伤（1/3）
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 6, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_baneforged_weapons_strength_both_phases(self, entries):
        # 祸铸武装（Warptide fp_new 增强，UPGRADE 整单位）：S+1，两相位，不挂 bearer
        bw = _entry(entries, "fp11e-chaosdaemons-warptide-e1")
        assert not bw.requires_toggles
        assert all(not f.condition for f in bw.effects)
        for phase, wpn in (("shooting", _gun(s=4)), ("melee", _melee(s=4))):
            atk, _, _ = inject_attacker(_attacker(wpn), [bw], frozenset())
            r = _run(atk, _target(t=5), Stance(phase=phase))
            assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)


# ══ 诚实边界：高频过度建模陷阱的反向断言 ═══════════════════════════════
class TestHonestyBoundaries:
    @pytest.mark.parametrize("row_id, why", [
        ("det000009978", "四神互斥分支（己方单位神祇关键词门）无载体"),
        ("fp11e-chaosdaemons-warptide-s3", "远程 × S>T 无 shooting_wound_s_gt_t 复合 tag"),
        ("000009816007", "Sv 特征值设定为 3+ 属 SET，非增量，无载体"),
        ("000008437007", "仅重投无效保护骰的「1」（非重投失败）无载体"),
        ("000009581002", "仅重投保存骰的「1」（非重投失败）无载体"),
        ("000009810005", "仅对灵能攻击与致命伤的 FNP 无载体"),
        ("000009819002", "负关键词门（排除 MONSTERS/VEHICLES）+ 战栗检定无载体"),
        ("det000009809", "Flux token 经济状态机无载体"),
        ("det000009813", "Surge move（移动域）无载体"),
        ("det000008436", "深入打击落点（部署几何）无载体"),
        ("det000009579", "第三方友军接战几何门无载体，裸编 [SUSTAINED HITS 1] 过度施加"),
        ("000009564003", "W 特征值 +2——引擎无 Wounds 特征值修正通道"),
        ("fp11e-chaosdaemons-lordswarp-s1", "Fights First（出手顺序域）无载体"),
        ("fp11e-chaosdaemons-warptide-s2", "侦测范围（detection range）无载体"),
        ("000009547002", "令敌方武器获 [HAZARDOUS]（攻击方自伤）从守方侧无载体"),
    ])
    def test_known_traps_stay_not_modeled(self, entries, row_id, why):
        e = _entry(entries, row_id)
        assert e.status == "not_modeled", (row_id, why)
        assert not e.effects
        assert e.not_modeled_notes_zh
