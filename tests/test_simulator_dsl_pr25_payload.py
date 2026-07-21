# tests/test_simulator_dsl_pr25_payload.py
"""P7-PR25 基因窃取者教派（Genestealer Cults，faction='GC'）全量 DSL 编码落账：
13 个分队规则 + 军规 Cult Ambush + 57 战略 + 36 增强 = 107
（8 encoded / 18 partial / 81 not_modeled）——零新引擎通道、零新态势开关、零新
condition tag。

教派气质＝伏击/增援/标记/复苏点/移动，可编率低（26/107 带效果）。最大的三个未建模
桶：① 「本回合作为增援登场」状态（Cult Ambush 军规辐射出的 A Perfect Ambush /
A Chink in Their Armour 等）无引擎开关载体；② 「只重骰 1 点」（Killer Reputation /
HYPERFEROCITY / VENGEANCE FOR THE MARTYR! 等）——引擎重骰通道语义是重骰失败骰；
③ 领导力测验的随机条件分支（Blessed Visages / BIO-HORROR REVELATION / GROWING DREAD）。

DB 对齐：17 fp_rules text_patches + 18 fp_new inserts（Heroes of the Uprising /
Purestrain Broodswarm / Xenocult Masses 三真新分队，Wahapedia 只滚入了 Final Day）；
fp_errata 零补丁。第 17 条 text_patch（DIVINE IMPERATIVE 整条重写）与「4 条爆破弹
Range 8"→6" 补丁回滚」都是迭代 2 回原 PDF 复核推翻迭代 1 判定的结果——FP 第 8 页
原文是「Change the Range characteristic ... to '8"'」，库现值即 8"，属免补。
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
PAYLOAD = Path("dsl_payloads/genestealercults.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 12 个分队容器名（stratagems.detachment / enhancements.detachment_name）
GC_DETACHMENTS = (
    "Biosanctic Broodsurge", "Brood Brother Auxilia", "Cult Unveiled",
    "Final Day", "Genespawn Onslaught", "Heroes of the Uprising",
    "Host of Ascension", "Infestation Swarm", "Outlander Claw",
    "Purestrain Broodswarm", "Xenocreed Congregation", "Xenocult Masses",
)
# 13 条分队规则物化条目 id（det + detachments 源行 id）——Brood Brother Auxilia
# 有两条规则行（Integrated Tactics 000009082 + BROOD BROTHERS 000009083）
GC_RULE_IDS = (
    "det000009066", "det000009070", "det000009074", "det000009078",
    "det000009082", "det000009083", "det000009459", "det000009467",
    "det000009475", "det000009826",
    "detfp11e-genestealercults-heroesuprising",
    "detfp11e-genestealercults-purestrainbroodswarm",
    "detfp11e-genestealercults-xenocultmasses",
)
ARMY_RULE_ID = "000008501"          # Cult Ambush（abilities 真实行，非物化）


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="claw"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="autogun", rng='24"'):
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


# ═══ 结构与 DB 对账 ═══════════════════════════════════════════════════════
class TestPayloadShape:
    def test_counts(self, entries):
        assert len(entries) == 107
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 8, "partial": 18, "not_modeled": 81}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        assert by == {"abilities": 14, "stratagems": 57, "enhancements": 36}

    def test_faction_is_gc(self, entries):
        assert all(e.faction == "GC" for e in entries)

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id

    def test_encoded_entries_have_effects_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "encoded":
                assert e.effects and e.provenance.get("text_sha256"), e.row_id

    def test_not_modeled_have_reason(self, entries):
        for e in entries:
            if e.status == "not_modeled":
                assert not e.effects and e.not_modeled_notes_zh, e.row_id

    def test_rules_materialize_from_detachments(self, entries):
        for rid in GC_RULE_IDS:
            e = _entry(entries, rid)
            assert e.table == "abilities"
            assert e.provenance.get("text_sha256"), rid

    def test_army_rule_is_plain_ability_row(self, entries):
        # 军规 Cult Ambush 是 abilities 真实行（owner_id 为空），不走 materialize
        e = _entry(entries, ARMY_RULE_ID)
        assert e.table == "abilities" and e.detachment is None
        assert e.status == "not_modeled"

    def test_all_effects_are_within_known_channels(self, entries):
        # 零新引擎通道护栏：每条 effect 的 (phase, op) 必落在既有消费点白名单
        from engines.simulator.sequence import ATTACKER_CONSUMED, TARGET_CONSUMED
        for e in entries:
            consumed = ATTACKER_CONSUMED if e.side == "attacker" else TARGET_CONSUMED
            for eff in e.effects:
                assert (eff.phase, eff.op) in consumed, (e.row_id, eff.phase, eff.op)

    def test_detachment_labels_are_known_containers(self, entries):
        for e in entries:
            if e.table in ("stratagems", "enhancements"):
                assert e.detachment in GC_DETACHMENTS, (e.row_id, e.detachment)


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='GC' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='GC' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        active = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='GC'")}
        con.close()
        covered = {e.row_id for e in entries
                   if e.table == "abilities" and e.row_id.startswith("det")}
        assert covered == active == set(GC_RULE_IDS)

    def test_fingerprints_match_db(self, entries):
        from db_compile.dsl_apply import _fingerprint
        con = self._db()
        for e in entries:
            if not e.effects:
                continue
            if e.table == "abilities":
                if e.row_id.startswith("det"):
                    src = con.execute(
                        "SELECT rule_text FROM detachments WHERE id=?",
                        (e.row_id[3:],)).fetchone()
                else:
                    src = con.execute("SELECT text_zh FROM abilities WHERE id=?",
                                      (e.row_id,)).fetchone()
            elif e.table == "stratagems":
                src = con.execute("SELECT text_zh FROM stratagems WHERE id=?",
                                  (e.row_id,)).fetchone()
            else:
                src = con.execute("SELECT description FROM enhancements WHERE id=?",
                                  (e.row_id,)).fetchone()
            assert src is not None, e.row_id
            assert _fingerprint(src[0]) == e.provenance["text_sha256"], e.row_id
        con.close()


# ═══ 守方向 payload 引擎级差分 ═════════════════════════════════════════════
class TestDefensiveFromPayload:
    def test_hyperadrenal_reflexes_invuln_melee_gate(self, entries):
        # 超肾上腺反射（Infestation Swarm 战略，encoded）：战斗阶段 4+ 无效保护
        # （WHEN=Fight phase → phase_melee 门；射击阶段不注入）
        hr = _entry(entries, "000009477002")
        tgt, _, _ = inject_target(_target(sv=7), [hr], frozenset())
        r = _run(_attacker(_melee(ap=-6)), tgt, Stance(phase="melee"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.03)
        # 射击阶段门不成立 → 无效保护不生效，Sv7 AP-6 全破
        tgt_s, _, _ = inject_target(_target(sv=7), [hr], frozenset())
        rs = _run(_attacker(_gun(ap=-6)), tgt_s, Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1.0, abs=0.02)

    def test_deft_manoeuvring_invuln_shooting_gate(self, entries):
        # 灵巧机动（Outlander Claw 战略，encoded）：对手射击阶段 4+ 无效保护
        dm = _entry(entries, "000009080006")
        tgt, _, _ = inject_target(_target(sv=7), [dm], frozenset())
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.03)
        tgt_m, _, _ = inject_target(_target(sv=7), [dm], frozenset())
        rm = _run(_attacker(_melee(ap=-6)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1.0, abs=0.02)

    def test_devoted_crew_damage_reduction_both_phases(self, entries):
        # 忠诚车组（Outlander Claw 战略，encoded）：被攻伤害 -1（WHEN 双阶段→无阶段门）
        dc = _entry(entries, "000009080003")
        base = _run(_attacker(_gun(d=2)), _target(sv=7, w=3),
                    Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=7, w=3), [dc], frozenset())
        r = _run(_attacker(_gun(d=2)), tgt, Stance(phase="shooting"))
        assert _ratio(base.damage, base.unsaved) == pytest.approx(2.0, abs=0.05)
        assert _ratio(r.damage, r.unsaved) == pytest.approx(1.0, abs=0.05)
        # 近战阶段同样注入（无阶段门）
        tgt_m, _, _ = inject_target(_target(sv=7, w=3), [dc], frozenset())
        rm = _run(_attacker(_melee(d=2)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.damage, rm.unsaved) == pytest.approx(1.0, abs=0.05)

    def test_slunk_from_underbelly_ap_worsen_shooting_gate(self, entries):
        # 自暗腹潜出（Xenocult Masses 战略，encoded）：来袭远程攻击 AP 恶化 1
        sl = _entry(entries, "fp11e-genestealercults-xenocultmasses-s3")
        base = _run(_attacker(_gun(ap=-1)), _target(sv=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=4), [sl], frozenset())
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        # AP-1 打 Sv4（5+，2/3 失败）→ AP0（4+，1/2 失败）
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 近战阶段不注入（phase_shooting 门）
        tgt_m, _, _ = inject_target(_target(sv=4), [sl], frozenset())
        rm = _run(_attacker(_melee(ap=-1)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_half_glimpsed_shadows_hit_debuff_shooting_gate(self, entries):
        # 半瞥之影（Infestation Swarm 分队规则，partial）：来袭远程命中 -1
        hg = _entry(entries, "det000009475")
        tgt, _, _ = inject_target(_target(), [hg], frozenset())
        r = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        # 近战阶段不注入（phase_shooting 门）
        tgt_m, _, _ = inject_target(_target(), [hg], frozenset())
        rm = _run(_attacker(_melee(ws=4)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_lurking_menace_hit_debuff_shooting_gate(self, entries):
        # 潜伏威胁（Cult Unveiled 战略，partial）：对手射击阶段来袭命中 -1
        lm = _entry(entries, "000009461005")
        tgt, _, _ = inject_target(_target(), [lm], frozenset())
        r = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        tgt_m, _, _ = inject_target(_target(), [lm], frozenset())
        rm = _run(_attacker(_melee(ws=4)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_unquestioning_fanaticism_fnp_needs_defender_toggle(self, entries):
        # 不容置疑的狂信（Xenocreed 分队规则，partial）：FNP 3+ 只给该 CHARACTER
        # 模型——须开 defender_bearer_leading，未开则拒注入并披露
        uf = _entry(entries, "det000009070")
        _, modeled_off, notes_off = inject_target(_target(), [uf], frozenset())
        assert not modeled_off and any("未启用" in n for n in notes_off)
        base = _run(_attacker(_gun()), _target(sv=7, w=3), Stance(phase="shooting"))
        tgt, modeled_on, _ = inject_target(
            _target(sv=7, w=3), [uf], frozenset({"defender_bearer_leading"}))
        assert modeled_on
        r = _run(_attacker(_gun()), tgt, Stance(phase="shooting"))
        # FNP 3+ → 每点伤害 2/3 被忽略
        assert _ratio(base.damage, base.unsaved) == pytest.approx(1.0, abs=0.03)
        assert _ratio(r.damage, r.unsaved) == pytest.approx(1 / 3, abs=0.03)

    def test_miasmic_fumes_hit_and_wound_debuff(self, entries):
        # 瘴气毒雾（Genespawn Onslaught 增强，partial）：瞄准携带者的攻击命中 -1、致伤 -1
        mf = _entry(entries, "000009468003")
        _, _, notes_off = inject_target(_target(), [mf], frozenset())
        assert any("未启用" in n for n in notes_off)
        tgt, _, _ = inject_target(_target(t=4), [mf],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_gun(bs=4, s=4)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        # S4 vs T4 → 4+（1/2）；致伤 -1 → 5+（1/3）
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_starfall_shells_hit_debuff_both_phases(self, entries):
        # 星陨弹（Outlander Claw 增强，partial）：被标记的敌方单位其后所有攻击命中 -1
        # （持续至本方下个射击阶段开始 → 双阶段，无阶段门）
        ss = _entry(entries, "000009079004")
        tgt, _, _ = inject_target(_target(), [ss], frozenset())
        r = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        tgt_m, _, _ = inject_target(_target(), [ss], frozenset())
        rm = _run(_attacker(_melee(ws=4)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 3, abs=0.02)

    def test_mark_of_star_children_t_improve(self, entries):
        # 星之子印记（Purestrain Broodswarm 增强，partial）：T+1（守方特征值通道）
        mk = _entry(entries, "fp11e-genestealercults-purestrainbroodswarm-e1")
        base = _run(_attacker(_melee(s=4)), _target(t=4), Stance(phase="melee"))
        tgt, _, _ = inject_target(_target(t=4), [mk], frozenset())
        r = _run(_attacker(_melee(s=4)), tgt, Stance(phase="melee"))
        # S4 vs T4（4+，1/2）→ T5（5+，1/3）
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)


# ═══ 攻方向 payload 引擎级差分 ═════════════════════════════════════════════
class TestAttackerFromPayload:
    def test_hypermorphic_fury_attacks_melee_charging_gate(self, entries):
        # 超变狂怒（Biosanctic Broodsurge 分队规则，partial）：冲锋回合近战 A+1
        # （melee_charging 复合门：射击阶段即便冲锋过也不注入）
        hf = _entry(entries, "det000009074")
        atk, _, _ = inject_attacker(_attacker(_melee()), [hf], frozenset())
        off = _run(atk, _target(), Stance(phase="melee"))
        on = _run(atk, _target(), Stance(phase="melee", charging=True))
        assert off.attacks.mean() == pytest.approx(1.0, abs=0.02)
        assert on.attacks.mean() == pytest.approx(2.0, abs=0.03)
        atk_s, _, _ = inject_attacker(_attacker(_gun()), [hf], frozenset())
        rs = _run(atk_s, _target(), Stance(phase="shooting", charging=True))
        assert rs.attacks.mean() == pytest.approx(1.0, abs=0.02)

    def test_avenge_star_children_hit_and_wound_both_phases(self, entries):
        # 为星之子复仇（Final Day 战略，encoded）：命中 +1、致伤 +1，持续至战斗结束
        # → 反向陷阱核查：原文不含阶段限定，故**不得**加阶段门（两阶段都须生效）
        av = _entry(entries, "000009828004")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [av], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=4, s=4)), [av], frozenset())
        rm = _run(atk_m, _target(t=4), Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_coordinated_trap_wound_modify(self, entries):
        # 协同陷阱（Host of Ascension 战略，encoded）：致伤 +1（双阶段无门）
        ct = _entry(entries, "000009068002")
        base = _run(_attacker(_melee(s=4)), _target(t=4), Stance(phase="melee"))
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ct], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_primed_and_readied_lowers_crit_hit_threshold(self, entries):
        # 蓄势待发（Host of Ascension 战略，encoded）：暴击命中阈值 6+ → 5+。
        # 暴击阈值本身无独立可观测量，用近距枪战（[LETHAL HITS]）做载体对拍。
        pr = _entry(entries, "000009068003")
        crs = _entry(entries, "000009080004")
        st = Stance(phase="shooting")
        atk1, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [crs], frozenset())
        lethal_only = _run(atk1, _target(t=6), st)
        atk2, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [crs, pr],
                                     frozenset())
        both = _run(atk2, _target(t=6), st)
        # 命中 1/2 不变；致伤率：暴击 1/6 自动致伤 + 余命中 2/6 × 1/3 = 5/18
        assert _ratio(lethal_only.hits, lethal_only.attacks) == pytest.approx(
            1 / 2, abs=0.02)
        assert _ratio(lethal_only.wounds, lethal_only.attacks) == pytest.approx(
            5 / 18, abs=0.02)
        # 暴击 5+ → 2/6 自动致伤 + 余命中 1/6 × 1/3 = 7/18
        assert _ratio(both.hits, both.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(both.wounds, both.attacks) == pytest.approx(7 / 18, abs=0.02)

    def test_close_range_shootout_lethal_shooting_gate(self, entries):
        # 近距枪战（Outlander Claw 战略，partial）：远程 [LETHAL HITS]（phase_shooting 门）
        crs = _entry(entries, "000009080004")
        base = _run(_attacker(_gun(s=4)), _target(t=6), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [crs], frozenset())
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) > _ratio(base.wounds, base.hits) + 0.05
        # 近战阶段不注入（phase_shooting 门）
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [crs], frozenset())
        rm = _run(atk_m, _target(t=6), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_fanatical_hail_hit_reroll_shooting_gate(self, entries):
        # 狂信弹雨（Xenocult Masses 战略，encoded）：远程可重骰命中（重骰失败骰）
        fh = _entry(entries, "fp11e-genestealercults-xenocultmasses-s2")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [fh], frozenset())
        r = _run(atk, _target(), Stance(phase="shooting"))
        # BS4：1/2 + 1/2×1/2 = 3/4
        assert _ratio(r.hits, r.attacks) == pytest.approx(3 / 4, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=4)), [fh], frozenset())
        rm = _run(atk_m, _target(), Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_frenzied_devotion_attacks_and_ws_melee_gate(self, entries):
        # 狂热虔信（Xenocreed 战略，partial）：近战 A+1 且 WS 特征值改善 1
        fd = _entry(entries, "000009072003")
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4)), [fd], frozenset())
        r = _run(atk, _target(), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2.0, abs=0.03)
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        # 射击阶段不注入（phase_melee 门）：A 与命中均回落基线
        atk_s, _, _ = inject_attacker(_attacker(_gun(bs=4)), [fd], frozenset())
        rs = _run(atk_s, _target(), Stance(phase="shooting"))
        assert rs.attacks.mean() == pytest.approx(1.0, abs=0.02)
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_gene_twisted_muscle_keyword_or_split_melee_gate(self, entries):
        # 基因扭曲肌肉（Biosanctic Broodsurge 战略，partial）：战斗阶段对 MONSTER 或
        # VEHICLE 致伤 +1——单关键字 tag 无 OR，拆两条编；复合 tag 自带近战门
        gm = _entry(entries, "000009076004")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [gm], frozenset())
        mon = _run(atk, _target(t=4, keywords=frozenset({"monster"})),
                   Stance(phase="melee"))
        veh = _run(atk, _target(t=4, keywords=frozenset({"vehicle"})),
                   Stance(phase="melee"))
        plain = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(mon.wounds, mon.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(veh.wounds, veh.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(plain.wounds, plain.hits) == pytest.approx(1 / 2, abs=0.02)
        # 双关键字目标：±1 夹取兜住重复叠加（不会变成 +2 → 2+）
        both = _run(atk, _target(t=4, keywords=frozenset({"monster", "vehicle"})),
                    Stance(phase="melee"))
        assert _ratio(both.wounds, both.hits) == pytest.approx(2 / 3, abs=0.02)
        # 射击阶段不注入（melee_target_has_keyword 复合门）
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [gm], frozenset())
        rs = _run(atk_s, _target(t=4, keywords=frozenset({"monster"})),
                  Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_surging_broodworship_devastating_wounds(self, entries):
        # 汹涌巢崇（Heroes of the Uprising 战略，partial）：[DEVASTATING WOUNDS]
        sb = _entry(entries, "fp11e-genestealercults-heroesuprising-s2")
        base = _run(_attacker(_melee(s=4)), _target(t=4), Stance(phase="melee"))
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [sb], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert base.mortals.mean() == 0
        assert r.mortals.mean() > 0

    def test_biomorph_adaptation_needs_bearer_toggle(self, entries):
        # 生物形态适应（Biosanctic Broodsurge 增强，partial）：近战 AP+1 与 D+1，
        # 需 bearer_leading（未开→拒注入并披露）
        ba = _entry(entries, "000009075003")
        _, modeled_off, notes_off = inject_attacker(
            _attacker(_melee()), [ba], frozenset())
        assert not modeled_off and any("未启用" in n for n in notes_off)
        atk, _, _ = inject_attacker(_attacker(_melee(ap=0, d=1)), [ba],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(sv=4, w=3), Stance(phase="melee"))
        # AP0 打 Sv4（4+，1/2 失败）→ AP-1（5+，2/3 失败）；D1 → D2
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2.0, abs=0.05)
        # 射击阶段不注入（phase_melee 门）
        atk_s, _, _ = inject_attacker(_attacker(_gun(ap=0, d=1)), [ba],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(sv=4, w=3), Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(rs.damage, rs.unsaved) == pytest.approx(1.0, abs=0.05)

    def test_contraband_munitions_s_improve_shooting_gate(self, entries):
        # 违禁军火（Heroes of the Uprising 增强，partial）：远程 S+2（特征值通道）
        cm = _entry(entries, "fp11e-genestealercults-heroesuprising-e2")
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [cm],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        # S4+2=6 vs T4（S>T 但未达 2T）→ 3+（2/3）
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [cm],
                                      frozenset({"bearer_leading"}))
        rm = _run(atk_m, _target(t=4), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_assassination_edict_vs_character_only(self, entries):
        # 刺杀敕令（Host of Ascension 增强，partial）：对 CHARACTER 命中 +1（双阶段）
        ae = _entry(entries, "000009067005")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [ae],
                                    frozenset({"bearer_leading"}))
        ch = _run(atk, _target(keywords=frozenset({"character"})),
                  Stance(phase="shooting"))
        plain = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(ch.hits, ch.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(plain.hits, plain.attacks) == pytest.approx(1 / 2, abs=0.02)
        # 原文无阶段限定 → 近战同样生效（反向陷阱核查：不得加阶段门）
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=4)), [ae],
                                      frozenset({"bearer_leading"}))
        rm = _run(atk_m, _target(keywords=frozenset({"character"})),
                  Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_gene_tailored_toxins_damage_both_phases(self, entries):
        # 基因定制毒素（Heroes of the Uprising 增强，partial）：携带者攻击 D+1
        # （原文 This model's attacks，无阶段限定 → 两阶段都须生效）
        gt = _entry(entries, "fp11e-genestealercults-heroesuprising-e1")
        _, modeled_off, notes_off = inject_attacker(
            _attacker(_melee()), [gt], frozenset())
        assert not modeled_off and any("未启用" in n for n in notes_off)
        base = _run(_attacker(_melee(d=1)), _target(sv=7, w=3),
                    Stance(phase="melee"))
        atk, _, _ = inject_attacker(_attacker(_melee(d=1)), [gt],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(sv=7, w=3), Stance(phase="melee"))
        assert _ratio(base.damage, base.unsaved) == pytest.approx(1.0, abs=0.05)
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2.0, abs=0.05)
        # 射击阶段同样生效（反向陷阱核查：不得加阶段门）
        atk_s, _, _ = inject_attacker(_attacker(_gun(d=1)), [gt],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(sv=7, w=3), Stance(phase="shooting"))
        assert _ratio(rs.damage, rs.unsaved) == pytest.approx(2.0, abs=0.05)

    def test_denunciator_of_tyrants_vs_character_both_phases(self, entries):
        # 暴君谴责者（Xenocreed 增强，partial）：对 CHARACTER 命中 +1、致伤 +1
        # （原文无阶段限定 → 裸 target_has_keyword，两阶段都须生效）
        dt = _entry(entries, "000009071003")
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4, s=4)), [dt],
                                    frozenset({"bearer_leading"}))
        ch = _run(atk, _target(t=4, keywords=frozenset({"character"})),
                  Stance(phase="shooting"))
        plain = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(ch.hits, ch.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(ch.wounds, ch.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(plain.hits, plain.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(plain.wounds, plain.hits) == pytest.approx(1 / 2, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=4, s=4)), [dt],
                                      frozenset({"bearer_leading"}))
        rm = _run(atk_m, _target(t=4, keywords=frozenset({"character"})),
                  Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_vanguard_tyrant_s_and_ap_melee_gate(self, entries):
        # 先锋暴君（Final Day 增强，partial）：携带者近战武器 S+1 与 AP+1
        # （两条效果都挂 phase_melee——射击阶段须双双回落基线）
        vt = _entry(entries, "000009827004")
        _, modeled_off, notes_off = inject_attacker(
            _attacker(_melee()), [vt], frozenset())
        assert not modeled_off and any("未启用" in n for n in notes_off)
        atk, _, _ = inject_attacker(_attacker(_melee(s=4, ap=0)), [vt],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4, sv=4), Stance(phase="melee"))
        # S4+1=5 vs T4 → 3+（2/3）；AP0→AP-1 打 Sv4（4+→5+，失败率 1/2→2/3）
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        # 射击阶段不注入（phase_melee 门）：S 与 AP 两路同时回落
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4, ap=0)), [vt],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(t=4, sv=4), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_assault_commando_needs_disembark_toggle(self, entries):
        # 突击突击队（Outlander Claw 增强，partial）：下车回合远程可重骰命中，
        # 需 bearer_leading + disembarked_this_turn 双开关
        ac = _entry(entries, "000009079005")
        _, _, notes = inject_attacker(_attacker(_gun()), [ac],
                                      frozenset({"bearer_leading"}))
        assert any("disembarked_this_turn" in n for n in notes)
        atk, _, _ = inject_attacker(
            _attacker(_gun(bs=4)), [ac],
            frozenset({"bearer_leading", "disembarked_this_turn"}))
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(3 / 4, abs=0.02)


@needs_db
class TestUnitSmoke:
    def test_load_unit_dsl_sees_gc_projection(self):
        # 真单位冒烟（PR4 教训：单测全绿也逮不到 load_unit_dsl 漏扫某表）
        from engines.simulator.profile import load_unit_dsl
        con = sqlite3.connect(str(DB))
        row = con.execute(
            "SELECT id FROM datasheets WHERE faction_id='GC' "
            "AND name LIKE '%Purestrain Genestealers%' LIMIT 1").fetchone()
        con.close()
        assert row, "库内应有 Purestrain Genestealers 兵牌"
        entries = load_unit_dsl(str(DB), row[0])
        assert any(e.faction == "GC" for e in entries), (
            "load_unit_dsl 未装载 GC 的 DSL 投影")
