# tests/test_simulator_dsl_pr27_payload.py
"""P7-PR27 Adeptus Mechanicus（帝国机械教，faction='AdM'）全量 DSL 编码落账：
1 条军规（教义指令）+ 13 个分队容器（10 个 Index/Codex/登舰行动分队 + 3 个 FP 新分队）的
13 条分队规则 + 63 战略 + 40 增强 = 117（16 encoded / 18 partial / 83 not_modeled）
——零新引擎通道、零新态势开关。

帝国机械教是「指令切换 + 目标点经济 + 远程增益」气质阵营：军规教义指令二选一、
分队规则的「获取目标点」几何、Noospheric Transference 的 Override 四选一、重掷「1」、
士气/移动/预备队/舱门（登舰行动）全无引擎载体，故 not_modeled 占多数。可编子集集中在
AP 改善 / [LETHAL HITS] / [SUSTAINED HITS] / [IGNORES COVER] / 特殊保护 / FNP /
命中·致伤骰修正 / 暴击阈值 / [LANCE]（melee_charging）。

fp_new 三个全新分队 Cohort Acquisitus / Lords of the Forge / Luminen Auto-choir
（fp11e-admech-*）由 db_compile/fp_rules_patches.json inserts 补录（各 1 规则 + 2 增强 +
3 战略 = 18 行）；同批 7 条 text_patch（Bomb Rack / Aerial Deployment / Tactica Obliqua /
ANALYTICAL DIVINATION 9"→8"，以及上游空壳行 THREAT-COGITATION TARGETERS 的
text_zh+detachment+phase 三列归位）与 4 条 fp_errata（3 架 Archaeopter 的 M + Transvector
去 AIRCRAFT）。AdM 无 removed_11e 行（FP 对现有分队均为重印）。
"""
import sqlite3
from pathlib import Path

import pytest

from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Effect,
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
PAYLOAD = Path("dsl_payloads/admech.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 13 个帝国机械教分队容器名（stratagems.detachment / enhancements.detachment_name）
ADM_DETACHMENTS = (
    "Cohort Cybernetica", "Data-Psalm Conclave", "Electromartyrs", "Eradication Cohort",
    "Explorator Maniple", "Haloscreed Battle Clade", "Machine Cult", "Rad-Zone Corps",
    "Response Clade", "Skitarii Hunter Cohort",
    "Cohort Acquisitus", "Lords of the Forge", "Luminen Auto-choir",
)
ARMY_RULE_ID = "000008382"          # 教义指令（Doctrina Imperatives）


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="control stave"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="galvanic rifle", rng='30"'):
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


