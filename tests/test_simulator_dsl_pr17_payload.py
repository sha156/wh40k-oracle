# tests/test_simulator_dsl_pr17_payload.py
"""P7-PR17 死亡守望（Deathwatch）编码落账：军规 Kill Teams + 分队规则 Mission Tactics
+ 6 战略 + 4 增强 = 12（0 encoded / 4 partial / 8 not_modeled）——零新引擎通道、零新开关。

死亡守望 11 版为 ADEPTUS ASTARTES 战团，内容挂 faction='SM'、分队 Black Spear Task Force
（军规=Kill Teams id 000009792、分队规则=Mission Tactics id 000008521）。旧十版 Agents of
the Imperium（AoI）为审判庭内容，不在本阵营范围。

覆盖（spec 七-1 双验范式，手算期望值写在断言旁）：
  · DB 对账：Black Spear 全部活跃 stratagems/enhancements 有 payload 条目、军规+分队规则
    两条 abilities 全覆盖；带 effects 条目指纹全对
  · 三态计数：0 encoded / 4 partial / 8 not_modeled（SM 战团气质=移动/元规则多，可编率低）
  · 真源 payload 引擎级差分：窃密之刃近战 S+1/D+1/AP+1（需 bearer_leading 开关）/
    克拉肯弹射击 AP 改善（近战不生效）/ 龙焰弹 [无视掩体] 仅射击 / 傲慢之甲守方 AP 恶化
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
PAYLOAD = Path("dsl_payloads/deathwatch.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

DW_ARMY_ABILITY_IDS = ("000009792", "000008521")   # Kill Teams（军规）+ Mission Tactics（分队规则）
BLACK_SPEAR = "Black Spear Task Force"


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
        # 2 abilities + 6 战略 + 4 增强 = 12（0 encoded / 4 partial / 8 not_modeled）
        assert len(entries) == 12
        by = {}
        for e in entries:
            by[e.status] = by.get(e.status, 0) + 1
        assert by == {"partial": 4, "not_modeled": 8}

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

    def test_army_rule_is_army_level(self, entries):
        # Kill Teams 为军规——detachment 为 None（军队级恒入选）
        km = _entry(entries, "000009792")
        assert km.detachment is None and km.side == "target"

    def test_target_side_entries(self, entries):
        target_ids = {e.row_id for e in entries if e.side == "target"}
        assert target_ids == {"000009792", "000008523002"}


@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_black_spear_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE detachment=? "
            "AND COALESCE(fp_status, '') != 'removed_11e'", (BLACK_SPEAR,))}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_active_black_spear_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE detachment_name=? "
            "AND COALESCE(fp_status, '') != 'removed_11e'", (BLACK_SPEAR,))}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active

    def test_army_and_detachment_abilities_covered(self, entries):
        covered = {e.row_id for e in entries if e.table == "abilities"}
        assert covered == set(DW_ARMY_ABILITY_IDS)

    def test_fingerprints_match_db(self, entries):
        from db_compile.dsl_apply import _fingerprint
        cols = {"abilities": "text_zh", "stratagems": "text_zh",
                "enhancements": "description"}
        con = self._db()
        for e in entries:
            if not e.effects:
                continue
            src = con.execute(
                f"SELECT {cols[e.table]} FROM {e.table} WHERE id=?",
                (e.row_id,)).fetchone()
            assert src is not None, e.row_id
            assert _fingerprint(src[0]) == e.provenance["text_sha256"], e.row_id
        con.close()


# ═══ 真源 payload 引擎级差分 ═══════════════════════════════════════════════

class TestAttackerFromPayload:
    def test_thief_of_secrets_melee_buffs_gated(self, entries):
        # 窃密之刃：近战 +1 S / +1 D / AP 改善1，需 bearer_leading 开关
        th = _entry(entries, "000008522002")
        # 开关关：不注入并披露
        _, _, notes = inject_attacker(_attacker(_melee()), [th], frozenset())
        assert any("bearer_leading" in n for n in notes)
        # 开关开：S4 vs T4 4+（1/2）→ S5>T4 3+（2/3）
        atk, _, _ = inject_attacker(_attacker(_melee(s=4, ap=0, d=1)), [th],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4, sv=7, w=3), Stance(phase="melee"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(2 / 3, abs=0.02)
        # 每未保存伤害 D1→D2（w=3 目标不封顶）
        assert _ratio(r.damage, r.unsaved) == pytest.approx(2.0, abs=0.03)
        # AP 改善1：AP0→AP-1 打 Sv4（4+→5+，失败 1/2→2/3）
        atk_ap, _, _ = inject_attacker(_attacker(_melee(s=4, ap=0)), [th],
                                       frozenset({"bearer_leading"}))
        rap = _run(atk_ap, _target(t=4, sv=4, w=3), Stance(phase="melee"))
        assert _ratio(rap.unsaved, rap.wounds) == pytest.approx(2 / 3, abs=0.02)

    def test_thief_of_secrets_shooting_unaffected(self, entries):
        # phase_melee 门：射击阶段远程武器不受影响（S4 vs T4 仍 4+）
        th = _entry(entries, "000008522002")
        atk, _, _ = inject_attacker(_attacker(_gun(s=4)), [th],
                                    frozenset({"bearer_leading"}))
        r = _run(atk, _target(t=4), Stance(phase="shooting"))
        assert _ratio(r.wounds, r.hits) == pytest.approx(1 / 2, abs=0.02)

    def test_kraken_rounds_shooting_ap(self, entries):
        # 克拉肯弹：射击远程武器 AP 改善1。AP0 打 Sv4（4+，1/2 失败）→ AP-1（5+，2/3）
        kr = _entry(entries, "000008523005")
        atk, _, _ = inject_attacker(_attacker(_gun(ap=0)), [kr], frozenset())
        r = _run(atk, _target(sv=4), Stance(phase="shooting"))
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(2 / 3, abs=0.02)
        # 近战阶段不注入（phase_shooting 门）→ 近战武器打 Sv4 仍 1/2
        atkm, _, _ = inject_attacker(_attacker(_melee(ap=0)), [kr], frozenset())
        rm = _run(atkm, _target(sv=4), Stance(phase="melee"))
        assert _ratio(rm.unsaved, rm.wounds) == pytest.approx(1 / 2, abs=0.02)

    def test_dragonfire_rounds_ignores_cover_shooting(self, entries):
        # 龙焰弹：远程武器 [无视掩体]。BS4 掩体命中-1（1/3）→ 无视掩体（1/2）
        df = _entry(entries, "000008523006")
        cover_tgt = _target(t=4, effects=(_COVER,))
        base = _run(_attacker(_gun(bs=4)), cover_tgt, Stance(phase="shooting"))
        atk, _, _ = inject_attacker(_attacker(_gun(bs=4)), [df], frozenset())
        r = _run(atk, cover_tgt, Stance(phase="shooting"))
        assert _ratio(base.hits, base.attacks) == pytest.approx(1 / 3, abs=0.02)
        assert _ratio(r.hits, r.attacks) == pytest.approx(1 / 2, abs=0.02)


class TestDefensiveFromPayload:
    def test_armour_of_contempt_ap_worsen(self, entries):
        # 傲慢之甲：被攻 AP 恶化1（守方向，两相位）。AP-1 打 Sv4（5+，2/3 失败）
        # → AP0（4+，1/2 失败）
        ac = _entry(entries, "000008523002")
        base = _run(_attacker(_gun(ap=-1)), _target(sv=4), Stance(phase="shooting"))
        tgt, _, _ = inject_target(_target(sv=4), [ac], frozenset())
        r = _run(_attacker(_gun(ap=-1)), tgt, Stance(phase="shooting"))
        assert _ratio(base.unsaved, base.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r.unsaved, r.wounds) == pytest.approx(1 / 2, abs=0.02)
        # 近战同样生效（condition 为空，两相位）
        base_m = _run(_attacker(_melee(ap=-1)), _target(sv=4), Stance(phase="melee"))
        tgt_m, _, _ = inject_target(_target(sv=4), [ac], frozenset())
        r_m = _run(_attacker(_melee(ap=-1)), tgt_m, Stance(phase="melee"))
        assert _ratio(base_m.unsaved, base_m.wounds) == pytest.approx(2 / 3, abs=0.02)
        assert _ratio(r_m.unsaved, r_m.wounds) == pytest.approx(1 / 2, abs=0.02)
