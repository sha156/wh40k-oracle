"""engines/roster/compose_rules.py — 11 版编制约束常量 + 关键词判定（P6-PR1b）。

核心规则常量写死（无数据缺口）；单位关键词从 units.keywords_json 读（判 CHARACTER/
BATTLELINE/EPIC HERO/DEDICATED TRANSPORT，供 warlord 资格 / Rule of Three 豁免）。
"""
from __future__ import annotations

import json
import sqlite3
from typing import Dict, Optional, Set

# 军表规模档 → 点数上限（11 版核心规则）
SIZE_LIMITS: Dict[str, int] = {
    "incursion": 1000,
    "strike_force": 2000,
    "onslaught": 3000,
}
DEFAULT_SIZE = "strike_force"

# 强化：每支军队 0-3 个，各唯一，仅 CHARACTER（非 EPIC HERO），每 CHARACTER 至多 1 个
MAX_ENHANCEMENTS = 3

# Rule of Three：同一 datasheet 至多 3 份；BATTLELINE / DEDICATED TRANSPORT 无上限；
# EPIC HERO 至多 1 份（每个传奇英雄只能选一次）
RULE_OF_THREE = 3
EPIC_HERO_MAX = 1

_KW_CHARACTER = "CHARACTER"
_KW_EPIC_HERO = "EPIC HERO"
_KW_BATTLELINE = "BATTLELINE"
_KW_DEDICATED_TRANSPORT = "DEDICATED TRANSPORT"


def size_limit(size: str) -> int:
    """规模档 → 点数上限；未知档回退 strike_force 2000。"""
    return SIZE_LIMITS.get(size, SIZE_LIMITS[DEFAULT_SIZE])


def unit_keywords(db_path, canonical_id: str) -> Set[str]:
    """单位关键词集合（大写规范化）；单位不存在或无关键词 → 空集。"""
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT keywords_json FROM units WHERE id = ?", (canonical_id,)).fetchone()
    finally:
        conn.close()
    return _parse_keywords(row[0]) if row else set()


def _parse_keywords(kj) -> Set[str]:
    if not kj:
        return set()
    try:
        data = json.loads(kj)
    except (ValueError, TypeError):
        return set()
    return {k.strip().upper() for k in data.get("keywords", []) if k and k.strip()}


def unit_keywords_bulk(db_path, ids) -> Dict[str, Set[str]]:
    """一次查多个单位的关键词 → {id: set}（避免验表按单位 N+1 连库）。

    查不到的 id **不出现在返回里**——调用方以此区分「单位不在库」与「有单位但无
    关键词」。原先给未知 id 补空集，会让 validate 对不存在的单位编造「非 CHARACTER」
    「模型数不在档位内」等事实性断言（gnhf 审查模块 3 F3，诚实降级红线）。
    """
    uniq = list(set(ids))
    if not uniq:
        return {}
    conn = sqlite3.connect(str(db_path))
    try:
        ph = ",".join("?" * len(uniq))
        rows = conn.execute(
            f"SELECT id, keywords_json FROM units WHERE id IN ({ph})", uniq).fetchall()
    finally:
        conn.close()
    return {uid: _parse_keywords(kj) for uid, kj in rows}


def is_character(kw: Set[str]) -> bool:
    return _KW_CHARACTER in kw


def is_epic_hero(kw: Set[str]) -> bool:
    return _KW_EPIC_HERO in kw


def is_rot_exempt(kw: Set[str]) -> bool:
    """Rule of Three 豁免：BATTLELINE / DEDICATED TRANSPORT 无数量上限。"""
    return _KW_BATTLELINE in kw or _KW_DEDICATED_TRANSPORT in kw


def datasheet_copy_limit(kw: Set[str]) -> Optional[int]:
    """该 datasheet 在一支军队里的份数上限；None=无上限（battleline/DT）。"""
    if is_rot_exempt(kw):
        return None
    if is_epic_hero(kw):
        return EPIC_HERO_MAX
    return RULE_OF_THREE
