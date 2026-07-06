"""calc_points：从 wh40k.sqlite 查点数（spec agent/tools.py 的 calc_points 工具）。

P2 阶段 units.points_json 恒为 NULL（Datasheets_models_cost.csv 未下载）——
诚实返回缺失原因，不编造数值，与 spec 的 dsl_status 诚实标记同一原则。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

MISSING_COST_NOTE = "缺 Datasheets_models_cost.csv（Wahapedia 点数表未下载），无法计算点数"
UNKNOWN_UNIT_NOTE = "未找到该 unit id"


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
            if points_json is None:
                out.append(UnitPoints(uid, name_en, None, MISSING_COST_NOTE))
            else:
                out.append(UnitPoints(
                    uid, name_en, json.loads(points_json).get("points"), None))
        return out
    finally:
        conn.close()
