# tests/test_simulator_dsl_pr23_payload.py
"""P7-PR23 Imperial Agents（帝国代理 faction='AoI'）全量 DSL 编码落账：7 个分队
的分队规则 + 战略 + 增强 = 69（4 encoded / 15 partial / 50 not_modeled）——零新引擎
通道、零新态势开关、零 fp_new。

帝国代理为审判庭/刺客/死亡守望/灰骑士/仲裁庭/虚空舰混编阵营，气质=特工/部署/预备队/
据点/战意/具体目标声明，可编率低（19/69 带效果）。可编子集：守方 FNP/invuln/T+1/AP 恶化、
近战重骰命中+致伤、[LETHAL HITS]、[IGNORES COVER]、[SUSTAINED HITS 1]、12" 内 +S/+AP、
对 PSYKER 重骰命中、近战 +1A、传家宝刃全特征值。

DB 对齐：2 text_patches（Rapid Tactical Relocation 9"→8" / Gift of the Prescient 3"→6"，
均几何漂移不影响 DSL，两条目本 payload 均 not_modeled）；ARMOUR OF CONTEMPT / TRUESILVER
ARMOUR「worsen AP by 1」库现文即 11 版免补。FP 唯一新分队 Veiled Blade Elimination Force
Wahapedia 已滚入 DB 故零 fp_new。
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
PAYLOAD = Path("dsl_payloads/imperialagents.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 7 个帝国代理分队容器名（stratagems.detachment / enhancements.detachment_name；
# Voidship’s Company 用 DB 弯撇号）
AOI_DETACHMENTS = (
    "Imperialis Fleet", "Interdiction Team", "Ordo Hereticus Purgation Force",
    "Ordo Malleus Daemon Hunters", "Ordo Xenos Alien Hunters",
    "Veiled Blade Elimination Force", "Voidship’s Company",
)
# 7 条分队规则物化条目 id（det + detachments 源行 id）
AOI_RULE_IDS = (
    "det000009125", "det000009129", "det000009133", "det000009137",
    "det000009359", "det000009368", "det000009756",
)


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


# ═══ 结构与 DB 对账 ═══════════════════════════════════════════════════════
class TestPayloadShape:
    def test_counts(self, entries):
        assert len(entries) == 69
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 4, "partial": 15, "not_modeled": 50}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        assert by == {"abilities": 7, "stratagems": 38, "enhancements": 24}

    def test_faction_is_aoi(self, entries):
        assert all(e.faction == "AoI" for e in entries)

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
        for rid in AOI_RULE_IDS:
            e = _entry(entries, rid)
            assert e.table == "abilities"
            assert e.provenance.get("text_sha256"), rid

    def test_target_side_entries(self, entries):
        # 守方向条目 = 10；其中 7 条带效果（位移力场 invuln / 以死尽责 FNP4 /
        # 不可侵犯管辖 FNP5 / 真银之甲 AP / 傲慢之甲 AP / 超量兴奋剂 T+1 / 暗纹裹尸布 FNP4）
        tgt = [e for e in entries if e.side == "target"]
        assert len(tgt) == 10
        assert len([e for e in tgt if e.effects]) == 7


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='AoI' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='AoI' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        active = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='AoI'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == active == set(AOI_RULE_IDS)

    def test_fingerprints_match_db(self, entries):
        from db_compile.dsl_apply import _fingerprint
        con = self._db()
        for e in entries:
            if not e.effects:
                continue
            if e.table == "abilities":
                src_id = e.row_id[3:]  # strip "det"
                src = con.execute("SELECT rule_text FROM detachments WHERE id=?",
                                  (src_id,)).fetchone()
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
    def test_duty_and_death_fnp4(self, entries):
        # 以死尽责（Interdiction Team 战略，encoded）：本单位 FNP 4+（守方，无相位门）
        dd = _entry(entries, "000009370003")
        base = _run(_attacker(_gun(ap=-6)), _target(w=1), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(w=1), [dd], frozenset())
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(base.damage, base.unsaved) == pytest.approx(1.0, abs=0.02)
        # FNP 4+ 免约 1/2 → 伤害/未保存 ≈ 1/2
        assert _ratio(r.damage, r.unsaved) == pytest.approx(1 / 2, abs=0.03)

    def test_displacer_field_invuln4(self, entries):
        # 位移力场（Imperialis Fleet 战略）：4+ 无效保护（守方，点名假设已用，无开关）
        df = _entry(entries, "000009139006")
        base = _run(_attacker(_gun(ap=-6)), _target(sv=7), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=7), [df], frozenset())
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(1.0, abs=0.02)
        # 4+ invuln 挡 1/2 → 未保存/致伤 ≈ 1/2
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.03)

    def test_blackweave_shroud_fnp_toggle(self, entries):
        # 暗纹裹尸布（Ordo Xenos 增强）：携带者 FNP 4+，需 defender_bearer_leading
        bs = _entry(entries, "000009126004")
        _, _, notes = inject_target(_target(), [bs], frozenset())
        assert any("defender_bearer_leading" in n or "未启用" in n for n in notes)
        base = _run(_attacker(_gun(ap=-6)), _target(w=1), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(w=1), [bs],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(r.damage, r.unsaved) == pytest.approx(1 / 2, abs=0.03)

    def test_hyperstimms_t_improve(self, entries):
        # 超量兴奋剂（Veiled Blade 战略）：本单位 T +1（守方，无相位门）
        hs = _entry(entries, "000009758003")
        # S5 vs T4 3+（2/3）→ T5 4+（1/2）
        base = _run(_attacker(_gun(s=5)), _target(t=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(t=4), [hs], frozenset())
        r = _run(_attacker(_gun(s=5)), tgt, Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_truesilver_armour_ap_worsen(self, entries):
        # 真银之甲（Ordo Malleus 战略）：被攻 AP 恶化 1（守方，两相位适用）
        ts = _entry(entries, "000009135005")
        base = _run(_attacker(_gun(ap=-1)), _target(sv=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=4), [ts], frozenset())
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        # AP-1 打 Sv4（5+，2/3 失败）→ AP0（4+，1/2 失败）
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 近战阶段同样注入（无相位门）：近战 AP-1 打 Sv4 → AP0
        tgt_m, _, _ = inject_target(_target(sv=4), [ts], frozenset())
        rm = _run(_attacker(_melee(ap=-1)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1 / 2, abs=0.02)


# ═══ 攻方向 payload 引擎级差分 ═════════════════════════════════════════════
class TestAttackerFromPayload:
    def test_crackdown_melee_rerolls(self, entries):
        # 扫荡镇压（Interdiction Team 战略，encoded）：近战重骰命中+致伤（Fight phase）
        cd = _entry(entries, "000009370002")
        atk, _, _ = inject_attacker(_attacker(_melee(ws=4, s=4)), [cd], frozenset())
        # WS4 重骰失败：命中 1/2 → 1/2+1/2·1/2 = 3/4
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(3 / 4, abs=0.02)
        # 致伤 S4 vs T4 4+（1/2）重骰失败 → 3/4
        assert _ratio(r.wounds, r.hits) == pytest.approx(3 / 4, abs=0.02)
        # 射击阶段不注入（phase_melee 门）：远程命中/攻击 = BS4 = 1/2
        atk_s, _, _ = inject_attacker(_attacker(_gun(bs=4)), [cd], frozenset())
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_dispense_justice_lethal_both_phases(self, entries):
        # 伸张正义（Ordo Hereticus 战略，encoded）：武器 [LETHAL HITS]（无相位门，两相位）
        dj = _entry(entries, "000009131003")
        # 射击：S4 vs T6 正常 5+ 致伤（1/3）；[LETHAL HITS] 暴击命中直接致伤 → 抬升
        base = _run(_attacker(_gun(s=4)), _target(t=6), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [dj], frozenset())
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) > _ratio(base.wounds, base.hits) + 0.05
        # 近战阶段同样注入（无相位门）
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [dj], frozenset())
        rm = _run(atk_m, _target(t=6), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) > 1 / 3 + 0.05

    def test_witch_hunter_reroll_vs_psyker(self, entries):
        # 猎巫者（Ordo Hereticus 增强，encoded）：对 PSYKER 目标重骰命中，需 bearer_leading
        wh = _entry(entries, "000009130005")
        _, _, notes = inject_attacker(_attacker(_gun()), [wh], frozenset())
        assert any("bearer_leading" in n or "未启用" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [wh],
                                    frozenset({"bearer_leading"}))
        # 对 PSYKER：命中重骰失败 1/2 → 3/4
        r = _run(atk, _target(t=4, keywords=frozenset({"psyker"})),
                 Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(3 / 4, abs=0.02)
        # 对非 PSYKER 目标不触发（target_has_keyword 门）：命中 = 1/2
        r2 = _run(atk, _target(t=4, keywords=frozenset()), Stance(phase="shooting"))
        assert _ratio(r2.hits, r2.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_close_quarters_barrage_within12(self, entries):
        # 近距弹幕（Imperialis Fleet 战略）：远程 12" 内 +1 S/+1 AP，需 range_within_12
        cqb = _entry(entries, "000009139004")
        _, _, nm = inject_attacker(_attacker(_gun(s=4)), [cqb], frozenset())
        assert any("range_within_12" in n or "未启用" in n for n in nm)
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [cqb],
                                    frozenset({"range_within_12"}))
        # 12" 内 +1 S：S4 vs T4 4+（1/2）→ S5 vs T4 3+（2/3）
        base = _run(_attacker(_gun(s=4)), _target(t=4), Stance(phase="shooting"))
        r = _run(atk, _target(t=4), Stance(phase="shooting", range_within_12=True))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_kraken_rounds_ap_shooting_gate(self, entries):
        # 克拉肯弹（Ordo Xenos 战略）：射击远程 AP 改善 1（phase_shooting 门）
        kr = _entry(entries, "000009127006")
        atk, _, _ = inject_attacker(_attacker(_gun(ap=0)), [kr], frozenset())
        # AP+1 打 Sv4（4+，1/2 失败）→ AP-1（5+，2/3 失败）
        base = _run(_attacker(_gun(ap=0)), _target(sv=4), Stance(phase="shooting"))
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        # 近战阶段不注入（phase_shooting 门）：近战 AP0 打 Sv4 仍 1/2
        atk_m, _, _ = inject_attacker(_attacker(_melee(ap=0)), [kr], frozenset())
        rm = _run(atk_m, _target(sv=4), Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_daemon_slayer_extra_attack_melee(self, entries):
        # 弑魔者（Ordo Malleus 增强）：近战 +1 A，需 bearer_leading
        ds = _entry(entries, "000009134002")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ds],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(_melee(s=4)), _target(t=4), Stance(phase="melee"))
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        # A+1（单模型 1→2 攻击）
        assert r.attacks.mean() == pytest.approx(2 * base.attacks.mean(), abs=0.05)
        # 射击阶段不注入（phase_melee 门）：远程单发攻击不变
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [ds],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting"))
        assert rs.attacks.mean() == pytest.approx(1.0, abs=0.02)

    def test_heirloom_blade_weapon_filter(self, entries):
        # 传家宝刃（Voidship’s Company 增强）：单溅镜甘蔗剑全特征值 +1（weapon_filter）
        hb = _entry(entries, "000009360003")
        # 无匹配武器 → 显式披露不静默
        _, _, nm = inject_attacker(_attacker(_melee(name="chainsword")), [hb],
                                   frozenset({"bearer_leading"}))
        assert any("cane-rapier" in n for n in nm)
        # 有匹配武器：A+1（1→2）、S+1（S4 vs T4 1/2→2/3）
        wpn = _melee(ws=4, s=4, ap=0, name="monomolecular cane-rapier")
        atk, _, _ = inject_attacker(_attacker(wpn), [hb],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(wpn), _target(t=4), Stance(phase="melee"))
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2 * base.attacks.mean(), abs=0.05)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_dragonfire_ignores_cover_shooting(self, entries):
        # 龙焰弹（Ordo Xenos 战略）：远程 [IGNORES COVER]（phase_shooting 门）
        dr = _entry(entries, "000009127005")
        # 掩体给守方 BS 惩罚（11版）——注入无视掩体后命中恢复
        base = _run(_attacker(_gun(bs=3)),
                    _target(sv=4), Stance(phase="shooting", target_in_cover=True))
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [dr], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="shooting", target_in_cover=True))
        # 无视掩体 → 命中率不再被掩体惩罚，命中/攻击更高
        assert _ratio(r.hits, r.attacks) > _ratio(base.hits, base.attacks) + 0.05

    def test_root_out_heresy_ignores_cover(self, entries):
        # 揪出异端（Ordo Hereticus 分队规则）：合规单位远程 [IGNORES COVER]
        rh = _entry(entries, "det000009129")
        base = _run(_attacker(_gun(bs=3)),
                    _target(sv=4), Stance(phase="shooting", target_in_cover=True))
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [rh], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="shooting", target_in_cover=True))
        assert _ratio(r.hits, r.attacks) > _ratio(base.hits, base.attacks) + 0.05
