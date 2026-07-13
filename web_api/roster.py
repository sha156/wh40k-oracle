"""web_api/roster.py — 军表实验室后端（BUILD-PLAN Stage 4 / P6-PR3）。

图鉴 canonical id 搭军表 → engines/roster 验表（实时，零 LLM）/ 点评（蒙特卡洛）。
RosterIn（camelCase）→ 引擎 Roster → 报告 → *Out 镜像（契约真源 web/src/lib/roster.ts）。
分队目录/强化清单从 enhancements 表派生（PR1a）；武器池复用模拟器装配层。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from web_api.contract import (CritiqueReportOut, RosterIn, TargetScoreOut,
                              UnitAssessmentOut, ValidationIssueOut,
                              ValidationReportOut)


def _to_loadout(raw: List[List[Any]]) -> Tuple[Tuple[str, int], ...]:
    """[[武器名,数量],...] → ((str,int),...)；非法项整体丢弃（不猜半份装配）。"""
    out: List[Tuple[str, int]] = []
    for item in raw or []:
        if not (isinstance(item, (list, tuple)) and len(item) == 2):
            return ()
        name, cnt = item
        try:
            c = int(cnt)
        except (TypeError, ValueError):
            return ()
        if not isinstance(name, str) or not name.strip() or c <= 0:
            return ()
        out.append((name.strip(), c))
    return tuple(out)


def _to_engine_roster(req: RosterIn):
    """RosterIn → engines.roster.Roster。"""
    from engines.roster import Roster, RosterUnit
    units = tuple(
        RosterUnit(
            canonical_id=u.canonical_id, name_en=u.name_en, models=max(1, u.models),
            is_warlord=u.is_warlord, enhancement=u.enhancement,
            loadout=_to_loadout(u.loadout))
        for u in req.units)
    return Roster(faction_id=req.faction_id, detachment_id=req.detachment_id,
                  size=req.size, units=units)


def validate_roster(db_path: Path, req: RosterIn) -> ValidationReportOut:
    from engines.roster import validate
    rep = validate(db_path, _to_engine_roster(req))
    return ValidationReportOut(
        total_points=rep.total_points, limit=rep.limit, legal=rep.legal,
        issues=[ValidationIssueOut(code=i.code, severity=i.severity,
                                   message=i.message, anchor=i.anchor,
                                   surfaced_only=i.surfaced_only)
                for i in rep.issues])


def critique_roster(db_path: Path, req: RosterIn, n: int = 1000) -> CritiqueReportOut:
    from engines.roster import critique
    rep = critique(db_path, _to_engine_roster(req), n=n)
    return CritiqueReportOut(
        total_points=rep.total_points,
        assessments=[
            UnitAssessmentOut(
                canonical_id=a.canonical_id, name_en=a.name_en, points=a.points,
                assessed=a.assessed, phase=a.phase, note=a.note,
                scores=[TargetScoreOut(key=s.key, label=s.label,
                                       expected_damage=s.expected_damage,
                                       damage_per_100=s.damage_per_100)
                        for s in a.scores])
            for a in rep.assessments],
        summary=list(rep.summary), not_modeled=list(rep.not_modeled))


def list_detachments(db_path: Path, faction_id: str) -> List[Dict[str, Any]]:
    """某阵营的分队目录（从 enhancements 表派生）：[{id,name}]，按名排序。"""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT DISTINCT detachment_id, detachment_name FROM enhancements "
            "WHERE faction_id = ? ORDER BY detachment_name", (faction_id,)).fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows if r[0]]


def list_enhancements(db_path: Path, detachment_id: str) -> List[Dict[str, Any]]:
    """某分队合法强化清单（强化下拉用）：[{id,name,cost}]，按点数排序。"""
    from db_compile.enhancements import list_for_detachment
    return list_for_detachment(db_path, detachment_id)


def unit_weapon_pool(db_path: Path, unit_id: str) -> Optional[List[str]]:
    """单位武器选项池（英文权威名，装配面板用）；单位不存在返回 None。"""
    from engines.simulator.profile import load_unit_header, load_weapon_pool
    if load_unit_header(db_path, unit_id) is None:
        return None
    return [w.name_en for w in load_weapon_pool(db_path, unit_id)]
