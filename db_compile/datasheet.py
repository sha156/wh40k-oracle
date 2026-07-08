"""datasheet：unit_id → 完整英文属性块（数值题查表的核心，绕开 PDF 检索）。

分层评测证明：数值/属性题在 PDF 里检索会被译名/拍扁坑（详见 crosscheck 记忆），
而 L3 库里每个单位的 M/T/Sv/W + 武器 A/S/AP/D 都是结构化的干净真值。本模块把它们
组装成一个属性块，供 agent 的 get_datasheet 工具直接回答「瘟疫战士的T是多少」这类问题。

只读，不改库。英文是权威真值；中文（name_zh）可缺，缺了不影响英文属性可查。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ModelProfile:
    name: str
    m: str
    t: str
    sv: str
    invuln: str
    w: str
    ld: str
    oc: str


@dataclass
class Weapon:
    name: str
    kind: str  # "ranged" | "melee"
    range: str
    a: str
    bs_ws: str
    s: str
    ap: str
    d: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class Datasheet:
    unit_id: str
    name_en: str
    name_zh: Optional[str]
    faction: Optional[str]
    points_min: Optional[int]
    points_options: List[dict]
    keywords: List[str]
    models: List[ModelProfile]
    weapons: List[Weapon]


def _parse_points(points_json: Optional[str]) -> tuple:
    if not points_json:
        return None, []
    try:
        data = json.loads(points_json)
    except (json.JSONDecodeError, TypeError):
        return None, []
    items = data.get("items") or []
    costs = [it.get("cost") for it in items if isinstance(it.get("cost"), int)]
    top = data.get("points")
    minimum = min(costs) if costs else (top if isinstance(top, int) else None)
    return minimum, items


def _parse_keywords(keywords_json: Optional[str]) -> List[str]:
    if not keywords_json:
        return []
    try:
        return list(json.loads(keywords_json).get("keywords") or [])
    except (json.JSONDecodeError, TypeError, AttributeError):
        return []


def _weapon_kind(range_val: str) -> str:
    return "melee" if (range_val or "").strip().lower() == "melee" else "ranged"


def _parse_weapon_keywords(keywords_json: Optional[str]) -> List[str]:
    if not keywords_json:
        return []
    try:
        raw = json.loads(keywords_json)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    return []


def lookup_datasheet(db_path, unit_id: str) -> Optional[Datasheet]:
    """按 canonical unit_id 组装完整属性块；查不到返回 None（诚实报缺，不编造）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT u.name_en, u.name_zh, u.points_json, u.keywords_json, f.name "
            "FROM units u LEFT JOIN factions f ON f.id = u.faction_id "
            "WHERE u.id = ?", (unit_id,)
        ).fetchone()
        if row is None:
            return None
        name_en, name_zh, points_json, keywords_json, faction = row
        points_min, points_options = _parse_points(points_json)

        models = [
            ModelProfile(name=m[0], m=m[1], t=m[2], sv=m[3], invuln=m[4],
                         w=m[5], ld=m[6], oc=m[7])
            for m in conn.execute(
                "SELECT name, m, t, sv, invuln, w, ld, oc FROM models "
                "WHERE unit_id = ?", (unit_id,))
        ]
        weapons = [
            Weapon(name=w[0], kind=_weapon_kind(w[1]), range=w[1], a=w[2],
                   bs_ws=w[3], s=w[4], ap=w[5], d=w[6],
                   keywords=_parse_weapon_keywords(w[7]))
            for w in conn.execute(
                "SELECT name_en, range, a, bs_ws, s, ap, d, keywords_json "
                "FROM weapons WHERE unit_id = ? ORDER BY id", (unit_id,))
        ]
        return Datasheet(
            unit_id=unit_id, name_en=name_en, name_zh=name_zh, faction=faction,
            points_min=points_min, points_options=points_options,
            keywords=_parse_keywords(keywords_json), models=models, weapons=weapons)
    finally:
        conn.close()


def find_datasheet(db_path, name: str,
                   resolver=None) -> Optional[Datasheet]:
    """中文/英文/俗名 → 解析 canonical id → 属性块。英文名直查优先，兜底走 entity_resolver。"""
    conn = sqlite3.connect(str(db_path))
    try:
        hit = conn.execute(
            "SELECT id FROM units WHERE name_en = ? COLLATE NOCASE LIMIT 1", (name,)
        ).fetchone()
    finally:
        conn.close()
    if hit:
        return lookup_datasheet(db_path, hit[0])

    from db_compile.entity_resolver import EntityResolver

    r = resolver or EntityResolver(db_path=Path(db_path))
    resolved = r.resolve(name)
    if resolved.canonical_id:
        return lookup_datasheet(db_path, resolved.canonical_id)
    return None
