# tests/test_simulator_dsl_pr20_payload.py
"""P7-PR20 Space Marines（通用星际战士 Codex 分队）编码落账：15 个分队
（13 现有 + 2 新 fp_new）的分队规则 + 战略 + 增强 = 158（0 encoded / 44 partial /
114 not_modeled）——零新引擎通道、零新态势开关。

Space Marines FP（VERSION 1.0）15 分队均挂 faction='SM'（战团/亚阵营混存）：
Librarius Conclave / Armoured Speartip / Headhunter Task Force / Ceramite Sentinels /
Blade of Ultramar / Hammer of Avernii / Spearpoint Task Force / Forgefather's Seekers /
Emperor's Shield / Shadowmark Talon / Bastion Task Force / Orbital Assault Force /
Reclamation Force（13 现有，文本与 11 版 FP 逐字一致零漂移）+ Fulguris Task Force /
Subversion Assets（2 新，fp_rules inserts 补录 id 前缀 fp11e-spacemarines-）。
Bastion 漏录战略 Angels Defiant 补回（000010677006）。分队规则条目物化到 abilities 新行。

SM 通用分队气质=移动/目标点/教条/预备队/重骰1 多，可编率低（44/158）：可编子集集中在
傲慢之甲守方 AP 恶化、[LETHAL HITS]/[SUSTAINED HITS 1]/[无视掩体]、近战 +A/+S/[LANCE]、
守方 S>T -1 致伤、FNP/无效保护/减伤、Stealth 射击命中-1。
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
PAYLOAD = Path("dsl_payloads/spacemarines.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 15 个 Space Marines 分队容器名（stratagems.detachment / enhancements.detachment_name）
SM_DETACHMENTS = (
    "Librarius Conclave", "Armoured Speartip", "Headhunter Task Force",
    "Ceramite Sentinels", "Blade of Ultramar", "Hammer of Avernii",
    "Spearpoint Task Force", "Forgefather’s Seekers", "Emperor’s Shield",
    "Shadowmark Talon", "Bastion Task Force", "Orbital Assault Force",
    "Reclamation Force", "Fulguris Task Force", "Subversion Assets",
)
# 18 条分队规则物化条目 id（det + detachments 源行 id；含双规则分队 Hammer/Spearpoint/Shadowmark）
SM_RULE_IDS = (
    "det000009784", "det000010777", "det000010782", "det000010758", "det000010632",
    "det000010620", "det000010621", "det000010626", "det000010627", "det000010367",
    "det000010459", "det000010463", "det000010464", "det000010675", "det000010679",
    "det000010683", "detfp11e-spacemarines-fulguris", "detfp11e-spacemarines-subversion",
)


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="blade"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, name="boltgun", rng='24"'):
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
        # 18 规则 + 84 战略 + 56 增强 = 158（0 encoded / 44 partial / 114 not_modeled）
        assert len(entries) == 158
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 44, "not_modeled": 114}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        assert by == {"abilities": 18, "stratagems": 84, "enhancements": 56}

    def test_faction_is_sm(self, entries):
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
        # SM 通用分队纯编码 PR：全部带假设/残量注记，无 encoded
        assert all(e.status != "encoded" for e in entries)

    def test_rules_materialize_from_detachments(self, entries):
        for rid in SM_RULE_IDS:
            e = _entry(entries, rid)
            assert e.table == "abilities"
            assert e.provenance.get("text_sha256"), rid

    def test_target_side_entries(self, entries):
        # 守方向条目 = 22：10 条傲慢之甲 + 12 条防守（Fiery Shield / Redoubtable /
        # Armour of Antoninus / Augmetic Fortitude / Malodraxian / Evasive Manoeuvres /
        # Adamantine Mantle / Umbral Raptor / Angels Defiant / Blind Screen /
        # Seals of Reconquest / Shroud Field），全部 partial
        tgt = [e for e in entries if e.side == "target"]
        assert len(tgt) == 22
        assert all(e.status == "partial" for e in tgt)


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(SM_DETACHMENTS)), SM_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name IN (%s) "
            "AND COALESCE(fp_status, '') != 'removed_11e'"
            % ",".join("?" * len(SM_DETACHMENTS)), SM_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_all_detachment_rules_covered(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == set(SM_RULE_IDS)

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
    def test_armour_of_contempt_ap_worsen(self, entries):
        # 傲慢之甲（Armoured Speartip 档）：被攻 AP 恶化1（守方向，两相位）
        # AP-1 打 Sv4（5+，2/3 失败）→ AP0（4+，1/2 失败）
        ac = _entry(entries, "000010780003")
        base = _run(_attacker(_gun(ap=-1)), _target(sv=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=4), [ac], frozenset())
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_angels_defiant_s_gt_t_both_phases(self, entries):
        # 天使不屈（Bastion 补录战略）：守方被 S>T 攻击致伤-1，两相位
        ad = _entry(entries, "fp11e-spacemarines-bastion-s6")
        for phase, wpn in (("shooting", _gun(s=5)), ("melee", _melee(s=5))):
            base = _run(_attacker(wpn), _target(t=4), Stance(phase=phase))
            tgt, _, _ = inject_target(_target(t=4), [ad], frozenset())
            r = _run(_attacker(wpn), tgt, Stance(phase=phase))
            assert _ratio(base.wounds, base.hits) == pytest.approx(2 / 3, abs=0.02)
            assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)
        # S=T（非 S>T）不触发：S4 vs T4 仍 4+
        r2 = _run(_attacker(_melee(s=4)),
                  inject_target(_target(t=4), [ad], frozenset())[0], Stance(phase="melee"))
        assert _ratio(r2.wounds, r2.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_armour_of_antoninus_fnp_toggle(self, entries):
        # 安东尼努斯之铠（Blade of Ultramar 增强）：FNP 5+，需 defender_bearer_leading
        aa = _entry(entries, "000010633002")
        _, _, notes = inject_target(_target(), [aa], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(w=1), [aa], frozenset({"defender_bearer_leading"}))
        base = _run(_attacker(_gun(ap=-6)), _target(w=1), Stance(phase="shooting"))
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        # FNP 5+ 令约 1/3 未保存伤害被免 → 伤害/未保存 ≈ 2/3
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2 / 3, abs=0.03)
        assert _ratio(base.damage, base.unsaved) == pytest.approx(1.0, abs=0.02)

    def test_evasive_manoeuvres_shooting_only(self, entries):
        # 闪避机动（Spearpoint 战略）：守方被射击命中-1 且致伤-1（近战不生效）
        em = _entry(entries, "000010630006")
        atk = _attacker(_gun(bs=4, s=4))
        tgt, _, _ = inject_target(_target(t=4), [em], frozenset())
        r = _run(atk, tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)      # 命中 4+→5+
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)       # 致伤 4+→5+
        # 近战阶段不注入（phase_shooting 门）：命中/致伤不变
        tgt_m, _, _ = inject_target(_target(t=4), [em], frozenset())
        rm = _run(_attacker(_melee(ws=4, s=4)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)


class TestAttackerFromPayload:
    def test_oath_of_macragge_melee_gated(self, entries):
        # 马克拉格之誓（Blade of Ultramar 增强）：近战 +1 A / +1 S，需 bearer_leading
        om = _entry(entries, "000010633003")
        _, _, notes = inject_attacker(_attacker(_melee()), [om], frozenset())
        assert any("bearer_leading" in n for n in notes)
        # 开关开：S4 vs T4 4+（1/2）→ S5 vs T4 3+（2/3）
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [om],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 攻击次数 A+1（单模型 1→2 攻击）：命中数/攻击数不变但攻击基数翻倍——用命中数对账
        base = _run(_attacker(_melee(s=4)), _target(t=4), Stance(phase="melee"))
        assert r.attacks.mean() == pytest.approx(2 * base.attacks.mean(), abs=0.05)
        # 射击阶段不注入（phase_melee 门）：远程 S4 vs T4 仍 4+
        atk_s, _, _ = inject_attacker(_attacker(_gun(s=4)), [om],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(t=4), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_vulkans_quest_within_12_shooting(self, entries):
        # 火神追寻（Forgefather 军规）：远程 12" 内 +1 S（特征值通道，射击门自含）
        vq = _entry(entries, "det000010367")
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [vq], frozenset())
        # ranged_within_12 自含射击门 → S4→S5 vs T4：4+（1/2）→ 3+（2/3）
        r = _run(atk, _target(t=4), Stance(phase="shooting", range_within_12=True))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 12" 外不触发：S4 vs T4 仍 4+
        r2 = _run(atk, _target(t=4), Stance(phase="shooting", range_within_12=False))
        assert _ratio(r2.wounds, r2.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_prescient_precision_lethal_hits_shooting(self, entries):
        # 预知精准（Librarius Conclave 战略）：远程 [LETHAL HITS]（射击门）
        # S4 vs T6：正常 5+ 致伤（1/3）；[LETHAL HITS] 令暴击命中（1/6）直接致伤 → 抬升致伤率
        pp = _entry(entries, "000009791007")
        base = _run(_attacker(_gun(s=4)), _target(t=6), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [pp], frozenset())
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) > _ratio(base.wounds, base.hits) + 0.05
        # 近战阶段不注入（phase_shooting 门）：近战 S4 vs T6 仍 5+（1/3）
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [pp], frozenset())
        rm = _run(atk_m, _target(t=6), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_courage_and_honour_lance_charge(self, entries):
        # 荣耀与荣光（Blade of Ultramar 战略）：近战 [LANCE]——冲锋回合致伤+1
        ch = _entry(entries, "000010634004")
        atk, _, _ = inject_attacker(_attacker(_melee(s=4)), [ch], frozenset())
        # 冲锋回合近战：S4 vs T4 4+（1/2）→ 致伤+1 → 3+（2/3）
        r = _run(atk, _target(t=4), Stance(phase="melee", charging=True))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 非冲锋回合：不触发（1/2）
        r2 = _run(atk, _target(t=4), Stance(phase="melee", charging=False))
        assert _ratio(r2.wounds, r2.hits) == pytest.approx(1 / 2, abs=0.02)
