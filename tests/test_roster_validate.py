"""tests/test_roster_validate.py — 军表引擎（P6-PR1b）。

纯逻辑（unit_cost/compose_rules/contracts，脱库）+ 集成（validate 逐条规则，真库）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engines.roster import Roster, RosterUnit, validate
from engines.roster.compose_rules import (RULE_OF_THREE, datasheet_copy_limit,
                                          size_limit)
from engines.roster.contracts import ERROR, WARN, ValidationIssue, ValidationReport
from engines.roster.points import _tiers_from_points_json, total_points, unit_cost

DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="wh40k.sqlite 不存在")

# 稳定 canonical id（真库）
INTERCESSOR = "000001157"       # SM BATTLELINE：5=80 / 10=150
APOTHECARY = "000000060"        # SM CHARACTER 非 EPIC HERO
BROADSIDE = "000000433"         # Tau 非 battleline 非 character：1=75/2=150/3=240
EPIC_HERO = "000000096"         # SM Carab Culln The Risen（EPIC HERO）
DET_BASTION = "000001130"       # SM Bastion Task Force
ENH = "Eye of the Primarch"     # Bastion 合法强化


# ── 纯逻辑：点数档位 ───────────────────────────────────────────────

def test_tiers_and_unit_cost():
    pj = '{"items":[{"desc":"5 models","cost":80},{"desc":"10 models","cost":150}]}'
    assert _tiers_from_points_json(pj) == {5: 80, 10: 150}
    assert unit_cost(pj, 5) == 80
    assert unit_cost(pj, 10) == 150
    assert unit_cost(pj, 7) is None       # 档位内无 → 无法定价
    assert unit_cost(None, 5) is None
    assert unit_cost("not json", 5) is None


def test_tiers_prefer_plain_and_reject_composite():
    # 同模型数：纯档 110 优先于加价档 125（不是 last-write-wins）——评审 CRITICAL
    agent = ('{"items":[{"desc":"1 model (Assigned Agent)","cost":125},'
             '{"desc":"1 model","cost":110}]}')
    assert _tiers_from_points_json(agent) == {1: 110}
    # 复合 datasheet（无 "model" 字样）严格正则不匹配 → 空档 → 无法定价（不静默编造）
    composite = ('{"items":[{"desc":"3 Headtakers and 3 Wolves","cost":110},'
                 '{"desc":"6 Headtakers and 6 Wolves","cost":220}]}')
    assert _tiers_from_points_json(composite) == {}
    # 仅加价档、同模型数多价且无纯档 → 歧义跳过
    ambiguous = ('{"items":[{"desc":"1 model (A)","cost":110},'
                 '{"desc":"1 model (B)","cost":125}]}')
    assert _tiers_from_points_json(ambiguous) == {}


def test_compose_rules_copy_limit():
    assert datasheet_copy_limit(set()) == RULE_OF_THREE
    assert datasheet_copy_limit({"BATTLELINE"}) is None       # 豁免
    assert datasheet_copy_limit({"DEDICATED TRANSPORT"}) is None
    assert datasheet_copy_limit({"EPIC HERO"}) == 1
    assert size_limit("incursion") == 1000
    assert size_limit("strike_force") == 2000
    assert size_limit("unknown") == 2000                       # 回退


def test_report_properties():
    rep = ValidationReport(100, 2000, False, (
        ValidationIssue("a", ERROR, "x"), ValidationIssue("b", WARN, "y")))
    assert len(rep.errors) == 1 and len(rep.warnings) == 1


# ── 集成：validate 逐条规则 ───────────────────────────────────────

def _codes(rep):
    return {i.code for i in rep.issues}


@needs_db
def test_legal_roster():
    r = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True, enhancement=ENH),
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5),
    )))
    assert r.legal is True and r.errors == ()
    # Apothecary 70 + Intercessor 5-model 80 + 强化 Eye of the Primarch 10
    # ——强化点数必须计入总分（模块 3 审查 F1：曾漏计且被旧期望值 150 钉成规格）
    assert r.total_points == 160


@needs_db
def test_warlord_count_and_character():
    # 0 warlord
    r0 = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5),)))
    assert "warlord_count" in _codes(r0) and r0.legal is False
    # warlord 非 CHARACTER（Intercessor 当 warlord）
    rn = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5, is_warlord=True),)))
    assert "warlord_not_character" in _codes(rn)


@needs_db
def test_rule_of_three_and_battleline_exempt():
    # 非 battleline character x4 → 超编
    r = validate(DB, Roster("SM", DET_BASTION, "strike_force", tuple(
        [RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=(i == 0))
         for i in range(4)])))
    assert "rot_exceeded" in _codes(r)
    # battleline x5 → 豁免，无 rot
    rb = validate(DB, Roster("SM", DET_BASTION, "strike_force", tuple(
        [RosterUnit(INTERCESSOR, "Intercessor Squad", 5) for _ in range(5)] +
        [RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True)])))
    assert "rot_exceeded" not in _codes(rb)


@needs_db
def test_epic_hero_max_one():
    r = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(EPIC_HERO, "Carab Culln", 1, is_warlord=True),
        RosterUnit(EPIC_HERO, "Carab Culln", 1),
    )))
    assert "rot_exceeded" in _codes(r)      # epic hero 至多 1


@needs_db
def test_points_over_limit():
    # incursion 1000：8× Intercessor 10 模型(150) = 1200 > 1000（battleline 免 RoT）
    r = validate(DB, Roster("SM", DET_BASTION, "incursion", tuple(
        [RosterUnit(INTERCESSOR, "Intercessor Squad", 10) for _ in range(8)] +
        [RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True)])))
    assert "points_over" in _codes(r) and r.total_points > r.limit


@needs_db
def test_unit_unpriced_warn():
    # Intercessor 档位只有 5/10 模型；选 7 → 无法定价 warn（surfaced_only）
    r = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(INTERCESSOR, "Intercessor Squad", 7, is_warlord=False),
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True),
    )))
    unpriced = [i for i in r.issues if i.code == "unit_unpriced"]
    assert unpriced and unpriced[0].surfaced_only and unpriced[0].severity == WARN


@needs_db
def test_enhancement_rules():
    # 错分队强化
    rw = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True,
                   enhancement="NotARealEnhancement"),)))
    assert "enh_wrong_detachment" in _codes(rw)
    # 强化挂非 CHARACTER
    rc = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5, enhancement=ENH),
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True),
    )))
    assert "enh_not_character" in _codes(rc)
    # 重复强化
    rd = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True, enhancement=ENH),
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1, enhancement=ENH),
    )))
    assert "enh_duplicate" in _codes(rd)


@needs_db
def test_enhancement_points_push_over_limit():
    # 竞技压线场景（模块 3 审查 F1）：24×Intercessor(80)=1920 + Apothecary 70 = 1990，
    # 挂 Hero of the Chapter(20) → 2010 > 2000 必须判超分；卸下强化则合法（成对负向）。
    units = tuple(
        [RosterUnit(INTERCESSOR, "Intercessor Squad", 5) for _ in range(24)] +
        [RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True,
                    enhancement="Hero of the Chapter")])
    r = validate(DB, Roster("SM", DET_BASTION, "strike_force", units))
    assert r.total_points == 2010
    assert "points_over" in _codes(r) and r.legal is False

    bare = tuple(u if not u.enhancement else
                 RosterUnit(u.canonical_id, u.name_en, u.models,
                            is_warlord=u.is_warlord)
                 for u in units)
    rb = validate(DB, Roster("SM", DET_BASTION, "strike_force", bare))
    assert rb.total_points == 1990 and rb.legal is True


@needs_db
def test_enhancement_unpriced_surfaced_not_counted():
    # 强化点数拿不到（错分队名/无数据）→ enh_unpriced warn 且不计入总分，不静默计 0
    r = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True,
                   enhancement="NotARealEnhancement"),)))
    unp = [i for i in r.issues if i.code == "enh_unpriced"]
    assert unp and unp[0].surfaced_only and unp[0].severity == WARN
    assert r.total_points == 70             # 只有 Apothecary，本体点数不受影响


@needs_db
def test_unknown_size_surfaced_not_silent():
    # 未知规模档 → warn 显式披露（回退 2000 但不静默；报错消息不撒谎）
    r = validate(DB, Roster("SM", DET_BASTION, "Onslaught", (  # 大小写错
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5, is_warlord=False),)))
    unk = [i for i in r.issues if i.code == "unknown_size"]
    assert unk and unk[0].surfaced_only and unk[0].severity == WARN
    # 直接断言回退文案不撒谎（模块 8 F3：原 `or total<=2000` 逃生门使断言恒真）
    assert "strike_force 2000" in unk[0].message


@needs_db
def test_unknown_unit_honest_degradation():
    # gnhf 审查模块 3 F3：过期 id（DB 重建/单位下线 → localStorage 旧军表）不许编造
    # 「非 CHARACTER」「模型数不在档位内」等事实性断言——只说系统知道的事实
    r = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit("999999999", "Ghost Unit", 5, is_warlord=True,
                   enhancement=ENH),
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1),
    )))
    codes = _codes(r)
    nf = [i for i in r.issues if i.code == "unit_not_found"]
    assert nf and nf[0].surfaced_only and nf[0].severity == WARN
    assert "999999999" in nf[0].message
    # 编造类断言全部不出现：warlord 资格 / 档位归因 / 强化 CHARACTER 资格
    assert "warlord_not_character" not in codes
    assert "unit_unpriced" not in codes
    assert "enh_not_character" not in codes


@needs_db
def test_unknown_unit_does_not_suppress_known_unit_checks():
    # 成对负向：库内单位的断言不因军表里混入未知单位而被跳过
    r = validate(DB, Roster("SM", DET_BASTION, "strike_force", (
        RosterUnit("999999999", "Ghost Unit", 5),
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5, is_warlord=True),
    )))
    assert "warlord_not_character" in _codes(r)      # Intercessor 仍被真校验
    assert "unit_not_found" in _codes(r)


@needs_db
def test_rot_exempt_over_three_surfaced_not_silent():
    # gnhf 审查模块 3 F2：battleline 超 3 份不再静默豁免——11 版豁免上限未查证
    # （十版为 6 份），设计文档裁决「不确定的 warn 不 error」
    rb = validate(DB, Roster("SM", DET_BASTION, "strike_force", tuple(
        [RosterUnit(INTERCESSOR, "Intercessor Squad", 5) for _ in range(5)] +
        [RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True)])))
    ex = [i for i in rb.issues if i.code == "rot_exempt_uncapped"]
    assert ex and ex[0].surfaced_only and ex[0].severity == WARN
    assert rb.legal is True                          # warn 不判死刑
    # 成对负向：3 份以内不发（豁免未生效，无需披露）
    r3 = validate(DB, Roster("SM", DET_BASTION, "strike_force", tuple(
        [RosterUnit(INTERCESSOR, "Intercessor Squad", 5) for _ in range(3)] +
        [RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True)])))
    assert "rot_exempt_uncapped" not in _codes(r3)


@needs_db
def test_enhancement_unverified_without_detachment():
    # 无 detachment → 强化归属未校验（surfaced_only，不假通过）
    r = validate(DB, Roster("SM", None, "strike_force", (
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1, is_warlord=True, enhancement=ENH),)))
    unv = [i for i in r.issues if i.code == "enh_unverified"]
    assert unv and unv[0].surfaced_only is True
