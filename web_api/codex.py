"""web_api/codex.py — 图鉴（L3 结构库只读浏览，BUILD-PLAN Stage 4）。

阵营列表 → 单位列表 → 单位兵牌（复用 build_entity_card）。全部只读查 sqlite，零 LLM。
中文阵营名从 unit_zh_detail.faction_zh 取众数（英文 factions 表无中文名）。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from web_api.contract import EntityCard
from web_api.entity_card import build_entity_card


# 官方阵营中文名（固定 25 个，curated）。不用 unit_zh_detail.faction_zh 众数——
# 含盟友单位的阵营（如 Genestealer Cults 有星界军 Brood Brothers）会被污染成错误中文名，
# 显示「自信的错误」比不显示更糟。缺项回退英文名（诚实）。
_FACTION_ZH: Dict[str, str] = {
    "SM": "星际战士", "GC": "基因窃取者教派", "AM": "星界军", "CSM": "混沌星际战士",
    "CD": "混沌恶魔", "AE": "艾尔达", "ORK": "兽人", "DG": "死亡守卫",
    "NEC": "死灵", "TAU": "钛帝国", "TS": "千子", "WE": "吞世者",
    "TYR": "泰伦虫族", "DRU": "黑暗灵族", "AoI": "帝国密探", "AdM": "机械神教",
    "AS": "战斗修女", "QT": "混沌骑士", "AC": "禁军", "GK": "灰骑士",
    "QI": "帝国骑士", "EC": "皇帝之子", "LoV": "沃坦联盟", "UN": "无阵营部队",
    "TL": "泰坦军团",
}


def list_factions(db_path) -> List[Dict[str, Any]]:
    """有单位的阵营列表：{id, name, nameZh, count}，按单位数降序。"""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT f.id, f.name, COUNT(u.id) n "
            "FROM factions f LEFT JOIN units u ON u.faction_id = f.id "
            "GROUP BY f.id HAVING n > 0 ORDER BY n DESC"
        ).fetchall()
        return [
            {"id": fid, "name": name, "nameZh": _FACTION_ZH.get(fid), "count": n}
            for fid, name, n in rows
        ]
    finally:
        conn.close()


def _min_points(points_json: Optional[str]) -> Optional[int]:
    if not points_json:
        return None
    try:
        opts = json.loads(points_json)
    except (json.JSONDecodeError, TypeError):
        return None
    costs = [o.get("cost") for o in opts if isinstance(o, dict) and o.get("cost") is not None]
    return min(costs) if costs else None


def list_units(db_path, faction_id: str) -> List[Dict[str, Any]]:
    """某阵营单位列表：{id, nameEn, nameZh, pts}，按英文名排序。"""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, name_en, name_zh, points_json FROM units "
            "WHERE faction_id = ? ORDER BY name_en",
            (faction_id,),
        ).fetchall()
        out = []
        for uid, en, zh, pj in rows:
            pmin = _min_points(pj)
            out.append({
                "id": uid, "nameEn": en, "nameZh": zh,
                "pts": ("{} 分起".format(pmin) if pmin is not None else None),
            })
        return out
    finally:
        conn.close()


def unit_card(db_path, unit_id: str) -> Optional[EntityCard]:
    """单位 id → EntityCard（复用 build_entity_card；未找到返回 None）。"""
    from db_compile.blacklibrary import load_zh_detail
    from db_compile.datasheet import lookup_datasheet

    ds = lookup_datasheet(db_path, unit_id)
    if ds is None:
        return None
    zh = load_zh_detail(db_path, unit_id)
    res = {"found": True, "datasheet": asdict(ds), "datasheet_zh": zh}
    return build_entity_card(res)


def faction_exists(db_path, faction_id: str) -> bool:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(
            "SELECT 1 FROM factions WHERE id = ? LIMIT 1", (faction_id,)
        ).fetchone() is not None
    finally:
        conn.close()
