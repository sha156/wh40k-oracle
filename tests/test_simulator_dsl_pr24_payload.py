# tests/test_simulator_dsl_pr24_payload.py
"""P7-PR24 钢铁联盟（Leagues Of Votann，faction='LoV'）全量 DSL 编码落账：12 个分队
的分队规则 + 战略 + 增强 = 109（6 encoded / 13 partial / 90 not_modeled）——零新引擎
通道、零新态势开关。

钢铁联盟为矮人耐战/精准射击阵营，气质=YP 经济/誓言（Hostile Acquisition⇄Fortify
Takeover）/审判标记/assailed·pinned·suppressed 状态门/预备队/移动/据点，可编率低
（21/109 带效果）。可编子集：守方 invuln4/被伤-1（S>T 门）/AP 恶化/匿踪-1命中/压制敌
命中-1、远程 [IGNORES COVER]/[LETHAL HITS]/[SUSTAINED HITS 1·2]/+1S/+1命中(12")/无视
命中修正、近战 AP+1。

DB 对齐见迭代 1：2 text_patches（SECURE POSITIONS WHEN 增补 / CLAIMSTAKER REFLEX
9"→8"）+ 18 fp_new inserts（Armoured Trailblazers/Farseekers/Hearthguard Covenant
三真新分队，均 Wahapedia 未滚入）。三条目其效果面各 not_modeled 或 partial。
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
PAYLOAD = Path("dsl_payloads/votann.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 12 个钢铁联盟分队容器名（stratagems.detachment / enhancements.detachment_name）
LOV_DETACHMENTS = (
    "Void Salvagers", "Hearthfire Strike", "Hearthband", "Needgaârd Oathband",
    "Persecution Prospect", "Dêlve Assault Shift", "Brandfast Oathband",
    "Hearthfyre Arsenal", "Mercenary Oathband", "Armoured Trailblazers",
    "Farseekers", "Hearthguard Covenant",
)
# 12 条分队规则物化条目 id（det + detachments 源行 id）
LOV_RULE_IDS = (
    "det000009528", "det000009536", "det000009822", "det000010434",
    "det000010438", "det000010442", "det000010446", "det000010450",
    "det000010707", "detfp11e-votann-trailblazers", "detfp11e-votann-farseekers",
    "detfp11e-votann-hearthguard",
)


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _melee(ws=4, s=4, ap=0, d=1, name="axe"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="bolter", rng='24"'):
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
        assert len(entries) == 109
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 6, "partial": 13, "not_modeled": 90}

    def test_table_breakdown(self, entries):
        by = {}
        for e in entries:
            by[e.table] = by.get(e.table, 0) + 1
        assert by == {"abilities": 12, "stratagems": 59, "enhancements": 38}

    def test_faction_is_lov(self, entries):
        assert all(e.faction == "LoV" for e in entries)

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
        for rid in LOV_RULE_IDS:
            e = _entry(entries, rid)
            assert e.table == "abilities"
            assert e.provenance.get("text_sha256"), rid

    def test_all_effects_are_within_known_channels(self, entries):
        # 零新引擎通道护栏：每条 effect 的 (phase, op) 必落在既有消费点白名单
        from engines.simulator.sequence import ATTACKER_CONSUMED, TARGET_CONSUMED
        for e in entries:
            consumed = ATTACKER_CONSUMED if e.side == "attacker" else TARGET_CONSUMED
            for eff in e.effects:
                assert (eff.phase, eff.op) in consumed, (e.row_id, eff.phase, eff.op)


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction='LoV' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id='LoV' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_all_detachment_rules_covered(self, entries):
        con = self._db()
        active = {"det" + r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction='LoV'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == active == set(LOV_RULE_IDS)

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
    def test_brekkeknots_invuln4(self, entries):
        # 护盾结界（Hearthband 战略，encoded）：4+ 无效保护（守方，无相位门）
        bk = _entry(entries, "000009824002")
        base = _run(_attacker(_gun(ap=-6)), _target(sv=7), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=7), [bk], frozenset())
        r = _run(_attacker(_gun(ap=-6)), tgt, Stance(phase="shooting"))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(1.0, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.03)

    def test_weavefield_flare_wound_gate(self, entries):
        # 织焰照明弹（Hearthfire Strike 战略，encoded）：S>T 时被伤 -1（守方，两相位）
        wf = _entry(entries, "000009538002")
        # S5 vs T4（S>T）→ 致伤 3+（2/3）；-1 致伤 → 4+（1/2）
        base = _run(_attacker(_gun(s=5)), _target(t=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(t=4), [wf], frozenset())
        r = _run(_attacker(_gun(s=5)), tgt, Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)
        # S4 vs T4（S==T，非 S>T）→ 门不成立，致伤仍 4+（1/2），无惩罚
        tgt2, _, _ = inject_target(_target(t=4), [wf], frozenset())
        r2 = _run(_attacker(_gun(s=4)), tgt2, Stance(phase="shooting"))
        assert _ratio(r2.wounds, r2.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_void_hardened_ap_worsen_both_phases(self, entries):
        # 虚空硬化（Needgaârd 战略，partial）：被攻 AP 恶化 1（守方，无相位门→两相位）
        vh = _entry(entries, "000010436002")
        base = _run(_attacker(_gun(ap=-1)), _target(sv=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=4), [vh], frozenset())
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        # AP-1 打 Sv4（5+，2/3 失败）→ AP0（4+，1/2 失败）
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 近战阶段同样注入（无相位门）
        tgt_m, _, _ = inject_target(_target(sv=4), [vh], frozenset())
        rm = _run(_attacker(_melee(ap=-1)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_gravitronic_pulse_hit_debuff_melee_gate(self, entries):
        # 重能脉冲（Hearthfire Strike 战略，partial）：被冲锋敌方近战反击命中骰 -1
        # （守方，phase_melee 门——冲锋阶段在射击阶段之后，本回合仅战斗阶段反击）
        gp = _entry(entries, "000009538005")
        base = _run(_attacker(_melee(ws=4)), _target(), Stance(phase="melee"))
        tgt, _, _ = inject_target(_target(), [gp], frozenset())
        r = _run(_attacker(_melee(ws=4)), tgt, Stance(phase="melee"))
        # WS4（1/2）→ -1 命中 → 5+（1/3）
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        # 射击阶段不注入（phase_melee 门）：来袭远程命中不受影响
        tgt_s, _, _ = inject_target(_target(), [gp], frozenset())
        rs = _run(_attacker(_gun(bs=4)), tgt_s, Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_dispersed_formation_stealth(self, entries):
        # 分散阵型（Persecution 战略，partial）：匿踪 → 远程来袭命中 -1（守方，phase_shooting）
        df = _entry(entries, "000010440007")
        base = _run(_attacker(_gun(bs=4)), _target(), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(), [df], frozenset())
        r = _run(_attacker(_gun(bs=4)), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        # 近战阶段不注入（phase_shooting 门）：近战命中不受影响
        tgt_m, _, _ = inject_target(_target(), [df], frozenset())
        rm = _run(_attacker(_melee(ws=4)), tgt_m, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)


# ═══ 攻方向 payload 引擎级差分 ═════════════════════════════════════════════
class TestAttackerFromPayload:
    def test_no_shot_wasted_lethal_shooting_gate(self, entries):
        # 弹无虚发（Farseekers 战略，encoded）：远程 [LETHAL HITS]（phase_shooting 门）
        nsw = _entry(entries, "fp11e-votann-farseekers-s2")
        base = _run(_attacker(_gun(s=4)), _target(t=6), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [nsw], frozenset())
        r = _run(atk, _target(t=6), Stance(phase="shooting"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(r.wounds, r.hits) > _ratio(base.wounds, base.hits) + 0.05
        # 近战阶段不注入（phase_shooting 门）：致伤/命中回落基线
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [nsw], frozenset())
        rm = _run(atk_m, _target(t=6), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_scornful_analysis_ignores_cover(self, entries):
        # 轻蔑剖析（Farseekers 战略，encoded）：远程 [IGNORES COVER]
        sa = _entry(entries, "fp11e-votann-farseekers-s1")
        base = _run(_attacker(_gun(bs=3)),
                    _target(sv=4), Stance(phase="shooting", target_in_cover=True))
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [sa], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="shooting", target_in_cover=True))
        assert _ratio(r.hits, r.attacks) > _ratio(base.hits, base.attacks) + 0.05

    def test_saturation_rounds_ignores_cover_bearer_gate(self, entries):
        # 饱和弹幕（Armoured Trailblazers 增强，partial）：远程 [IGNORES COVER]，需 bearer_leading
        sr = _entry(entries, "fp11e-votann-trailblazers-e1")
        _, _, nm = inject_attacker(_attacker(_gun(bs=3)), [sr], frozenset())
        assert any("bearer_leading" in n or "未启用" in n for n in nm)
        base = _run(_attacker(_gun(bs=3)),
                    _target(sv=4), Stance(phase="shooting", target_in_cover=True))
        atk, _, _ = inject_attacker(_attacker(_gun(bs=3)), [sr],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(sv=4), Stance(phase="shooting", target_in_cover=True))
        assert _ratio(r.hits, r.attacks) > _ratio(base.hits, base.attacks) + 0.05

    def test_fury_of_hearth_s_improve_shooting_gate(self, entries):
        # 炉火之怒（Hearthband 战略，partial）：远程 +1 S（phase_shooting 门）
        fh = _entry(entries, "000009824007")
        base = _run(_attacker(_gun(s=4)), _target(t=4), Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [fh], frozenset())
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        # S4 vs T4（4+，1/2）→ S5 vs T4（3+，2/3）
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 近战阶段不注入（phase_shooting 门）：近战 S4 vs T4 仍 1/2
        atk_m, _, _ = inject_attacker(_attacker(_melee(s=4)), [fh], frozenset())
        rm = _run(atk_m, _target(t=4), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_honour_of_the_hold_melee_ap_gate(self, entries):
        # 坚守荣誉（Needgaârd 战略，partial）：近战 AP 改善 1（phase_melee 门）
        hh = _entry(entries, "000010436003")
        base = _run(_attacker(_melee(ap=0)), _target(sv=4), Stance(phase="melee"))
        atk, _, _ = inject_attacker(_attacker(_melee(ap=0)), [hh], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="melee"))
        # AP0 打 Sv4（4+，1/2 失败）→ AP-1（5+，2/3 失败）
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        # 射击阶段不注入（phase_melee 门）：远程 AP0 打 Sv4 仍 1/2
        atk_s, _, _ = inject_attacker(_attacker(_gun(ap=0)), [hh], frozenset())
        rs = _run(atk_s, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(rs.unsaved, rs.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_eye_of_the_hunt_hit_within12(self, entries):
        # 远索者（Farseekers 分队规则，partial）：12" 内远程 +1 命中，需 range_within_12
        eh = _entry(entries, "detfp11e-votann-farseekers")
        _, _, nm = inject_attacker(_attacker(_gun(bs=4)), [eh], frozenset())
        assert any("range_within_12" in n or "未启用" in n for n in nm)
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [eh],
                                    frozenset({"range_within_12"}))
        base = _run(_attacker(_gun(bs=4)), _target(t=4), Stance(phase="shooting"))
        r = _run(atk, _target(t=4), Stance(phase="shooting", range_within_12=True))
        # BS4（1/2）→ +1 命中 → 3+（2/3）
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 2, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(2 / 3, abs=0.02)

    def test_trivarg_sustained2_disembark_gate(self, entries):
        # 特里瓦格电子植入体（Brandfast 增强，partial）：下车回合远程 [SUSTAINED HITS 2]，
        # 需 bearer_leading + disembarked_this_turn
        tv = _entry(entries, "000010447003")
        _, _, nm = inject_attacker(_attacker(_gun(bs=4)), [tv], frozenset())
        assert any("disembarked_this_turn" in n or "未启用" in n for n in nm)
        atk, _, _ = inject_attacker(
            _attacker(_gun(bs=4)), [tv],
            frozenset({"bearer_leading", "disembarked_this_turn"}))
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        # BS4 命中 1/2 + 暴击(1/6)×2 追加命中 = 1/2 + 1/3 = 5/6
        assert _ratio(r.hits, r.attacks) == pytest.approx(5 / 6, abs=0.03)
