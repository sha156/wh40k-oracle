"""engines/roster/points.py — 军表点数重算（P6-PR1b）。

按单位选定的模型数从 points_json 的档位取价（不是基准档最小值——军表要的是「这个模型
数多少分」）。个别单位有「第 3 支起更贵」档，MVP 用基准 items 档，超出档位的模型数返回
None（诚实标注无法定价，不猜）。
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import replace
from typing import Dict, List, Optional

from engines.roster.contracts import Roster, RosterUnit

_MODELS_RE = re.compile(r"(\d+)")


def _tiers_from_points_json(points_json: Optional[str]) -> Dict[int, int]:
    """points_json → {模型数: cost}（取 items 基准档，desc 如 '5 models'）。"""
    if not points_json:
        return {}
    try:
        data = json.loads(points_json)
    except (ValueError, TypeError):
        return {}
    out: Dict[int, int] = {}
    for it in data.get("items", []):
        m = _MODELS_RE.search(str(it.get("desc", "")))
        cost = it.get("cost")
        if m and isinstance(cost, int):
            out[int(m.group(1))] = cost
    return out


def unit_cost(points_json: Optional[str], models: int) -> Optional[int]:
    """给定模型数的点数；档位里没有该模型数 → None（无法定价，诚实标注）。"""
    return _tiers_from_points_json(points_json).get(models)


def _load_points_json(conn, canonical_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT points_json FROM units WHERE id = ?", (canonical_id,)).fetchone()
    return row[0] if row else None


def recompute(db_path, roster: Roster) -> Roster:
    """给每个单位按其模型数填 points（无法定价留 None）。返回新 Roster（不改入参）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        new_units: List[RosterUnit] = []
        for u in roster.units:
            pj = _load_points_json(conn, u.canonical_id)
            new_units.append(replace(u, points=unit_cost(pj, u.models)))
    finally:
        conn.close()
    return replace(roster, units=tuple(new_units))


def total_points(roster: Roster) -> int:
    """已定价单位点数之和（None 计 0——未定价项由 validate 单独 warn）。"""
    return sum(u.points or 0 for u in roster.units)