# ══ 结构与 DB 对账 ════════════════════════════════════════════════════════
class TestPayloadShape:
    def test_counts(self, entries):
        assert len(entries) == 117
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 16, "partial": 18, "not_modeled": 83}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        # 1 军规 + 10 库内分队规则 + 3 fp_new 分队规则；54 库内战略 + 9 fp_new；
        # 34 库内增强 + 6 fp_new
        assert by == {"abilities": 14, "stratagems": 63, "enhancements": 40}

    def test_faction_is_adm(self, entries):
        assert all(e.faction == "AdM" for e in entries)

    def test_army_rule_present_and_not_modeled(self, entries):
        # 教义指令是军规行（非 det 前缀、无 materialize）——二选一状态无开关，只能 not_modeled
        ar = _entry(entries, ARMY_RULE_ID)
        assert ar.table == "abilities" and ar.status == "not_modeled"
        assert not ar.effects and ar.not_modeled_notes_zh

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

    def test_no_new_engine_channel(self, entries):
        # 纯编码 PR：所有 (phase, op) 必须是既有通道
        known = {
            ("attacks", "modify"),
            ("hit", "auto_wound"), ("hit", "crit_threshold"), ("hit", "extra_hits"),
            ("hit", "ignore_hit_mods"), ("hit", "modify"), ("hit", "reroll"),
            ("wound", "modify"), ("wound", "s_improve"),
            ("damage", "modify"),
            ("save", "ap_improve"), ("save", "cover"), ("save", "ignores_cover"),
            ("save", "invuln"), ("fnp", "fnp"),
        }
        for e in entries:
            for f in e.effects:
                assert (f.phase, f.op) in known, (e.row_id, f.phase, f.op)

    def test_no_new_toggle(self, entries):
        # 零新态势开关：只复用 PR4/PR6 既有的三个通用假设开关
        used = {t for e in entries for t in e.requires_toggles}
        assert used == {"bearer_leading", "defender_bearer_leading",
                        "disembarked_this_turn"}

    def test_bearer_limited_entries_gated_by_toggle(self, entries):
        # 携带者限定 / 光环范围假设的条目不得无条件注入——必须挂 bearer 开关
        for rid, tog in (("000010747004", "bearer_leading"),          # 电容叶片
                         ("000010747005", "bearer_leading"),          # 万机神之怒
                         ("000009745005", "bearer_leading"),          # 内载致命性
                         ("000008568004", "bearer_leading"),          # 逻辑师
                         ("000008385004", "bearer_leading"),          # 无双灭绝者
                         ("000008568003", "defender_bearer_leading"),  # 遗传学家
                         ("000008385003", "defender_bearer_leading")):  # 恶语低吟
            assert tog in _entry(entries, rid).requires_toggles, rid

    def test_unit_scope_entry_has_no_bearer_toggle(self, entries):
        # 反面：原文写「This unit has ...」的整单位增强不得挂 bearer 开关
        assert not _entry(entries, "fp11e-admech-luminen-e2").requires_toggles


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(ADM_DETACHMENTS)), ADM_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_no_orphan_adm_stratagem_outside_detachments(self):
        # THREAT-COGITATION TARGETERS 曾是 detachment/phase/text 三列皆空的孤儿行，
        # 已由 fp_rules text_patch 归位——回归守卫：AdM 不得再有分队为空的战略
        con = self._db()
        orphans = [r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='AdM' "
            "AND COALESCE(detachment, '') = ''")]
        con.close()
        assert orphans == []

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(ADM_DETACHMENTS)), ADM_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        rule_ids = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='AdM'")}
        con.close()
        covered = {e.row_id for e in entries
                   if e.table == "abilities" and e.row_id != ARMY_RULE_ID}
        assert covered == rule_ids

    def test_adm_has_no_removed_11e_rows(self):
        # FP 对 10 个现有分队均为重印，零删除
        con = self._db()
        dead = con.execute(
            "SELECT COUNT(*) FROM stratagems WHERE faction='AdM' "
            "AND fp_status='removed_11e'").fetchone()[0]
        dead += con.execute(
            "SELECT COUNT(*) FROM enhancements WHERE faction_id='AdM' "
            "AND fp_status='removed_11e'").fetchone()[0]
        con.close()
        assert dead == 0

    def test_fp_new_rows_marked_added_11e(self):
        con = self._db()
        added = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-admech-%'")}
        added |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-admech-%'")}
        con.close()
        assert len(added) == 15          # 9 战略 + 6 增强（分队行不带 fp_status 列）

    def test_11e_text_patches_landed(self):
        # 5 处 A/B 真漂移必须已落库（fp-rules 先于 dsl-apply）
        con = self._db()
        bomb = con.execute("SELECT text_zh FROM abilities "
                           "WHERE id='000002087_a3'").fetchone()[0]
        assert "At the end of your opponent" in bomb and '24"' in bomb
        aerial = con.execute("SELECT text_zh FROM abilities "
                             "WHERE id='000002085_a3'").fetchone()[0]
        assert aerial == "In your first Movement phase, this unit can make an ingress move."
        tactica = con.execute("SELECT text_zh FROM abilities "
                              "WHERE id='000002082_a2'").fetchone()[0]
        assert 'ends a move within 8"' in tactica and "Once per turn" not in tactica
        div = con.execute("SELECT text_zh FROM stratagems "
                          "WHERE id='000009746007'").fetchone()[0]
        assert 'within 8" of that enemy unit' in div and 'within 9"' not in div
        tct = con.execute("SELECT text_zh, detachment, phase FROM stratagems "
                          "WHERE id='000010748005'").fetchone()
        assert "re‑roll the Damage roll" in tct[0]
        assert tct[1] == "Eradication Cohort" and tct[2] == "Shooting phase"
        con.close()

    def test_11e_errata_landed(self):
        con = self._db()
        m = dict(con.execute(
            "SELECT unit_id, m FROM models WHERE unit_id IN "
            "('000002087', '000002086', '000002085')"))
        assert m == {"000002087": "-", "000002086": "-", "000002085": '14"'}
        kw = con.execute("SELECT keywords_json FROM units "
                         "WHERE id='000002085'").fetchone()[0]
        assert "Aircraft" not in kw
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


