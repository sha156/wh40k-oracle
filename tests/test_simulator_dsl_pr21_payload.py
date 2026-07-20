# tests/test_simulator_dsl_pr21_payload.py
"""P7-PR21 Imperial Knights（帝国骑士 faction='QI'）全量 DSL 编码落账：8 个分队
（6 现有 + 2 新 fp_new）的分队规则 + 战略 + 增强 = 79（0 encoded / 18 partial /
61 not_modeled）——零新引擎通道、零新态势开关。

帝国骑士为超重型步行机甲（Vehicle/Titanic/Walker）阵营，气质=光环/移动/据点/预备队/
Bondsman 从属/治疗/CP 经济，可编率低（18/79）。可编子集集中在守方 FNP/invuln/T+1/AP恶化、
近战 S>T 致伤-1、[LANCE]/[LETHAL HITS]/[SUSTAINED HITS 2]/[RAPID FIRE 1]/[IGNORES COVER]、
近战 +A/+命中、无视命中减值。

fp_new 两新分队 Dominus Foebreakers / Throne-bonded Outriders（fp11e-imperialknights-*）
由 db_compile/fp_rules_patches.json inserts 补录；Tactical Foil 9"→8" 文本漂移已补。
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
PAYLOAD = Path("dsl_payloads/imperialknights.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 8 个帝国骑士分队容器名（stratagems.detachment / enhancements.detachment_name）
QI_DETACHMENTS = (
    "Freeblade Company", "Gate Warden Lance", "Questor Forgepact",
    "Questoris Companions", "Spearhead-At-Arms", "Valourstrike Lance",
    "Dominus Foebreakers", "Throne-bonded Outriders",
)
# 9 条分队规则物化条目 id（det + detachments 源行 id；Valourstrike Lance 双规则 Bold
# Gallantry + Valour's Reward；末二为 fp_new）
QI_RULE_IDS = (
    "det000010492", "det000009760", "det000010496", "det000010500",
    "det000010505", "det000010754", "det000010501",
    "detfp11e-imperialknights-dominus", "detfp11e-imperialknights-throne",
)


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="chainsword"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, name="battlecannon", rng='24"'):
    return WeaponProfile(name_zh=None, name_en=name, range=rng,
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=(), count=1)


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
        assert len(entries) == 79
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 18, "not_modeled": 61}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        assert by == {"abilities": 9, "stratagems": 42, "enhancements": 28}

    def test_faction_is_qi(self, entries):
        assert all(e.faction == "QI" for e in entries)

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id

    def test_not_modeled_have_reason(self, entries):
        for e in entries:
            if e.status == "not_modeled":
                assert not e.effects and e.not_modeled_notes_zh, e.row_id

    def test_no_encoded(self, entries):
        # 超重机甲阵营纯编码 PR：全部带假设/残量注记，无 encoded
        assert all(e.status != "encoded" for e in entries)

    def test_rules_materialize_from_detachments(self, entries):
        for rid in QI_RULE_IDS:
            e = _entry(entries, rid)
            assert e.table == "abilities"
            assert e.provenance.get("text_sha256"), rid

    def test_target_side_entries(self, entries):
        # 守方向条目 = 9：传奇骑士 FNP + 破枪反制/英勇不退/以责为盾/旋转离子盾/坚忍存活/
        # 全能者恩典 6 战略 + 圣所/受祝甲板 2 增强；其中 7 条带效果（坚忍存活/全能者恩典 nm）
        tgt = [e for e in entries if e.side == "target"]
        assert len(tgt) == 9
        assert len([e for e in tgt if e.effects]) == 7


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(QI_DETACHMENTS)), QI_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(QI_DETACHMENTS)), QI_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_all_detachment_rules_covered(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == set(QI_RULE_IDS)

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


# ═══ 真源 payload 引擎级差分 ═══════════════════════════════════════════════
class TestDefensiveFromPayload:
    def test_knights_of_legend_fnp6(self, entries):
        # 传奇骑士（Freeblade Company 军规）：IK 模型 FNP 6+（守方，无相位门）
        kl = _entry(entries, "det000010754")
        base = _run(_attacker(_gun(ap=-6)), _target(w=1), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(w=1), [kl], frozenset())
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(base.damage, base.unsaved) == pytest.approx(1.0, abs=0.02)
        # FNP 6+ 免约 1/6 → 伤害/未保存 ≈ 5/6
        assert _ratio(r.damage, r.unsaved) == pytest.approx(5 / 6, abs=0.03)

    def test_sanctuary_invuln_toggle(self, entries):
        # 圣所（Freeblade Company 增强）：5+ 无效保护，需 defender_bearer_leading
        sa = _entry(entries, "000010755005")
        _, _, notes = inject_target(_target(), [sa], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(sv=7), [sa],
                                  frozenset({"defender_bearer_leading"}))
        base = _run(_attacker(_gun(ap=-6)), _target(sv=7), Stance(phase="shooting"))
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        # 5+ invuln 挡 1/3 → 未保存/致伤 ≈ 2/3（基线无甲全过）
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(1.0, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.03)

    def test_blessed_plate_t_improve(self, entries):
        # 受祝甲板（Dominus Foebreakers fp_new 增强）：T+1，需 defender_bearer_leading
        bp = _entry(entries, "fp11e-imperialknights-dominus-e1")
        _, _, notes = inject_target(_target(), [bp], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        # S5 vs T4 3+（2/3）→ T5 4+（1/2）
        base = _run(_attacker(_gun(s=5)), _target(t=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(t=4), [bp],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_gun(s=5)), tgt, Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_lancebreaker_melee_s_gt_t(self, entries):
        # 破枪反制（Gate Warden Lance 战略）：近战被 S>T 攻击致伤-1（melee_wound_s_gt_t）
        lb = _entry(entries, "000010498003")
        # 近战 S5 vs T4：2/3 → 致伤-1 → 1/2
        tgt, _, _ = inject_target(_target(t=4), [lb], frozenset())
        r = _run(_attacker(_melee(s=5)), tgt, Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)
        # 射击阶段不注入（近战门）：远程 S5 vs T4 仍 2/3
        tgt_s, _, _ = inject_target(_target(t=4), [lb], frozenset())
        rs = _run(_attacker(_gun(s=5)), tgt_s, Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(2 / 3, abs=0.02)

    def test_let_duty_ap_worsen_shooting(self, entries):
        # 以责为盾（Spearhead-At-Arms 战略）：守方被射击 AP 恶化1（近战不注入）
        ld = _entry(entries, "000010507006")
        base = _run(_attacker(_gun(ap=-1)), _target(sv=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=4), [ld], frozenset())
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        # AP-1 打 Sv4（5+，2/3 失败）→ AP0（4+，1/2 失败）
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 近战阶段不注入（phase_shooting 门）：AP-1 打 Sv4 仍 2/3
        tgt_m, _, _ = inject_target(_target(sv=4), [ld], frozenset())
        rm = _run(_attacker(_melee(ap=-1)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(2 / 3, abs=0.02)


class TestAttackerFromPayload:
    def test_run_them_through_lance_charge(self, entries):
        # 贯穿！（Valourstrike Lance 战略）：近战 [LANCE]——冲锋回合致伤+1
        rt = _entry(entries, "000010494002")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [rt], frozenset())
        # 冲锋回合近战 S4 vs T4：4+（1/2）→ +1 → 3+（2/3）
        r = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 非冲锋回合不触发（1/2）
        r2 = _run(atk, _target(t=4), Stance(phase="melee", charging=False))
        assert _ratio(r2.wounds, r2.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_vow_of_retribution_lethal_shooting(self, entries):
        # 复仇誓约（Valourstrike Lance 战略）：远程 [LETHAL HITS]（射击门）
        vr = _entry(entries, "000010494005")
        base = _run(_attacker(_gun(s=4)), _target(t=6), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [vr], frozenset())
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        # S4 vs T6 正常 5+ 致伤（1/3）；[LETHAL HITS] 暴击命中直接致伤 → 抬升致伤率
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) > _ratio(base.wounds, base.hits) + 0.05
        # 近战阶段不注入（phase_shooting 门）：近战 S4 vs T6 仍 5+（1/3）
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [vr], frozenset())
        rm = _run(atk_m, _target(t=6), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_bringer_of_justice_melee_gated(self, entries):
        # 正义使者（Freeblade Company 增强）：近战 +2 A / +1 命中，需 bearer_leading
        bj = _entry(entries, "000010755002")
        _, _, notes = inject_attacker(_attacker(_melee()), [bj], frozenset())
        assert any("bearer_leading" in n for n in notes)
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [bj],
                                    frozenset({"bearer_leading"}))
        base = _run(_attacker(_melee(s=4)), _target(t=4), Stance(phase="melee"))
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        # A+2（单模型 1→3 攻击）
        assert r.attacks.mean() == pytest.approx(3 * base.attacks.mean(), abs=0.05)
        # 命中+1：4+（1/2）→ 3+（2/3）
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        # 射击阶段不注入（phase_melee 门）：远程单发命中/攻击不变
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [bj],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting"))
        assert rs.attacks.mean() == pytest.approx(1.0, abs=0.02)

    def test_titanic_bombardment_sustained_shooting(self, entries):
        # 巨神轰炸（Gate Warden Lance 战略）：远程 [SUSTAINED HITS 2]（射击门）
        tb = _entry(entries, "000010498006")
        base = _run(_attacker(_gun(bs=4)), _target(t=4), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [tb], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        # 暴击命中（1/6）各 +2 命中 → 命中数/攻击数抬升
        assert _ratio(r.hits, r.attacks) > _ratio(base.hits, base.attacks) + 0.1
        # 近战阶段不注入（phase_shooting 门）：近战命中数不受额外命中影响
        atk_m, _, _ = inject_attacker(_attacker(_melee(ws=4)), [tb], frozenset())
        rm = _run(atk_m, _target(t=4), Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)
