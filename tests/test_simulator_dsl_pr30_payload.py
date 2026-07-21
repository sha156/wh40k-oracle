"""P7-PR30 灵族（Aeldari，faction='AE'）全量 DSL 编码落账：1 条军规（战斗专注）
+ 19 个分队容器（16 个库内分队 + 3 个 FP 全新分队）的 21 条分队规则 + 100 战略
（含 Army Rules 容器下的 6 道灵动机动行）+ 60 增强 = 182
（21 encoded / 25 partial / 136 not_modeled）——零新引擎通道、零新态势开关。

灵族是「战斗专注令牌 × 灵动机动 × 移动/预备队机动」气质阵营：军规与绝大多数分队规则、
战略都落在移动域、射击资格域（[ASSAULT]/[PISTOL]/过度警戒/撤退后射击）、预备队域、
目标点控制域、令牌与 CP 经济、命运骰池、死后反打与复活，全部无引擎载体，故 not_modeled
占大多数。可编子集集中在命中·致伤骰修正与重掷 / AP 改善·恶化 / [IGNORES COVER] /
[LETHAL HITS] / [SUSTAINED HITS 1] / [DEVASTATING WOUNDS] / [LANCE] / 掩体（Stealth）/
FNP / 无效保护 / 伤害减免 / S·A·伤害加值。

fp_rules 侧：Armoured Warhost 11 版整页重印（1 规则 + 2 增强 + 3 战略）落 6 条 text_patch
+ 5 条 removed_11e；重印分队真漂移 3 条（WEAVING STRIDE 9"→8"、Archraider 的 Lord of
Deceit 改每回合一次且改为可选、VENGEFUL SORROW 改核心 surge move）；RULES UPDATES 7 条；
Fateful Performance / Path of the Outcast / Twilight Flickers 三个全新分队 18 行 inserts
（fp11e-aeldari-*）。工作单见 docs/superpowers/plans/2026-07-20-p7-pr30-aeldari-worklist.md。
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
PAYLOAD = Path("dsl_payloads/aeldari.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 19 个灵族分队容器名 + Army Rules 伪容器
# （stratagems.detachment / enhancements.detachment_name 口径）
AE_DETACHMENTS = (
    "Army Rules",
    "Khaine’s Arrow", "Protector Host", "Wraiths of the Void", "Star-dancer Masque",
    "Armoured Warhost", "Warhost", "Windrider Host", "Spirit Conclave",
    "Guardian Battlehost", "Ghosts of the Webway", "Devoted of Ynnead",
    "Seer Council", "Aspect Host", "Serpent’s Brood", "Eldritch Raiders",
    "Corsair Coterie",
    "Fateful Performance", "Path of the Outcast", "Twilight Flickers",
)
ARMY_RULE_ID = "000009894"          # 战斗专注（Battle Focus）


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="power sword", effects=()):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=tuple(effects), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="shuriken catapult", rng='18"', effects=()):
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


# ══ 结构与三态判据 ═══════════════════════════════════════════════════════════
class TestPayloadShape:
    def test_counts(self, entries):
        assert len(entries) == 182
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 21, "partial": 25, "not_modeled": 136}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        # 1 军规 + 18 库内分队规则 + 3 fp_new 分队规则；91 库内战略（94-3 removed）
        # + 9 fp_new；54 库内增强（56-2 removed）+ 6 fp_new
        assert by == {"abilities": 22, "stratagems": 100, "enhancements": 60}

    def test_faction_is_ae(self, entries):
        assert all(e.faction == "AE" for e in entries)

    def test_army_rule_present_and_not_modeled(self, entries):
        # 战斗专注是军规行（非 det 前缀、无 materialize）——令牌经济 + 六道灵动机动，
        # 引擎无令牌状态机与移动域，只能 not_modeled
        ar = _entry(entries, ARMY_RULE_ID)
        assert ar.table == "abilities" and ar.status == "not_modeled"
        assert not ar.effects and ar.not_modeled_notes_zh
        assert ar.detachment is None

    def test_detachment_field_matches_container_names(self, entries):
        # 分队字段必须落在真实容器名上（军规行除外）——写成规则名会被 select_entries 永不匹配
        for e in entries:
            if e.row_id == ARMY_RULE_ID:
                assert e.detachment is None
            else:
                assert e.detachment in AE_DETACHMENTS, (e.row_id, e.detachment)

    def test_eldritch_raiders_and_corsair_coterie_have_two_rule_rows(self, entries):
        # 两个海盗分队各有两条分队规则行（本体规则 + Veterans of the Void 编制条款）
        for rid in ("det000010697", "det000010698"):
            assert _entry(entries, rid).detachment == "Eldritch Raiders"
        for rid in ("det000010702", "det000010703"):
            assert _entry(entries, rid).detachment == "Corsair Coterie"

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
            ("hit", "auto_wound"), ("hit", "extra_hits"), ("hit", "ignore_hit_mods"),
            ("hit", "modify"), ("hit", "reroll"),
            ("wound", "modify"), ("wound", "mortal_pool"), ("wound", "reroll"),
            ("wound", "s_improve"),
            ("damage", "damage_reduction"), ("damage", "modify"),
            ("fnp", "fnp"),
            ("save", "ap_improve"), ("save", "cover"), ("save", "ignores_cover"),
            ("save", "invuln"), ("save", "sv_improve"),
        }
        for e in entries:
            for f in e.effects:
                assert (f.phase, f.op) in known, (e.row_id, f.phase, f.op)

    def test_no_new_toggle(self, entries):
        # 零新态势开关：只复用既有的两个通用假设开关
        used = {t for e in entries for t in e.requires_toggles}
        assert used == {"defender_bearer_leading", "range_within_12"}

    def test_bearer_leading_only_where_bearer_leads_its_unit(self, entries):
        # 「携带者所在/所率单位」型防守增强才挂 defender_bearer_leading
        for rid in ("000009903003",      # 幻影力场（携带者所在单位）
                    "000009927004"):     # 微光石（携带者所率相位战士单位）
            assert ("defender_bearer_leading"
                    in _entry(entries, rid).requires_toggles), rid

    def test_aura_and_bearer_only_entries_have_no_bearer_toggle(self, entries):
        # 反面（PR28/PR29 教训）：受益者是「范围内的另一友军单位」的光环增强、
        # 以及只作用于携带者本人的增强，都不挂 bearer 开关——
        # bearer_leading 语义是「携带者正率领本单位」，挂上会把语义写反
        for rid in ("000009325002",      # 圣所符文（9" 内另一友军单位）
                    "000009769002",      # 指引临在（6" 内另一友军 VEHICLE 单位）
                    "000009907004",      # 迷雾符文（12" 内另一友军灵构体单位）
                    "000009919002",      # 殷尼德之凝视（只给携带者本人的武器）
                    "000009919004",      # 借来的活力（只给携带者本人）
                    "000009919005",      # 病态之力（只给携带者本人）
                    "000009927002",      # 谋杀之相（只给携带者本人）
                    "000010649003",      # 织者的哀嚎（只给携带者本人）
                    "000009351003"):     # 艾尔达奈什之路（只给携带者本人）
            assert not _entry(entries, rid).requires_toggles, rid

    def test_range_toggle_paired_with_ranged_within_12_tag(self, entries):
        # ranged_within_12 是「自含射击阶段的绝对射程档假设」——必须与开关成对
        for e in entries:
            if any(tuple(f.condition) == ("ranged_within_12",) for f in e.effects):
                assert "range_within_12" in e.requires_toggles, e.row_id
        assert "range_within_12" in _entry(entries, "000009900005").requires_toggles

    def test_weapon_filter_entries(self, entries):
        assert _entry(entries, "000009335003").weapon_filter == "shuriken"
        assert _entry(entries, "000009919002").weapon_filter == "eldritch storm"
        # 其余条目不得误留 weapon_filter（会静默只作用于部分武器）
        filtered = {e.row_id for e in entries if e.weapon_filter}
        assert filtered == {"000009335003", "000009919002"}

    def test_self_keyword_note_only_on_non_opt_in_entries(self, entries):
        """适用面纪律（PR13/PR28/PR29 既有约定，PR30 自审复核后落成护栏）。

        战略/增强是 opt-in 条目——`select_entries` 必须被点名才入选，所以原文 TARGET 段
        的单位类型限制（「One HOWLING BANSHEES unit」/「排除 WRAITH CONSTRUCT」）是**玩家
        选择**，点名即声明，不计作未建模残量。前序已并阵营同判：星界军 BRUTAL TRAINING
        （One MILITARUM TEMPESTUS unit）、FURIOUS CANNONADE（One Squadron unit）、
        混沌星际战士 BALEFIRE BOON（One Soul Forge unit）、死灵 QUANTUM DEFLECTION
        （One NECRONS VEHICLE unit）全部是 encoded。

        分队规则相反——它**非 opt-in**（分队一匹配就自动施加），「Each time a〈窄关键词〉
        模型……」限定的是受益者集合而非玩家选择；引擎无攻/守方自关键词门，注入到任何
        攻/守方都会生效，必须逐条注记并降 partial。本测试把这条判据钉成名单，防止将来
        铺量时两类被混判。
        """
        NEEDLE = "自关键词门"
        flagged = {e.row_id for e in entries
                   if any(NEEDLE in n for n in e.not_modeled_notes_zh)}
        # 只有非 opt-in 的分队规则行（det 前缀）才带该注记
        assert flagged == {"det000009333",           # 坚决防御（GUARDIANS/DIRE AVENGERS）
                           "det000009910",           # 不惜一切代价的防御（四类模型）
                           "det000010648",           # 蛇群之赐（HARLEQUINS MOUNTED/VEHICLE）
                           "detfp11e-aeldari-twilight"}   # 扭曲之舞（HARLEQUINS）
        for rid in flagged:
            e = _entry(entries, rid)
            assert e.table == "abilities" and e.status == "partial", rid
        # 反面：opt-in 条目一律不因 TARGET 段单位类型限制而降级
        for rid in ("000009326003", "000009904007", "000009908004",
                    "000010700003", "fp11e-aeldari-twilight-s1"):
            assert _entry(entries, rid).status == "encoded", rid

    def test_narrower_than_target_clause_is_disclosed(self, entries):
        # 例外面：战略里「受益面窄于/异于 TARGET 单位」的从句仍须注记并降 partial——
        # 海盗应得的的完整重掷只给 ANHRATHE 单位，基础从句（重掷 1）无引擎载体
        e = _entry(entries, "000010705002")
        assert e.status == "partial"
        assert any("ANHRATHE" in n for n in e.not_modeled_notes_zh)

    def test_reroll_ops_are_fail_only(self, entries):
        for e in entries:
            for f in e.effects:
                if f.op == "reroll":
                    assert tuple(f.params) == ("fail",), e.row_id


# ══ DB 对账 ═════════════════════════════════════════════════════════════════
@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(AE_DETACHMENTS)), AE_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(AE_DETACHMENTS)), AE_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_no_orphan_ae_row_outside_detachments(self):
        # PR27 教训：上游空壳行（分队列为空）会被靠 detachment 过滤的对账测试静默漏掉
        con = self._db()
        orphans = [r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='AE' "
            "AND COALESCE(detachment, '') = ''")]
        orphans += [r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='AE' "
            "AND COALESCE(detachment_name, '') = ''")]
        con.close()
        assert orphans == []

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        rule_ids = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='AE'")}
        con.close()
        covered = {e.row_id for e in entries
                   if e.table == "abilities" and e.row_id != ARMY_RULE_ID}
        assert covered == rule_ids

    def test_removed_11e_rows_are_out_of_payload(self, entries):
        # Armoured Warhost 十版 2 增强 3 战略被 11 版重印取代 → 标 removed_11e 且不进 payload
        con = self._db()
        dead = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='AE' AND fp_status='removed_11e'")}
        dead |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='AE' "
            "AND fp_status='removed_11e'")}
        con.close()
        assert dead == {"000009770003", "000009770005", "000009770007",
                        "000009769003", "000009769005"}
        assert not (dead & {e.row_id for e in entries})

    def test_fp_new_rows_marked_added_11e(self):
        con = self._db()
        added = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-aeldari-%'")}
        added |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-aeldari-%'")}
        con.close()
        assert len(added) == 15          # 9 战略 + 6 增强（分队行不带 fp_status 列）

    def test_fateful_performance_is_a_distinct_detachment(self):
        # 11 版全新分队 Fateful Performance 与库内 Ghosts of the Webway 分队规则同名
        # （Acrobatic Onslaught），但 FP page_022 RULES UPDATES 仍在勘误 GotW ——
        # 两分队 11 版并存，不是改名。补录行必须与旧行同时存在且正文不同
        con = self._db()
        rows = {r[0]: r[1] for r in con.execute(
            "SELECT id, rule_text FROM detachments WHERE faction='AE' "
            "AND name_en='Acrobatic Onslaught'")}
        con.close()
        assert set(rows) == {"000009914", "fp11e-aeldari-fateful"}
        assert "ACROBATIC" in rows["fp11e-aeldari-fateful"]
        assert "TRAVELLING PLAYERS" not in rows["fp11e-aeldari-fateful"]
        assert "BATTLELINE" in rows["000009914"]

    def test_11e_text_patches_landed(self):
        # A/B 真漂移必须已落库（fp-rules 先于 dsl-apply）
        con = self._db()
        sc = con.execute("SELECT rule_text FROM detachments "
                         "WHERE id='000009768'").fetchone()[0]
        assert "[ASSAULT]" in sc and "re-roll Advance rolls" not in sc
        gp = con.execute("SELECT description FROM enhancements "
                         "WHERE id='000009769002'").fetchone()[0]
        assert 'within 6"' in gp and 'within 9"' not in gp
        ss = con.execute("SELECT description FROM enhancements "
                         "WHERE id='000009769004'").fetchone()[0]
        assert "In your Movement phase" in ss and "In your Command phase" not in ss
        lw = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009770002'").fetchone()[0]
        assert "Your unit has Feel No Pain 5+ against mortal wounds." in lw
        so = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009770006'").fetchone()[0]
        assert "One damage roll" in so and "fast dice rolling" not in so
        ve = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009770004'").fetchone()[0]
        assert "does not prevent your unit from being eligible to shoot" in ve
        ar = con.execute("SELECT description FROM enhancements "
                         "WHERE id='000010704004'").fetchone()[0]
        assert "Once per turn" in ar and "you can use this ability" in ar
        vs = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000010705007'").fetchone()[0]
        assert 'surge move of up to D6+1"' in vs and "as close as possible" not in vs
        for sid in ("000009928004", "000009900003"):
            txt = con.execute("SELECT text_zh FROM stratagems WHERE id=?",
                              (sid,)).fetchone()[0]
            assert "unengaged" in txt, sid
            assert "not within Engagement Range" not in txt, sid
        sfd = con.execute("SELECT rule_text FROM detachments "
                          "WHERE id='000009918'").fetchone()[0]
        assert 'surge move of up to D6+1"' in sfd
        assert "Lethal Surge move instead" not in sfd
        # 三条整条 9"→8" 几何漂移
        for sid in ("000010650006", "000009916005", "000009904005"):
            txt = con.execute("SELECT text_zh FROM stratagems WHERE id=?",
                              (sid,)).fetchone()[0]
            assert '9"' not in txt and '8"' in txt, sid
        # UNSHROUDED TRUTH 的 FP 勘误只改 TARGET 段的灵能者光环距离；
        # EFFECT 段「离所有敌军模型 9" 以上重新部署」FP 未改，不许连坐
        ut = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009924004'").fetchone()[0]
        assert 'is within 8" of one or more friendly Asuryani Psyker models' in ut
        assert 'more than 9" horizontally away from all enemy models' in ut
        hd = con.execute("SELECT description FROM enhancements "
                         "WHERE id='000009907005'").fetchone()[0]
        assert 'within 8"' in hd and "Once per turn" not in hd
        con.close()

    def test_reprinted_detachments_left_untouched(self):
        # Serpent's Brood（FP p6-p7）/ Eldritch Raiders（p8-p9）/ Corsair Coterie
        # （p10-p11）三分队的规则与绝大多数条目与库现文逐字一致（Wahapedia 已滚入）
        # → 免补。用 FP 正文里的判据短语锁死，而不是只量长度
        con = self._db()
        for did, needles in (
                ("000010648", ("[SUSTAINED HITS 1]", "disembarks from a Transport",
                               "TRAVELLING PLAYERS")),
                ("000010697", ("eligible to declare a charge in a turn in which they "
                               "Advanced", "re-roll the Advance roll")),
                ("000010702", ("suffers D3 mortal wounds", "Void Thieves"))):
            txt = con.execute("SELECT rule_text FROM detachments WHERE id=?",
                              (did,)).fetchone()[0]
            for needle in needles:
                assert needle in txt, (did, needle)
        # 未被 FP 改动的条目不该出现在本 PR 的 text_patch 清单里
        import json
        from pathlib import Path as _P
        patched = {p["id"] for p in json.loads(
            _P("db_compile/fp_rules_patches.json").read_text(encoding="utf-8")
        )["text_patches"]}
        untouched = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN "
            "('Eldritch Raiders', 'Serpent’s Brood')")} - {"000010650006"}
        untouched |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN "
            "('Eldritch Raiders', 'Serpent’s Brood', 'Corsair Coterie')")} - {
                "000010704004"}
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
        "000009325002",         # 圣所符文（WHEN=对手射击阶段）
        "000009335003",         # 手里剑风暴（WHEN=我方射击阶段）
        "000009326005",         # 集火扫射（WHEN=我方射击阶段）
        "000009343003",         # 灵视（WHEN=我方射击阶段）
        "000009904006",         # 集中火力（WHEN=我方射击阶段）
        "000009904007",         # 螺旋闪避（WHEN=对手射击阶段）
        "000009907004",         # 迷雾符文（原文限远程攻击）
        "000009920006",         # 灵视（远程武器关键词）
        "000009924005",         # 无可逃避的命运（WHEN=我方射击阶段）
        "000009927004",         # 微光石（原文限远程攻击）
        "000010705006",         # 斗篷与阴影（Stealth＝11 版远程掩体）
        "detfp11e-aeldari-twilight",   # 扭曲之舞（Stealth）
    )
    MELEE_ONLY = (
        "000009343002",         # 守护构装（WHEN=近战阶段）
        "000009352003",         # 疾刺（WHEN=近战阶段）
        "000009351003",         # 艾尔达奈什之路（近战武器 AP）
        "000009908004",         # 彼岸之刃（近战武器 [DEVASTATING WOUNDS]）
        "000009919004",         # 借来的活力（近战武器 A）
        "000009919005",         # 病态之力（原文限近战攻击）
        "000009924003",         # 预警（WHEN=近战阶段）
        "000009927002",         # 谋杀之相（近战武器伤害）
        "000010649003",         # 织者的哀嚎（近战武器 S/A）
        "000010700004",         # 伊瑞尔的表率（WHEN=近战阶段）
        "000010705002",         # 海盗应得的（WHEN=近战阶段）
    )
    # WHEN 明确写「（对手/我方）射击阶段**或**近战阶段」，或原文根本未限相位 ——
    # 两相位皆可生效，加相位门反而是欠建模（PR13 反方向 MEDIUM 的同型判据）
    NO_PHASE_GATE = (
        "000009326002", "000009335002", "000009352002",   # 虚空幽魂 ×3
        "000009900002",         # 闪电般的反应
        "000009903003",         # 幻影力场（原文未限相位）
        "000009904002",         # 自天而降（我方射击阶段或近战阶段）
        "000009908003",         # 灵骨装甲（对手射击阶段或近战阶段）
        "000009912002",         # 守护齐射（我方射击阶段或近战阶段）
        "000009912003",         # 护盾节点（对手射击阶段或近战阶段）
        "000009920003",         # 阴森韧性（对手射击阶段或近战阶段）
        "000009928002",         # 战士专注（我方射击阶段或近战阶段）
        "det000009333",         # 坚决防御（原文未限相位）
        "det000009910",         # 不惜一切代价的防御（原文未限相位）
        "det000010648",         # 蛇群之赐（原文未限相位）
        "000010700003",         # 无情杀手（我方射击阶段或近战阶段）
        "000010704005",         # 虚空石（原文未限相位）
    )
    CHARGE_GATED = (
        "000009326003",                 # 刃之专注（冲锋回合近战重掷命中）
        "000010699003",                 # 迅捷突击（[LANCE]）
        "fp11e-aeldari-twilight-s1",    # 预兆彩排（[LANCE]）
    )

    def test_shooting_only_entries_gated(self, entries):
        for rid in self.SHOOTING_ONLY:
            e = _entry(entries, rid)
            assert e.effects, rid
            for f in e.effects:
                assert tuple(f.condition) == ("phase_shooting",), (rid, f.condition)

    def test_melee_only_entries_gated(self, entries):
        for rid in self.MELEE_ONLY:
            e = _entry(entries, rid)
            assert e.effects, rid
            for f in e.effects:
                assert tuple(f.condition) == ("phase_melee",), (rid, f.condition)

    def test_two_phase_entries_are_not_over_gated(self, entries):
        # 反方向核对：WHEN 覆盖两相位的条目不许挂 phase_* 门（过度加门＝欠建模）
        for rid in self.NO_PHASE_GATE:
            for f in _entry(entries, rid).effects:
                assert tuple(f.condition) == (), (rid, f.condition)

    def test_charge_conditioned_entries_use_composite_tag(self, entries):
        # 冲锋后触发的条款必须用自含近战门的 melee_charging——
        # 裸 charging 会在射击阶段误放行（PR10/11/12/14 四次同型 HIGH）
        for rid in self.CHARGE_GATED:
            e = _entry(entries, rid)
            assert e.effects, rid
            for f in e.effects:
                assert tuple(f.condition) == ("melee_charging",), (rid, f.condition)

    def test_no_bare_charging_tag_anywhere(self, entries):
        for e in entries:
            for f in e.effects:
                assert tuple(f.condition) != ("charging",), e.row_id

    def test_half_range_entry_is_partial_and_disclosed(self, entries):
        # half_range 不自含相位门——挂它的条目一律降 partial 并注明须只在射击模拟下开启
        e = _entry(entries, "000010705004")
        assert e.status == "partial"
        assert any(tuple(f.condition) == ("half_range",) for f in e.effects)
        assert any("只在射击模拟下开启" in n for n in e.not_modeled_notes_zh)


# ══ 行为断言：可编条目真的改变结果 ════════════════════════════════════════════
def _atk_with(entries, rid, weapons, toggles=frozenset()):
    atk, modeled, _ = inject_attacker(_attacker(*weapons), [_entry(entries, rid)],
                                      frozenset(toggles))
    assert modeled, rid
    return atk


def _tgt_with(entries, rid, target, toggles=frozenset()):
    tgt, modeled, _ = inject_target(target, [_entry(entries, rid)], frozenset(toggles))
    assert modeled, rid
    return tgt


class TestDefensiveBehaviour:
    def test_void_ghosts_hit_minus_one_in_both_phases(self, entries):
        base = _target()
        buffed = _tgt_with(entries, "000009326002", base)
        for phase, weapon in (("shooting", _gun()), ("melee", _melee())):
            st = Stance(phase=phase)
            plain = _run(_attacker(weapon), base, st)
            worse = _run(_attacker(weapon), buffed, st)
            # BS/WS 4+ → 3/6；命中 -1 后 2/6
            assert _ratio(worse.damage, plain.damage) == pytest.approx(2 / 3, abs=0.05)

    def test_spiralling_evasion_invuln_shooting_only(self, entries):
        base = _target(sv=6)
        buffed = _tgt_with(entries, "000009904007", base)
        shoot = Stance(phase="shooting")
        assert _run(_attacker(_gun(ap=-2)), buffed, shoot).damage.mean() < \
            _run(_attacker(_gun(ap=-2)), base, shoot).damage.mean()
        fight = Stance(phase="melee")
        assert _run(_attacker(_melee(ap=-2)), buffed, fight).damage.mean() == \
            pytest.approx(_run(_attacker(_melee(ap=-2)), base, fight).damage.mean(),
                          rel=0.02)

    def test_voidstone_invuln_both_phases(self, entries):
        base = _target(sv=6)
        buffed = _tgt_with(entries, "000010704005", base)
        for phase, weapon in (("shooting", _gun(ap=-3)), ("melee", _melee(ap=-3))):
            st = Stance(phase=phase)
            assert _run(_attacker(weapon), buffed, st).damage.mean() < \
                _run(_attacker(weapon), base, st).damage.mean()

    def test_wraithbone_armour_damage_reduction(self, entries):
        base = _target(t=4, sv=3, w=3, models=3)
        buffed = _tgt_with(entries, "000009908003", base)
        st = Stance(phase="shooting")
        plain = _run(_attacker(_gun(d=2, ap=-2)), base, st)
        red = _run(_attacker(_gun(d=2, ap=-2)), buffed, st)
        assert _ratio(red.damage, plain.damage) == pytest.approx(0.5, abs=0.05)

    def test_yriels_example_fnp_melee_only(self, entries):
        base = _target(sv=4)
        buffed = _tgt_with(entries, "000010700004", base)
        fight = Stance(phase="melee")
        assert _ratio(_run(_attacker(_melee()), buffed, fight).damage,
                      _run(_attacker(_melee()), base, fight).damage) \
            == pytest.approx(2 / 3, abs=0.05)
        shoot = Stance(phase="shooting")
        assert _run(_attacker(_gun()), buffed, shoot).damage.mean() == pytest.approx(
            _run(_attacker(_gun()), base, shoot).damage.mean(), rel=0.02)

    def test_runes_of_sanctuary_worsens_ap(self, entries):
        base = _target(sv=4)
        buffed = _tgt_with(entries, "000009325002", base)
        st = Stance(phase="shooting")
        assert _run(_attacker(_gun(ap=-1)), buffed, st).damage.mean() < \
            _run(_attacker(_gun(ap=-1)), base, st).damage.mean()

    def test_determined_defence_improves_armour_save(self, entries):
        base = _target(sv=4)
        buffed = _tgt_with(entries, "det000009333", base)
        st = Stance(phase="shooting")
        assert _run(_attacker(_gun()), buffed, st).damage.mean() < \
            _run(_attacker(_gun()), base, st).damage.mean()

    def test_shimmerstone_requires_bearer_toggle(self, entries):
        base = _target()
        e = [_entry(entries, "000009927004")]
        blocked, modeled, notes = inject_target(base, e, frozenset())
        assert not modeled and blocked is base
        assert any("defender_bearer_leading" in n for n in notes)
        ok, modeled, _ = inject_target(base, e, frozenset({"defender_bearer_leading"}))
        assert modeled and ok.effects

    def test_stealth_entries_grant_cover(self, entries):
        base = _target(sv=4)
        st = Stance(phase="shooting")
        plain = _run(_attacker(_gun()), base, st)
        for rid in ("000010705006", "detfp11e-aeldari-twilight"):
            buffed = _tgt_with(entries, rid, base)
            assert _run(_attacker(_gun()), buffed, st).damage.mean() < \
                plain.damage.mean(), rid


class TestOffensiveBehaviour:
    def test_bladefocus_reroll_only_on_charging_melee(self, entries):
        w = _melee()
        atk = _atk_with(entries, "000009326003", [w])
        plain = _attacker(w)
        charged = Stance(phase="melee", charging=True)
        assert _run(atk, _target(), charged).damage.mean() > \
            _run(plain, _target(), charged).damage.mean()
        # 射击阶段即使 charging 开着也不许放行（复合 tag 自含近战门）
        shoot = Stance(phase="shooting", charging=True)
        g = _gun()
        atk_g = _atk_with(entries, "000009326003", [g])
        assert _run(atk_g, _target(), shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), _target(), shoot).damage.mean(), rel=0.02)

    def test_lance_entries_add_wound_on_charge(self, entries):
        w = _melee(s=4)
        tgt = _target(t=5)
        charged = Stance(phase="melee", charging=True)
        for rid in ("000010699003", "fp11e-aeldari-twilight-s1"):
            atk = _atk_with(entries, rid, [w])
            assert _run(atk, tgt, charged).damage.mean() > \
                _run(_attacker(w), tgt, charged).damage.mean(), rid
            # 未冲锋回合不生效
            plainst = Stance(phase="melee")
            assert _run(atk, tgt, plainst).damage.mean() == pytest.approx(
                _run(_attacker(w), tgt, plainst).damage.mean(), rel=0.02), rid

    def test_focused_fusillade_wound_plus_one_shooting_only(self, entries):
        g = _gun(s=4)
        tgt = _target(t=5)
        atk = _atk_with(entries, "000009326005", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk, tgt, shoot).damage.mean() > \
            _run(_attacker(g), tgt, shoot).damage.mean()
        m = _melee(s=4)
        atk_m = _atk_with(entries, "000009326005", [m])
        fight = Stance(phase="melee")
        assert _run(atk_m, tgt, fight).damage.mean() == pytest.approx(
            _run(_attacker(m), tgt, fight).damage.mean(), rel=0.02)

    def test_focused_firepower_ap_improve(self, entries):
        g = _gun()
        tgt = _target(sv=4)
        atk = _atk_with(entries, "000009904006", [g])
        st = Stance(phase="shooting")
        assert _run(atk, tgt, st).damage.mean() > \
            _run(_attacker(g), tgt, st).damage.mean()

    def test_blades_from_beyond_devastating_wounds(self, entries):
        m = _melee(s=4)
        tgt = _target(t=4, sv=2)
        atk = _atk_with(entries, "000009908004", [m])
        fight = Stance(phase="melee")
        assert _run(atk, tgt, fight).damage.mean() > \
            _run(_attacker(m), tgt, fight).damage.mean()

    def test_ynnari_soulsight_lethal_hits_and_ignores_cover(self, entries):
        g = _gun(s=3)
        tgt = _target(t=6, sv=4)
        atk = _atk_with(entries, "000009920006", [g])
        st = Stance(phase="shooting", target_in_cover=True)
        assert _run(atk, tgt, st).damage.mean() > \
            _run(_attacker(g), tgt, st).damage.mean()

    def test_ruthless_killers_damage_plus_one_both_phases(self, entries):
        for phase, w in (("shooting", _gun(d=1)), ("melee", _melee(d=1))):
            atk = _atk_with(entries, "000010700003", [w])
            st = Stance(phase=phase)
            assert _ratio(_run(atk, _target(w=3, models=3), st).damage,
                          _run(_attacker(w), _target(w=3, models=3), st).damage) \
                == pytest.approx(2.0, abs=0.1)

    def test_blitzing_firepower_needs_range_toggle(self, entries):
        g = _gun()
        e = [_entry(entries, "000009900005")]
        blocked, modeled, notes = inject_attacker(_attacker(g), e, frozenset())
        assert not modeled and any("range_within_12" in n for n in notes)
        atk = _atk_with(entries, "000009900005", [g], {"range_within_12"})
        st = Stance(phase="shooting", range_within_12=True)
        assert _run(atk, _target(), st).damage.mean() > \
            _run(_attacker(g), _target(), st).damage.mean()

    def test_weapon_filter_shuriken_storm_only_hits_named_weapons(self, entries):
        shuri, other = _gun(name="shuriken catapult", s=4), _gun(name="lasblaster", s=4)
        atk = _atk_with(entries, "000009335003", [shuri, other])
        by_name = {w.name_en: w for w in atk.loadout}
        assert by_name["shuriken catapult"].effects
        assert not by_name["lasblaster"].effects

    def test_weapon_filter_gaze_of_ynnead(self, entries):
        storm, other = _gun(name="Eldritch Storm"), _gun(name="shuriken pistol")
        atk = _atk_with(entries, "000009919002", [storm, other])
        by_name = {w.name_en: w for w in atk.loadout}
        assert by_name["Eldritch Storm"].effects
        assert not by_name["shuriken pistol"].effects

    def test_weapon_filter_miss_is_disclosed_not_silent(self, entries):
        atk, modeled, notes = inject_attacker(
            _attacker(_gun(name="lasblaster")), [_entry(entries, "000009919002")],
            frozenset())
        assert not modeled
        assert any("eldritch storm" in n.lower() for n in notes)

    def test_weavers_wail_s_and_a(self, entries):
        m = _melee(s=4)
        tgt = _target(t=8)
        atk = _atk_with(entries, "000010649003", [m])
        fight = Stance(phase="melee")
        # S 4→7 且 A +1：致伤从 6+ 变 5+，攻击数翻倍
        assert _run(atk, tgt, fight).damage.mean() > \
            2.5 * _run(_attacker(m), tgt, fight).damage.mean()

    def test_warrior_focus_ignores_negative_hit_mods(self, entries):
        g = _gun()
        smoked = _target(effects=_entry(entries, "000009326002").effects)
        st = Stance(phase="shooting")
        atk = _atk_with(entries, "000009928002", [g])
        # 无 DSL 时守方 -1 命中生效；战士专注后忽略负修正 → 回到裸命中
        assert _run(atk, smoked, st).damage.mean() > \
            _run(_attacker(g), smoked, st).damage.mean()
        assert _run(atk, smoked, st).damage.mean() == pytest.approx(
            _run(_attacker(g), _target(), st).damage.mean(), rel=0.03)

    def test_boons_of_the_brood_sustained_hits(self, entries):
        g = _gun()
        atk = _atk_with(entries, "det000010648", [g])
        st = Stance(phase="shooting")
        assert _run(atk, _target(), st).damage.mean() > \
            _run(_attacker(g), _target(), st).damage.mean()

    def test_outcast_ambush_rapid_fire_needs_half_range(self, entries):
        g = _gun()
        atk = _atk_with(entries, "000010705004", [g])
        st_far = Stance(phase="shooting")
        st_near = Stance(phase="shooting", half_range=True)
        assert _run(atk, _target(sv=4), st_near).damage.mean() > \
            _run(atk, _target(sv=4), st_far).damage.mean()


# ══ 诚实语义：not_modeled 条目在报告里露面但不改数值 ═════════════════════════
class TestHonestyDisclosure:
    def test_not_modeled_entries_surface_in_notes(self, entries):
        g = _gun()
        e = [_entry(entries, "000009894")]        # 军规战斗专注
        atk, modeled, notes = inject_attacker(_attacker(g), e, frozenset())
        assert not modeled and notes
        assert atk.loadout[0].effects == ()

    def test_defensive_entry_on_attacker_path_is_direction_disclosed(self, entries):
        g = _gun()
        e = [_entry(entries, "000009326002")]     # 虚空幽魂（守方向）
        atk, modeled, notes = inject_attacker(_attacker(g), e, frozenset())
        assert not modeled
        assert any("防守向" in n for n in notes)
        assert atk.loadout[0].effects == ()

    def test_partial_residue_notes_are_passed_through(self, entries):
        g = _gun()
        atk, modeled, notes = inject_attacker(
            _attacker(g), [_entry(entries, "000009343003")], frozenset())
        assert modeled
        assert any("未建模残量" in n for n in notes)

    def test_all_effects_are_consumed_by_engine(self, entries):
        # 攻守两侧全部 effects 必须落在引擎消费点上（否则报告里出现却不影响结果）
        from engines.simulator.sequence import (
            unconsumed_attacker_effect_notes,
            unconsumed_target_effect_notes,
        )
        atk_entries = [e for e in entries if e.side == "attacker" and e.effects]
        tgt_entries = [e for e in entries if e.side == "target" and e.effects]
        toggles = frozenset({"range_within_12", "defender_bearer_leading"})
        atk, _, _ = inject_attacker(
            _attacker(_gun(name="shuriken catapult"), _melee(name="Eldritch Storm")),
            atk_entries, toggles)
        assert unconsumed_attacker_effect_notes(atk) == []
        tgt, _, _ = inject_target(_target(), tgt_entries, toggles)
        assert unconsumed_target_effect_notes(tgt) == []
