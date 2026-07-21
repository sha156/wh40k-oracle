# tests/test_simulator_dsl_pr22_payload.py
"""P7-PR22 Chaos Knights（混沌骑士，faction='QT'）全量 DSL 编码落账：8 个分队
（6 现有 + 2 新 fp_new）的分队规则 + 战略 + 增强 = 75（4 encoded / 16 partial /
55 not_modeled）——零新引擎通道、零新态势开关。

混沌骑士与帝国骑士（PR21）同为超重型步行机甲阵营，可编率同样低——技能以 Dread 技能
选择、Empowered 状态机、光环共享、侦测范围、致命伤/治疗、移动/据点/CP 经济为主。
可编子集集中在守方 AP 恶化 / invuln / FNP / T+1 / 伤害-1 / Stealth=掩体，与攻方
[SUSTAINED HITS 1] / [IGNORES COVER] / 暴击阈值 / 近战 AP+1 / 近战 WS+1。

fp_new 两全新分队 Bastions of Tyranny / Hunting Warpack（fp11e-chaosknights-*）由
db_compile/fp_rules_patches.json inserts 补录；Iconoclast Fiefdom 11 版完整重印的
3 条 text_patch + 9 条 removed_11e + 4 条新增插行同批落账，removed_11e 行零覆盖。
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
PAYLOAD = Path("dsl_payloads/chaosknights.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 8 个混沌骑士分队容器名（stratagems.detachment / enhancements.detachment_name）
QT_DETACHMENTS = (
    "Traitoris Lance", "Iconoclast Fiefdom", "Infernal Lance",
    "Lords of Dread", "Houndpack Lance", "Helhunt Lance",
    "Bastions of Tyranny", "Hunting Warpack",
)
# 8 条分队规则物化条目 id（det + detachments 源行 id；末二为 fp_new）
QT_RULE_IDS = (
    "det000008518", "det000009764", "det000010303", "det000010307",
    "det000010311", "det000010750",
    "detfp11e-chaosknights-bastions", "detfp11e-chaosknights-hunting",
)


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="reaper chainsword"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="avenger chaincannon", rng='24"'):
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
        assert len(entries) == 75
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 4, "partial": 16, "not_modeled": 55}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        # 战略 44 行 − 5 removed_11e = 39；增强 32 行 − 4 removed_11e = 28
        assert by == {"abilities": 8, "stratagems": 39, "enhancements": 28}

    def test_faction_is_qt(self, entries):
        assert all(e.faction == "QT" for e in entries)

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

    def test_bearer_limited_enhancements_gated_by_toggle(self, entries):
        # 携带者限定的增强不得无条件注入——必须挂 bearer 开关
        for rid, tog in (("000008516005", "defender_bearer_leading"),
                         ("000010304002", "bearer_leading"),
                         ("000010304004", "defender_bearer_leading"),
                         ("000010308007", "defender_bearer_leading"),
                         ("000010312005", "defender_bearer_leading")):
            assert tog in _entry(entries, rid).requires_toggles, rid

    def test_no_new_engine_channel(self, entries):
        # 纯编码 PR：所有 (phase, op) 必须是既有通道
        known = {
            ("save", "ap_improve"), ("save", "invuln"), ("save", "cover"),
            ("save", "ignores_cover"), ("fnp", "fnp"), ("hit", "extra_hits"),
            ("hit", "crit_threshold"), ("hit", "bs_improve"), ("hit", "modify"),
            ("wound", "t_improve"), ("damage", "damage_reduction"),
        }
        for e in entries:
            for f in e.effects:
                assert (f.phase, f.op) in known, (e.row_id, f.phase, f.op)


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(QT_DETACHMENTS)), QT_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(QT_DETACHMENTS)), QT_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_removed_11e_rows_have_zero_coverage(self, entries):
        # Iconoclast Fiefdom 11 版完整重印未收录的 9 行必须零覆盖（沿 PR18 先例）
        con = self._db()
        dead = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='QT' "
            "AND fp_status='removed_11e'")}
        dead |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='QT' "
            "AND fp_status='removed_11e'")}
        con.close()
        assert len(dead) == 9
        assert not (dead & {e.row_id for e in entries})

    def test_all_detachment_rules_covered(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == set(QT_RULE_IDS)

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
    def test_beasthide_manifestation_ap_worsen_both_phases(self, entries):
        # 兽皮显化（Helhunt Lance 战略）：被攻 AP 恶化 1，射击/近战两相位均注入
        bm = _entry(entries, "000010752004")
        for phase, wpn in (("shooting", _gun(ap=-1)), ("melee", _melee(ap=-1))):
            base = _run(_attacker(wpn), _target(sv=4), Stance(phase=phase))
            tgt, _, _ = inject_target(_target(sv=4), [bm], frozenset())
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            # AP-1 vs Sv4+ → 5+（1/3 过）；恶化回 AP0 → 4+（1/2 过）
            assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_hellforged_construction_melee_only(self, entries):
        # 地狱锻造（Infernal Lance 战略）：WHEN=近战阶段 → 只在近战注入
        hc = _entry(entries, "000010305003")
        tgt, _, _ = inject_target(_target(sv=4), [hc], frozenset())
        rm = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 射击阶段不放行：仍是 AP-1 → 5+
        rs = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_stalking_focus_shooting_only(self, entries):
        # 潜行专注（Hunting Warpack 战略）：原文明写 Ranged attacks → 只射击门
        sf = _entry(entries, "fp11e-chaosknights-hunting-s3")
        tgt, _, _ = inject_target(_target(sv=4), [sf], frozenset())
        rs = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)
        rm = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_diabolic_bulwark_invuln_shooting_only(self, entries):
        # 恶魔壁垒（Infernal Lance 战略）：对手射击阶段 4+ invuln，近战不注入
        db = _entry(entries, "000010305007")
        tgt, _, _ = inject_target(_target(sv=7), [db], frozenset())
        rs = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)
        rm = _run(_attacker(_melee(ap=-6)), tgt, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1.0, abs=0.02)

    def test_veil_of_medrengard_two_tier_invuln(self, entries):
        # 梅德朗加德之幕（Traitoris Lance 增强）：射击 4+ / 近战 5+ 分门，须携带者开关
        vm = _entry(entries, "000008516005")
        _, _, notes = inject_target(_target(), [vm], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(sv=7), [vm],
                                  frozenset({"defender_bearer_leading"}))
        rs = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)
        rm = _run(_attacker(_melee(ap=-6)), tgt, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_disdain_for_the_weak_fnp6_melee_only(self, entries):
        # 蔑视弱者（Traitoris Lance 战略）：WHEN=近战阶段 → FNP 6+ 只在近战注入
        dw = _entry(entries, "000008517004")
        tgt, _, _ = inject_target(_target(w=1), [dw], frozenset())
        rm = _run(_attacker(_melee(ap=-6)), tgt, Stance(phase="melee"))
        assert _ratio(rm.damage, rm.unsaved) == pytest.approx(5 / 6, abs=0.03)
        rs = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.damage, rs.unsaved) == pytest.approx(1.0, abs=0.02)

    def test_insensate_bloodthirst_fnp5_melee_only(self, entries):
        # 狂乱嗜血（Hunting Warpack 战略）：WHEN=近战阶段 → FNP 5+ 只在近战注入
        ib = _entry(entries, "fp11e-chaosknights-hunting-s1")
        tgt, _, _ = inject_target(_target(w=1), [ib], frozenset())
        rm = _run(_attacker(_melee(ap=-6)), tgt, Stance(phase="melee"))
        assert _ratio(rm.damage, rm.unsaved) == pytest.approx(2 / 3, abs=0.03)
        rs = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.damage, rs.unsaved) == pytest.approx(1.0, abs=0.02)

    def test_runes_of_disdain_damage_reduction_both_phases(self, entries):
        # 蔑视符文（Lords of Dread 战略）：伤害-1，射击/近战两相位
        rd = _entry(entries, "000010309004")
        tgt, _, _ = inject_target(_target(sv=7, w=3), [rd], frozenset())
        for phase, wpn in (("shooting", _gun(ap=-6, d=3)),
                           ("melee", _melee(ap=-6, d=3))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.damage, r.unsaved) == pytest.approx(2.0, abs=0.05)

    def test_fleshmetal_fusion_t_improve(self, entries):
        # 血肉金属融合（Infernal Lance 增强）：携带者 T+1，须守方携带者开关
        ff = _entry(entries, "000010304004")
        _, _, notes = inject_target(_target(), [ff], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        base = _run(_attacker(_gun(s=5)), _target(t=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(t=4), [ff],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_gun(s=5)), tgt, Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_storm_of_darkness_stealth_is_cover_shooting_only(self, entries):
        # 暗影风暴（Traitoris Lance 战略）：11 版 Stealth=掩体收益（命中侧 BS 惩罚），
        # 「获 Stealth」与「获掩体收益」两从句收敛为同一二元状态，只编一份；近战不注入
        sd = _entry(entries, "000008517007")
        assert len(sd.effects) == 1
        base = _run(_attacker(_gun(bs=3)), _target(sv=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=4), [sd], frozenset())
        r = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, base.hits) < 1.0          # 掩体 → 命中侧惩罚
        # 近战阶段不注入：命中率与基线一致
        bm = _run(_attacker(_melee(ws=3)), _target(sv=4), Stance(phase="melee"))
        rm = _run(_attacker(_melee(ws=3)), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, bm.hits) == pytest.approx(1.0, abs=0.02)

    def test_panoply_ap_worsen_needs_bearer_toggle(self, entries):
        # 受咒骑士全装（Houndpack Lance 增强）：针对携带者的攻击 AP 恶化 1，两相位
        pk = _entry(entries, "000010312005")
        _, _, notes = inject_target(_target(), [pk], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(sv=4), [pk],
                                  frozenset({"defender_bearer_leading"}))
        for phase, wpn in (("shooting", _gun(ap=-1)), ("melee", _melee(ap=-1))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_intimidating_reminder_incoming_hit_minus1(self, entries):
        # 威慑警示（Bastions of Tyranny 战略）：被压制的敌单位攻击命中 -1（守方向，两相位）
        ir = _entry(entries, "fp11e-chaosknights-bastions-s3")
        base = _run(_attacker(_gun(bs=3)), _target(), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(), [ir], frozenset())
        r = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)
        # 近战同样生效（suppressed 覆盖对手整个回合）
        rm = _run(_attacker(_melee(ws=3)), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_blessing_of_dark_master_cover_shooting_only(self, entries):
        # 黑暗主宰的祝福（Lords of Dread 增强）：携带者 Stealth=掩体，仅射击
        bd = _entry(entries, "000010308007")
        tgt, _, _ = inject_target(_target(sv=4), [bd],
                                  frozenset({"defender_bearer_leading"}))
        base = _run(_attacker(_gun(bs=3)), _target(sv=4), Stance(phase="shooting"))
        r = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, base.hits) < 1.0
        bm = _run(_attacker(_melee(ws=3)), _target(sv=4), Stance(phase="melee"))
        rm = _run(_attacker(_melee(ws=3)), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, bm.hits) == pytest.approx(1.0, abs=0.02)


# ══ 攻方向：真源 payload 引擎级差别 ════════════════════════════════════
class TestOffensiveFromPayload:
    def test_warp_vision_ignores_cover_shooting_only(self, entries):
        # 次元视界（Infernal Lance 战略）：远程武器 [IGNORES COVER]
        wv = _entry(entries, "000010305006")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [wv], frozenset())
        cover = Stance(phase="shooting", target_in_cover=True)
        base = _run(_attacker(_gun(bs=3)), _target(sv=4), cover)
        r = _run(atk, _target(sv=4), cover)
        assert _ratio(r.hits, base.hits) > 1.0

    def test_snarling_rivalry_ignores_cover(self, entries):
        # 咆哮竞逐（Hunting Warpack 增强，UPGRADE 整单位生效）：远程 [IGNORES COVER]
        sr = _entry(entries, "fp11e-chaosknights-hunting-e2")
        assert not sr.requires_toggles          # 原文是「This unit's ranged attacks」
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [sr], frozenset())
        cover = Stance(phase="shooting", target_in_cover=True)
        base = _run(_attacker(_gun(bs=3)), _target(sv=4), cover)
        r = _run(atk, _target(sv=4), cover)
        assert _ratio(r.hits, base.hits) > 1.0

    def test_marked_prey_sustained_hits_both_phases(self, entries):
        # 标记猎物（Houndpack Lance 分队规则）：[SUSTAINED HITS 1]，原文无相位限制
        mp = _entry(entries, "det000010311")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [mp], frozenset())
        base = _run(_attacker(_gun(bs=3)), _target(), Stance(phase="shooting"))
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.hits, base.hits) > 1.0
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=3)), [mp], frozenset())
        bm = _run(_attacker(_melee(ws=3)), _target(), Stance(phase="melee"))
        rm = _run(atk_m, _target(), Stance(phase="melee"))
        assert _ratio(rm.hits, bm.hits) > 1.0

    def test_merciless_fusillade_sustained_hits_both_phases(self, entries):
        # 无情齐射（Helhunt Lance 战略）：WHEN=射击阶段初或近战阶段初 → 两相位不加门
        mf = _entry(entries, "000010752003")
        assert all(not f.condition for f in mf.effects)
        for phase, wpn in (("shooting", _gun(bs=3)), ("melee", _melee(ws=3))):
            atk, _, _ = inject_attacker(_attacker(wpn), [mf], frozenset())
            base = _run(_attacker(wpn), _target(), Stance(phase=phase))
            r = _run(atk, _target(), Stance(phase=phase))
            assert _ratio(r.hits, base.hits) > 1.0

    def test_conquerors_without_mercy_melee_charging_only(self, entries):
        # 无情征服者（Traitoris Lance 战略）：冲锋回合近战武器 AP+1（melee_charging）
        cm = _entry(entries, "000008517003")
        atk, _, _ = inject_attacker(_attacker(_melee(ap=0)), [cm], frozenset())
        base = _run(_attacker(_melee(ap=0)), _target(sv=4),
                    Stance(phase="melee", charging=True))
        r = _run(atk, _target(sv=4), Stance(phase="melee", charging=True))
        # AP0 vs Sv4+（1/2 过）→ AP-1 → 5+（1/3 过）
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        # 非冲锋回合不生效
        rn = _run(atk, _target(sv=4), Stance(phase="melee", charging=False))
        assert _ratio(rn.unsaved, rn.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 射击阶段不生效
        atk_s, _, _ = inject_attacker(_attacker(_gun(ap=0)), [cm], frozenset())
        rs = _run(atk_s, _target(sv=4), Stance(phase="shooting", charging=True))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_hungry_for_combat_crit_threshold_melee_only(self, entries):
        # 渴战（Houndpack Lance 战略）：近战未修正命中 5+ 即暴击（近战门）。
        # 暴击阈值单独不可观测，用同 payload 的无情齐射 [SUSTAINED HITS 1] 做放大镜：
        # 阈值 6+→5+ 会让额外命中变多。
        hc = _entry(entries, "000010313003")
        mf = _entry(entries, "000010752003")
        assert all(f.condition == ("phase_melee",) for f in hc.effects)
        only_sus, _, _ = inject_attacker(_attacker(_melee(ws=3)), [mf], frozenset())
        both, _, _ = inject_attacker(_attacker(_melee(ws=3)), [mf, hc], frozenset())
        base = _run(only_sus, _target(), Stance(phase="melee"))
        r = _run(both, _target(), Stance(phase="melee"))
        assert _ratio(r.hits, base.hits) > 1.0
        # 射击阶段近战门不放行：与只有 [SUSTAINED HITS 1] 时一致
        only_s, _, _ = inject_attacker(_attacker(_gun(bs=3)), [mf], frozenset())
        both_s, _, _ = inject_attacker(_attacker(_gun(bs=3)), [mf, hc], frozenset())
        bs = _run(only_s, _target(), Stance(phase="shooting"))
        rs = _run(both_s, _target(), Stance(phase="shooting"))
        assert _ratio(rs.hits, bs.hits) == pytest.approx(1.0, abs=0.02)

    def test_knight_diabolus_ws_improve_melee_only(self, entries):
        # 恶魔骑士（Infernal Lance 增强）：携带者近战武器 WS 特征值改善 1，须携带者开关
        kd = _entry(entries, "000010304002")
        _, _, notes = inject_attacker(_attacker(_melee(ws=4)), [kd], frozenset())
        assert any("bearer_leading" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4)), [kd],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(_melee(ws=4)), _target(), Stance(phase="melee"))
        r = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        # 射击阶段不放行
        atk_s, _, _ = inject_attacker(_attacker(_gun(bs=4)), [kd],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(), Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)


# ══ 诚实边界：高频过度建模陷阱的反向断言 ═══════════════════════════════
class TestHonestyBoundaries:
    @pytest.mark.parametrize("row_id, why", [
        ("detfp11e-chaosknights-bastions", "目标战栗（Battle-shocked）态无载体"),
        ("000010309007", "负关键词门（排除 MONSTERS/VEHICLES）无载体"),
        ("000010309005", "重投「1」（非重投失败）无载体"),
        ("000010752002", "仅对致命伤的 FNP 无载体"),
        ("fp11e-chaosknights-bastions-s1", "仅对致命伤的 FNP 无载体"),
        ("det000010303", "Empowered 状态机 + 二选一/三选一单分支无载体"),
        ("000010308005", "Sv 设定为 2+ 属 SET，非增量，无载体"),
        ("fp11e-chaosknights-bastions-e2", "随机 A 的重投无载体"),
        ("detfp11e-chaosknights-hunting", "侦测范围（detection range）无载体"),
        ("000010312003", "重投「1」+ 异单位授予无载体"),
    ])
    def test_known_traps_stay_not_modeled(self, entries, row_id, why):
        e = _entry(entries, row_id)
        assert e.status == "not_modeled", (row_id, why)
        assert not e.effects
        assert e.not_modeled_notes_zh
