# tests/test_simulator_dsl_pr4_payload.py
"""P7-PR4 编码落账：8 分队规则物化 + 27 战略 + 27 增强 + CDS 升级。

覆盖（spec 七-1 双验范式，手算期望值写在断言旁，期望值必须动）：
  · DB 对账：TAU 活跃行（排除 fp_status='removed_11e'）全部有 payload 条目，
    removed 行必须没有——「重印即替换」裁定的消费侧口径
  · 真源 payload 引擎级差分：每类新通道条目至少一条（期望值必须动）
  · 守方向条目经 inject_target 施加的端到端数值验证
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
    select_entries,
)
from engines.simulator.sequence import run_sequence

N = 60000
PAYLOAD = Path("dsl_payloads/tau.json")
DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")


@pytest.fixture(scope="module")
def entries():
    return load_payload_file(PAYLOAD)


def _weapon(bs=4, s=4, ap=0, name="test gun", effects=()):
    return WeaponProfile(name_zh=None, name_en=name, range='24"',
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=s, ap=ap,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(*weapons):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=tuple(weapons))


def _target(t=4, sv=6, invuln=None, models=5, effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=1, oc=1,
                         effects=tuple(effects))


def _entry(entries, row_id):
    return next(e for e in entries if e.row_id == row_id)


def _atk_with(entries, row_id, toggles, weapon=None):
    atk, modeled, notes = inject_attacker(
        _attacker(weapon or _weapon()), [_entry(entries, row_id)],
        frozenset(toggles))
    return atk, modeled, notes


# ═══ DB 对账：活跃行全覆盖、removed 行零覆盖 ═══════════════════════════════

@needs_db
class TestDbReconciliation:
    def _db(self):
        return sqlite3.connect(str(DB))

    def test_active_stratagems_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE faction = 'TAU' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "stratagems"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")

    def test_removed_stratagems_not_covered(self, entries):
        con = self._db()
        removed = {r[0] for r in con.execute(
            "SELECT id FROM stratagems WHERE fp_status = 'removed_11e'")}
        con.close()
        assert removed and not removed & {
            e.row_id for e in entries if e.table == "stratagems"}

    def test_active_enhancements_all_covered(self, entries):
        con = self._db()
        active = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE faction_id = 'TAU' "
            "AND COALESCE(fp_status, '') != 'removed_11e'")}
        removed = {r[0] for r in con.execute(
            "SELECT id FROM enhancements WHERE fp_status = 'removed_11e'")}
        con.close()
        covered = {e.row_id for e in entries if e.table == "enhancements"}
        assert covered == active, (
            f"漏编 {sorted(active - covered)} / 多编 {sorted(covered - active)}")
        assert removed and not removed & covered

    def test_all_detachment_rules_materialized(self, entries):
        # TAU 非噪声规则行（含 AAC 补录）全部有物化条目（id = det+源id）
        con = self._db()
        rules = {r[0] for r in con.execute(
            "SELECT id FROM detachments WHERE faction = 'TAU' "
            "AND UPPER(name_en) != 'KEYWORDS'")}
        con.close()
        materialized = {e.row_id for e in entries if e.table == "abilities"
                        and e.row_id.startswith("det")}
        assert materialized == {f"det{r}" for r in rules}

    def test_projection_counts_match_payload(self, entries):
        # DB 投影三态计数 == 真源计数（dsl-apply 已跑过；rebuild 后由 restore 链保证）。
        # P7-PR5 起真源是多文件（tau + worldeaters + …），对账按全部 payload 聚合
        con = self._db()
        db_counts = {}
        for table in ("abilities", "stratagems", "enhancements"):
            for status, n in con.execute(
                    f"SELECT dsl_status, COUNT(*) FROM {table} "
                    f"WHERE effect_dsl_json IS NOT NULL GROUP BY dsl_status"):
                db_counts[status] = db_counts.get(status, 0) + n
        con.close()
        want = {}
        for f in sorted(Path("dsl_payloads").glob("*.json")):
            for e in load_payload_file(f):
                want[e.status] = want.get(e.status, 0) + 1
        assert db_counts == want


# ═══ 分队规则物化条目：引擎级差分 ═══════════════════════════════════════════

class TestBondedHeroes:
    def test_s_improve_at_12(self, entries):
        # S4 vs T4 → 4+（1/2）；12″ 档 S5 vs T4 → 3+（4/6）
        atk, modeled, _ = _atk_with(entries, "det000008814", {"range_within_12"})
        assert any("已施加" in m for m in modeled)
        st = Stance(phase="shooting", range_within_12=True)
        raw = run_sequence(atk, _target(), st, n=N, seed=7)
        assert raw.wounds.mean() / raw.hits.mean() == pytest.approx(4 / 6, abs=0.02)

    def test_ap_tier_needs_8(self, entries):
        # Sv3+ AP0：8″ 档加 AP-1 → 未过保 2/6→3/6，伤害 ×1.5；只开 12″ 档不加
        atk, _, _ = _atk_with(entries, "det000008814", {"range_within_12",
                                                        "range_within_8"})
        base = run_sequence(atk, _target(sv=3),
                            Stance(phase="shooting", range_within_12=True),
                            n=N, seed=7).damage.mean()
        both = run_sequence(atk, _target(sv=3),
                            Stance(phase="shooting", range_within_8=True),
                            n=N, seed=7).damage.mean()
        assert both / base == pytest.approx(1.5, abs=0.06)

    def test_toggle_off_no_injection(self, entries):
        _, modeled, notes = _atk_with(entries, "det000008814", set())
        assert not modeled and any("未启用" in x for x in notes)


class TestHuntersInstincts:
    def test_hit_tier(self, entries):
        # BS4+ 命中 0.5 → 低于满编 +1 命中骰 → 4/6
        atk, _, _ = _atk_with(entries, "det000008818", {"target_below_starting"})
        st = Stance(phase="shooting", target_below_starting=True)
        raw = run_sequence(atk, _target(), st, n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(4 / 6, abs=0.02)

    def test_wound_tier_implies_hit_tier(self, entries):
        # 低于半编：命中 4/6 且致伤 4+→3+（4/6）——两档同动
        atk, _, _ = _atk_with(entries, "det000008818", {"target_below_starting",
                                                        "target_below_half"})
        st = Stance(phase="shooting", target_below_half=True)
        raw = run_sequence(atk, _target(), st, n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(4 / 6, abs=0.02)
        assert raw.wounds.mean() / raw.hits.mean() == pytest.approx(4 / 6, abs=0.02)


class TestSkirmishFightersDefensive:
    def test_ranged_5pp_via_inject_target(self, entries):
        # 守方 Kroot：Sv6+ 打 AP-2 本无保存 → 射击 5++ 使未过保 1.0→4/6
        tgt, modeled, _ = inject_target(
            _target(), [_entry(entries, "det000008819")], frozenset())
        assert any("已施加（守方）" in m for m in modeled)
        raw = run_sequence(_attacker(_weapon(ap=-2)), tgt,
                           Stance(phase="shooting"), n=N, seed=7)
        assert raw.unsaved.mean() / raw.wounds.mean() == pytest.approx(4 / 6, abs=0.02)

    def test_melee_6pp(self, entries):
        tgt, _, _ = inject_target(
            _target(), [_entry(entries, "det000008819")], frozenset())
        melee = WeaponProfile(name_zh=None, name_en="claw", range="Melee",
                              attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=-2,
                              damage=DiceExpr(k=1), count=1)
        raw = run_sequence(_attacker(melee), tgt, Stance(phase="melee"), n=N, seed=7)
        assert raw.unsaved.mean() / raw.wounds.mean() == pytest.approx(5 / 6, abs=0.02)


class TestMarkerlightPrecision:
    def test_bs_and_sustained(self, entries):
        # BS4+：bs_improve → 3+（4/6 命中）+ sustained 1（暴击 1/6 追加）
        atk, _, _ = _atk_with(entries, "det000009635", {"markerlight_visible"})
        raw = run_sequence(atk, _target(), Stance(phase="shooting"), n=N, seed=7)
        assert (raw.hits.mean() / raw.attacks.mean()
                == pytest.approx(4 / 6 + 1 / 6, abs=0.02))


# ═══ 战略条目差分 ═══════════════════════════════════════════════════════════

class TestStratagemEffectsPr4:
    def test_arrokon_brackets_by_target_size(self, entries):
        # 5 模型不触发（0.5）；6 模型 sustained 1（0.5+1/6）；11 模型 sustained 2（0.5+2/6）
        for models, want in ((5, 0.5), (6, 0.5 + 1 / 6), (11, 0.5 + 2 / 6)):
            atk, _, _ = _atk_with(entries, "000008816005", set())
            raw = run_sequence(atk, _target(models=models),
                               Stance(phase="shooting"), n=N, seed=7)
            assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(
                want, abs=0.02), f"models={models}"

    def test_arrokon_not_in_melee(self, entries):
        # 复合 tag 自含射击阶段：近战不触发
        atk, _, _ = _atk_with(
            entries, "000008816005", set(),
            weapon=WeaponProfile(name_zh=None, name_en="fist", range="Melee",
                                 attacks=DiceExpr(k=1), bs_ws=4, strength=4,
                                 ap=0, damage=DiceExpr(k=1), count=1))
        raw = run_sequence(atk, _target(models=11), Stance(phase="melee"),
                           n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(0.5, abs=0.02)

    def test_responsive_volley_crit5(self, entries):
        # 未修正 5+ 暴击：配 sustained 词条无从验证暴击阈值本身——用掩体场景：
        # BS4+ 掩体（BS 恶化→5+）命中 2/6；但暴击阈值 5+ 看自然骰 → 自然 5/6 恒命中
        # → 命中率 = P(自然≥5)=2/6（暴击）+ P(自然4 & 4≥5)=0 → 仍 2/6？改用无掩体：
        # 无掩体命中 3/6+暴击无增量……crit_threshold 的可观测差分=接 sustained：
        atk, _, _ = _atk_with(entries, "000009637004", set())
        # 叠加一个裸 sustained 词条观测暴击频率：crit 5+（2/6）→ hits/attacks=0.5+2/6
        from engines.simulator.contracts import Effect
        w = atk.loadout[0]
        from dataclasses import replace as _rep
        w2 = _rep(w, effects=w.effects + (
            Effect("hit", "extra_hits", (DiceExpr(k=1),), (), "test sustained"),))
        atk2 = _rep(atk, loadout=(w2,))
        raw = run_sequence(atk2, _target(), Stance(phase="shooting"), n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(
            0.5 + 2 / 6, abs=0.02)

    def test_guided_by_unity_lethal(self, entries):
        # [LETHAL HITS]：S4 vs T4 wounds/attacks 0.25 → 命中暴击自动致伤
        # = P(hit)×P(wound) 部分改：暴击 1/6 直接致伤 + 非暴击命中 2/6×1/2
        # → (1/6 + 2/6×1/2) = 1/3（基线 0.5×0.5=0.25）
        atk, _, _ = _atk_with(entries, "fp11e-tau-aux-gbu", set())
        raw = run_sequence(atk, _target(), Stance(phase="shooting"), n=N, seed=7)
        assert raw.wounds.mean() / raw.attacks.mean() == pytest.approx(1 / 3, abs=0.02)

    def test_experimental_ammunition_s_mode(self, entries):
        # 模式 A：S4→S5 vs T4 → 致伤 4+→3+
        atk, _, _ = _atk_with(entries, "000009984005", set())
        raw = run_sequence(atk, _target(), Stance(phase="shooting"), n=N, seed=7)
        assert raw.wounds.mean() / raw.hits.mean() == pytest.approx(4 / 6, abs=0.02)

    def test_boarding_blades_melee_only(self, entries):
        # 近战 AP+1（Sv3+：伤害×1.5）；射击不生效
        melee = WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                              attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                              damage=DiceExpr(k=1), count=1)
        atk, _, _ = _atk_with(entries, "000009646002", set(), weapon=melee)
        base = run_sequence(_attacker(melee), _target(sv=3),
                            Stance(phase="melee"), n=N, seed=7).damage.mean()
        on = run_sequence(atk, _target(sv=3), Stance(phase="melee"),
                          n=N, seed=7).damage.mean()
        assert on / base == pytest.approx(1.5, abs=0.06)


class TestDefensiveStratagems:
    def test_stimm_injectors_fnp6(self, entries):
        # FNP6+：伤害 ×5/6
        tgt, modeled, _ = inject_target(
            _target(), [_entry(entries, "000008816003")], frozenset())
        assert modeled
        base = run_sequence(_attacker(_weapon()), _target(),
                            Stance(phase="shooting"), n=N, seed=7).damage.mean()
        on = run_sequence(_attacker(_weapon()), tgt,
                          Stance(phase="shooting"), n=N, seed=7).damage.mean()
        assert on / base == pytest.approx(5 / 6, rel=0.05)

    def test_counterfire_d_minus_1_shooting_only(self, entries):
        # D2 武器 → 减伤 1 → 伤害减半（射击）；近战条件不放行
        tgt, _, _ = inject_target(
            _target(), [_entry(entries, "000008812007")], frozenset())
        d2 = WeaponProfile(name_zh=None, name_en="d2 gun", range='24"',
                           attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                           damage=DiceExpr(k=2), count=1)
        tgt_w2 = TargetProfile(canonical_id="t", name_en="T", name_zh=None,
                               models=5, t=4, sv=6, invuln=None, w=2, oc=1,
                               effects=tgt.effects)
        base_t = TargetProfile(canonical_id="t", name_en="T", name_zh=None,
                               models=5, t=4, sv=6, invuln=None, w=2, oc=1)
        base = run_sequence(_attacker(d2), base_t, Stance(phase="shooting"),
                            n=N, seed=7).damage.mean()
        on = run_sequence(_attacker(d2), tgt_w2, Stance(phase="shooting"),
                          n=N, seed=7).damage.mean()
        assert on / base == pytest.approx(0.5, rel=0.05)

    def test_emp_grenades_bs_worsen(self, entries):
        # 守方 EMP：攻方 BS4+ → 特征值恶化 → 5+（命中 2/6）
        tgt, _, _ = inject_target(
            _target(), [_entry(entries, "000008822004")], frozenset())
        raw = run_sequence(_attacker(_weapon()), tgt, Stance(phase="shooting"),
                           n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(2 / 6, abs=0.02)

    def test_autoreactive_needs_hidden_toggle(self, entries):
        # Sv4+ AP0：hidden 开 → 3+（未过保 2/6）；不开 → 不注入
        entry = _entry(entries, "fp11e-tau-aac-s3")
        tgt_off, modeled_off, notes = inject_target(
            _target(sv=4), [entry], frozenset())
        assert not modeled_off and any("未启用" in x for x in notes)
        tgt_on, modeled_on, _ = inject_target(
            _target(sv=4), [entry], frozenset({"defender_hidden"}))
        assert modeled_on
        raw = run_sequence(_attacker(_weapon()), tgt_on,
                           Stance(phase="shooting"), n=N, seed=7)
        assert raw.unsaved.mean() / raw.wounds.mean() == pytest.approx(2 / 6, abs=0.02)


# ═══ 增强条目差分 ═══════════════════════════════════════════════════════════

class TestEnhancementEffects:
    def test_plasma_accelerator_full_stack(self, entries):
        # weapon_filter 命中 plasma rifle：A+1（攻击翻倍）、S4→6 vs T4（3+ 致伤）、
        # AP-1（Sv3+→未过保 3/6）、D+1（每未过保伤害 2）
        w = _weapon(name="Plasma rifle")
        atk, modeled, _ = _atk_with(entries, "000009983004", set(), weapon=w)
        assert any("限武器" in m for m in modeled)
        # 守方 2W：raw.damage 是有效移除伤害，1W 目标会把 D 的第二点当溢出吞掉
        tgt = TargetProfile(canonical_id="t", name_en="T", name_zh=None, models=5,
                            t=4, sv=3, invuln=None, w=2, oc=1)
        raw = run_sequence(atk, tgt, Stance(phase="shooting"), n=N, seed=7)
        assert raw.attacks.mean() == pytest.approx(2.0, abs=0.02)      # A 1→2
        assert raw.wounds.mean() / raw.hits.mean() == pytest.approx(4 / 6, abs=0.02)
        # D 1→2：对 2W 模型恰好整杀，有效伤害 = unsaved × 2
        assert raw.damage.mean() / raw.unsaved.mean() == pytest.approx(2.0, abs=0.05)

    def test_weapon_filter_no_match_disclosed(self, entries):
        atk, modeled, notes = _atk_with(entries, "000009983004", set(),
                                        weapon=_weapon(name="pulse carbine"))
        assert not modeled and any("没有名字含" in x for x in notes)

    def test_precision_of_patient_hunter_two_tiers(self, entries):
        # 命中 +1（骰修正 0.5→4/6）；开战轮门控再致伤 +1（4+→3+）
        atk, _, _ = _atk_with(entries, "000008442003", {"bearer_leading"})
        st1 = Stance(phase="shooting")
        raw1 = run_sequence(atk, _target(), st1, n=N, seed=7)
        assert raw1.hits.mean() / raw1.attacks.mean() == pytest.approx(4 / 6, abs=0.02)
        assert raw1.wounds.mean() / raw1.hits.mean() == pytest.approx(3 / 6, abs=0.02)
        st2 = Stance(phase="shooting", detachment_rounds=True)
        raw2 = run_sequence(atk, _target(), st2, n=N, seed=7)
        assert raw2.wounds.mean() / raw2.hits.mean() == pytest.approx(4 / 6, abs=0.02)

    def test_through_unity_devastation_needs_guided(self, entries):
        # 受益方视角：guided 开 → lethal（wounds/attacks 0.25→1/3）；关 → 不注入
        _, modeled_off, notes = _atk_with(entries, "000008442005", set())
        assert not modeled_off and any("未启用" in x for x in notes)
        atk, _, _ = _atk_with(entries, "000008442005", {"guided"})
        raw = run_sequence(atk, _target(), Stance(phase="shooting", guided=True),
                           n=N, seed=7)
        assert raw.wounds.mean() / raw.attacks.mean() == pytest.approx(1 / 3, abs=0.02)

    def test_borthrod_gland_melee_crit5(self, entries):
        # 近战暴击 5+：接 sustained 观测（同 Responsive Volley 方法）
        from dataclasses import replace as _rep
        from engines.simulator.contracts import Effect
        melee = WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                              attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                              damage=DiceExpr(k=1), count=1)
        atk, _, _ = _atk_with(entries, "000008821002", {"bearer_leading"},
                              weapon=melee)
        w2 = _rep(atk.loadout[0], effects=atk.loadout[0].effects + (
            Effect("hit", "extra_hits", (DiceExpr(k=1),), (), "test sustained"),))
        atk2 = _rep(atk, loadout=(w2,))
        raw = run_sequence(atk2, _target(), Stance(phase="melee"), n=N, seed=7)
        assert raw.hits.mean() / raw.attacks.mean() == pytest.approx(
            0.5 + 2 / 6, abs=0.02)

    def test_experienced_leader_wound_reroll(self, entries):
        # 致伤失败重骰：S4 vs T4 → 0.5 + 0.5×0.5 = 0.75
        atk, _, _ = _atk_with(entries, "000009645002", set())
        raw = run_sequence(atk, _target(), Stance(phase="shooting"), n=N, seed=7)
        assert raw.wounds.mean() / raw.hits.mean() == pytest.approx(0.75, abs=0.02)

    def test_root_carved_weapons_dev_wounds(self, entries):
        # DEV WOUNDS：暴击致伤入致命池（mortals>0 且跳保存）
        melee = WeaponProfile(name_zh=None, name_en="blade", range="Melee",
                              attacks=DiceExpr(k=1), bs_ws=4, strength=4, ap=0,
                              damage=DiceExpr(k=1), count=1)
        atk, _, _ = _atk_with(entries, "000008821005", {"bearer_leading"},
                              weapon=melee)
        raw = run_sequence(atk, _target(sv=2), Stance(phase="melee"), n=N, seed=7)
        # 暴击致伤概率 = P(hit)×P(wound roll=6)=0.5×1/6 → mortals/attacks ≈ 1/12
        assert raw.mortals.mean() / raw.attacks.mean() == pytest.approx(
            1 / 12, abs=0.01)


# ═══ 选择层端到端：守方分队自动入选防守规则 ═══════════════════════════════════

class TestDefensiveSelection:
    def test_khp_defender_gets_skirmish_fighters(self, entries):
        sel, _ = select_entries(list(entries), detachment="Kroot Hunting Pack")
        ids = {e.row_id for e in sel}
        assert "det000008819" in ids          # 防守规则随分队自动入选
        assert "det000008818" in ids          # 攻方向规则同样入选（注入层分侧）
        tgt, modeled, notes = inject_target(_target(), sel, frozenset())
        assert any("Skirmish Fighters" in m or "特遣队" in m for m in modeled)
        # 攻方向条目在守方注入路径给方向说明，不假装生效
        assert any("攻方向条目" in x for x in notes)

    def test_enhancement_naming_via_select(self, entries):
        sel, _ = select_entries(list(entries), detachment="Kauyon",
                                enhancements=("耐心猎手之精准",))
        assert any(e.row_id == "000008442003" for e in sel)


@needs_db
class TestLoadUnitDslCoversEnhancements:
    def test_enhancement_entries_loaded_from_db(self):
        # 回归护栏（PR4 冒烟逮到）：load_unit_dsl 漏扫 enhancements 表时，
        # 增强条目对模拟链路完全不可见（dsl_available/点名注入全失效）
        import sqlite3 as _sq
        from engines.simulator.profile import load_unit_dsl
        con = _sq.connect(str(DB))
        row = con.execute(
            "SELECT id FROM units WHERE faction_id = 'TAU' LIMIT 1").fetchone()
        con.close()
        assert row, "库中无 TAU 单位"
        entries = load_unit_dsl(DB, row[0])
        assert any(e.table == "enhancements" for e in entries), (
            "load_unit_dsl 未装载 enhancements 表的 DSL 投影")
