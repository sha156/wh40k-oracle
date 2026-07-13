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

# 与 engines/simulator/assembly.py 对齐的严格档位正则：必须 "N model(s)"，避免把复合
# datasheet 描述（"3 X and 3 Y"）里的头一个数字当成模型数（评审 CRITICAL）。
_MODELS_RE = re.compile(r"(\d+)\s*models?", re.IGNORECASE)
# 「纯档位」：desc 只有 "N model(s)" 无其它修饰——它是基准价（无分队/特殊语境加价）
_PLAIN_RE = re.compile(r"^\s*(\d+)\s*models?\s*$", re.IGNORECASE)


def _tiers_from_points_json(points_json: Optional[str]) -> Dict[int, int]:
    """points_json → {模型数: cost}。

    基准档（纯 "N models"）优先——Agent 类单位同模型数有分队加价档（"1 model" 110 vs
    "1 model (Assigned Agent)" 125），取纯档基准价而非最后写入者。复合单位（"3 X and 3 Y"）
    严格正则不匹配 → 跳过 → 无法定价 → 上层 surfaced（不静默编造错价）。同模型数多个非纯档
    且价不同 → 歧义跳过（None）。
    """
    if not points_json:
        return {}
    try:
        data = json.loads(points_json)
    except (ValueError, TypeError):
        return {}
    plain: Dict[int, int] = {}
    qualified: Dict[int, set] = {}
    for it in data.get("items", []):
        desc = str(it.get("desc", ""))
        cost = it.get("cost")
        if not isinstance(cost, int):
            continue
        pm = _PLAIN_RE.match(desc.strip())
        if pm:
            plain[int(pm.group(1))] = cost
            continue
        m = _MODELS_RE.search(desc)
        if m:
            qualified.setdefault(int(m.group(1)), set()).add(cost)
    out: Dict[int, int] = dict(plain)
    for k, costs in qualified.items():
        if k in out:            # 纯档基准价优先
            continue
        if len(costs) == 1:     # 唯一 qualified 价 → 采用
            out[k] = next(iter(costs))
        # 多个不同 qualified 价且无纯档 → 歧义，跳过 → unit_cost 返 None → surfaced
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
