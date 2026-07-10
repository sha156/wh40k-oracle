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
    base: Optional[str] = None   # 底盘尺寸（Wahapedia base_size，如 '40mm'；旧库/未知为 None）


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
                         w=m[5], ld=m[6], oc=m[7], base=m[8])
            for m in conn.execute(
                "SELECT name, m, t, sv, invuln, w, ld, oc, base FROM models "
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


def _norm_stat(v) -> str:
    """把属性值归一化到可比对形式：去移动单位/救护 + 号，只留核心 token。"""
    if v is None:
        return ""
    s = str(v).strip().lower()
    for junk in ('"', "”", "“", "″", "′", "'", "寸", "吋", "+", " "):
        s = s.replace(junk, "")
    return s


def diff_core_stats(ds: "Datasheet", zh: Optional[dict]) -> List[dict]:
    """比较 Wahapedia(权威) 与黑图书馆中文层同一单位的 M/T/SV/W，返回冲突字段清单。

    动机：get_datasheet 把官方英文属性块与黑图中文层合并进同一响应，实测约 29/919 个
    单位两源数值不一致（War Dog Moirax T9≠10、Land Speeder W9≠6 等）。不检测就可能在
    一次回答里同时给出两个矛盾数值。仅在两边各恰好一个 model 时比较（多 model 对齐易误判）。
    返回 [{"field","official","blackforum"}, ...]，空列表表示一致或无法比较。
    """
    zh_stats = (zh or {}).get("属性") or []
    if len(ds.models) != 1 or len(zh_stats) != 1:
        return []
    wm, zm = ds.models[0], zh_stats[0]
    if not isinstance(zm, dict):
        return []
    conflicts = []
    for field_name, off_val, zh_key in (
        ("M", wm.m, "m"), ("T", wm.t, "t"), ("SV", wm.sv, "sv"), ("W", wm.w, "w"),
        ("BASE", wm.base, "unitBase"),   # 底盘尺寸：官方 base_size vs 黑图书馆 unitBase
    ):
        zh_val = zm.get(zh_key)
        if zh_val in (None, "", "?", "-"):
            continue
        if off_val in (None, "", "?", "-"):
            # 任一侧缺值只是数据缺失（如官方 base_size 留空），不算数值矛盾
            continue
        if _norm_stat(off_val) != _norm_stat(zh_val):
            conflicts.append({"field": field_name,
                              "official": off_val, "blackforum": zh_val})
    return conflicts


class AmbiguousUnitName(LookupError):
    """同一 name_en 存在于多个阵营（评审 #25：4 个阵营各有 Helbrute，旧 LIMIT 1
    静默取任意一行）。调用方须把 candidates 抛给用户/LLM 指明阵营，绝不静默取一。
    candidates 形如 `Helbrute (WE)`，可原样回填 find_datasheet 精确重查。"""

    def __init__(self, name: str, candidates, hits=None):
        super().__init__(name)
        self.name = name
        self.candidates = list(candidates)
        self.hits = list(hits or [])   # [(unit_id, name_en, faction_id)]，供调用方做候选预览


def find_datasheet(db_path, name: str,
                   resolver=None) -> Optional[Datasheet]:
    """中文/英文/俗名 → 解析 canonical id → 属性块。英文名直查优先，兜底走 entity_resolver。

    同名跨阵营多命中时抛 AmbiguousUnitName（含阵营限定候选），不静默取一。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        hits = conn.execute(
            "SELECT id, name_en, faction_id FROM units WHERE name_en = ? COLLATE NOCASE",
            (name,)
        ).fetchall()
    finally:
        conn.close()
    if len(hits) == 1:
        return lookup_datasheet(db_path, hits[0][0])
    if len(hits) > 1:
        raise AmbiguousUnitName(
            name, ["{} ({})".format(n, fac or "?") for _, n, fac in hits],
            hits=hits)

    from db_compile.entity_resolver import EntityResolver

    r = resolver or EntityResolver(db_path=Path(db_path))
    resolved = r.resolve(name)
    # 只信 exact（别名表精确命中/UNIT_ALIASES 链/`名字 (阵营)` 消歧串）。fuzzy 会返回
    # confident 错单位（如 机械教游侠→Tech-priest Dominus），数值权威路径宁可诚实报缺
    # 也不给错答案。
    if resolved.canonical_id and resolved.confidence == "exact":
        return lookup_datasheet(db_path, resolved.canonical_id)
    return None