# ══ 阶段门纪律（双向核对：该加的加、不该加的不加）═══════════════════════════
class TestPhaseGating:
    SHOOTING_ONLY = (
        "000008573003",   # 自动占卜索敌（远程武器 [IGNORES COVER]）
        "000009282003",   # 弹道同步（远程 [LETHAL HITS]）
        "000009282005",   # 救援系统（WHEN=对手射击阶段）
        "000008565007",   # 流明祝福（WHEN=对手射击阶段）
        "000008569006",   # 熏香排气（WHEN=对手射击阶段）
        "000008386007",   # 壁垒律令（WHEN=对手射击阶段）
        "000008386006",   # 致命剂量（远程 [LETHAL HITS]）
        "000008386005",   # 预校准净化方案（远程攻击重掷命中）
        "000009291004",   # 预知火网（远程 [SUSTAINED HITS 1]）
        "000008561005",   # 孤立摧毁（WHEN=我方射击阶段）
        "000008569005",   # 自动神谕回收（远程攻击致伤 +1）
        "fp11e-admech-acquisitus-s1",   # 缺陷检视（远程 [IGNORES COVER]）
        "det000009280",   # 机魂超载（远程武器 AP 改善）
        "det000008559",   # 潜行优化（Stealth）
        "detfp11e-admech-luminen",      # 电子静滞圣咏（远程 [LETHAL HITS]）
        "000010747004",   # 电容叶片（远程武器 S +1）
        "000008385003",   # 恶语低吟（Stealth）
        "000008385004",   # 无双灭绝者（远程 [SUSTAINED HITS 1]）
        "fp11e-admech-luminen-e2",      # 电磁瘴气火盆（Stealth）
    )
    MELEE_ONLY = (
        "000008565003",   # 无情之拳颂唱（WHEN=近战阶段，近战攻击致伤 +1）
        "000008386002",   # 凶兆光环（WHEN=近战阶段，持续到回合结束）
        "000010747005",   # 万机神之怒（近战武器）
        "000009745005",   # 内载致命性（近战武器）
    )
    BOTH_PHASES = (
        "000008573005",   # 机械优越（忽略修正，不限相位）
        "000008573007",   # 万机神的仁慈（FNP）
        "000009746003",   # 索敌覆写（WHEN=射击阶段或近战阶段）
        "000009291002",   # 响应护盾（WHEN=对手射击阶段或近战阶段）
        "000008561003",   # 二进制攻势（WHEN=两相位开始，全部武器 AP）
        "000008561002",   # 仿生耐力（WHEN=对手射击阶段或近战阶段）
        "fp11e-admech-lordsforge-s1",   # 经文预断（WHEN=对手射击阶段或近战阶段）
        "detfp11e-admech-lordsforge",   # 战形披挂（特殊保护 + FNP，不限相位）
        "000008568004",   # 逻辑师（「每次攻击」不限攻击类型）
        "000008568003",   # 遗传学家（特殊保护）
    )

    def test_shooting_only_entries_gated(self, entries):
        for rid in self.SHOOTING_ONLY:
            e = _entry(entries, rid)
            assert e.effects, rid
            assert all(f.condition == ("phase_shooting",) for f in e.effects), rid

    def test_melee_only_entries_gated(self, entries):
        for rid in self.MELEE_ONLY:
            e = _entry(entries, rid)
            assert e.effects, rid
            assert all(f.condition == ("phase_melee",) for f in e.effects), rid

    def test_both_phase_entries_not_over_gated(self, entries):
        # 反方向守卫：WHEN 覆盖两相位的条目多加相位门 = 欠建模，同属事实错误
        for rid in self.BOTH_PHASES:
            e = _entry(entries, rid)
            assert e.effects, rid
            assert all(not f.condition for f in e.effects), rid

    def test_lance_uses_melee_charging_composite(self, entries):
        # 伺服驱动冲锋（[LANCE]）：裸 charging 会在射击阶段误放行，必须用复合 tag
        sdc = _entry(entries, "000010748002")
        assert all(f.condition == ("melee_charging",) for f in sdc.effects)

    def test_every_effect_phase_gate_is_known_form(self, entries):
        allowed = {(), ("phase_shooting",), ("phase_melee",), ("melee_charging",)}
        for e in entries:
            for f in e.effects:
                assert tuple(f.condition) in allowed, (e.row_id, f.condition)


