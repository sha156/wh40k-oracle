"""P7-PR29 星界军（Astra Militarum，faction='AM'）全量 DSL 编码落账：1 条军规（指挥之声）
+ 13 个分队容器（11 个库内分队 + 2 个 FP 全新分队）的 14 条分队规则 + 65 战略 + 42 增强
= 122（13 encoded / 20 partial / 89 not_modeled）——零新引擎通道、零新态势开关。

星界军是「命令（Orders）驱动 + 远程火力 + 载具搭乘」气质阵营：军规「指挥之声」是六道命令
择一下达、分队规则与战略大量落在命令域 / 移动域 / 预备队 / 目标点经济 / 登舰行动舱门，
全部无引擎载体，故 not_modeled 占大多数。可编子集集中在 AP 改善·恶化 / [IGNORES COVER] /
[LETHAL HITS] / 掩体 / FNP / 命中·致伤骰修正与重掷 / 暴击阈值 / S 改善 / A 加值 / 伤害减免。

fp_rules 侧：Bridgehead Strike 11 版整页重印（1 规则 + 2 增强 + 3 战略）落 5 条 text_patch
+ 5 条 removed_11e；Grizzled Company 的 ADDITIONAL ARMOUR 持续期改写、RULES UPDATES 的
Masters of Camouflage / Swift Interception 9"→8" / Draw Them Out 9"→8" / Tanglefoot Grenades
共 12 条 text_patch；Abhuman Auxiliaries / Designation Force 两全新分队 12 行 inserts
（fp11e-am-*）。工作单见 docs/superpowers/plans/2026-07-20-p7-pr29-astramilitarum-worklist.md。
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
PAYLOAD = Path("dsl_payloads/astramilitarum.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 13 个星界军分队容器名（stratagems.detachment / enhancements.detachment_name 口径）
AM_DETACHMENTS = (
    "Armoured Infantry", "Bridgehead Strike", "Combined Arms", "Embarked Regiment",
    "Grizzled Company", "Hammer of the Emperor", "Mechanised Assault", "Recon Element",
    "Siege Regiment", "Steel Hammer", "Tempestus Boarding Regiment",
    "Abhuman Auxiliaries", "Designation Force",
)
ARMY_RULE_ID = "000008377"          # 指挥之声（Voice of Command）


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="chainsword", effects=()):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=tuple(effects), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="boltgun", rng='24"', effects=()):
    return WeaponProfile(name_zh=None, name_en=name, range=rng,
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=tuple(effects), count=1)


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


# ══ 结构与 DB 对账 ═══════════════════════════════════════════════════════════
class TestPayloadShape:
    def test_counts(self, entries):
        assert len(entries) == 122
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 13, "partial": 20, "not_modeled": 89}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        # 1 军规 + 12 库内分队规则 + 2 fp_new 分队规则；59 库内战略（62-3 removed）
        # + 6 fp_new；38 库内增强（40-2 removed）+ 4 fp_new
        assert by == {"abilities": 15, "stratagems": 65, "enhancements": 42}

    def test_faction_is_am(self, entries):
        assert all(e.faction == "AM" for e in entries)

    def test_army_rule_present_and_not_modeled(self, entries):
        # 指挥之声是军规行（非 det 前缀、无 materialize）——六道命令择一下达，
        # 引擎无命令状态开关，只能 not_modeled
        ar = _entry(entries, ARMY_RULE_ID)
        assert ar.table == "abilities" and ar.status == "not_modeled"
        assert not ar.effects and ar.not_modeled_notes_zh

    def test_detachment_field_matches_container_names(self, entries):
        # 分队字段必须落在真实容器名上（军规行除外）——写成规则名会被 select_entries 永不匹配
        for e in entries:
            if e.row_id == ARMY_RULE_ID:
                assert e.detachment is None
            else:
                assert e.detachment in AM_DETACHMENTS, (e.row_id, e.detachment)

    def test_bridgehead_strike_has_two_rule_rows(self, entries):
        # 库里 Bridgehead Strike 有两条分队规则行（Only the Best + Fire Zone Purge），
        # 11 版重印只收录后者——前者仅能在 DSL 注记披露（detachments 不在失效白名单内）
        otb = _entry(entries, "det000009798")
        assert otb.detachment == "Bridgehead Strike" and otb.status == "not_modeled"
        assert any("整页重印只收录" in n for n in otb.not_modeled_notes_zh)
        assert _entry(entries, "det000009799").detachment == "Bridgehead Strike"

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
            ("hit", "auto_wound"), ("hit", "crit_threshold"), ("hit", "modify"),
            ("hit", "reroll"),
            ("wound", "modify"), ("wound", "reroll"), ("wound", "s_improve"),
            ("damage", "damage_reduction"),
            ("save", "ap_improve"), ("save", "cover"), ("save", "ignores_cover"),
            ("fnp", "fnp"),
        }
        for e in entries:
            for f in e.effects:
                assert (f.phase, f.op) in known, (e.row_id, f.phase, f.op)

    def test_no_new_toggle(self, entries):
        # 零新态势开关：只复用既有的四个通用假设开关
        used = {t for e in entries for t in e.requires_toggles}
        assert used == {"bearer_leading", "defender_bearer_leading",
                        "disembarked_this_turn", "range_within_12"}

    def test_bearer_leading_only_where_bearer_leads_its_unit(self, entries):
        # 携带者「率领本单位」型条目挂 bearer 开关
        assert "bearer_leading" in _entry(entries, "000008380003").requires_toggles
        assert ("defender_bearer_leading"
                in _entry(entries, "000009861004").requires_toggles)

    def test_aura_and_bearer_only_entries_have_no_bearer_toggle(self, entries):
        # 反面（PR28 教训）：受益者是「范围内的另一友军单位」的光环增强、
        # 以及只作用于携带者本人的增强，都不挂 bearer 开关——
        # bearer_leading 语义是「携带者正率领本单位」，挂上会把语义写反
        for rid in ("000010791004",      # 万机神圣膏（光环，3" 内友军）
                    "000009861003",      # 圣涂油膏（受益者是另一友军 TRANSPORT）
                    "000009865003",      # 不屈战驹（只给携带者本人）
                    "fp11e-am-abhuman-e2",   # 尽责典范（只给携带者本人）
                    "000009857004"):     # 传世佩枪（只给携带者本人的手枪）
            assert not _entry(entries, rid).requires_toggles, rid

    def test_disembark_gate_on_disembark_conditioned_entries(self, entries):
        for rid in ("det000009860", "000010792007", "000009862004"):
            assert "disembarked_this_turn" in _entry(entries, rid).requires_toggles, rid

    def test_range_toggle_paired_with_ranged_within_12_tag(self, entries):
        # ranged_within_12 是「自含射击阶段的绝对射程档假设」——必须与开关成对
        for e in entries:
            if any(tuple(f.condition) == ("ranged_within_12",) for f in e.effects):
                assert "range_within_12" in e.requires_toggles, e.row_id

    def test_weapon_filter_entries(self, entries):
        assert _entry(entries, "000009802003").weapon_filter == "hot-shot"
        assert _entry(entries, "000009857004").weapon_filter == "pistol"
        # 其余条目不得误留 weapon_filter（会静默只作用于部分武器）
        filtered = {e.row_id for e in entries if e.weapon_filter}
        assert filtered == {"000009802003", "000009857004"}


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(AM_DETACHMENTS)), AM_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(AM_DETACHMENTS)), AM_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_no_orphan_am_row_outside_detachments(self):
        # PR27 教训：上游空壳行（分队列为空）会被靠 detachment 过滤的对账测试静默漏掉
        con = self._db()
        orphans = [r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='AM' "
            "AND COALESCE(detachment, '') = ''")]
        orphans += [r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='AM' "
            "AND COALESCE(detachment_name, '') = ''")]
        con.close()
        assert orphans == []

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        rule_ids = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='AM'")}
        con.close()
        covered = {e.row_id for e in entries
                   if e.table == "abilities" and e.row_id != ARMY_RULE_ID}
        assert covered == rule_ids

    def test_removed_11e_rows_are_out_of_payload(self, entries):
        # Bridgehead Strike 十版 2 增强 3 战略被 11 版重印取代 → 标 removed_11e 且不进 payload
        con = self._db()
        dead = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='AM' AND fp_status='removed_11e'")}
        dead |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='AM' "
            "AND fp_status='removed_11e'")}
        con.close()
        assert dead == {"000009802002", "000009802004", "000009802006",
                        "000009801004", "000009801005"}
        assert not (dead & {e.row_id for e in entries})

    def test_fp_new_rows_marked_added_11e(self):
        con = self._db()
        added = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-am-%'")}
        added |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-am-%'")}
        con.close()
        assert len(added) == 10          # 6 战略 + 4 增强（分队行不带 fp_status 列）

    def test_11e_text_patches_landed(self):
        # A/B 真漂移必须已落库（fp-rules 先于 dsl-apply）
        con = self._db()
        fzp = con.execute("SELECT rule_text FROM detachments "
                          "WHERE id='000009799'").fetchone()[0]
        assert "was set up this turn" in fzp and "from Reserves" not in fzp
        moc = con.execute("SELECT rule_text FROM detachments "
                          "WHERE id='000009868'").fetchone()[0]
        assert "wholly within a" not in moc and "(to a maximum of 3+)" in moc
        sd = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009802005'").fetchone()[0]
        assert "[IGNORES COVER]" in sd and "cannot have the Benefit of Cover" not in sd
        omp = con.execute("SELECT text_zh, phase FROM stratagems "
                          "WHERE id='000009802007'").fetchone()
        assert "End of your opponent’s Charge phase." in omp[0]
        assert omp[1] == "Charge phase"
        aa = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000010638007'").fetchone()[0]
        assert "Until the end of the phase," in aa
        for sid in ("000009862005", "000009870003"):
            txt = con.execute("SELECT text_zh FROM stratagems WHERE id=?",
                              (sid,)).fetchone()[0]
            assert '9"' not in txt and '8"' in txt, sid
        tg = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009870006'").fetchone()[0]
        assert "-1 to charge rolls" in tg and "subtract 2 from the Charge roll" not in tg
        pdb = con.execute("SELECT description FROM enhancements "
                          "WHERE id='000009801003'").fetchone()[0]
        assert "ingress move" in pdb
        con.close()

    def test_reprinted_detachments_left_untouched(self):
        # Steel Hammer（FP p5）/ Armoured Infantry（p7）/ Grizzled Company（p9）三分队规则
        # 与库现文逐字一致（Wahapedia 已滚入）→ 免补。用 FP 正文里的判据短语锁死，
        # 而不是只量长度——长度断言对任何漂移都会放行
        con = self._db()
        for did, needles in (
                ("000010786", ("target enemy units within Engagement Range",
                               "excluding attacks made with Indirect Fire weapons")),
                ("000010790", ("Add Squadron to the list of units", "ON MY SIGNAL",
                               "keyword (excluding Artillery units")),
                ("000010636", ("Add 1 to the number of Orders",
                               "re-roll a Hit roll of 1"))):
            txt = con.execute("SELECT rule_text FROM detachments WHERE id=?",
                              (did,)).fetchone()[0]
            for needle in needles:
                assert needle in txt, (did, needle)
        # Siege Regiment 的 Creeping Barrage change-to 库现文已逐字为 11 版 → 同样免补
        cb = con.execute("SELECT rule_text FROM detachments "
                         "WHERE id='000009856'").fetchone()[0]
        assert "that unit is shaken" in cb
        assert "The maximum number of units that can be shaken" in cb
        # 三分队的战略/增强也不该出现在本 PR 的 text_patch 清单里
        import json
        from pathlib import Path
        patched = {p["id"] for p in json.loads(
            Path("db_compile/fp_rules_patches.json").read_text(encoding="utf-8")
        )["text_patches"]}
        untouched = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN "
            "('Steel Hammer', 'Armoured Infantry')")}
        untouched |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN "
            "('Steel Hammer', 'Armoured Infantry', 'Grizzled Company')")}
        con.close()
        assert not (untouched & patched)

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
        "det000009388",         # 净扫协议（远程 [LETHAL HITS]）
        "000008381005",         # 交叉火力（WHEN=我方射击阶段）
        "000008381007",         # 坚定守护者（WHEN=对手射击阶段）
        "000009802005",         # 伺服标定器（远程 [IGNORES COVER]）
        "000009862004",         # 清剿与占领（WHEN=我方射击阶段）
        "000009866007",         # 附加装甲（WHEN=对手射击阶段）
        "000009870005",         # 英勇佯动（WHEN=对手射击阶段）
        "000010638004",         # 老兵神射手（远程 [IGNORES COVER]）
        "000010638005",         # 净化之火（远程 [LETHAL HITS]）
        "000010638006",         # 莫迪安一分钟（WHEN=我方射击阶段）
        "000010638007",         # 附加护甲（WHEN=对手射击阶段）
        "000010788005",         # 碎裂齐射（WHEN=我方射击阶段）
        "000010788007",         # 压力下的精准（WHEN=我方射击阶段）
        "000010792006",         # 协同火力（WHEN=我方射击阶段）
        "000010792007",         # 首轮齐射（WHEN=我方射击阶段）
        "000009861003",         # 圣涂油膏（WHEN=我方射击阶段开始）
        "fp11e-am-designation-s3",   # 污沼烟幕（WHEN=对手射击阶段开始）
    )
    MELEE_ONLY = (
        "000009390002",         # 残酷训练（近战武器 A/S）
        "000010788002",         # 怒火引擎（近战武器 A/AP）
    )
    BOTH_PHASES = (
        "det000009868",         # 伪装大师（常驻掩体，无 WHEN 相位）
        "000009381003",         # 闪避掩蔽（WHEN=对手射击阶段或近战阶段）
        "fp11e-am-abhuman-s1",  # 厚颅固执（WHEN=对手射击阶段或近战阶段）
        "000009857004",         # 传世佩枪（手枪 A+2，无相位限定）
        "000009861004",         # 烟雾手雷（常驻掩体，无 WHEN 相位）
        "000009865003",         # 不屈战驹（常驻 FNP）
        "000010791004",         # 万机神圣膏（常驻光环 FNP）
        "fp11e-am-abhuman-e2",  # 尽责典范（常驻 FNP）
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
        # 反方向守卫（PR13 教训）：WHEN 覆盖两相位或常驻的条目多加相位门 = 欠建模，
        # 同属事实错误。掩体/FNP 类由引擎自身的射击门承担，DSL 不重复加门
        for rid in self.BOTH_PHASES:
            e = _entry(entries, rid)
            assert e.effects, rid
            assert all(not f.condition for f in e.effects), rid

    def test_within_12_entries_use_ranged_composite_tag(self, entries):
        # 「12" 内」三条：ranged_within_12 自含射击相位；裸用 half_range 或无门都会失真
        for rid in ("000009802003", "000009858004", "000009866006"):
            e = _entry(entries, rid)
            assert all(f.condition == ("ranged_within_12",) for f in e.effects), rid

    # half_range / stationary 只读态势字段、**不自含相位门**（对比 ranged_within_12
    # 的 `stance.phase == "shooting" and ...`）——原文限「远程武器」却挂这两个 tag 的条目
    # 会在「近战模拟 + 该开关仍开着」时误放行。本 PR 不为一条加新复合 tag，
    # 改为一律降 partial 并把该过度施加写进注记（第五次同型 HIGH 的守卫）
    PHASE_BLIND_TAGS = ("half_range", "stationary")

    def test_phase_blind_tag_entries_are_partial_and_disclosed(self, entries):
        hits = []
        for e in entries:
            if any(tuple(f.condition) and f.condition[0] in self.PHASE_BLIND_TAGS
                   for f in e.effects):
                hits.append(e.row_id)
                assert e.status == "partial", e.row_id
                assert any("不含相位门" in n for n in e.not_modeled_notes_zh), e.row_id
        assert sorted(hits) == ["000008380003", "000009858006"]

    def test_furious_fusillade_leaks_into_melee_as_disclosed(self, entries):
        # 把已披露的过度施加钉成可执行事实：注记说「近战模拟里同时开半射程开关会误放行」，
        # 这里就断言它确实会——将来若引擎补了复合 tag，本测试会红，提示回来收紧编码
        ff = _entry(entries, "000009858006")
        atk, _, _ = inject_attacker(_attacker(_melee()), [ff], frozenset())
        leaked = _run(atk, _target(), Stance(phase="melee", half_range=True))
        assert leaked.attacks.mean() == pytest.approx(2.0, abs=0.01)
        clean = _run(atk, _target(), Stance(phase="melee"))
        assert clean.attacks.mean() == pytest.approx(1.0, abs=0.01)

    def test_every_effect_condition_is_known_form(self, entries):
        allowed = {
            (), ("phase_shooting",), ("phase_melee",),
            ("ranged_within_12",), ("half_range",), ("stationary",),
        }
        for e in entries:
            for f in e.effects:
                assert tuple(f.condition) in allowed, (e.row_id, f.condition)

    def test_reroll_ops_use_fail_semantics(self, entries):
        for e in entries:
            for f in e.effects:
                if f.op == "reroll":
                    assert tuple(f.params) == ("fail",), e.row_id


# ══ 防高估：无载体从句一律不编（逐类守卫）═══════════════════════════════════
class TestAntiOvercount:
    ORDERS_DOMAIN = (
        "000008377",       # 指挥之声（军规：六道命令择一）
        "det000010636",    # 无情纪律（命令数 +1 × 重掷 1）
        "det000010790",    # 中队指挥（新增 ON MY SIGNAL 命令）
        "000008381002", "000008381004", "000008381006",
        "000009390003", "000009858003", "000009862002", "000010638002",
        "000008380004", "000008380005", "000009801002", "000009857005",
        "000009865002", "000010637002", "000010637003", "000010637004",
        "000010637005", "000010787002", "000010791002",
    )
    REROLL_ONES = (
        "det000009798",    # 唯有精锐
        "det000010636",    # 无情纪律第二从句
        "000009865005",    # 老练车组
    )
    MULTI_CHOICE = (
        "000008377",       # 指挥之声（六选一）
        "det000009856",    # 炮兵支援（三选一）
        "000010637003",    # 天鹰之眼（新增可选命令）
        "000010637004",    # 特勤老兵（新增可选命令）
    )
    SHOOTING_TIMES_TARGET_KEYWORD = (
        "det000008379",    # 天生士兵（负关键词门 + 射击 × MONSTER/VEHICLE）
        "000010792005",    # 支援炮火（射击 × MONSTER/VEHICLE）
    )

    def test_orders_domain_not_encoded(self, entries):
        # 命令（Orders）是「军官逐单位择一下达 + 数量上限 + 范围门 + 士气门」的状态机——
        # 引擎无命令状态开关，裸编任一条等于把可选命令当恒开
        for rid in self.ORDERS_DOMAIN:
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_reroll_ones_not_encoded(self, entries):
        # 引擎 hit/wound reroll 只有「重掷全部失败骰」一种语义，重掷特定点数「1」无载体
        for rid in self.REROLL_ONES:
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_multi_choice_entries_not_encoded(self, entries):
        for rid in self.MULTI_CHOICE:
            assert _entry(entries, rid).status == "not_modeled", rid

    def test_shooting_times_target_keyword_not_encoded(self, entries):
        # 引擎只有通用 target_has_keyword（近战也放行）与 melee_target_has_keyword，
        # 无「射击 × 目标关键词」复合 tag；负关键词门（排除 MONSTER/VEHICLE）更无载体
        for rid in self.SHOOTING_TIMES_TARGET_KEYWORD:
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_attacker_self_below_half_not_encoded(self, entries):
        # 最后时刻：前置门是「本单位低于半编」的攻方自身战损档——
        # 开关 target_below_half 是守方档，无攻方自身战损载体
        e = _entry(entries, "000009866002")
        assert e.status == "not_modeled" and not e.effects

    def test_strict_s_lt_t_not_encoded(self, entries):
        # 歼灭部队：S<T 严格小于且跨相位——melee_s_lte_t 既含 S==T 又丢射击侧，双向失真
        e = _entry(entries, "000009389003")
        assert e.status == "not_modeled" and not e.effects

    def test_engagement_range_penalty_waiver_not_encoded(self, entries):
        # 不息炮火：引擎射击序列本就不施加交战范围命中惩罚，
        # 裸编 ignore_hit_mods 会凭空造出加成
        e = _entry(entries, "det000010786")
        assert e.status == "not_modeled" and not e.effects

    def test_out_of_sequence_mortal_wounds_not_encoded(self, entries):
        # 就位开火 / 雷区：攻击序列外的致命伤池与自伤均无载体
        for rid in ("000009802007", "000009858007"):
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_damage_reroll_not_encoded(self, entries):
        # 泰坦杀手：重掷伤害骰——damage 通道只有 modify / damage_reduction
        e = _entry(entries, "000010787003")
        assert e.status == "not_modeled" and not e.effects


# ══ 攻方向：真源 payload → 引擎级差别 ══════════════════════════════════════
class TestOffensiveFromPayload:
    def test_armoured_fist_wound_plus_one_needs_disembark_toggle(self, entries):
        af = _entry(entries, "det000009860")
        assert af.status == "encoded"
        base = _run(_attacker(_gun(s=4)), _target(t=4), Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
        atk, modeled, _ = inject_attacker(_attacker(_gun(s=4)), [af],
                                          frozenset({"disembarked_this_turn"}))
        assert modeled
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 未开开关 → 不注入并显式披露
        atk2, modeled2, nm2 = inject_attacker(_attacker(_gun(s=4)), [af], frozenset())
        assert not modeled2 and any("未启用" in n for n in nm2)
        r2 = _run(atk2, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r2.wounds, r2.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_armoured_fist_shooting_only(self, entries):
        af = _entry(entries, "det000009860")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [af],
                                    frozenset({"disembarked_this_turn"}))
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_firing_hot_only_hits_hot_shot_weapons(self, entries):
        fh = _entry(entries, "000009802003")
        assert fh.status == "encoded" and fh.weapon_filter == "hot-shot"
        stance = Stance(phase="shooting", range_within_12=True)
        atk, modeled, _ = inject_attacker(
            _attacker(_gun(s=4, name="hot-shot lasgun")), [fh],
            frozenset({"range_within_12"}))
        assert modeled
        r = _run(atk, _target(t=4), Stance(phase="shooting", range_within_12=True))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)   # S5 vs T4
        # 非 hot-shot 武器不吃增益（loadout 无匹配时显式披露）
        atk2, modeled2, nm2 = inject_attacker(_attacker(_gun(s=4, name="lasgun")), [fh],
                                              frozenset({"range_within_12"}))
        assert not modeled2 and any("没有名字含" in n for n in nm2)
        r2 = _run(atk2, _target(t=4), stance)
        assert _ratio(r2.wounds, r2.hits) == pytest.approx(1 / 2, abs=0.02)
        # 12" 档开关未开 → 条件不放行
        atk3, _, _ = inject_attacker(_attacker(_gun(s=4, name="hot-shot lasgun")), [fh],
                                     frozenset({"range_within_12"}))
        r3 = _run(atk3, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r3.wounds, r3.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_firing_hot_ap_improve(self, entries):
        fh = _entry(entries, "000009802003")
        atk, _, _ = inject_attacker(_attacker(_gun(name="hot-shot lasgun", ap=0)),
                                    [fh], frozenset({"range_within_12"}))
        r = _run(atk, _target(sv=4), Stance(phase="shooting", range_within_12=True))
        # AP-1 vs Sv4+ → 保存 5+（1/3 过保 → 2/3 未过保）
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_brutal_training_melee_attacks_and_strength(self, entries):
        bt = _entry(entries, "000009390002")
        assert bt.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [bt], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2.0, abs=0.01)          # A 1→2
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)  # S4→S5 vs T4
        # 射击阶段不放行（近战门）
        gatk, _, _ = inject_attacker(_attacker(_gun(s=4)), [bt], frozenset())
        rs = _run(gatk, _target(t=4), Stance(phase="shooting"))
        assert rs.attacks.mean() == pytest.approx(1.0, abs=0.01)
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_engine_of_wrath_six_attacks_and_ap2(self, entries):
        ew = _entry(entries, "000010788002")
        assert ew.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_melee(ap=0)), [ew], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(7.0, abs=0.01)           # A 1→7
        # AP-2 vs Sv4+ → 保存 6+（1/6 过保 → 5/6 未过保）
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(5 / 6, abs=0.02)

    def test_furious_fusillade_half_range_only(self, entries):
        ff = _entry(entries, "000009858006")
        # half_range 不自含相位门 → partial（过度施加已在注记披露，见 TestPhaseGating）
        assert ff.status == "partial"
        atk, _, _ = inject_attacker(_attacker(_gun()), [ff], frozenset())
        near = _run(atk, _target(), Stance(phase="shooting", half_range=True))
        far = _run(atk, _target(), Stance(phase="shooting"))
        assert near.attacks.mean() == pytest.approx(2.0, abs=0.01)
        assert far.attacks.mean() == pytest.approx(1.0, abs=0.01)

    def test_flare_burst_hit_reroll_within_12(self, entries):
        fb = _entry(entries, "000009858004")
        assert fb.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [fb],
                                    frozenset({"range_within_12"}))
        r = _run(atk, _target(), Stance(phase="shooting", range_within_12=True))
        # BS4+ 重掷失败 → 1 - (1/2)^2 = 3/4
        assert _ratio(r.hits, r.attacks) == pytest.approx(3 / 4, abs=0.02)
        r2 = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r2.hits, r2.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_furious_cannonade_ap_within_12(self, entries):
        fc = _entry(entries, "000009866006")
        assert fc.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_gun(ap=0)), [fc],
                                    frozenset({"range_within_12"}))
        r = _run(atk, _target(sv=4), Stance(phase="shooting", range_within_12=True))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_veteran_sharpshooters_cancels_cover(self, entries):
        vs = _entry(entries, "000010638004")
        assert vs.status == "encoded"
        camo = _entry(entries, "det000009868")
        covered, _, _ = inject_target(_target(), [camo], frozenset())
        base = _run(_attacker(_gun(bs=4)), covered, Stance(phase="shooting"))
        # 11 版掩体 = 恶化 BS 1 点（射击专属）→ BS5+
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 3, abs=0.02)
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [vs], frozenset())
        r = _run(atk, covered, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_fields_of_fire_ap_improve_shooting_only(self, entries):
        fof = _entry(entries, "000008381005")
        assert fof.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_gun(ap=0)), [fof], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        matk, _, _ = inject_attacker(_attacker(_melee(ap=0)), [fof], frozenset())
        rm = _run(matk, _target(sv=4), Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_purging_fire_lethal_hits(self, entries):
        pf = _entry(entries, "000010638005")
        assert pf.status == "partial"
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4, s=3)), [pf], frozenset())
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        # S3 vs T6（2S≤T）→ 6+ 致伤 = 1/6。BS4+ 时命中里有 1/3 是暴击（6/(4,5,6)），
        # [LETHAL HITS] 让它们直接过致伤 → 1/3 + (2/3)(1/6) = 4/9
        assert _ratio(r.wounds, r.hits) == pytest.approx(4 / 9, abs=0.02)
        # 未挂 [LETHAL HITS] 的裸枪对照：纯 6+ 致伤
        bare = _run(_attacker(_gun(bs=4, s=3)), _target(t=6), Stance(phase="shooting"))
        assert _ratio(bare.wounds, bare.hits) == pytest.approx(1 / 6, abs=0.02)

    def test_drill_commander_crit_threshold_needs_lethal_carrier(self, entries):
        # 暴击阈值单独不改命中率——须与 [LETHAL HITS] 型武器能力合看才可观测
        dc = _entry(entries, "000008380003")
        assert dc.status == "partial"
        lethal = (Effect(phase="hit", op="auto_wound", params=(),
                         condition=(), source="武器自带 [LETHAL HITS]"),)
        gun = _gun(bs=4, s=3, effects=lethal)
        base = _run(_attacker(gun), _target(t=6), Stance(phase="shooting", stationary=True))
        # 暴击 6 → 命中里 1/3 直接过致伤，其余 6+ → 1/3 + (2/3)(1/6) = 4/9
        assert _ratio(base.wounds, base.hits) == pytest.approx(4 / 9, abs=0.02)
        atk, modeled, _ = inject_attacker(_attacker(gun), [dc],
                                          frozenset({"bearer_leading"}))
        assert modeled
        r = _run(atk, _target(t=6), Stance(phase="shooting", stationary=True))
        # 暴击阈值 5+ → 命中里 2/3 直接过致伤 → 2/3 + (1/3)(1/6) = 13/18
        assert _ratio(r.wounds, r.hits) == pytest.approx(13 / 18, abs=0.02)
        # 未驻停 → 条件不放行
        rn = _run(atk, _target(t=6), Stance(phase="shooting"))
        assert _ratio(rn.wounds, rn.hits) == pytest.approx(4 / 9, abs=0.02)

    def test_servo_designators_cancels_cover_shooting_only(self, entries):
        sd = _entry(entries, "000009802005")
        # 受益面是全军友军 MT 单位而非战略 TARGET 单位 → partial + 攻方关键词注记
        assert sd.status == "partial"
        assert any("攻方自关键词" in n for n in sd.not_modeled_notes_zh)
        camo = _entry(entries, "det000009868")
        covered, _, _ = inject_target(_target(), [camo], frozenset())
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [sd], frozenset())
        r = _run(atk, covered, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_shattering_salvo_and_accuracy_under_pressure(self, entries):
        ss = _entry(entries, "000010788005")
        assert ss.status == "encoded"
        camo = _entry(entries, "det000009868")
        covered, _, _ = inject_target(_target(), [camo], frozenset())
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [ss], frozenset())
        assert _ratio(*(lambda r: (r.hits, r.attacks))(
            _run(atk, covered, Stance(phase="shooting")))) == pytest.approx(1 / 2, abs=0.02)
        aup = _entry(entries, "000010788007")
        assert aup.status == "encoded"
        atk2, _, _ = inject_attacker(_attacker(_gun(bs=4)), [aup], frozenset())
        r2 = _run(atk2, _target(), Stance(phase="shooting"))
        assert _ratio(r2.hits, r2.attacks) == pytest.approx(3 / 4, abs=0.02)
        # 近战不放行
        m2, _, _ = inject_attacker(_attacker(_melee(ws=4)), [aup], frozenset())
        rm = _run(m2, _target(), Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_opening_salvo_wound_plus_one_needs_disembark(self, entries):
        os_ = _entry(entries, "000010792007")
        assert os_.status == "encoded"
        atk, modeled, _ = inject_attacker(_attacker(_gun(s=4)), [os_],
                                          frozenset({"disembarked_this_turn"}))
        assert modeled
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk2, modeled2, _ = inject_attacker(_attacker(_gun(s=4)), [os_], frozenset())
        assert not modeled2

    def test_legacy_sidearm_pistol_filter(self, entries):
        ls = _entry(entries, "000009857004")
        assert ls.status == "partial" and ls.weapon_filter == "pistol"
        atk, modeled, _ = inject_attacker(
            _attacker(_gun(name="laspistol"), _gun(name="lasgun")), [ls], frozenset())
        assert modeled
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert r.attacks.mean() == pytest.approx(4.0, abs=0.01)   # 1+2 手枪 + 1 枪


# ══ 守方向：inject_target 通道 ══════════════════════════════════════════════
class TestDefensiveFromPayload:
    def test_additional_armour_worsens_attacker_ap(self, entries):
        aa = _entry(entries, "000010638007")
        assert aa.status == "encoded" and aa.side == "target"
        base = _run(_attacker(_gun(ap=-1)), _target(sv=4), Stance(phase="shooting"))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
        tgt, modeled, _ = inject_target(_target(sv=4), [aa], frozenset())
        assert modeled
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        # AP-1 恶化 1 → AP0 vs Sv4+ → 保存 4+（1/2 未过保）
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 近战不放行（WHEN=对手射击阶段）
        rm = _run(_attacker(_melee(ap=-1)), tgt, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_ablative_plating_damage_reduction_shooting_only(self, entries):
        ap = _entry(entries, "000009866007")
        assert ap.status == "encoded" and ap.side == "target"
        raw = _target(sv=7, w=3, models=3)
        tgt, _, _ = inject_target(raw, [ap], frozenset())
        base = _run(_attacker(_gun(d=2)), raw, Stance(phase="shooting"))
        r = _run(_attacker(_gun(d=2)), tgt, Stance(phase="shooting"))
        assert r.damage.mean() == pytest.approx(base.damage.mean() / 2, rel=0.05)
        # 近战不放行
        mbase = _run(_attacker(_melee(d=2)), raw, Stance(phase="melee"))
        rm = _run(_attacker(_melee(d=2)), tgt, Stance(phase="melee"))
        assert rm.damage.mean() == pytest.approx(mbase.damage.mean(), rel=0.01)

    def test_masters_of_camouflage_cover_is_hit_side(self, entries):
        moc = _entry(entries, "det000009868")
        assert moc.status == "partial" and moc.side == "target"
        tgt, modeled, _ = inject_target(_target(), [moc], frozenset())
        assert modeled
        r = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        # 11 版掩体只作用于远程——近战命中不受影响（引擎自带射击门，DSL 不重复加门）
        rm = _run(_attacker(_melee(ws=4)), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_courageous_diversion_fnp_and_hit_penalty(self, entries):
        cd = _entry(entries, "000009870005")
        assert cd.status == "partial" and cd.side == "target"
        raw = _target(sv=7, models=10)
        tgt, _, _ = inject_target(raw, [cd], frozenset())
        base = _run(_attacker(_gun(bs=4)), raw, Stance(phase="shooting"))
        r = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        # 命中 -1 与 FNP 6+ 复合：伤害 ≈ base × (2/3) × (5/6)
        assert r.damage.mean() == pytest.approx(
            base.damage.mean() * (2 / 3) * (5 / 6), rel=0.06)

    def test_omnissian_unguents_aura_fnp5(self, entries):
        ou = _entry(entries, "000010791004")
        assert ou.status == "partial" and ou.side == "target"
        raw = _target(sv=7, models=10)
        tgt, _, _ = inject_target(raw, [ou], frozenset())
        base = _run(_attacker(_gun()), raw, Stance(phase="shooting"))
        r = _run(_attacker(_gun()), tgt, Stance(phase="shooting"))
        assert r.damage.mean() == pytest.approx(base.damage.mean() * (2 / 3), rel=0.06)

    def test_exemplar_of_duty_fnp4_both_phases(self, entries):
        ed = _entry(entries, "fp11e-am-abhuman-e2")
        assert ed.status == "partial" and ed.side == "target"
        raw = _target(sv=7, models=10)
        tgt, _, _ = inject_target(raw, [ed], frozenset())
        for phase, wpn in (("shooting", _gun()), ("melee", _melee())):
            base = _run(_attacker(wpn), raw, Stance(phase=phase))
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert r.damage.mean() == pytest.approx(
                base.damage.mean() * (1 / 2), rel=0.06), phase

    def test_thick_skulled_obdurance_ap_worsen_both_phases(self, entries):
        ts = _entry(entries, "fp11e-am-abhuman-s1")
        assert ts.status == "partial" and ts.side == "target"
        for phase, wpn in (("shooting", _gun(ap=-1)), ("melee", _melee(ap=-1))):
            raw = _target(sv=4)
            tgt, _, _ = inject_target(raw, [ts], frozenset())
            base = _run(_attacker(wpn), raw, Stance(phase=phase))
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02), phase

    def test_duck_and_cover_hit_penalty_applies_in_both_phases(self, entries):
        # 本 payload 唯一的「两相位守方命中惩罚」——不加相位门的判断必须由行为断言背书，
        # 否则 test_both_phase_entries_not_over_gated 只是在核结构
        dc = _entry(entries, "000009381003")
        assert dc.status == "partial" and dc.side == "target"
        tgt, modeled, _ = inject_target(_target(), [dc], frozenset())
        assert modeled
        for phase, wpn in (("shooting", _gun(bs=4)), ("melee", _melee(ws=4))):
            base = _run(_attacker(wpn), _target(), Stance(phase=phase))
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
            assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02), phase

    def test_defensive_entries_disclosed_on_attack_path(self, entries):
        # 方向说明：守方向条目走攻方注入路径必须显式披露，不静默吞
        aa = _entry(entries, "000010638007")
        atk, modeled, nm = inject_attacker(_attacker(_gun()), [aa], frozenset())
        assert not modeled and any("防守向条目" in n for n in nm)
