"""calc_points：从 wh40k.sqlite 查点数（spec agent/tools.py 的 calc_points 工具）。

points_json 现已导入（Wahapedia 档位 + 官方 MFM 覆写），仅极少数单位在源表中无点数。
返回值取「基准档最小 cost」（与 datasheet._parse_points 同语义），**不取顶层 points**——
顶层对未被 MFM 覆写的单位是「各档 cost 累加和」的错误语义，会给出虚高点数。
无点数记录时诚实返回缺失原因，不编造。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

MISSING_COST_NOTE = "该单位在 Wahapedia 点数表中无记录，无法计算点数"
UNKNOWN_UNIT_NOTE = "未找到该 unit id"


def _min_points(points_json: Optional[str]) -> Optional[int]:
    """取基准档最小 cost（与 datasheet._parse_points 一致）；无 items 时回退顶层 points。"""
    try:
        data = json.loads(points_json)
    except (json.JSONDecodeError, TypeError):
        return None
    items = data.get("items") or []
    costs = [it.get("cost") for it in items if isinstance(it.get("cost"), int)]
    if costs:
        return min(costs)
    top = data.get("points")
    return top if isinstance(top, int) else None


@dataclass(frozen=True)
class UnitPoints:
    unit_id: str
    name_en: Optional[str]
    points: Optional[int]
    note: Optional[str]


def calc_points(db_path: Path, unit_ids: List[str]) -> List[UnitPoints]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        out: List[UnitPoints] = []
        for uid in unit_ids:
            cur.execute(
                "SELECT name_en, points_json FROM units WHERE id = ?", (uid,))
            row = cur.fetchone()
            if row is None:
                out.append(UnitPoints(uid, None, None, UNKNOWN_UNIT_NOTE))
                continue
            name_en, points_json = row
            pts = _min_points(points_json) if points_json is not None else None
            if pts is None:
                out.append(UnitPoints(uid, name_en, None, MISSING_COST_NOTE))
            else:
                out.append(UnitPoints(uid, name_en, pts, None))
        return out
    finally:
        conn.close()