# ══ 守方向：真源 payload → 引擎级差别 ══════════════════════════════════════
class TestDefensiveFromPayload:
    def test_luminescent_blessing_invuln4_shooting_only(self, entries):
        # 流明祝福：WHEN=对手射击阶段 → 只在射击注入
        lb = _entry(entries, "000008565007")
        assert lb.status == "encoded"
        tgt, _, _ = inject_target(_target(), [lb], frozenset())
        rs = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)
        rm = _run(_attacker(_melee(ws=3)), tgt, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1.0, abs=0.02)

    def test_bulwark_imperative_invuln4_shooting_only(self, entries):
        bi = _entry(entries, "000008386007")
        tgt, _, _ = inject_target(_target(), [bi], frozenset())
        rs = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_responsive_shielding_invuln4_both_phases(self, entries):
        rs_e = _entry(entries, "000009291002")
        assert rs_e.status == "partial"          # 「本单位在目标点范围内」几何门无载体
        assert all(not f.condition for f in rs_e.effects)
        tgt, _, _ = inject_target(_target(), [rs_e], frozenset())
        for phase, wpn in (("shooting", _gun(bs=3)), ("melee", _melee(ws=3))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_saviour_systems_wound_minus1_shooting_only(self, entries):
        ss = _entry(entries, "000009282005")
        tgt, _, _ = inject_target(_target(t=4), [ss], frozenset())
        rs = _run(_attacker(_gun(s=4)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 3, abs=0.02)
        rm = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_baleful_halo_wound_minus1_melee_only(self, entries):
        # 凶兆光环：WHEN=近战阶段、持续到回合结束——近战是回合最后一个攻击阶段，
        # 故本回合仅近战可受益（阶段性 WHEN 的正确推法）
        bh = _entry(entries, "000008386002")
        tgt, _, _ = inject_target(_target(t=4), [bh], frozenset())
        rm = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 3, abs=0.02)
        rs = _run(_attacker(_gun(s=4)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_bionic_endurance_fnp5_both_phases(self, entries):
        be = _entry(entries, "000008561002")
        tgt, _, _ = inject_target(_target(w=1), [be], frozenset())
        for phase, wpn in (("shooting", _gun(ap=-6)), ("melee", _melee(ap=-6))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.damage, r.unsaved) == pytest.approx(2 / 3, abs=0.03)

    def test_benevolence_fnp6_is_generic_threshold(self, entries):
        # 万机神的仁慈：只编通用 6+；对致命伤的 5+ 分档诚实降 partial
        bo = _entry(entries, "000008573007")
        assert bo.status == "partial" and bo.not_modeled_notes_zh
        tgt, _, _ = inject_target(_target(w=1), [bo], frozenset())
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(r.damage, r.unsaved) == pytest.approx(5 / 6, abs=0.03)

    def test_scriptural_prognosis_ap_worsen_both_phases(self, entries):
        # 经文预断：守方 AP 恶化 1（负参并入攻方 ap_improve 净算）
        sp = _entry(entries, "fp11e-admech-lordsforge-s1")
        assert sp.status == "partial"            # 目标点几何门 + 短于整阶段的持续期均无载体
        tgt, _, _ = inject_target(_target(sv=4), [sp], frozenset())
        for phase, wpn in (("shooting", _gun(ap=-1)), ("melee", _melee(ap=-1))):
            base = _run(_attacker(wpn), _target(sv=4), Stance(phase=phase))
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            # AP-1 vs Sv4+ → 5+（2/3 过）；恶化回 AP0 → 4+（1/2 过）
            assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_war_form_mantles_invuln_and_fnp(self, entries):
        wf = _entry(entries, "detfp11e-admech-lordsforge")
        assert wf.status == "partial"
        tgt, _, _ = inject_target(_target(w=1), [wf], frozenset())
        r = _run(_attacker(_gun(bs=3, ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)   # 4+ 特保
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2 / 3, abs=0.03)   # FNP 5+

    def test_stealth_optimisation_cover_is_bs_penalty_shooting_only(self, entries):
        # 11 版 Stealth = 掩体收益；引擎把掩体折成射击阶段的 BS 惩罚，近战不受影响
        so = _entry(entries, "det000008559")
        tgt, _, _ = inject_target(_target(), [so], frozenset())
        rs = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)
        rm = _run(_attacker(_melee(ws=3)), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_electromiasmic_brazier_cover_without_toggle(self, entries):
        eb = _entry(entries, "fp11e-admech-luminen-e2")
        assert eb.status == "encoded" and not eb.requires_toggles
        tgt, _, _ = inject_target(_target(), [eb], frozenset())
        r = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_malphonic_susurrus_needs_defender_bearer_toggle(self, entries):
        ms = _entry(entries, "000008385003")
        _, _, notes = inject_target(_target(), [ms], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(), [ms],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_genetor_needs_defender_bearer_toggle(self, entries):
        gn = _entry(entries, "000008568003")
        _, _, notes = inject_target(_target(), [gn], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(), [gn],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_gun(bs=3)), tgt, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)


# ══ 攻方向：真源 payload → 引擎级差别 ══════════════════════════════════════
class TestOffensiveFromPayload:
    def test_remorseless_fist_wound_plus1_melee_only(self, entries):
        cf = _entry(entries, "000008565003")
        assert cf.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [cf], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [cf], frozenset())
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_isolate_and_destroy_wound_plus1_shooting_only(self, entries):
        # 孤立摧毁：「目标 6\" 内无其他敌军单位」在 1v1 天然满足（同 [CLEAVE] 单目标前提）
        iad = _entry(entries, "000008561005")
        assert iad.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [iad], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [iad], frozenset())
        rm = _run(atk_m, _target(t=4), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_ballistic_synchrony_lethal_hits_shooting_only(self, entries):
        bs_e = _entry(entries, "000009282003")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [bs_e], frozenset())
        r = _run(atk, _target(t=8), Stance(phase="shooting"))
        # S4 vs T8 需 6+ 致伤（1/6）；[LETHAL HITS] 让 1/6 的暴击命中直接致伤
        base = _run(_attacker(_gun(bs=4, s=4)), _target(t=8), Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 6, abs=0.02)
        assert _ratio(r.wounds, r.hits) > _ratio(base.wounds, base.hits) + 0.1
        # 近战不放行
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=4, s=4)), [bs_e], frozenset())
        rm = _run(atk_m, _target(t=8), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 6, abs=0.02)

    def test_servo_driven_charge_lance_only_on_charging_melee(self, entries):
        sdc = _entry(entries, "000010748002")
        assert sdc.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [sdc], frozenset())
        rc = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        assert _ratio(rc.wounds, rc.hits) == pytest.approx(2 / 3, abs=0.02)
        rn = _run(atk, _target(t=4), Stance(phase="melee", charging=False))
        assert _ratio(rn.wounds, rn.hits) == pytest.approx(1 / 2, abs=0.02)
        # 关键：射击阶段 + 本回合冲锋时不得放行（裸 charging 会在此处误加成）
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [sdc], frozenset())
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting", charging=True))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_targeting_override_crit5_lifts_lethal_hits(self, entries):
        # 索敌覆写单独无可观测效果（暴击阈值需暴击消费者）——与致命剂量同注入验证
        to = _entry(entries, "000009746003")
        ld = _entry(entries, "000008386006")
        assert all(not f.condition for f in to.effects)
        only_lethal, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [ld], frozenset())
        both, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [ld, to], frozenset())
        r1 = _run(only_lethal, _target(t=8), Stance(phase="shooting"))
        r2 = _run(both, _target(t=8), Stance(phase="shooting"))
        assert _ratio(r2.wounds, r2.hits) > _ratio(r1.wounds, r1.hits) + 0.1

    def test_binharic_offence_ap_improve_both_phases(self, entries):
        bo = _entry(entries, "000008561003")
        assert bo.status == "encoded"
        for phase, wpn in (("shooting", _gun(ap=0)), ("melee", _melee(ap=0))):
            atk, _, _ = inject_attacker(_attacker(wpn), [bo], frozenset())
            base = _run(_attacker(wpn), _target(sv=4), Stance(phase=phase))
            r = _run(atk, _target(sv=4), Stance(phase=phase))
            assert _ratio(base.unsaved, base.wounds) == pytest.approx(1 / 2, abs=0.02)
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_overload_machine_spirits_ap_shooting_only(self, entries):
        oms = _entry(entries, "det000009280")
        assert oms.status == "partial"          # [HAZARDOUS] 自伤未建模
        atk, _, _ = inject_attacker(_attacker(_gun(ap=0)), [oms], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee(ap=0)), [oms], frozenset())
        rm = _run(atk_m, _target(sv=4), Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_precognitated_firefields_sustained1_shooting_only(self, entries):
        pf = _entry(entries, "000009291004")
        assert pf.status == "partial"           # BATTLELINE 升 SH2 未建模（保守欠建模）
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [pf], frozenset())
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_peerless_eradicator_needs_bearer_toggle(self, entries):
        pe = _entry(entries, "000008385004")
        _, _, notes = inject_attacker(_attacker(_gun(bs=4)), [pe], frozenset())
        assert any("bearer_leading" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [pe],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_pre_calibrated_purge_hit_reroll_shooting_only(self, entries):
        pc = _entry(entries, "000008386005")
        assert pc.status == "partial"           # 部署区几何门无载体
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [pc], frozenset())
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(3 / 4, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=4)), [pc], frozenset())
        rm = _run(atk_m, _target(), Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_defect_scrutiny_ignores_cover(self, entries):
        ds = _entry(entries, "fp11e-admech-acquisitus-s1")
        assert ds.status == "partial"           # RECON AUGURY 12" 第三单位几何未建模
        in_cover = _target(effects=(Effect("save", "cover", (), (), "掩体"),))
        base = _run(_attacker(_gun(bs=3)), in_cover, Stance(phase="shooting"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [ds], frozenset())
        r = _run(atk, in_cover, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_machine_superiority_ignores_negative_hit_mods(self, entries):
        ms = _entry(entries, "000008573005")
        assert ms.status == "partial"
        debuffed = _target(effects=(Effect("hit", "modify", (-1,), (), "减命中"),))
        base = _run(_attacker(_gun(bs=3)), debuffed, Stance(phase="shooting"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [ms], frozenset())
        r = _run(atk, debuffed, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_capacitor_vanes_s_improve_needs_bearer_toggle(self, entries):
        cv = _entry(entries, "000010747004")
        _, _, notes = inject_attacker(_attacker(_gun(s=4)), [cv], frozenset())
        assert any("bearer_leading" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [cv],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 近战不放行
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [cv],
                                      frozenset({"bearer_leading"}))
        rm = _run(atk_m, _target(t=4), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_omnissiah_fury_three_channels_melee_only(self, entries):
        of = _entry(entries, "000010747005")
        assert of.status == "partial"           # 仅携带者本人的近战武器
        assert {(f.phase, f.op) for f in of.effects} == {
            ("attacks", "modify"), ("save", "ap_improve"), ("damage", "modify")}
        atk, _, _ = inject_attacker(_attacker(_melee(ws=3, ap=0, d=1)), [of],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(_melee(ws=3, ap=0, d=1)), _target(sv=4, w=4),
                    Stance(phase="melee"))
        r = _run(atk, _target(sv=4, w=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(3 * base.attacks.mean(), abs=0.05)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2.0, abs=0.05)

    def test_inloaded_lethality_attacks_and_damage_melee_only(self, entries):
        il = _entry(entries, "000009745005")
        atk, _, _ = inject_attacker(_attacker(_melee(ws=3, d=1)), [il],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(_melee(ws=3, d=1)), _target(w=4), Stance(phase="melee"))
        r = _run(atk, _target(w=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(4 * base.attacks.mean(), abs=0.05)
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2.0, abs=0.05)

    def test_logis_hit_plus1_both_phases(self, entries):
        lg = _entry(entries, "000008568004")
        assert lg.status == "partial"           # 「获取目标点」几何未建模
        for phase, wpn in (("shooting", _gun(bs=4)), ("melee", _melee(ws=4))):
            atk, _, _ = inject_attacker(_attacker(wpn), [lg],
                                        frozenset({"bearer_leading"}))
            r = _run(atk, _target(), Stance(phase=phase))
            assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_auto_oracular_retrieval_needs_disembark_toggle(self, entries):
        ar = _entry(entries, "000008569005")
        assert ar.requires_toggles == ("disembarked_this_turn",)
        _, _, notes = inject_attacker(_attacker(_gun(s=4)), [ar], frozenset())
        assert any("disembarked_this_turn" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [ar],
                                    frozenset({"disembarked_this_turn"}))
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_cyber_static_canticles_lethal_hits_shooting_only(self, entries):
        cc = _entry(entries, "detfp11e-admech-luminen")
        assert cc.status == "partial"           # CORPUSCARII 自关键词门未建模
        base = _run(_attacker(_gun(bs=4, s=4)), _target(t=8), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [cc], frozenset())
        r = _run(atk, _target(t=8), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) > _ratio(base.wounds, base.hits) + 0.1


# ══ 反面守卫：不该被编码的机制确实没编 ═════════════════════════════════════
class TestHonestNotModeled:
    ONE_OF_N = ("000008382",            # 教义指令（守护/征服二选一）
                "det000008563",         # 万机神的祝祷（二选一）
                "det000009744",         # 诺斯层传输（Override 四选一）
                "000010748004")         # 解缚之怒（多选一 + [HAZARDOUS]）
    REROLL_ONES = ("det000008567", "det000010746", "det000009289",
                   "000009746002", "fp11e-admech-luminen-s1")
    SHOOTING_X_KEYWORD = ("000008572005",   # 反否定者 [ANTI-VEHICLE 4+]
                          "000008385005")   # 高压灭菌谴责 [ANTI-INFANTRY/MONSTER]

    def test_one_of_n_choices_not_encoded(self, entries):
        for rid in self.ONE_OF_N:
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_reroll_of_ones_not_encoded(self, entries):
        # 引擎重掷只有「重掷失败」一种模式，重掷特定点数无通道
        for rid in self.REROLL_ONES:
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_shooting_times_target_keyword_not_encoded(self, entries):
        # 无「射击阶段 × 目标关键词」复合 tag；裸 target_has_keyword 会在近战误放行
        for rid in self.SHOOTING_X_KEYWORD:
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_no_target_has_keyword_condition_anywhere(self, entries):
        for e in entries:
            for f in e.effects:
                assert "keyword" not in str(f.condition), (e.row_id, f.condition)

    def test_mortal_wound_only_fnp_not_encoded(self, entries):
        # 铁魂咒言：仅对致命伤的 FNP 4+——裸编成通用 FNP 会大幅高估
        e = _entry(entries, "000008565002")
        assert e.status == "not_modeled" and not e.effects

    def test_attacker_own_strength_bracket_not_encoded(self, entries):
        # 机魂复苏：依赖「攻方自身」低于满编/半编——引擎的 target_below_* 是目标侧
        e = _entry(entries, "000008573004")
        assert e.status == "not_modeled" and not e.effects

    def test_six_inch_range_gate_not_encoded(self, entries):
        # 电灵显现：6" 距离档——引擎只有 8"/12"，8" 档会对 6"-8" 误放行
        e = _entry(entries, "000009299002")
        assert e.status == "not_modeled" and not e.effects

    @needs_db
    def test_objective_geometry_entries_are_never_encoded(self, entries):
        # 自查守卫（本 PR 自审逮到的 HIGH 根因）：帝国机械教遍地是「在目标点范围内」前提，
        # 引擎无目标点几何载体。任何原文含该前提又落了 effects 的条目，必须降 partial
        # 并写明高估——否则 encoded 就是在断言「全部从句已落地」而实际漏了一个门。
        con = sqlite3.connect(str(DB))
        cols = {"abilities": ("detachments", "rule_text"),
                "stratagems": ("stratagems", "text_zh"),
                "enhancements": ("enhancements", "description")}
        offenders = []
        for e in entries:
            if not e.effects:
                continue
            tbl, col = cols[e.table]
            rid = e.row_id[3:] if e.table == "abilities" else e.row_id
            row = con.execute("SELECT %s FROM %s WHERE id=?" % (col, tbl), (rid,)).fetchone()
            text = (row[0] or "").lower() if row else ""
            if "objective" in text and e.status == "encoded":
                offenders.append(e.row_id)
        con.close()
        assert offenders == [], f"含目标点前提却标 encoded：{offenders}"

    def test_new_weapon_grant_not_encoded(self, entries):
        # TL-4Ø9：增强授予整把新武器，属装配层职责，DSL 无「加武器」通道
        e = _entry(entries, "fp11e-admech-lordsforge-e2")
        assert e.status == "not_modeled" and not e.effects
