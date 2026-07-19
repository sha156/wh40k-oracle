# tests/test_simulator_dsl_pr19_payload.py
"""P7-PR19 黑暗天使（Dark Angels）编码落账：8 个分队（5 现有 + 3 新 fp_new）的
分队规则 + 战略 + 增强 = 73（0 encoded / 22 partial / 51 not_modeled）——零新引擎通道、零新开关。

黑暗天使 11 版为 ADEPTUS ASTARTES 战团，内容挂 faction='SM'。8 个分队容器名：
Company of Hunters / Inner Circle Task Force / Unforgiven Task Force / Lion's Blade Task Force /
Wrath of the Rock（5 现有，文本与 11 版 FP 逐字一致零漂移）+ Dark Age Arsenal / Darkflight
Pursuit / Interrogation Conclave（3 新，fp_rules inserts 补录 id 前缀 fp11e-da-）。分队规则条目
物化到 abilities 新行（spec D5，id=det+detachments 源行 id）。

覆盖（spec 七-1 双验范式，手算期望值写在断言旁）：
  · DB 对账：8 分队全部活跃 stratagems/enhancements 有 payload 条目、8 条分队规则全覆盖；
    带 effects 条目指纹全对（materialize 对 detachments.rule_text 核）
  · 三态计数：0 encoded / 22 partial / 51 not_modeled（SM 战团气质=移动/目标点/士气多，可编率低）
  · 真源 payload 引擎级差分：傲慢之甲守方 AP 恶化 / 尽责坚韧守方 S>T -1 致伤 / 远古兵刃近战
    +2S+1AP+1D（需 bearer_leading）/ 罪愆昭示等离子武器 +1 命中（weapon_filter，射击门 + 非等离子
    武器不受影响）/ 不赦之怒 [LETHAL HITS] 提升致伤 / 高速专注守方射击命中-1（近战不生效）
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
PAYLOAD = Path("dsl_payloads/darkangels.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 8 个黑暗天使分队容器名（stratagems.detachment / enhancements.detachment_name）
DA_DETACHMENTS = (
    "Company of Hunters", "Inner Circle Task Force", "Unforgiven Task Force",
    "Lion’s Blade Task Force", "Wrath of the Rock",
    "Dark Age Arsenal", "Darkflight Pursuit", "Interrogation Conclave",
)
# 8 条分队规则的物化条目 id（det + detachments 源行 id）
DA_RULE_IDS = (
    "det000008777", "det000008773", "det000008770", "det000009732", "det000010154",
    "detfp11e-da-arsenal", "detfp11e-da-darkflight", "detfp11e-da-conclave",
)


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="blade"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, name="boltgun"):
    return WeaponProfile(name_zh=None, name_en=name, range='24"',
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
        # 8 规则 + 33 战略 + 32 增强 = 73（0 encoded / 22 partial / 51 not_modeled）
        assert len(entries) == 73
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 22, "not_modeled": 51}

    def test_faction_is_sm_subfaction(self, entries):
        assert all(e.faction == "SM" for e in entries)

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
        # SM 战团纯编码 PR：全部带假设/残量注记，无 encoded
        assert all(e.status != "encoded" for e in entries)

    def test_rules_materialize_from_detachments(self, entries):
        for rid in DA_RULE_IDS:
            e = _entry(entries, rid)
            assert e.table == "abilities"
            assert e.provenance.get("text_sha256"), rid

    def test_target_side_entries(self, entries):
        # 守方向条目 = 12：5 条傲慢之甲 + 高速专注 + 坚不可摧战线 + 追念之旗 + 尽责坚韧 + 暗影之翼
        # + 2 条守方向 not_modeled（岿-Unmatched Fortitude 射击×S>T 无载体、Strength in Unity 空间分支）
        target_ids = {e.row_id for e in entries if e.side == "target"}
        assert len(target_ids) == 12
        assert "000008779003" in target_ids and "det000010154" in target_ids


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(DA_DETACHMENTS)), DA_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(DA_DETACHMENTS)), DA_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_all_detachment_rules_covered(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == set(DA_RULE_IDS)

    def test_fingerprints_match_db(self, entries):
        from db_compile.dsl_apply import _fingerprint
        con = self._db()
        for e in entries:
            if not e.effects:
                continue
            mat = None
            for cand in (e,):  # materialize lives on the raw dict; re-read from DB by table
                pass
            if e.table == "abilities":
                # 分队规则物化：指纹对 detachments.rule_text 核
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
    def test_armour_of_contempt_ap_worsen(self, entries):
        # 傲慢之甲（Company of Hunters 档）：被攻 AP 恶化1（守方向，两相位）
        # AP-1 打 Sv4（5+，2/3 失败）→ AP0（4+，1/2 失败）
        ac = _entry(entries, "000008779003")
        base = _run(_attacker(_gun(ap=-1)), _target(sv=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=4), [ac], frozenset())
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_dutiful_tenacity_s_gt_t_both_phases(self, entries):
        # 尽责坚韧（Wrath of the Rock 军规）：守方被 S>T 攻击致伤-1，两相位
        # S5 vs T4（S>T）：正常 3+（2/3）→ -1 → 4+（1/2）
        dt = _entry(entries, "det000010154")
        for phase, wpn in (("shooting", _gun(s=5)), ("melee", _melee(s=5))):
            base = _run(_attacker(wpn), _target(t=4), Stance(phase=phase))
            tgt, _, _ = inject_target(_target(t=4), [dt], frozenset())
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(base.wounds, base.hits) == pytest.approx(2 / 3, abs=0.02)
            assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)
        # S=T（非 S>T）不触发：S4 vs T4 仍 4+
        r2 = _run(_attacker(_melee(s=4)),
                  inject_target(_target(t=4), [dt], frozenset())[0], Stance(phase="melee"))
        assert _ratio(r2.wounds, r2.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_high_speed_focus_shooting_only(self, entries):
        # 高速专注（Company of Hunters）：守方被射击命中-1（近战不生效）
        hf = _entry(entries, "000008779006")
        atk = _attacker(_gun(bs=4))
        tgt, _, _ = inject_target(_target(), [hf], frozenset())
        r = _run(atk, tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)   # 4+→5+
        # 近战阶段不注入（phase_shooting 门）：近战武器命中不变（1/2）
        tgt_m, _, _ = inject_target(_target(), [hf], frozenset())
        rm = _run(_attacker(_melee(ws=4)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)


class TestAttackerFromPayload:
    def test_ancient_weapons_melee_gated(self, entries):
        # 远古兵刃（Wrath of the Rock 增强）：近战 +2S / AP改善1 / D+1，需 bearer_leading
        aw = _entry(entries, "000010155003")
        # 开关关：不注入并披露
        _, _, notes = inject_attacker(_attacker(_melee()), [aw], frozenset())
        assert any("bearer_leading" in n for n in notes)
        # 开关开：S4 vs T4 4+（1/2）→ S6 vs T4 3+（2/3）
        atk, _, _ = inject_attacker(_attacker(_melee(s=4, ap=0, d=1)), [aw],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4, sv=7, w=3), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 每未保存伤害 D1→D2（w=3 不封顶）
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2.0, abs=0.03)
        # AP 改善1：AP0→AP-1 打 Sv4（4+→5+，1/2→2/3 失败）
        atk_ap, _, _ = inject_attacker(_attacker(_melee(s=4, ap=0)), [aw],
                                       frozenset({"bearer_leading"}))
        rap = _run(atk_ap, _target(t=4, sv=4, w=3), Stance(phase="melee"))
        assert _ratio(rap.unsaved, rap.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_ancient_weapons_shooting_unaffected(self, entries):
        # phase_melee 门：射击阶段远程武器不受影响（S4 vs T4 仍 4+）
        aw = _entry(entries, "000010155003")
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [aw],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_revelation_of_guilt_plasma_filter(self, entries):
        # 罪愆昭示（Dark Age Arsenal）：等离子远程武器 +1 命中（weapon_filter='plasma'，射击门）
        rg = _entry(entries, "fp11e-da-arsenal-s3")
        # 等离子武器：BS4（1/2）→ +1 → BS3（2/3）
        atk, mod, _ = inject_attacker(_attacker(_gun(bs=4, name="plasma incinerator")),
                                      [rg], frozenset())
        assert mod and any("plasma" in m.lower() for m in mod)
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)
        # 非等离子武器（boltgun）：weapon_filter 不匹配 → 命中不变（1/2）+ 披露
        atk2, _, nm = inject_attacker(_attacker(_gun(bs=4, name="boltgun")), [rg], frozenset())
        r2 = _run(atk2, _target(), Stance(phase="shooting"))
        assert _ratio(r2.hits, r2.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert any("plasma" in n.lower() for n in nm)
        # 近战阶段：等离子武器不存在于近战 loadout；此处验证射击门——用等离子名近战武器
        # 但 condition=phase_shooting，故近战不注入命中加成
        atk3, _, _ = inject_attacker(_attacker(_melee(ws=4, name="plasma blade")), [rg],
                                     frozenset())
        r3 = _run(atk3, _target(), Stance(phase="melee"))
        assert _ratio(r3.hits, r3.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_unforgiven_fury_lethal_hits_raises_wounds(self, entries):
        # 不赦之怒（Unforgiven Task Force）：全武器 [LETHAL HITS]（暴击自动致伤，两相位）
        # S4 vs T6：正常 5+ 致伤（1/3）；[LETHAL HITS] 令暴击命中（1/6）直接致伤 → 提升致伤率
        uf = _entry(entries, "000008389003")
        base = _run(_attacker(_gun(s=4)), _target(t=6), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [uf], frozenset())
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        base_ratio = _ratio(base.wounds, base.hits)
        buff_ratio = _ratio(r.wounds, r.hits)
        assert base_ratio == pytest.approx(1 / 3, abs=0.02)
        assert buff_ratio > base_ratio + 0.05    # 暴击自动致伤明显抬升致伤率
