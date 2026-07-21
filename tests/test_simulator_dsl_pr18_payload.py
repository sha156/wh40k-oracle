# tests/test_simulator_dsl_pr18_payload.py
"""P7-PR18 太空野狼（Space Wolves）编码落账：9 分队规则物化 + 33 战略 + 22 增强 = 64
（5 encoded / 12 partial / 47 not_modeled）——零新引擎通道、零新态势开关。

太空野狼 11 版为 ADEPTUS ASTARTES 战团，内容挂 faction='SM'，覆盖 7 个分队：
Champions of Fenris（11 版完整重印）、Legends of Saga and Song 与 Veterans of the
Fang（11 版全新）、四条 Saga（Great Wolf / Beastslayer / Bold / Hunter）。军规沿用
通用 Oath of Moment（000008350，非本战团专属，按血天使 PR9 先例不重复收录）。

覆盖（spec 七-1 双验范式，手算期望值写在断言旁）：
  · DB 对账：7 个分队全部活跃 stratagems/enhancements 有 payload 条目、9 行分队规则
    全物化（含 Saga of the Great Wolf 的 Howling Onslaught 与 Restrictions 附属行）；
    带 effects 条目指纹全对
  · 三态计数：5 encoded / 12 partial / 47 not_modeled
  · 真源 payload 引擎级差分：传奇屠戮者关键词门 [LETHAL HITS]（不加相位门）/ 无羁凶性
    与群狼之眼的相位门互补 / 勇士指引双相位重骰 / 吟游者的预言 [LANCE] 仅冲锋 /
    野性暴怒冲锋叠加 / 猎手之眼射击 AP+无视掩体 / 预见之敌与英勇决意的守方相位门差异
"""
import json
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
PAYLOAD = Path("dsl_payloads/spacewolves.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

# 7 个太空野狼分队（stratagems.detachment / enhancements.detachment_name 口径）
SW_DETACHMENTS = ("Champions of Fenris", "Saga of the Great Wolf",
                  "Saga of the Beastslayer", "Saga of the Bold",
                  "Saga of the Hunter", "Legends of Saga and Song",
                  "Veterans of the Fang")
# 9 行分队规则（detachments.id；物化条目 id = "det" + 该 id）
SW_DET_RULE_IDS = ("000009850", "000010260", "000010264", "000010268",
                   "000010657", "000010658", "000010659",
                   "fp11e-sw-legends-det", "fp11e-sw-fang-det")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


@pytest.fixture(scope="module")
def raw_payload():
    return json.loads(PAYLOAD.read_text(encoding="utf-8"))


def _melee(ws=4, s=4, ap=0, d=1, name="frost blade"):
    return WeaponProfile(name_zh=None, name_en=name, range="Melee",
                         attacks=DiceExpr(k=1), bs_ws=ws, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _gun(bs=4, s=4, ap=0, d=1, name="bolt rifle"):
    return WeaponProfile(name_zh=None, name_en=name, range='24"',
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=s, ap=ap,
                         damage=DiceExpr(k=d), effects=(), count=1)


def _attacker(*weapons):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=tuple(weapons))


def _target(t=4, sv=7, models=5, w=1, invuln=None, keywords=frozenset(),
            effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=w, oc=1,
                         keywords=keywords, effects=tuple(effects))


_COVER = Effect(phase="save", op="cover", params=(), condition=(), source="cover")


def _entry(entries, row_id):
    return next(e for e in entries if e.row_id == row_id)


def _run(atk, target, stance):
    return run_sequence(atk, target, stance, n=N, seed=42)


def _ratio(numer, denom):
    return numer.mean() / denom.mean()


# ═══ 结构与 DB 对账 ═══════════════════════════════════════════════════════

class TestPayloadShape:
    def test_counts(self, entries):
        # 9 分队规则 + 33 战略 + 22 增强 = 64（5 encoded / 12 partial / 47 not_modeled）
        assert len(entries) == 64
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"encoded": 5, "partial": 12, "not_modeled": 47}
        by_table = {}
        for e in entries:
            by_table[e.table] = by_table.get(e.table, 0) + 1
        assert by_table == {"abilities": 9, "stratagems": 33, "enhancements": 22}

    def test_faction_is_sm_subfaction(self, entries):
        assert all(e.faction == "SM" for e in entries)

    def test_every_entry_belongs_to_a_space_wolves_detachment(self, entries):
        # 战团载荷按分队划界（无独立 faction 行）——不许混入其他战团的分队
        assert {e.detachment for e in entries} == set(SW_DETACHMENTS)

    def test_partial_entries_all_have_notes_and_fingerprint(self, entries):
        for e in entries:
            if e.status == "partial":
                assert e.effects and e.not_modeled_notes_zh, e.row_id
                assert e.provenance.get("text_sha256"), e.row_id

    def test_not_modeled_have_reason(self, entries):
        for e in entries:
            if e.status == "not_modeled":
                assert not e.effects and e.not_modeled_notes_zh, e.row_id

    def test_no_new_toggles_introduced(self, entries):
        # 零新态势开关（沿 PR9-17 约定）：只用既有注册开关
        used = {t for e in entries for t in e.requires_toggles}
        assert used <= {"bearer_leading", "defender_bearer_leading"}

    def test_detachment_rules_all_materialized(self, raw_payload):
        mat = {e["id"]: e.get("materialize") for e in raw_payload["entries"]
               if e["table"] == "abilities"}
        assert len(mat) == 9
        for row_id, m in mat.items():
            assert m == {"from_table": "detachments", "from_id": row_id[3:],
                         "from_column": "rule_text"}, row_id

    def test_target_side_entries(self, entries):
        target_ids = {e.row_id for e in entries if e.side == "target"}
        assert target_ids == {
            "fp11e-sw-fenris-s1", "fp11e-sw-fenris-s3",   # 狼图腾 / 界隙潜行
            "000010266006", "000010661002", "000010262004",  # 英勇决意 / 预见之敌 / 压倒性猛攻
            "000010269005",                                # 屠兽者头盔
            "fp11e-sw-legends-e2", "000010261003",         # 凶悍表率 / 芬里斯之韧
        }


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        q = ("SELECT id FROM stratagems WHERE faction='SM' AND detachment IN (%s) "
             "AND COALESCE(fp_status, '') != 'removed_11e'"
             % ",".join("?" * len(SW_DETACHMENTS)))
        active = {r[0] for r in con.execute(q, SW_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        q = ("SELECT id FROM enhancements WHERE faction_id='SM' "
             "AND detachment_name IN (%s) "
             "AND COALESCE(fp_status, '') != 'removed_11e'"
             % ",".join("?" * len(SW_DETACHMENTS)))
        active = {r[0] for r in con.execute(q, SW_DETACHMENTS)}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_detachment_rules_materialized(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == {f"det{d}" for d in SW_DET_RULE_IDS}

    def test_fingerprints_match_db(self, entries):
        from db_compile.dsl_apply import _fingerprint
        cols = {"stratagems": "text_zh", "enhancements": "description"}
        con = self._db()
        for e in entries:
            if not e.effects:
                continue
            if e.table == "abilities":
                src = con.execute(
                    "SELECT rule_text FROM detachments WHERE id=?",
                    (e.row_id[3:],)).fetchone()
            else:
                src = con.execute(
                    f"SELECT {cols[e.table]} FROM {e.table} WHERE id=?",
                    (e.row_id,)).fetchone()
            assert src is not None, e.row_id
            assert _fingerprint(src[0]) == e.provenance["text_sha256"], e.row_id
        con.close()


# ═══ 真源 payload 引擎级差分（攻方向）═══════════════════════════════════════

class TestAttackerFromPayload:
    def test_legendary_slayers_lethal_gated_by_keyword_not_by_phase(self, entries):
        # 传奇屠戮者：对 CHARACTER/MONSTER/VEHICLE 目标 [LETHAL HITS]。
        # WS4 S4 vs T4：暴击命中 1/6 自动致伤 + 非暴击命中 2/6 × 致伤 1/2 = 1/3；
        # 无关键词目标维持 1/2 × 1/2 = 1/4
        ls = _entry(entries, "det000010268")
        atk, _, _ = inject_attacker(_attacker(_melee()), [ls], frozenset())
        r_mon = _run(atk, _target(keywords=frozenset({"monster"})),
                     Stance(phase="melee"))
        assert _ratio(r_mon.wounds, r_mon.attacks) == pytest.approx(1 / 3, abs=0.02)
        r_plain = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(r_plain.wounds, r_plain.attacks) == pytest.approx(1 / 4, abs=0.02)

    def test_legendary_slayers_also_applies_to_shooting(self, entries):
        # 原文为「makes an attack」不分相位——不许加相位门（加门=欠建模）
        ls = _entry(entries, "det000010268")
        atk, _, _ = inject_attacker(_attacker(_gun()), [ls], frozenset())
        r = _run(atk, _target(keywords=frozenset({"vehicle"})),
                 Stance(phase="shooting"))
        assert _ratio(r.wounds, r.attacks) == pytest.approx(1 / 3, abs=0.02)

    def test_unbridled_ferocity_melee_only(self, entries):
        # 无羁凶性：WHEN=近战阶段 → 致伤 +1。S4 vs T4 4+（1/2）→ 3+（2/3）
        uf = _entry(entries, "000010270002")
        atk, _, _ = inject_attacker(_attacker(_melee()), [uf], frozenset())
        r = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk_s, _, _ = inject_attacker(_attacker(_gun()), [uf], frozenset())
        rs = _run(atk_s, _target(), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_eye_of_the_pack_shooting_only(self, entries):
        # 群狼之眼：WHEN=己方射击阶段 → 射击致伤 +1（与无羁凶性构成互补相位门）
        ep = _entry(entries, "000010661006")
        atk, _, _ = inject_attacker(_attacker(_gun()), [ep], frozenset())
        r = _run(atk, _target(), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee()), [ep], frozenset())
        rm = _run(atk_m, _target(), Stance(phase="melee"))
        assert _ratio(rm.wounds, rm.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_inspiring_presence_lethal_melee_only(self, entries):
        # 鼓舞临在：近战武器 [LETHAL HITS]（1/3）；射击阶段不注入（1/4）
        ip = _entry(entries, "000010266002")
        atk, _, _ = inject_attacker(_attacker(_melee()), [ip], frozenset())
        r = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(r.wounds, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        atk_s, _, _ = inject_attacker(_attacker(_gun()), [ip], frozenset())
        rs = _run(atk_s, _target(), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.attacks) == pytest.approx(1 / 4, abs=0.02)

    def test_champions_guidance_reroll_in_both_phases(self, entries):
        # 勇士指引：WHEN=射击或近战二选一 → 条件留空，两相位都重骰失败命中骰
        # 命中 1/2 → 1/2 + 1/2×1/2 = 3/4
        cg = _entry(entries, "000010266003")
        atk_s, _, _ = inject_attacker(_attacker(_gun()), [cg], frozenset())
        rs = _run(atk_s, _target(), Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(3 / 4, abs=0.02)
        atk_m, _, _ = inject_attacker(_attacker(_melee()), [cg], frozenset())
        rm = _run(atk_m, _target(), Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(3 / 4, abs=0.02)

    def test_giant_amongst_giants_needs_bearer_toggle(self, entries):
        # 巨人中的巨人：携带者近战 S+1（+2 W 无通道）。开关关 → 披露不注入
        gg = _entry(entries, "fp11e-sw-fenris-e1")
        _, _, notes = inject_attacker(_attacker(_melee()), [gg], frozenset())
        assert any("bearer_leading" in n for n in notes)
        # 开关开：S4 vs T4 4+（1/2）→ S5>T4 3+（2/3）
        atk, _, _ = inject_attacker(_attacker(_melee()), [gg],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 射击阶段不生效（phase_melee 门）
        atk_s, _, _ = inject_attacker(_attacker(_gun()), [gg],
                                      frozenset({"bearer_leading"}))
        rs = _run(atk_s, _target(), Stance(phase="shooting"))
        assert _ratio(rs.wounds, rs.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_braggarts_steel_s_plus_two_is_characteristic_channel(self, entries):
        # 夸口之钢：近战 S+2 走特征值通道。S4 vs T6 5+（1/3）→ S6=T6 4+（1/2）
        bs = _entry(entries, "000010265002")
        atk, _, _ = inject_attacker(_attacker(_melee()), [bs],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=6), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)
        base = _run(_attacker(_melee()), _target(t=6), Stance(phase="melee"))
        assert _ratio(base.wounds, base.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_skjalds_foretelling_lance_only_when_charging(self, entries):
        # 吟游者的预言 [LANCE]：仅冲锋回合近战致伤 +1（melee_charging 复合门）
        sf = _entry(entries, "000010660005")
        atk, _, _ = inject_attacker(_attacker(_melee()), [sf],
                                    frozenset({"bearer_leading"}))
        r_charge = _run(atk, _target(), Stance(phase="melee", charging=True))
        assert _ratio(r_charge.wounds, r_charge.hits) == pytest.approx(2 / 3, abs=0.02)
        r_still = _run(atk, _target(), Stance(phase="melee"))
        assert _ratio(r_still.wounds, r_still.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_feral_rage_charge_bonus_stacks(self, entries):
        # 野性暴怒：近战 A+1；冲锋后再 +1（两条 attacks/modify 在引擎侧累加）
        fr = _entry(entries, "000010261005")
        atk, _, _ = inject_attacker(_attacker(_melee()), [fr],
                                    frozenset({"bearer_leading"}))
        r_still = _run(atk, _target(), Stance(phase="melee"))
        assert r_still.attacks.mean() == pytest.approx(2.0, abs=0.01)
        r_charge = _run(atk, _target(), Stance(phase="melee", charging=True))
        assert r_charge.attacks.mean() == pytest.approx(3.0, abs=0.01)

    def test_eye_of_the_hunter_shooting_ap_and_ignores_cover(self, entries):
        # 猎手之眼：远程 AP 改善 1 + [IGNORES COVER]（均为射击门）
        eh = _entry(entries, "fp11e-sw-fang-e1")
        atk, _, _ = inject_attacker(_attacker(_gun()), [eh],
                                    frozenset({"bearer_leading"}))
        # AP0→AP-1 打 Sv4（4+→5+，失败 1/2→2/3）
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        # [IGNORES COVER]：掩体目标 BS4 命中 1/3 → 1/2
        cover_tgt = _target(effects=(_COVER,))
        base = _run(_attacker(_gun()), cover_tgt, Stance(phase="shooting"))
        rc = _run(atk, cover_tgt, Stance(phase="shooting"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(rc.hits, rc.attacks) == pytest.approx(1 / 2, abs=0.02)
        # 近战阶段不注入（两条效果均带 phase_shooting 门）
        atk_m, _, _ = inject_attacker(_attacker(_melee()), [eh],
                                      frozenset({"bearer_leading"}))
        rm = _run(atk_m, _target(sv=4), Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_elders_guidance_melee_ap(self, entries):
        # 长者指引：所领导 BLOOD CLAWS 单位近战 AP 改善 1（AP0→AP-1 打 Sv4）
        eg = _entry(entries, "000010269004")
        atk, _, _ = inject_attacker(_attacker(_melee()), [eg],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(sv=4), Stance(phase="melee"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)


# ═══ 真源 payload 引擎级差分（守方向）═══════════════════════════════════════

class TestDefensiveFromPayload:
    def test_the_foe_foreseen_ap_worsen_both_phases(self, entries):
        # 预见之敌：被攻 AP 恶化 1（WHEN 含射击与近战 → 无相位门）
        ff = _entry(entries, "000010661002")
        for phase, weapon in (("shooting", _gun(ap=-1)), ("melee", _melee(ap=-1))):
            base = _run(_attacker(weapon), _target(sv=4), Stance(phase=phase))
            tgt, _, _ = inject_target(_target(sv=4), [ff], frozenset())
            r = _run(_attacker(weapon), tgt, Stance(phase=phase))
            assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
            assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_heroic_resolve_damage_reduction_shooting_only(self, entries):
        # 英勇决意：WHEN 仅敌方射击阶段 → 被射击伤害 -1；近战阶段不生效
        hr = _entry(entries, "000010266006")
        tgt, _, _ = inject_target(_target(w=3), [hr], frozenset())
        r = _run(_attacker(_gun(d=2)), tgt, Stance(phase="shooting"))
        assert _ratio(r.damage, r.unsaved) == pytest.approx(1.0, abs=0.03)
        base = _run(_attacker(_gun(d=2)), _target(w=3), Stance(phase="shooting"))
        assert _ratio(base.damage, base.unsaved) == pytest.approx(2.0, abs=0.03)
        rm = _run(_attacker(_melee(d=2)), tgt, Stance(phase="melee"))
        assert _ratio(rm.damage, rm.unsaved) == pytest.approx(2.0, abs=0.03)

    def test_overwhelming_onslaught_hit_penalty_melee_only(self, entries):
        # 压倒性猛攻：WHEN=近战阶段 → 攻击本单位命中 -1（WS4 1/2 → 1/3）；射击不生效
        oo = _entry(entries, "000010262004")
        tgt, _, _ = inject_target(_target(), [oo], frozenset())
        r = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        rs = _run(_attacker(_gun()), tgt, Stance(phase="shooting"))
        assert _ratio(rs.hits, rs.attacks) == pytest.approx(1 / 2, abs=0.02)

    def test_fierce_example_t_improve(self, entries):
        # 凶悍表率：携带者单位 T+1（T4→T5：S4 由 4+ 降到 5+）
        fe = _entry(entries, "fp11e-sw-legends-e2")
        _, _, notes = inject_target(_target(), [fe], frozenset())
        assert any("defender_bearer_leading" in n for n in notes)
        tgt, _, _ = inject_target(_target(), [fe],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_gun()), tgt, Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 3, abs=0.02)

    def test_fenrisian_grit_fnp(self, entries):
        # 芬里斯之韧：FNP 4+ → 每点伤害半数被无视
        fg = _entry(entries, "000010261003")
        tgt, _, _ = inject_target(_target(), [fg],
                                  frozenset({"defender_bearer_leading"}))
        r = _run(_attacker(_gun()), tgt, Stance(phase="shooting"))
        assert _ratio(r.damage, r.unsaved) == pytest.approx(0.5, abs=0.03)

    def test_stalk_between_worlds_stealth_shooting_only(self, entries):
        # 界隙潜行：本单位获 Stealth（11 版=掩体收益，仅射击）→ BS4 命中 1/2 → 1/3
        sb = _entry(entries, "fp11e-sw-fenris-s3")
        tgt, _, _ = inject_target(_target(), [sb], frozenset())
        r = _run(_attacker(_gun()), tgt, Stance(phase="shooting"))
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 3, abs=0.02)
        rm = _run(_attacker(_melee()), tgt, Stance(phase="melee"))
        assert _ratio(rm.hits, rm.attacks) == pytest.approx(1 / 2, abs=0.02)
