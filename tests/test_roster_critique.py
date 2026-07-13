"""tests/test_roster_critique.py — 军表点评引擎（P6-PR2）。

纯逻辑（典型目标/summary）+ 集成（真库装配→模拟→性价比，武器角色区分）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engines.roster import Roster, RosterUnit
from engines.roster.critique import (CritiqueReport, TargetScore, UnitAssessment,
                                     _archetypes, _build_summary, critique)

DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="wh40k.sqlite 不存在")

INTERCESSOR = "000001157"
BROADSIDE = "000000433"
APOTHECARY = "000000060"
DET = "000001130"


# ── 纯逻辑 ────────────────────────────────────────────────────────

def test_archetypes_shape():
    arch = _archetypes()
    keys = {k for k, _, _ in arch}
    assert keys == {"geq", "meq", "teq", "veh"}
    veh = next(t for k, _, t in arch if k == "veh")
    assert veh.t == 10 and "VEHICLE" in veh.keywords and veh.w == 12


def test_summary_flags_unassessed_and_low_antitank():
    # 一个已评估（对 VEH 每100点 0.7，偏低）+ 一个未评估
    assessed = UnitAssessment(
        "x", "WeakGun", 80, assessed=True, phase="shooting",
        scores=(TargetScore("veh", "载具(VEH)", 0.57, 0.71),))
    unassessed = UnitAssessment("y", "NoLoad", 50, assessed=False, note="需装配")
    summary = _build_summary((assessed, unassessed))
    joined = " ".join(summary)
    assert "1/2 单位未评估" in joined
    assert "反装甲最强" in joined and "WeakGun" in joined
    assert "反装甲可能不足" in joined     # best <3.0 → 告警


def test_summary_no_antitank_warning_when_strong():
    strong = UnitAssessment(
        "x", "RailGun", 75, assessed=True, phase="shooting",
        scores=(TargetScore("veh", "载具(VEH)", 3.0, 4.0),))
    summary = " ".join(_build_summary((strong,)))
    assert "反装甲最强" in summary and "反装甲可能不足" not in summary


# ── 集成 ──────────────────────────────────────────────────────────

@needs_db
def test_critique_assesses_loadout_units():
    r = Roster("SM", DET, "strike_force", (
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5, loadout=(("Bolt rifle", 5),)),
    ))
    rep = critique(DB, r, n=800, seed=7)
    assert isinstance(rep, CritiqueReport)
    a = rep.assessments[0]
    assert a.assessed and a.phase == "shooting"
    assert len(a.scores) == 4
    geq = next(s for s in a.scores if s.key == "geq")
    assert geq.expected_damage > 0 and geq.damage_per_100 is not None


@needs_db
def test_critique_surfaces_unloadout_unit():
    r = Roster("SM", DET, "strike_force", (
        RosterUnit(APOTHECARY, "Apothecary Biologis", 1),   # 无 loadout
    ))
    rep = critique(DB, r, n=500)
    a = rep.assessments[0]
    assert a.assessed is False and "需装配" in a.note


@needs_db
def test_critique_weapon_role_distinction():
    """铁轨炮（反装甲）对 VEH 性价比应高于步枪；步枪对 GEQ 应高于铁轨炮。"""
    r = Roster("T'au", None, "strike_force", (
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5, loadout=(("Bolt rifle", 5),)),
        RosterUnit(BROADSIDE, "Broadside Battlesuits", 1, loadout=(("Heavy rail rifle", 1),)),
    ))
    rep = critique(DB, r, n=1500, seed=11)
    bolt = rep.assessments[0]
    rail = rep.assessments[1]

    def score(a, key):
        return next(s.damage_per_100 for s in a.scores if s.key == key)

    assert score(rail, "veh") > score(bolt, "veh")     # 铁轨炮反装甲更强
    assert score(bolt, "geq") > score(rail, "geq")     # 步枪打杂兵更划算


@needs_db
def test_critique_deterministic():
    r = Roster("SM", DET, "strike_force", (
        RosterUnit(INTERCESSOR, "Intercessor Squad", 5, loadout=(("Bolt rifle", 5),)),))
    r1 = critique(DB, r, n=600, seed=42)
    r2 = critique(DB, r, n=600, seed=42)
    assert r1.assessments[0].scores == r2.assessments[0].scores
