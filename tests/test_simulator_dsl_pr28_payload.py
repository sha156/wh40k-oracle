# tests/test_simulator_dsl_pr28_payload.py
"""P7-PR28 混沌星际战士（Chaos Space Marines，faction='CSM'）全量 DSL 编码落账：
1 条军规（黑暗契约）+ 20 个分队容器（18 个库内分队 + 2 个 FP 全新分队）的
23 条分队规则 + 105 战略 + 68 增强 = 197（19 encoded / 44 partial / 134 not_modeled）
——零新引擎通道、零新态势开关。

混沌星际战士是「黑暗契约状态机 + 士气恐惧 + 移动资格」气质阵营：军规黑暗契约二选一、
神印五选一、Desperate Pact / 契约调用 / Default to Doctrine 三套状态、Battle-shock 士气链、
目标点经济、大量移动与冲锋资格条款全无引擎载体，故 not_modeled 占多数。可编子集集中在
AP 改善·恶化 / [IGNORES COVER] / Stealth（掩体）/ FNP / 特殊保护 / 命中·致伤骰修正与重掷 /
暴击阈值 / [LANCE]（melee_charging）/ [HEAVY]（stationary）/ [DEVASTATING WOUNDS] /
S≤T·S>T 延迟判定。

fp_new 两个全新分队 Devotees of Destruction / Murdertalon Raiders（fp11e-csm-*）与
Cabal of Chaos 11 版重印新增的 1 增强 3 战略由 db_compile/fp_rules_patches.json inserts
补录（共 16 行）；同批 13 条 text_patch 与 9 条 removed_11e（Cabal of Chaos 旧条目）
见工作单 docs/superpowers/plans/2026-07-20-p7-pr28-csm-worklist.md。
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
PAYLOAD = Path("dsl_payloads/csm.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 20 个混沌星际战士分队容器名（stratagems.detachment / enhancements.detachment_name）
CSM_DETACHMENTS = (
    "Cabal of Chaos", "Champions of Chaos", "Chaos Cult", "Creations of Bile",
    "Cult of the Arkifane", "Deceptors", "Dread Talons", "Fellhammer Siege-host",
    "Huron’s Marauders", "Infernal Reavers", "Nightmare Hunt", "Pactbound Zealots",
    "Renegade Raiders", "Renegade Warband", "Soulforged Warpack", "Underdeck Uprising",
    "Veterans of the Long War", "Warpstrike Champions",
    "Devotees of Destruction", "Murdertalon Raiders",
)
ARMY_RULE_ID = "000008359"          # 黑暗契约（Dark Pacts）


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="chainsword"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="boltgun", rng='24"'):
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
        assert len(entries) == 197
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 19, "partial": 44, "not_modeled": 134}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        # 1 军规 + 21 库内分队规则 + 2 fp_new 分队规则；96 库内战略（102-6 removed）+ 9 fp_new；
        # 63 库内增强（66-3 removed）+ 5 fp_new
        assert by == {"abilities": 24, "stratagems": 105, "enhancements": 68}

    def test_faction_is_csm(self, entries):
        assert all(e.faction == "CSM" for e in entries)

    def test_army_rule_present_and_not_modeled(self, entries):
        # 黑暗契约是军规行（非 det 前缀、无 materialize）——二选一状态无开关，只能 not_modeled
        ar = _entry(entries, ARMY_RULE_ID)
        assert ar.table == "abilities" and ar.status == "not_modeled"
        assert not ar.effects and ar.not_modeled_notes_zh

    def test_detachment_field_matches_container_names(self, entries):
        # 分队字段必须落在真实容器名上（军规行除外）——写成规则名会让 select_entries 永不匹配
        for e in entries:
            if e.row_id == ARMY_RULE_ID:
                assert e.detachment is None
            else:
                assert e.detachment in CSM_DETACHMENTS, (e.row_id, e.detachment)

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
            ("hit", "modify"), ("hit", "reroll"),
            ("wound", "crit_threshold"), ("wound", "modify"), ("wound", "mortal_pool"),
            ("wound", "reroll"), ("wound", "s_improve"), ("wound", "t_improve"),
            ("damage", "modify"), ("damage", "damage_reduction"),
            ("save", "ap_improve"), ("save", "cover"), ("save", "ignores_cover"),
            ("save", "invuln"), ("fnp", "fnp"),
        }
        for e in entries:
            for f in e.effects:
                assert (f.phase, f.op) in known, (e.row_id, f.phase, f.op)

    def test_no_new_toggle(self, entries):
        # 零新态势开关：只复用既有的四个通用假设开关
        used = {t for e in entries for t in e.requires_toggles}
        assert used == {"bearer_leading", "defender_bearer_leading",
                        "disembarked_this_turn", "advanced_or_fell_back"}

    def test_bearer_limited_entries_gated_by_toggle(self, entries):
        # 携带者限定的条目不得无条件注入——必须挂 bearer 开关
        for rid, tog in (("fp11e-csm-cabal-e1", "bearer_leading"),        # 混沌导管
                         ("000009773005", "bearer_leading"),              # 首要试验体
                         ("000010743004", "bearer_leading"),              # 灵魂熔炉之印
                         ("000008964002", "bearer_leading"),              # 诅咒之牙
                         ("000008976003", "bearer_leading"),              # 钢铁匠艺
                         ("000008357005", "bearer_leading"),              # 燃血护符
                         ("000010739005", "bearer_leading"),              # 扎古拉
                         ("000009773003", "defender_bearer_leading"),     # 活体甲壳
                         ("000008964004", "defender_bearer_leading"),     # 混淆之幕
                         ("000009503003", "defender_bearer_leading"),     # 力量膨胀
                         ("000008972003", "defender_bearer_leading"),     # 夜之幕
                         ("fp11e-csm-murdertalon-e1",
                          "defender_bearer_leading")):                    # 影兜护符
            assert tog in _entry(entries, rid).requires_toggles, rid

    def test_aura_entries_have_no_bearer_toggle(self, entries):
        # 反面：受益者是「范围内的另一友军单位」的光环型增强不挂 bearer 开关
        # （bearer_leading 语义是「携带者正率领本单位」，挂上会把语义写反）
        for rid in ("000008985002", "000008985004", "000009512002"):
            assert not _entry(entries, rid).requires_toggles, rid

    def test_disembark_and_fallback_gates(self, entries):
        assert _entry(entries, "000008969006").requires_toggles == ("disembarked_this_turn",)
        assert "advanced_or_fell_back" in _entry(entries, "000008960002").requires_toggles


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(CSM_DETACHMENTS)), CSM_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(CSM_DETACHMENTS)), CSM_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_no_orphan_csm_row_outside_detachments(self):
        # PR27 教训：上游空壳行（分队列为空）会被靠 detachment 过滤的对账测试静默漏掉
        con = self._db()
        orphans = [r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='CSM' "
            "AND COALESCE(detachment, '') = ''")]
        orphans += [r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='CSM' "
            "AND COALESCE(detachment_name, '') = ''")]
        con.close()
        assert orphans == []

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        rule_ids = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='CSM'")}
        con.close()
        covered = {e.row_id for e in entries
                   if e.table == "abilities" and e.row_id != ARMY_RULE_ID}
        assert covered == rule_ids

    def test_removed_11e_rows_are_out_of_payload(self, entries):
        # Cabal of Chaos 十版 3 增强 6 战略被 11 版重印取代 → 标 removed_11e 且不进 payload
        con = self._db()
        dead = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='CSM' AND fp_status='removed_11e'")}
        dead |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='CSM' "
            "AND fp_status='removed_11e'")}
        con.close()
        assert len(dead) == 9
        assert not (dead & {e.row_id for e in entries})

    def test_fp_new_rows_marked_added_11e(self):
        con = self._db()
        added = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-csm-%'")}
        added |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-csm-%'")}
        con.close()
        assert len(added) == 14          # 9 战略 + 5 增强（分队行不带 fp_status 列）

    def test_11e_text_patches_landed(self):
        # A/B 真漂移必须已落库（fp-rules 先于 dsl-apply）
        con = self._db()
        wellspring = con.execute("SELECT rule_text FROM detachments "
                                 "WHERE id='000010150'").fetchone()[0]
        assert "+2 S" in wellspring and "Leaping Warpflame" not in wellspring
        moc = con.execute("SELECT rule_text FROM detachments "
                          "WHERE id='000008362'").fetchone()[0]
        assert "EPIC HERO</span> unit can only be attached" in moc
        pos = con.execute("SELECT text_zh FROM stratagems "
                          "WHERE id='000010740007'").fetchone()[0]
        assert pos.endswith("Your unit has +2 to charge rolls.")
        for sid in ("000008965006", "000008986006", "000008961007"):
            txt = con.execute("SELECT text_zh FROM stratagems WHERE id=?",
                              (sid,)).fetchone()[0]
            assert 'within 8" of that enemy unit' in txt, sid
            assert 'within 9" of that enemy unit' not in txt, sid
        bod = con.execute("SELECT text_zh, cp_cost FROM stratagems "
                          "WHERE id='000008961004'").fetchone()
        assert "<b>WHEN:</b> Fight phase." in bod[0] and bod[1] == "1"
        con.close()

    def test_unholy_fortitude_cp_not_touched(self):
        # 假警报守卫：refine 把 p8 的浮动 2CP 标到了 UNHOLY FORTITUDE 行，
        # 但整页只有一个 2CP 且库内 SOUL-TALLY OFFERING 已是 2CP → 不补
        con = self._db()
        cps = dict(con.execute("SELECT id, cp_cost FROM stratagems "
                               "WHERE id IN ('000010744004', '000010744007')"))
        con.close()
        assert cps == {"000010744004": "2", "000010744007": "1"}

    def test_11e_errata_landed(self):
        con = self._db()
        m = con.execute("SELECT m FROM models WHERE unit_id='000000961'").fetchone()[0]
        assert m == '12"'
        kw = con.execute("SELECT keywords_json FROM units "
                         "WHERE id='000000961'").fetchone()[0]
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
        "fp11e-csm-cabal-s3",   # 亚空间烈焰缠身（远程 [IGNORES COVER]）
        "000008982005",         # 疯狂专注（WHEN=我方射击阶段）
        "000010744007",         # 邪能坚韧（WHEN=对手射击阶段）
        "000008977006",         # 坚定决心（WHEN=对手射击阶段）
        "000010695006",         # 腐化弹药（远程攻击 AP 改善）
        "000008961006",         # 让银河燃烧（远程 [IGNORES COVER]）
        "000010740006",         # 破城打击（远程 [IGNORES COVER]）
        "000008358007",         # 腐臭瘴气（WHEN=对手射击阶段，Stealth）
        "000008964004",         # 混淆之幕（Stealth）
        "000008972003",         # 夜之幕（Stealth）
        "000010641002",         # 灰纱咒（Stealth）
        "000010694003",         # 猎手之眼（远程 [IGNORES COVER]）
        "fp11e-csm-devotees-s1",  # 毁灭之赐（远程 [LETHAL HITS] + [SUSTAINED HITS 1]）
    )
    MELEE_ONLY = (
        "000008982004",         # 邪恶献祭（近战武器 A +1）
        "000008977002",         # 不屈袭击者（WHEN=近战阶段）
        "000010740003",         # 腐化装甲（WHEN=战斗阶段、持续到回合结束）
        "000009773005",         # 首要试验体（近战武器）
        "000008964002",         # 诅咒之牙（近战武器 AP）
        "000008357005",         # 燃血护符（近战武器 A/S）
        "000008968003",         # 恐惧劫掠者（近战攻击重掷）
        "fp11e-csm-murdertalon-e2",   # 受诅之翼契约（近战 A +1）
    )
    BOTH_PHASES = (
        "det000008959",         # 仇恨焦点（不限相位）
        "det000008967",         # 劫掠者与蹂躏者（AP 改善，不限相位）
        "det000010692",         # 血仇（不限相位）
        "det000010742",         # 灵魂熔炉恩赐（特殊保护）
        "000008982002",         # 荣耀之选（WHEN=射击阶段或近战阶段）
        "000009774002",         # 狰狞相貌（WHEN=对手射击阶段或近战阶段）
        "000010744003",         # 邪火恩赐（WHEN=射击阶段或近战阶段）
        "000008358004",         # 亵渎狂热（WHEN=射击阶段或近战阶段）
        "000008969002",         # 坚定不移（WHEN=对手射击阶段或近战阶段）
        "000008961003",         # 轻蔑漠视（WHEN=对手射击阶段或近战阶段）
        "000010740002",         # 灵能错位（WHEN=对手射击阶段或近战阶段）
        "000008986002",         # 绝望誓约（WHEN=射击阶段或近战阶段）
        "000009513002",         # 邪能祭坛（WHEN=对手射击阶段或近战阶段）
        "000009513003",         # 瞬息之力（WHEN=射击阶段或近战阶段）
        "000010695003",         # 复仇毁灭（WHEN=射击阶段或近战阶段）
        "000008969006",         # 毁灭突袭（WHEN=射击阶段或近战阶段）
        "000010743004",         # 灵魂熔炉之印（「每次攻击」不限攻击类型）
        "000008976004",         # 钢缚仇恨（「每次攻击」不限攻击类型）
        "000010688002",         # 暴君之声（命中 +1，不限攻击类型）
        "000008960002",         # 渴望复仇（命中 +1，不限攻击类型）
        "000008960005",         # 战帅的馈赠（暴击致伤阈值，不限攻击类型）
        "000010739005",         # 扎古拉（「携带者武器」不分远近）
        "000009512002",         # 煽动者（「武器」不分远近）
        "000008985004",         # 诱人附款（重掷命中，不限攻击类型）
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
        # [LANCE] 三条：裸 charging 会在射击阶段误放行，必须用复合 tag
        for rid in ("fp11e-csm-murdertalon-s1", "fp11e-csm-cabal-e1"):
            e = _entry(entries, rid)
            assert all(f.condition == ("melee_charging",) for f in e.effects), rid
        # 劫掠者狂舞：WHEN=战斗阶段 + 「本回合冲锋过」→ 同一复合门
        assert all(f.condition == ("melee_charging",)
                   for f in _entry(entries, "000010689005").effects)

    def test_empyric_wellspring_two_clause_gates(self, entries):
        # 灵能涌泉：第一条从句在射击阶段、第二条在近战阶段——各挂各的门
        ew = _entry(entries, "det000010150")
        gates = {(f.phase, f.op, tuple(f.condition)) for f in ew.effects}
        assert gates == {
            ("wound", "s_improve", ("phase_shooting",)),
            ("wound", "s_improve", ("phase_melee",)),
            ("save", "ap_improve", ("phase_melee",)),
        }

    def test_every_effect_condition_is_known_form(self, entries):
        allowed = {
            (), ("phase_shooting",), ("phase_melee",), ("melee_charging",),
            ("stationary",), ("target_below_half",), ("melee_s_lte_t",),
            ("wound_s_gt_t",), ("target_has_keyword", "vehicle"),
            ("melee_target_has_keyword", "character"),
        }
        for e in entries:
            for f in e.effects:
                assert tuple(f.condition) in allowed, (e.row_id, f.condition)


# ══ 防高估：无载体从句一律不编（逐类守卫）═══════════════════════════════════
class TestAntiOvercount:
    SINGLE_PHASE_TIMES_TARGET_STATE = (
        "000008965004",   # 逐个击破（射击 × 低于满编）
        "000008977004",   # 无情炮击（射击 × 低于半编）
        "000008973002",   # 无底残酷（近战 × 士气/战损）
        "000008973004",   # 无情猎手（射击 × 士气/战损）
    )
    RANGED_TIMES_S_GT_T = (
        "det000008975",             # 钢铁坚毅
        "fp11e-csm-devotees-s3",    # 不灭之恨（毁灭信徒）
    )
    MULTI_CHOICE = (
        "000008359",       # 黑暗契约（军规二选一）
        "det000008362",    # 混沌之印（神印五选一 × 契约二选一）
        "det000009772",    # 实验性增体（六选一 / 随机二）
        "det000010687",    # 暴君的鞭策（二选一）
        "000010689002",    # 悍勇杀手（三选一）
        "000010695002",    # 从不落于下风（二选一）
    )

    def test_single_phase_times_target_state_not_encoded(self, entries):
        # 引擎无「单一相位 × 目标战损档」复合 tag：裸挂战损 tag 会在另一相位误放行，
        # 只挂相位门又丢掉战损前提——两个方向都错，故整条不编
        for rid in self.SINGLE_PHASE_TIMES_TARGET_STATE:
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_ranged_times_s_gt_t_not_encoded(self, entries):
        for rid in self.RANGED_TIMES_S_GT_T:
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_multi_choice_entries_not_encoded(self, entries):
        for rid in self.MULTI_CHOICE:
            assert _entry(entries, rid).status == "not_modeled", rid

    def test_reroll_ones_and_single_die_reroll_not_encoded(self, entries):
        # 引擎 hit/wound reroll 只有「重掷全部失败骰」一种语义
        for rid in ("det000010693", "detfp11e-csm-murdertalon", "000008960004"):
            e = _entry(entries, rid)
            assert e.status == "not_modeled" and not e.effects, rid

    def test_keyword_disjunction_not_encoded(self, entries):
        # 灵魂清算献祭：CHARACTER/MONSTER/VEHICLE 三者任一——无析取载体
        e = _entry(entries, "000010744004")
        assert e.status == "not_modeled" and not e.effects

    def test_reroll_ops_use_fail_semantics(self, entries):
        for e in entries:
            for f in e.effects:
                if f.op == "reroll":
                    assert tuple(f.params) == ("fail",), e.row_id


# ══ 攻方向：真源 payload → 引擎级差别 ══════════════════════════════════════
class TestOffensiveFromPayload:
    def test_wreathed_in_warpflame_ignores_cover_shooting_only(self, entries):
        # 11 版掩体（13.08）= 恶化该次攻击 BS 1 点（射击专属），故差别体现在命中面
        wiw = _entry(entries, "fp11e-csm-cabal-s3")
        assert wiw.status == "encoded"
        night = _entry(entries, "000008972003")          # Stealth 型守方掩体来源
        covered, _, _ = inject_target(_target(), [night],
                                      frozenset({"defender_bearer_leading"}))
        base = _run(_attacker(_gun(bs=4)), covered, Stance(phase="shooting"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 3, abs=0.02)
        atk, modeled, _ = inject_attacker(_attacker(_gun(bs=4)), [wiw], frozenset())
        assert modeled
        r = _run(atk, covered, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_baleful_boon_ap_improve_both_phases(self, entries):
        bb = _entry(entries, "000010744003")
        assert bb.status == "encoded"
        for phase, wpn in (("shooting", _gun(ap=0)), ("melee", _melee(ap=0))):
            base = _run(_attacker(wpn), _target(sv=4), Stance(phase=phase))
            assert _ratio(base.unsaved, base.wounds) == pytest.approx(1 / 2, abs=0.02)
            atk, _, _ = inject_attacker(_attacker(wpn), [bb], frozenset())
            r = _run(atk, _target(sv=4), Stance(phase=phase))
            # AP-1 vs Sv4+ → 保存 5+（1/3 过保 → 2/3 未过保）
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_inveterate_murderers_s_lte_t_melee_only(self, entries):
        im = _entry(entries, "000009504002")
        assert im.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [im], frozenset())
        rm = _run(atk, _target(t=4), Stance(phase="melee"))
        # S=T → 4+ 致伤；+1 修正 → 3+
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(2 / 3, abs=0.02)
        # S>T 时本条不生效
        atk2, _, _ = inject_attacker(_attacker(_melee(s=8)), [im], frozenset())
        rm2 = _run(atk2, _target(t=4), Stance(phase="melee"))
        assert _ratio(rm2.wounds, rm2.hits) == pytest.approx(5 / 6, abs=0.02)
        # 射击阶段不放行
        atk3, _, _ = inject_attacker(_attacker(_gun(s=4)), [im], frozenset())
        rs = _run(atk3, _target(t=4), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_plunging_talons_lance_charging_only(self, entries):
        pt = _entry(entries, "fp11e-csm-murdertalon-s1")
        assert pt.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [pt], frozenset())
        rc = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        assert _ratio(rc.wounds, rc.hits) == pytest.approx(2 / 3, abs=0.02)
        rn = _run(atk, _target(t=4), Stance(phase="melee", charging=False))
        assert _ratio(rn.wounds, rn.hits) == pytest.approx(1 / 2, abs=0.02)
        # 射击阶段不放行（近战武器在射击阶段不出手，故用枪核对复合门不外溢）
        gatk, _, _ = inject_attacker(_attacker(_gun(s=4)), [pt], frozenset())
        rs = _run(gatk, _target(t=4), Stance(phase="shooting", charging=True))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_reavers_flurry_extra_attack_charging_melee(self, entries):
        rf = _entry(entries, "000010689005")
        assert rf.status == "encoded"
        atk, _, _ = inject_attacker(_attacker(_melee()), [rf], frozenset())
        rc = _run(atk, _target(), Stance(phase="melee", charging=True))
        rn = _run(atk, _target(), Stance(phase="melee", charging=False))
        assert rc.hits.mean() == pytest.approx(2 * rn.hits.mean(), rel=0.05)

    def test_rain_of_ruin_heavy_needs_stationary(self, entries):
        ror = _entry(entries, "detfp11e-csm-devotees")
        assert ror.status == "partial"
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [ror], frozenset())
        rs = _run(atk, _target(), Stance(phase="shooting", stationary=True))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(2 / 3, abs=0.02)
        rm = _run(atk, _target(), Stance(phase="shooting", stationary=False))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_iron_artifice_anti_vehicle_only_vs_vehicle(self, entries):
        ia = _entry(entries, "000008976003")
        assert ia.status == "partial"
        atk, _, _ = inject_attacker(_attacker(_gun(s=4, ap=-6)), [ia],
                                    frozenset({"bearer_leading"}))
        veh = _run(atk, _target(t=10, keywords=frozenset({"vehicle"})),
                   Stance(phase="shooting"))
        inf = _run(atk, _target(t=10, keywords=frozenset({"infantry"})),
                   Stance(phase="shooting"))
        # S4 vs T10 → 6+ 致伤；[ANTI-VEHICLE 4+] 让 4+ 即暴击致伤（自动致伤）
        assert _ratio(veh.wounds, veh.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(inf.wounds, inf.hits) == pytest.approx(1 / 6, abs=0.02)

    def test_specimens_for_the_spider_melee_character_only(self, entries):
        sfs = _entry(entries, "000009774004")
        assert sfs.status == "partial"
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [sfs], frozenset())
        chara = _run(atk, _target(t=4, keywords=frozenset({"character"})),
                     Stance(phase="melee"))
        other = _run(atk, _target(t=4, keywords=frozenset({"infantry"})),
                     Stance(phase="melee"))
        assert _ratio(chara.wounds, chara.hits) == pytest.approx(3 / 4, abs=0.02)
        assert _ratio(other.wounds, other.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_toggle_gate_blocks_injection_when_off(self, entries):
        # 携带者开关未开 → 不注入并显式披露（不静默）
        ia = _entry(entries, "000008976003")
        atk, modeled, not_modeled = inject_attacker(_attacker(_gun()), [ia], frozenset())
        assert not modeled and any("bearer_leading" in n for n in not_modeled)
        assert atk.loadout[0].effects == ()


# ══ 守方向：真源 payload → 引擎级差别 ══════════════════════════════════════
class TestDefensiveFromPayload:
    def test_unholy_fortitude_t_plus1_shooting_only(self, entries):
        uf = _entry(entries, "000010744007")
        assert uf.status == "encoded"
        tgt, _, _ = inject_target(_target(t=4), [uf], frozenset())
        rs = _run(_attacker(_gun(s=4)), tgt, Stance(phase="shooting"))
        # S4 vs T5 → 5+ 致伤（1/3）
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 3, abs=0.02)
        rm = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_steadfast_determination_fnp5_shooting_only(self, entries):
        sd = _entry(entries, "000008977006")
        assert sd.status == "encoded"
        tgt, _, _ = inject_target(_target(w=1), [sd], frozenset())
        rs = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.damage, rs.unsaved) == pytest.approx(2 / 3, abs=0.03)
        rm = _run(_attacker(_melee(ap=-6)), tgt, Stance(phase="melee"))
        assert _ratio(rm.damage, rm.unsaved) == pytest.approx(1.0, abs=0.03)

    def test_monstrous_visages_hit_minus1_both_phases(self, entries):
        mv = _entry(entries, "000009774002")
        assert mv.status == "encoded"
        tgt, _, _ = inject_target(_target(), [mv], frozenset())
        for phase, wpn in (("shooting", _gun(bs=3)), ("melee", _melee(ws=3))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_low_cunning_wound_minus1_when_s_gt_t(self, entries):
        lc = _entry(entries, "000009504003")
        assert lc.status == "encoded"
        tgt, _, _ = inject_target(_target(t=4), [lc], frozenset())
        rs = _run(_attacker(_gun(s=8)), tgt, Stance(phase="shooting"))
        # S8 vs T4 → 2+ 致伤，-1 → 3+
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(2 / 3, abs=0.02)
        # S=T 时不触发
        re = _run(_attacker(_gun(s=4)), tgt, Stance(phase="shooting"))
        assert _ratio(re.wounds, re.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_unfailingly_obdurate_ap_worsen_both_phases(self, entries):
        uo = _entry(entries, "000008969002")
        assert uo.status == "encoded"
        tgt, _, _ = inject_target(_target(sv=4), [uo], frozenset())
        for phase, wpn in (("shooting", _gun(ap=-1)), ("melee", _melee(ap=-1))):
            base = _run(_attacker(wpn), _target(sv=4), Stance(phase=phase))
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            # AP-1 对 Sv4+ → 保存 5+（未过保 2/3）；恶化回 AP0 → 4+（未过保 1/2）
            assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_armour_of_corruption_damage_minus1_melee_only(self, entries):
        aoc = _entry(entries, "000010740003")
        assert aoc.status == "encoded"
        tgt, _, _ = inject_target(_target(w=3, sv=7), [aoc], frozenset())
        rm = _run(_attacker(_melee(d=3)), tgt, Stance(phase="melee"))
        assert _ratio(rm.damage, rm.unsaved) == pytest.approx(2.0, abs=0.05)
        rs = _run(_attacker(_gun(d=3)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.damage, rs.unsaved) == pytest.approx(3.0, abs=0.05)

    def test_shadowcowl_talisman_invuln5_needs_bearer_toggle(self, entries):
        st = _entry(entries, "fp11e-csm-murdertalon-e1")
        assert st.status == "encoded"
        off, _, notes = inject_target(_target(sv=7), [st], frozenset())
        assert off.effects == () and any("defender_bearer_leading" in n for n in notes)
        on, _, _ = inject_target(_target(sv=7), [st],
                                 frozenset({"defender_bearer_leading"}))
        # 无护甲（Sv 7+）→ 只剩 5+ 特殊保护：过保 1/3、未过保 2/3
        r = _run(_attacker(_gun(ap=-6)), on, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        bare = _run(_attacker(_gun(ap=-6)), _target(sv=7), Stance(phase="shooting"))
        assert _ratio(bare.unsaved, bare.wounds) == pytest.approx(1.0, abs=0.02)

    def test_soul_forge_boons_invuln5_both_phases(self, entries):
        sfb = _entry(entries, "det000010742")
        assert sfb.status == "partial"
        tgt, _, _ = inject_target(_target(sv=7), [sfb], frozenset())
        for phase, wpn in (("shooting", _gun(ap=-6)), ("melee", _melee(ap=-6))):
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_night_shroud_cover_shooting_only(self, entries):
        # 11 版 Stealth（24.33）→ 掩体收益（13.08）= 恶化该次远程攻击 BS 1 点；
        # 近战不受掩体影响
        ns = _entry(entries, "000008972003")
        assert ns.status == "encoded"
        tgt, _, _ = inject_target(_target(), [ns],
                                  frozenset({"defender_bearer_leading"}))
        rs = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 3, abs=0.02)
        rm = _run(_attacker(_melee(ws=4)), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)
