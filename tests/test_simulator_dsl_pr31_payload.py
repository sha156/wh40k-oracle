"""P7-PR31 吞噬者（Tyranids，faction='TYR'）全量 DSL 编码落账：2 条军规（突触 /
扭曲阴影）+ 14 个分队容器（12 个库内分队 + 2 个 FP 全新分队）的 14 条分队规则
+ 67 战略 + 41 增强 = 124（16 encoded / 19 partial / 89 not_modeled）
——零新引擎通道、零新态势开关（只复用既有的 bearer_leading 与
defender_bearer_leading 两个通用假设门）。

吞噬者是「突触范围位置态 × 再生复活 × 群体机动」气质阵营：军规与过半分队规则、战略
落在突触范围位置态、治疗与复活域、移动与预备队域、目标点控制、战斗震撼与士气、
死后反打，全部无引擎载体，故 not_modeled 占多数。可编子集集中在命中·致伤骰修正与
重掷 / AP 改善·恶化 / [IGNORES COVER] / [LETHAL HITS] / [SUSTAINED HITS 1] / 掩体 /
FNP / 无效保护 / 伤害减免 / S 加值 / 暴击阈值。

fp_rules 侧：Warrior Bioform Onslaught 11 版整页重印（1 规则 + 2 增强 + 3 战略）落
5 条 text_patch + 6 条 removed_11e + 1 条 fp_new（ALIEN PHYSIOLOGY）；RULES UPDATES
真漂移 11 条——其中 Insurmountable Odds / HYPERSENSORY SCILLIA / Biovores 三条来自
PDF 原页（refine 缓存 page_019.md 尾部截断整块漏掉，PyMuPDF 兜底捞回）；
Ambush Predators / Talons of the Norn Queen 两个全新分队 12 行 inserts
（fp11e-tyranids-*）。工作单见
docs/superpowers/plans/2026-07-20-p7-pr31-tyranids-worklist.md。
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
PAYLOAD = Path("dsl_payloads/tyranids.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 14 个吞噬者分队容器名（stratagems.detachment / enhancements.detachment_name 口径）
TYR_DETACHMENTS = (
    "Invasion Fleet", "Unending Swarm", "Assimilation Swarm", "Vanguard Onslaught",
    "Crusher Stampede", "Synaptic Nexus", "Tyranid Attack", "Boarding Swarm",
    "Biotide", "Infestation Swarm", "Warrior Bioform Onslaught",
    "Subterranean Assault",
    "Ambush Predators", "Talons of the Norn Queen",
)
# 军规行（吞噬者有两条：突触 + 扭曲阴影，两条 FP 都做了 RULES UPDATES）
ARMY_RULE_IDS = frozenset({"000000705", "000000707"})


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="scything talons", effects=()):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=tuple(effects), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="devourer", rng='18"', effects=()):
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
        assert len(entries) == 124
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 16, "partial": 19, "not_modeled": 89}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        # 2 军规 + 12 库内分队规则 + 2 fp_new 分队规则；60 库内战略（64-4 removed）
        # + 7 fp_new；37 库内增强（39-2 removed）+ 4 fp_new
        assert by == {"abilities": 16, "stratagems": 67, "enhancements": 41}

    def test_faction_is_tyr(self, entries):
        assert all(e.faction == "TYR" for e in entries)

    def test_both_army_rules_present_and_not_modeled(self, entries):
        # 突触与扭曲阴影都是军规行（非 det 前缀、无 materialize）：
        # 突触范围是位置态、扭曲阴影是战斗震撼域，零新开关约束下均无载体
        for rid in sorted(ARMY_RULE_IDS):
            ar = _entry(entries, rid)
            assert ar.table == "abilities" and ar.status == "not_modeled"
            assert not ar.effects and ar.not_modeled_notes_zh
            assert ar.detachment is None

    def test_synapse_melee_strength_is_disclosed_not_encoded(self, entries):
        # 突触第二款「近战攻击 S+1」本身有 (wound, s_improve) 通道，但整条挂在
        # 「本单位处于我军突触范围内」的位置态前提下——裸编＝对任何吞噬者攻方无条件
        # +1 S。本测试把「有通道但仍不编」的理由钉住，防止后续铺量时被"顺手补上"
        notes = _entry(entries, "000000705").not_modeled_notes_zh
        assert any("s_improve" in n for n in notes)
        assert any("突触范围" in n for n in notes)

    def test_detachment_field_matches_container_names(self, entries):
        # 分队字段必须落在真实容器名上（军规行除外）——写成规则名会被 select_entries 永不匹配
        for e in entries:
            if e.row_id in ARMY_RULE_IDS:
                assert e.detachment is None
            else:
                assert e.detachment in TYR_DETACHMENTS, (e.row_id, e.detachment)

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
            ("hit", "auto_wound"), ("hit", "bs_improve"), ("hit", "crit_threshold"),
            ("hit", "extra_hits"), ("hit", "ignore_hit_mods"), ("hit", "modify"),
            ("hit", "reroll"),
            ("wound", "modify"), ("wound", "reroll"), ("wound", "s_improve"),
            ("damage", "damage_reduction"), ("damage", "modify"),
            ("fnp", "fnp"),
            ("save", "ap_improve"), ("save", "cover"), ("save", "ignores_cover"),
            ("save", "invuln"), ("save", "sv_improve"),
        }
        for e in entries:
            for f in e.effects:
                assert (f.phase, f.op) in known, (e.row_id, f.phase, f.op)

    def test_no_new_toggle(self, entries):
        # 零新态势开关：只复用注册表里既有的两个「携带者作用面成立」通用假设门
        used = {t for e in entries for t in e.requires_toggles}
        assert used == {"bearer_leading", "defender_bearer_leading"}

    def test_bearer_leading_on_every_enhancement_with_effects(self, entries):
        """携带者型增强两侧同标准（PR31 自审 MEDIUM-2）。

        `bearer_leading` / `defender_bearer_leading` 是「携带者正率领本单位、作用面
        成立」的纯注入门。本阵营带 effects 的增强**全部**是「携带者本人」或「携带者
        所在单位」型，故攻守两侧一律挂门——攻方少挂会造成同文件内攻/守披露不对称：
        守方 Chameleonic 不开开关就拒注入并显式披露，攻方 Ocular Adaptation 却零提示
        直通（把增强施加到根本没带它的单位上）。

        例外只有一条：自然化伪装的受益者是首轮开始时另选的至多三个无尽群兽单位
        （不一定含携带者所在单位），挂 bearer 门会把语义写反——这是 PR28/PR29/PR30
        反复钉过的判据，故显式列为白名单而不是放宽全局断言。
        """
        AURA_EXCEPTION = {"000008408003"}        # 自然化伪装
        for e in entries:
            if e.table != "enhancements" or not e.effects:
                continue
            if e.row_id in AURA_EXCEPTION:
                assert not e.requires_toggles, e.row_id
                continue
            want = ("bearer_leading" if e.side == "attacker"
                    else "defender_bearer_leading")
            assert want in e.requires_toggles, (e.row_id, e.side)
        # 反面：分队规则与战略不是「携带者」型条目，不许挂 bearer 门
        for e in entries:
            if e.table != "enhancements":
                assert not any(t.endswith("bearer_leading")
                               for t in e.requires_toggles), e.row_id

    def test_other_selected_units_entry_has_no_bearer_toggle(self, entries):
        # 反面（PR28/PR29/PR30 教训）：受益者是「另外选定的一批友军单位」时不挂 bearer
        # 开关——bearer_leading 语义是「携带者正率领本单位」，挂上会把语义写反
        e = _entry(entries, "000008408003")      # 自然化伪装（另选三个无尽群兽单位）
        assert not e.requires_toggles
        assert any("不一定含携带者所在单位" in n for n in e.not_modeled_notes_zh)

    def test_attacker_side_entries_never_use_target_toggles(self, entries):
        # 攻方注入路径只收 ATTACKER_TOGGLES；把 defender_* 写进攻方条目 = 静默永不生效
        for e in entries:
            if e.side == "attacker":
                assert not any(t.startswith("defender_") for t in e.requires_toggles), \
                    e.row_id

    def test_no_weapon_filter_anywhere(self, entries):
        # 本阵营无「只作用于某把具名武器」的条目；虫巢心智之力的「灵能武器」是关键词
        # 界定的集合，weapon_filter 只能按名字子串选，选不中 → 该条判 not_modeled
        assert {e.row_id for e in entries if e.weapon_filter} == set()
        pw = _entry(entries, "000008421002")     # Power of the Hive Mind
        assert pw.status == "not_modeled"
        assert any("weapon_filter" in n for n in pw.not_modeled_notes_zh)

    def test_self_keyword_note_only_on_non_opt_in_detachment_rules(self, entries):
        """适用面纪律（PR13/PR28/PR29/PR30 既有约定，本 PR 沿用并落成护栏）。

        战略/增强是 opt-in 条目——`select_entries` 必须被点名才入选，所以原文 TARGET 段
        的单位类型限制与几何/状态前提（「One HARVESTER unit」「处于我军突触范围内」
        「位于我方控制的目标点范围内」）是**玩家点名时自行满足**，不计作未建模残量。

        分队规则相反——它**非 opt-in**（分队一匹配就自动施加），「Each time a〈窄关键词〉
        模型/单位……」限定的是受益者集合而非玩家选择；引擎无攻/守方自关键词门，注入到
        任何攻/守方都会生效，必须逐条注记并降 partial。
        """
        NEEDLE = "自关键词门"
        flagged = {e.row_id for e in entries
                   if any(NEEDLE in n for n in e.not_modeled_notes_zh)}
        assert flagged == {"det000009723",       # 半瞥之影（GREAT DEVOURER）
                           "det000009736"}       # 战兽领主（三类泰伦战士模型）
        for rid in flagged:
            e = _entry(entries, rid)
            assert e.table == "abilities" and e.status == "partial", rid
        # 反面：opt-in 条目一律不因 TARGET 段单位类型/状态前提而降级
        for rid in ("000009682002",              # 生物酸激涌（TARGET 须在突触范围内）
                    "000009725002",              # 超肾上腺反射（One GREAT DEVOURER unit）
                    "000009738006",              # 寄生载荷（One TYRANID WARRIORS unit）
                    "fp11e-tyranids-norn-s2"):   # 低等猎物（NORN ASSIMILATOR/EMISSARY）
            assert _entry(entries, rid).status == "encoded", rid

    def test_effect_branch_residue_is_disclosed(self, entries):
        # EFFECT 段内部的运行时分歧（「若…则改为」「若…则同样 +1」）必须注记并降 partial
        for rid, needle in (("000008349002", "FNP 5+"),        # 突触范围则升 5+
                            ("000008413005", "FNP 4+"),        # 目标点范围则升 4+
                            ("000008413006", "HARVESTER"),     # 收割者则暴击阈值 5+
                            ("000008418002", "战斗震撼"),      # 检定失败则致伤 +1
                            ("000008422004", "战斗震撼"),      # 检定失败则致伤 -1
                            ("000008409005", "15")):           # 15 模型档暴击阈值
            e = _entry(entries, rid)
            assert e.status == "partial", rid
            assert any(needle in n for n in e.not_modeled_notes_zh), (rid, needle)

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
        # faction='TYR' 是必要过滤：Infestation Swarm 是 TYR/GC 共用的登舰行动分队，
        # 库里有 faction='GC' 的同名同容器副本（另属基因窃取者教派，不进本载荷）
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='TYR' AND detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(TYR_DETACHMENTS)), TYR_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='TYR' "
            "AND detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(TYR_DETACHMENTS)), TYR_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_shared_boarding_detachment_gc_rows_are_out_of_payload(self, entries):
        # 共用容器名的守卫：GC 侧 6 行（4 战略 + 2 增强）必须留给未来的 GC PR，
        # 不许被 TYR 载荷吞掉——去掉 faction 过滤时本测试会红
        con = self._db()
        gc = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='GC' "
            "AND detachment='Infestation Swarm'")}
        gc |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='GC' "
            "AND detachment_name='Infestation Swarm'")}
        con.close()
        assert len(gc) == 6
        assert not (gc & {e.row_id for e in entries})

    def test_no_orphan_tyr_row_outside_detachments(self):
        # PR27 教训：上游空壳行（分队列为空）会被靠 detachment 过滤的对账测试静默漏掉
        con = self._db()
        orphans = [r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='TYR' "
            "AND COALESCE(detachment, '') = ''")]
        orphans += [r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='TYR' "
            "AND COALESCE(detachment_name, '') = ''")]
        con.close()
        assert orphans == []

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        rule_ids = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='TYR'")}
        con.close()
        covered = {e.row_id for e in entries
                   if e.table == "abilities" and e.row_id not in ARMY_RULE_IDS}
        assert covered == rule_ids

    def test_removed_11e_rows_are_out_of_payload(self, entries):
        # WBO 十版 2 增强 4 战略被 11 版重印取代 → 标 removed_11e 且不进 payload
        con = self._db()
        dead = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='TYR' AND fp_status='removed_11e'")}
        dead |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='TYR' "
            "AND fp_status='removed_11e'")}
        con.close()
        assert dead == {"000009738002", "000009738003", "000009738004",
                        "000009738007", "000009737002", "000009737004"}
        assert not (dead & {e.row_id for e in entries})

    def test_fp_new_rows_marked_added_11e(self):
        con = self._db()
        added = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-tyranids-%'")}
        added |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE fp_status='added_11e' "
            "AND id LIKE 'fp11e-tyranids-%'")}
        con.close()
        assert len(added) == 11          # 7 战略 + 4 增强（分队行不带 fp_status 列）

    def test_new_detachments_have_zero_prior_db_rows(self):
        # fp_new 前置判据：两个"全新"分队在补录前库内 0 命中（synthetic id 是唯一来源）
        con = self._db()
        for det in ("Ambush Predators", "Talons of the Norn Queen"):
            legacy = [r[0] for r in con.execute(
                "SELECT id FROM stratagems WHERE detachment=? "
                "AND id NOT LIKE 'fp11e-%'", (det,))]
            legacy += [r[0] for r in con.execute(
                "SELECT id FROM enhancements WHERE detachment_name=? "
                "AND id NOT LIKE 'fp11e-%'", (det,))]
            assert legacy == [], (det, legacy)
        con.close()

    def test_11e_text_patches_landed(self):
        # A/B 真漂移必须已落库（fp-rules 先于 dsl-apply）
        con = self._db()
        lb = con.execute("SELECT rule_text FROM detachments "
                         "WHERE id='000009736'").fetchone()[0]
        assert "5+ invulnerable save" in lb
        assert "Objective Control characteristic of 3" not in lb
        io_ = con.execute("SELECT rule_text FROM detachments "
                          "WHERE id='000008407'").fetchone()[0]
        assert 'surge move of up to D6"' in io_ and "as close as possible" not in io_
        idf = con.execute("SELECT description FROM enhancements "
                          "WHERE id='000008412003'").fetchone()[0]
        assert "that use is -1 CP" in idf and "for 0CP" not in idf
        oa = con.execute("SELECT description FROM enhancements "
                         "WHERE id='000009737003'").fetchone()[0]
        assert "melee attacks have +1 to hit rolls" in oa
        em = con.execute("SELECT description FROM enhancements "
                         "WHERE id='000009737005'").fetchone()[0]
        assert "re-roll wound rolls" in em and "Advanced" not in em
        sm = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009738005'").fetchone()[0]
        assert "End of your Movement phase" in sm and "is secured" in sm
        pp = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000009738006'").fetchone()[0]
        assert "[IGNORE COVER]" in pp and "Benefit of Cover" not in pp
        # HYPERSENSORY SCILLIA 的 9"→8" 只改 TARGET 段两处；EFFECT 段 6" 不许连坐
        hs = con.execute("SELECT text_zh FROM stratagems "
                         "WHERE id='000008418005'").fetchone()[0]
        assert '9"' not in hs and hs.count('within 8"') == 2
        assert 'Normal move of up to 6"' in hs
        # 兵牌技能层：surge move 术语化 / 整条改写 / 定点 9"→8"
        ba = con.execute("SELECT text_zh FROM abilities "
                         "WHERE id='000000490_a1'").fetchone()[0]
        assert 'surge move of up to D6+2"' in ba
        smc = con.execute("SELECT text_zh FROM abilities "
                          "WHERE id='000000485_a1'").fetchone()[0]
        assert "At the end of your opponent’s Fight phase" in smc
        assert 'more than 8"' in smc
        sh = con.execute("SELECT text_zh FROM abilities "
                         "WHERE id='000000468_a1'").fetchone()[0]
        assert 'within 8"' in sh and "Once per turn" not in sh
        mp = con.execute("SELECT text_zh FROM abilities "
                         "WHERE id='000000461_a2'").fetchone()[0]
        assert "Once per turn" in mp and "Balance Dataslate" not in mp
        for aid in ("000002693_a1", "000003888_a1"):
            pl = con.execute("SELECT text_zh FROM abilities WHERE id=?",
                             (aid,)).fetchone()[0]
            assert "-1 CP" in pl and "for 0CP" not in pl, aid
        # 两条 9"→8" 定点补丁：同句里的投放半径（18" / 48"）FP 未改，不许连坐
        for aid, radius in (("000000498_a1", '18"'), ("000000491_a1", '48"')):
            txt = con.execute("SELECT text_zh FROM abilities WHERE id=?",
                              (aid,)).fetchone()[0]
            assert 'more than 8"' in txt and '9"' not in txt, aid
            assert radius in txt, aid
        con.close()

    def test_reprinted_content_left_untouched(self):
        # Subterranean Assault（FP p5-p6）整分队 1 规则 + 4 增强 + 6 战略与库现文逐字
        # 一致（Wahapedia 已滚入）→ 免补。用 FP 正文里的判据短语锁死，而不是只量长度
        import json
        from pathlib import Path as _P
        con = self._db()
        sa = con.execute("SELECT rule_text FROM detachments "
                         "WHERE id='000010146'").fetchone()[0]
        for needle in ("Tunnel Marker", "re-roll a Hit roll of 1",
                       "BURROWER", "Designer’s Note"):
            assert needle in sa, needle
        patched = {p["id"] for p in json.loads(
            _P("db_compile/fp_rules_patches.json").read_text(encoding="utf-8")
        )["text_patches"]}
        untouched = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='TYR' "
            "AND detachment='Subterranean Assault'")}
        untouched |= {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='TYR' "
            "AND detachment_name='Subterranean Assault'")}
        untouched.add("000010146")
        con.close()
        assert not (untouched & patched)

    def test_army_rules_need_no_patch(self):
        # 军规两条的 RULES UPDATES change-to 与库现文逐字一致（Wahapedia 已滚入）→ 免补
        import json
        from pathlib import Path as _P
        con = self._db()
        syn = con.execute("SELECT text_zh FROM abilities "
                          "WHERE id='000000705'").fetchone()[0]
        assert "take that test on 3D6 instead of 2D6" in syn
        assert "add 1 to the Strength characteristic of that attack" in syn
        sitw = con.execute("SELECT text_zh FROM abilities "
                           "WHERE id='000000707'").fetchone()[0]
        assert "unleash the Shadow in the Warp" in sitw
        con.close()
        patched = {p["id"] for p in json.loads(
            _P("db_compile/fp_rules_patches.json").read_text(encoding="utf-8")
        )["text_patches"]}
        assert not (ARMY_RULE_IDS & patched)

    def test_fingerprints_match_db(self, entries):
        from db_compile.dsl_apply import _fingerprint
        con = self._db()
        for e in entries:
            if not e.effects:
                continue
            if e.table == "abilities":
                rid = e.row_id[3:] if e.row_id.startswith("det") else e.row_id
                col, tbl = ("rule_text", "detachments") if e.row_id.startswith("det") \
                    else ("text_zh", "abilities")
                src = con.execute(f"SELECT {col} FROM {tbl} WHERE id=?",
                                  (rid,)).fetchone()
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
        "det000009723",         # 半瞥之影（原文限远程攻击）
        "000008422006",         # 群体导引齐射（WHEN=我方射击阶段）
        "000009700004",         # 群体猎手（WHEN=我方射击阶段）
        "000009700005",         # 冲锋虫潮（WHEN=对手射击阶段）
        "000009738006",         # 寄生载荷（WHEN=我方射击阶段）
        "000008408003",         # 自然化伪装（原文限远程攻击）
        "000008417003",         # 变色龙（原文限远程攻击）
    )
    MELEE_ONLY = (
        "000008349003",         # 肾上腺激涌（WHEN=近战阶段）
        "000008413006",         # 确保生物质（WHEN=近战阶段）
        "000008422003",         # 暴走巨兽（WHEN=近战阶段）
        "000008422004",         # 野性咆哮（WHEN=近战阶段）
        "000009682002",         # 生物酸激涌（WHEN=近战阶段）
        "000009691002",         # 灵巧杀手（WHEN=近战阶段）
        "000009725002",         # 超肾上腺反射（WHEN=近战阶段）
        "fp11e-tyranids-norn-s2",     # 低等猎物（WHEN=近战阶段被选定作战）
        "000008412005",         # 寄生生物形态（原文限近战武器）
        "000009737003",         # 视觉适应（11 版重印后限近战攻击）
        "000009737005",         # 至高伟力（原文限近战攻击）
        "000010147005",         # 三角兽首领（原文限近战武器）
    )
    # WHEN 明确写「（对手/我方）射击阶段**或**近战阶段」，或原文根本未限相位，
    # 或持续期跨两相位 —— 加相位门反而是欠建模（PR13 反方向 MEDIUM 的同型判据）
    NO_PHASE_GATE = (
        "det000009736",         # 战兽领主（原文未限相位）
        "000008349002",         # 快速再生（对手射击阶段或近战阶段）
        "000008409004",         # 蜂拥成群（对手射击阶段或近战阶段）
        "000008409005",         # 涌动群兽（我方射击阶段或近战阶段）
        "000008413002",         # 育种守卫本能（原文未限相位）
        "000008413005",         # 剥离甲壳（对手射击阶段或近战阶段）
        "000008418002",         # 突袭强攻（我方射击阶段或近战阶段）
        "000008556005",         # 强化虫巢节点（对手射击阶段或近战阶段）
        "000008348005",         # 适应性生理（原文未限相位）
        "000008417004",         # 潜行者（原文未限相位）
        "000008421004",         # 突触控制（原文未限相位）
        "000009681003",         # 强化甲壳（原文未限相位）
        "fp11e-tyranids-norn-e2",     # 突触预知（原文未限相位）
    )

    def test_shooting_only_entries_gated(self, entries):
        for rid in self.SHOOTING_ONLY:
            e = _entry(entries, rid)
            assert e.effects, rid
            for f in e.effects:
                assert tuple(f.condition) == ("phase_shooting",), (rid, f.condition)

    def test_melee_only_entries_gated(self, entries):
        # 严格相等（PR31 自审 MEDIUM-4）：放宽成「三选一」会让日后误把某条改成
        # melee_target_has_keyword（＝凭空多出目标关键词限制）时静默通过
        for rid in self.MELEE_ONLY:
            e = _entry(entries, rid)
            assert e.effects, rid
            for f in e.effects:
                assert tuple(f.condition) == ("phase_melee",), (rid, f.condition)

    def test_two_phase_entries_are_not_over_gated(self, entries):
        # 反方向核对：WHEN 覆盖两相位/未限相位的条目不许挂 phase_* 门（过度加门＝欠建模）
        for rid in self.NO_PHASE_GATE:
            for f in _entry(entries, rid).effects:
                assert tuple(f.condition) == (), (rid, f.condition)

    def test_enfilading_emergence_spans_both_phases(self, entries):
        # 侧射突现 WHEN=移动阶段结束、持续到「我方下一个近战阶段结束」——
        # 顺 WHEN 往后推，本回合射击阶段与近战阶段都在持续期内，故不加相位门
        e = _entry(entries, "000010148004")
        assert e.status == "encoded" and len(e.effects) == 2
        for f in e.effects:
            assert tuple(f.condition) == (), f.condition

    def test_monstrous_nemesis_uses_composite_melee_keyword_tag(self, entries):
        # 「近战 × 目标关键词」必须用自含近战门的 melee_target_has_keyword——
        # 裸 target_has_keyword 会在射击阶段误放行（PR10/11/12/14 同型 HIGH 的关键词版）
        e = _entry(entries, "000008404005")
        assert {tuple(f.condition) for f in e.effects} == {
            ("melee_target_has_keyword", "monster"),
            ("melee_target_has_keyword", "vehicle")}

    def test_no_bare_target_has_keyword_anywhere(self, entries):
        # 本阵营没有「通相位/射击 × 目标关键词」的可编条目：无相位门的裸关键词 tag
        # 一旦出现，就是把只对近战/只对射击生效的条款放行到了另一相位
        for e in entries:
            for f in e.effects:
                assert f.condition[:1] != ("target_has_keyword",), e.row_id

    def test_no_bare_charging_tag_anywhere(self, entries):
        for e in entries:
            for f in e.effects:
                assert tuple(f.condition) != ("charging",), e.row_id

    def test_counterpredation_sole_gate_is_not_modeled(self, entries):
        """整条效果的**唯一开关**无载体时判 not_modeled（PR31 自审 MEDIUM-1）。

        反捕猎的 +1S/+1AP 只对「瞄准 hidden 状态敌军单位」的攻击生效——这不是
        「若…则更好」的增量分支（那类降 partial 即可），而是整条效果的唯一开关；
        且 WHEN 是「近战阶段本单位被选定作战」，能被选定作战即已在接战范围内，
        11 版侦测规则下目标几乎不可能仍 hidden。按恒满足编码＝近乎全程虚增一档 S
        与一档 AP，与本载荷对扰动捕食的判据同型，故整条不编。
        """
        e = _entry(entries, "fp11e-tyranids-ambush-s1")
        assert e.status == "not_modeled" and not e.effects
        assert any("唯一开关" in n for n in e.not_modeled_notes_zh)
        assert any("hidden" in n for n in e.not_modeled_notes_zh)

    def test_alien_physiology_uses_delayed_s_gt_t_tag(self, entries):
        # wound_s_gt_t 把 S/T 比较延迟到引擎最终 S 处判定，且不自含相位门——
        # 正合 WHEN 覆盖两相位的 ALIEN PHYSIOLOGY
        e = _entry(entries, "fp11e-tyranids-wbo-s1")
        assert e.side == "target" and e.status == "encoded"
        assert [tuple(f.condition) for f in e.effects] == [("wound_s_gt_t",)]


# ══ 行为断言：可编条目真的改变结果 ════════════════════════════════════════════
def _atk_with(entries, rid, weapons, toggles=frozenset({"bearer_leading"})):
    atk, modeled, _ = inject_attacker(_attacker(*weapons), [_entry(entries, rid)],
                                      frozenset(toggles))
    assert modeled, rid
    return atk


def _tgt_with(entries, rid, target, toggles=frozenset({"defender_bearer_leading"})):
    tgt, modeled, _ = inject_target(target, [_entry(entries, rid)], frozenset(toggles))
    assert modeled, rid
    return tgt


class TestDefensiveBehaviour:
    def test_teeming_masses_hit_minus_one_in_both_phases(self, entries):
        base = _target()
        buffed = _tgt_with(entries, "000008409004", base)
        for phase, weapon in (("shooting", _gun()), ("melee", _melee())):
            st = Stance(phase=phase)
            plain = _run(_attacker(weapon), base, st)
            worse = _run(_attacker(weapon), buffed, st)
            # BS/WS 4+ → 3/6；命中 -1 后 2/6
            assert _ratio(worse.damage, plain.damage) == pytest.approx(2 / 3, abs=0.05)

    def test_onrushing_horde_hit_minus_one_shooting_only(self, entries):
        base = _target()
        buffed = _tgt_with(entries, "000009700005", base)
        shoot = Stance(phase="shooting")
        assert _ratio(_run(_attacker(_gun()), buffed, shoot).damage,
                      _run(_attacker(_gun()), base, shoot).damage) \
            == pytest.approx(2 / 3, abs=0.05)
        fight = Stance(phase="melee")
        assert _run(_attacker(_melee()), buffed, fight).damage.mean() == pytest.approx(
            _run(_attacker(_melee()), base, fight).damage.mean(), rel=0.02)

    def test_lithe_killers_invuln_melee_only(self, entries):
        base = _target(sv=6)
        buffed = _tgt_with(entries, "000009691002", base)
        fight = Stance(phase="melee")
        assert _run(_attacker(_melee(ap=-3)), buffed, fight).damage.mean() < \
            _run(_attacker(_melee(ap=-3)), base, fight).damage.mean()
        shoot = Stance(phase="shooting")
        assert _run(_attacker(_gun(ap=-3)), buffed, shoot).damage.mean() == \
            pytest.approx(_run(_attacker(_gun(ap=-3)), base, shoot).damage.mean(),
                          rel=0.02)

    def test_synaptoprescience_invuln_both_phases(self, entries):
        base = _target(sv=6)
        buffed = _tgt_with(entries, "fp11e-tyranids-norn-e2", base)
        for phase, weapon in (("shooting", _gun(ap=-3)), ("melee", _melee(ap=-3))):
            st = Stance(phase=phase)
            assert _run(_attacker(weapon), buffed, st).damage.mean() < \
                _run(_attacker(weapon), base, st).damage.mean()

    def test_leader_beasts_invuln_both_phases(self, entries):
        base = _target(sv=6)
        buffed = _tgt_with(entries, "det000009736", base, toggles=frozenset())
        for phase, weapon in (("shooting", _gun(ap=-3)), ("melee", _melee(ap=-3))):
            st = Stance(phase=phase)
            assert _run(_attacker(weapon), buffed, st).damage.mean() < \
                _run(_attacker(weapon), base, st).damage.mean()

    def test_reinforced_hive_node_worsens_ap(self, entries):
        base = _target(sv=4)
        buffed = _tgt_with(entries, "000008556005", base, toggles=frozenset())
        for phase, weapon in (("shooting", _gun(ap=-1)), ("melee", _melee(ap=-1))):
            st = Stance(phase=phase)
            assert _run(_attacker(weapon), buffed, st).damage.mean() < \
                _run(_attacker(weapon), base, st).damage.mean()

    def test_rapid_regeneration_fnp_six(self, entries):
        base = _target(sv=4)
        buffed = _tgt_with(entries, "000008349002", base, toggles=frozenset())
        st = Stance(phase="shooting")
        # FNP 6+ → 伤害保留 5/6
        assert _ratio(_run(_attacker(_gun()), buffed, st).damage,
                      _run(_attacker(_gun()), base, st).damage) \
            == pytest.approx(5 / 6, abs=0.05)

    def test_synaptic_control_damage_reduction(self, entries):
        base = _target(t=4, sv=3, w=3, models=3)
        buffed = _tgt_with(entries, "000008421004", base)
        st = Stance(phase="shooting")
        assert _ratio(_run(_attacker(_gun(d=2, ap=-2)), buffed, st).damage,
                      _run(_attacker(_gun(d=2, ap=-2)), base, st).damage) \
            == pytest.approx(0.5, abs=0.05)

    def test_chameleonic_grants_cover_shooting_only(self, entries):
        base = _target(sv=4)
        buffed = _tgt_with(entries, "000008417003", base)
        shoot = Stance(phase="shooting")
        assert _run(_attacker(_gun()), buffed, shoot).damage.mean() < \
            _run(_attacker(_gun()), base, shoot).damage.mean()
        fight = Stance(phase="melee")
        assert _run(_attacker(_melee()), buffed, fight).damage.mean() == pytest.approx(
            _run(_attacker(_melee()), base, fight).damage.mean(), rel=0.02)

    def test_alien_physiology_only_when_s_gt_t(self, entries):
        base = _target(t=4)
        buffed = _tgt_with(entries, "fp11e-tyranids-wbo-s1", base, toggles=frozenset())
        for phase, mk in (("shooting", _gun), ("melee", _melee)):
            st = Stance(phase=phase)
            # S6 > T4 → 致伤 -1 生效
            assert _run(_attacker(mk(s=6)), buffed, st).damage.mean() < \
                _run(_attacker(mk(s=6)), base, st).damage.mean(), phase
            # S4 == T4 → 不生效
            assert _run(_attacker(mk(s=4)), buffed, st).damage.mean() == pytest.approx(
                _run(_attacker(mk(s=4)), base, st).damage.mean(), rel=0.02), phase

    def test_bearer_entries_require_toggle(self, entries):
        base = _target()
        e = [_entry(entries, "000008348005")]        # 适应性生理
        blocked, modeled, notes = inject_target(base, e, frozenset())
        assert not modeled and blocked is base
        assert any("defender_bearer_leading" in n for n in notes)
        ok, modeled, _ = inject_target(base, e, frozenset({"defender_bearer_leading"}))
        assert modeled and ok.effects


class TestOffensiveBehaviour:
    def test_rampaging_monstrosities_reroll_melee_only(self, entries):
        m = _melee()
        atk = _atk_with(entries, "000008422003", [m])
        fight = Stance(phase="melee")
        assert _run(atk, _target(), fight).damage.mean() > \
            _run(_attacker(m), _target(), fight).damage.mean()
        g = _gun()
        atk_g = _atk_with(entries, "000008422003", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk_g, _target(), shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), _target(), shoot).damage.mean(), rel=0.02)

    def test_bio_acid_surge_sustained_hits_melee_only(self, entries):
        m = _melee()
        atk = _atk_with(entries, "000009682002", [m])
        fight = Stance(phase="melee")
        assert _run(atk, _target(), fight).damage.mean() > \
            _run(_attacker(m), _target(), fight).damage.mean()
        g = _gun()
        atk_g = _atk_with(entries, "000009682002", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk_g, _target(), shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), _target(), shoot).damage.mean(), rel=0.02)

    def test_swarm_guided_salvoes_ignores_cover_and_hit_mods(self, entries):
        g = _gun()
        atk = _atk_with(entries, "000008422006", [g])
        st = Stance(phase="shooting", target_in_cover=True)
        assert _run(atk, _target(sv=4), st).damage.mean() > \
            _run(_attacker(g), _target(sv=4), st).damage.mean()
        # 忽略命中修正：守方 -1 命中（冲锋虫潮）被抵消
        smoked = _target(effects=_entry(entries, "000009700005").effects)
        assert _run(atk, smoked, Stance(phase="shooting")).damage.mean() == \
            pytest.approx(_run(_attacker(g), _target(), Stance(phase="shooting"))
                          .damage.mean(), rel=0.03)
        # 负向：近战阶段不放行（掉 phase_shooting 门会让近战也无视掩体）
        m = _melee()
        atk_m = _atk_with(entries, "000008422006", [m])
        fight = Stance(phase="melee", target_in_cover=True)
        assert _run(atk_m, _target(sv=4), fight).damage.mean() == pytest.approx(
            _run(_attacker(m), _target(sv=4), fight).damage.mean(), rel=0.02)

    def test_parasitic_payload_ignores_cover_shooting_only(self, entries):
        g = _gun()
        atk = _atk_with(entries, "000009738006", [g])
        st = Stance(phase="shooting", target_in_cover=True)
        assert _run(atk, _target(sv=4), st).damage.mean() > \
            _run(_attacker(g), _target(sv=4), st).damage.mean()
        m = _melee()
        atk_m = _atk_with(entries, "000009738006", [m])
        fight = Stance(phase="melee", target_in_cover=True)
        assert _run(atk_m, _target(sv=4), fight).damage.mean() == pytest.approx(
            _run(_attacker(m), _target(sv=4), fight).damage.mean(), rel=0.02)

    def test_enfilading_emergence_helps_in_both_phases(self, entries):
        for phase, mk in (("shooting", _gun), ("melee", _melee)):
            w = mk()
            atk = _atk_with(entries, "000010148004", [w])
            st = Stance(phase=phase, target_in_cover=True)
            assert _run(atk, _target(sv=4), st).damage.mean() > \
                _run(_attacker(w), _target(sv=4), st).damage.mean(), phase

    def test_lesser_prey_s_plus_two_melee_only(self, entries):
        tgt = _target(t=6)
        m = _melee(s=4)
        atk = _atk_with(entries, "fp11e-tyranids-norn-s2", [m])
        fight = Stance(phase="melee")
        # S4 vs T6 致伤 5+ → S6 vs T6 致伤 4+
        assert _ratio(_run(atk, tgt, fight).damage,
                      _run(_attacker(m), tgt, fight).damage) \
            == pytest.approx(1.5, abs=0.12)
        g = _gun(s=4)
        atk_g = _atk_with(entries, "fp11e-tyranids-norn-s2", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk_g, tgt, shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), tgt, shoot).damage.mean(), rel=0.02)

    def test_ocular_adaptation_hit_plus_one_melee_only(self, entries):
        m = _melee(ws=4)
        atk = _atk_with(entries, "000009737003", [m])
        fight = Stance(phase="melee")
        # WS4+ 3/6 → 命中 +1 后 4/6
        assert _ratio(_run(atk, _target(), fight).damage,
                      _run(_attacker(m), _target(), fight).damage) \
            == pytest.approx(4 / 3, abs=0.06)
        g = _gun(bs=4)
        atk_g = _atk_with(entries, "000009737003", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk_g, _target(), shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), _target(), shoot).damage.mean(), rel=0.02)

    def test_elevated_might_reroll_wounds_and_ap(self, entries):
        m = _melee(s=4)
        tgt = _target(t=5, sv=4)
        atk = _atk_with(entries, "000009737005", [m])
        fight = Stance(phase="melee")
        assert _run(atk, tgt, fight).damage.mean() > \
            1.4 * _run(_attacker(m), tgt, fight).damage.mean()
        g = _gun(s=4)
        atk_g = _atk_with(entries, "000009737005", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk_g, tgt, shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), tgt, shoot).damage.mean(), rel=0.02)

    def test_trygon_prime_s_and_ws(self, entries):
        m = _melee(ws=4, s=4)
        tgt = _target(t=5)
        atk = _atk_with(entries, "000010147005", [m])
        fight = Stance(phase="melee")
        # WS 改善 1（3/6→4/6）× S4→S5 对 T5（致伤 5+→4+）
        assert _ratio(_run(atk, tgt, fight).damage,
                      _run(_attacker(m), tgt, fight).damage) \
            == pytest.approx(4 / 3 * 1.5, abs=0.15)
        g = _gun(bs=4, s=4)
        atk_g = _atk_with(entries, "000010147005", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk_g, tgt, shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), tgt, shoot).damage.mean(), rel=0.02)

    def test_monstrous_nemesis_only_vs_monster_or_vehicle_in_melee(self, entries):
        m = _melee(s=4)
        atk = _atk_with(entries, "000008404005", [m])
        fight = Stance(phase="melee")
        for kw in ("monster", "vehicle"):
            tgt = _target(t=6, keywords=frozenset({kw}))
            assert _run(atk, tgt, fight).damage.mean() > \
                _run(_attacker(m), tgt, fight).damage.mean(), kw
        plain = _target(t=6)
        assert _run(atk, plain, fight).damage.mean() == pytest.approx(
            _run(_attacker(m), plain, fight).damage.mean(), rel=0.02)
        # 射击阶段即使目标是 MONSTER 也不放行（复合 tag 自含近战门）
        g = _gun(s=4)
        atk_g = _atk_with(entries, "000008404005", [g])
        mon = _target(t=6, keywords=frozenset({"monster"}))
        shoot = Stance(phase="shooting")
        assert _run(atk_g, mon, shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), mon, shoot).damage.mean(), rel=0.02)

    def test_secure_biomass_lethal_hits_melee_only(self, entries):
        m = _melee(s=3)
        tgt = _target(t=7)
        atk = _atk_with(entries, "000008413006", [m])
        fight = Stance(phase="melee")
        assert _run(atk, tgt, fight).damage.mean() > \
            _run(_attacker(m), tgt, fight).damage.mean()
        # 负向：[LETHAL HITS] 不许泄漏到射击阶段
        g = _gun(s=3)
        atk_g = _atk_with(entries, "000008413006", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk_g, tgt, shoot).damage.mean() == pytest.approx(
            _run(_attacker(g), tgt, shoot).damage.mean(), rel=0.02)

    def test_adrenal_surge_crit_threshold_needs_crit_keyed_weapon(self, entries):
        # 暴击阈值 5+ 只有在武器带暴击驱动能力时才改变结果——本测试用带 [LETHAL HITS]
        # 的武器（借确保生物质的 effects）验证它真的被引擎消费
        lethal = _entry(entries, "000008413006").effects
        m = _melee(s=3, effects=lethal)
        tgt = _target(t=7)
        atk = _atk_with(entries, "000008349003", [m])
        fight = Stance(phase="melee")
        assert _run(atk, tgt, fight).damage.mean() > \
            _run(_attacker(m), tgt, fight).damage.mean()
        # 负向：射击阶段两条（[LETHAL HITS] 与暴击阈值）都不放行
        g = _gun(s=3, effects=lethal)
        atk_g = _atk_with(entries, "000008349003", [g])
        shoot = Stance(phase="shooting")
        assert _run(atk_g, tgt, shoot).damage.mean() == pytest.approx(
            _run(_attacker(_gun(s=3)), tgt, shoot).damage.mean(), rel=0.02)

    def test_attacker_enhancement_requires_bearer_toggle(self, entries):
        # 攻方侧与守方侧同标准：不开 bearer_leading 一律拒注入并显式披露，
        # 不许零提示直通（PR31 自审 MEDIUM-2）
        e = [_entry(entries, "000009737003")]        # 视觉适应
        blocked, modeled, notes = inject_attacker(
            _attacker(_melee()), e, frozenset())
        assert not modeled
        assert blocked.loadout[0].effects == ()
        assert any("bearer_leading" in n for n in notes)

    def test_stalker_hit_and_wound_both_phases(self, entries):
        tgt = _target(t=5)
        for phase, mk in (("shooting", _gun), ("melee", _melee)):
            w = mk(s=4)
            atk = _atk_with(entries, "000008417004", [w])
            st = Stance(phase=phase)
            assert _run(atk, tgt, st).damage.mean() > \
                1.5 * _run(_attacker(w), tgt, st).damage.mean(), phase


# ══ 诚实语义：not_modeled 条目在报告里露面但不改数值 ═════════════════════════
class TestHonestyDisclosure:
    def test_not_modeled_entries_surface_in_notes(self, entries):
        g = _gun()
        e = [_entry(entries, "000000705")]        # 军规突触
        atk, modeled, notes = inject_attacker(_attacker(g), e, frozenset())
        assert not modeled and notes
        assert atk.loadout[0].effects == ()

    def test_defensive_entry_on_attacker_path_is_direction_disclosed(self, entries):
        g = _gun()
        e = [_entry(entries, "000008409004")]     # 蜂拥成群（守方向）
        atk, modeled, notes = inject_attacker(_attacker(g), e, frozenset())
        assert not modeled
        assert any("防守向" in n for n in notes)
        assert atk.loadout[0].effects == ()

    def test_partial_residue_notes_are_passed_through(self, entries):
        g = _gun()
        atk, modeled, notes = inject_attacker(
            _attacker(g), [_entry(entries, "000008418002")], frozenset())
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
        toggles = frozenset({"bearer_leading", "defender_bearer_leading"})
        atk, _, _ = inject_attacker(_attacker(_gun(), _melee()), atk_entries, toggles)
        assert unconsumed_attacker_effect_notes(atk) == []
        tgt, _, _ = inject_target(_target(), tgt_entries, toggles)
        assert unconsumed_target_effect_notes(tgt) == []
