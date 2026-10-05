"""engines/roster/points.py — 军表点数重算（P6-PR1b）。

按单位选定的模型数从 points_json 的档位取价（不是基准档最小值——军表要的是「这个模型
数多少分」）。个别单位有「第 3 支起更贵」档，MVP 用基准 items 档，超出档位的模型数返回
None（诚实标注无法定价，不猜）。
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
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
    try:
        source = json.loads(points_json or "{}").get("mfm") or {}
    except (ValueError, AttributeError):
        source = {}
    if source.get("current") is False:
        return None
    if source.get("tiers"):
        return _official_cost(source["tiers"], models, 1, ())
    return _tiers_from_points_json(points_json).get(models)


def _weapon_base(name):
    # Firing profiles refer to the same purchased weapon.
    return re.split(r"\s+[-–]\s+", name.strip(), maxsplit=1)[0].casefold()


def _official_cost(rows, models, occurrence, loadout, weapon_names=()):
    from db_compile.point_tiers import model_count, tier_applies
    try:
        applicable = [r for r in rows if tier_applies(r["tier"], occurrence)]
    except ValueError:
        return None
    costs = {r["cost"] for r in applicable if model_count(r["models"]) == models}
    if len(costs) != 1:
        return None
    surcharges = {_weapon_base(r["models"][4:]): r["cost"] for r in applicable
                  if r["models"].casefold().startswith("per ")}
    if surcharges and not loadout:
        return None  # Weapon choices now affect MFM prices; do not assume free equipment.
    cost = costs.pop()
    known_weapons = {_weapon_base(name) for name in weapon_names}
    for name, count in loadout:
        if not isinstance(name, str) or type(count) is not int or count <= 0:
            return None
        base = _weapon_base(name)
        if surcharges and base not in surcharges and base not in known_weapons:
            return None  # Unknown equipment is not evidence of a free option.
        cost += surcharges.get(base, 0) * count
    # Optional extra-model packages need an explicit composition selector.
    if any(r["models"].startswith("+") for r in applicable):
        return None
    return cost


def _chapter_slug(conn, roster):
    if not roster.detachment_id or roster.faction_id != "SM":
        return None
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='official_mfm_detachments'").fetchone():
        return None
    names = conn.execute("SELECT DISTINCT detachment_name FROM enhancements WHERE detachment_id=? AND faction_id='SM'", (roster.detachment_id,)).fetchall()
    slugs = {s for (name,) in names for (s,) in conn.execute(
        "SELECT faction_slug FROM official_mfm_detachments WHERE lower(name)=lower(?)", (name,))}
    return next(iter(slugs)) if len(slugs) == 1 else None


def _roster_price_slug(conn, roster, identities, has_keywords):
    """Exact canonical ties may establish a chapter; conflicting ties cannot.

    Shared detachment names alone remain ambiguous. A generic canonical entry
    in a proven chapter roster uses that chapter's exact complete source head.
    This selects prices only, without certifying equipment or army legality.
    """
    from db_compile.mfm_context import CHAPTER_SLUGS, canonical_price_identity

    routes = set()
    chapters = set()
    for _name, faction, _points, keywords in identities.values():
        if faction != "SM":
            continue
        identity = canonical_price_identity(faction, keywords) if has_keywords else ("space-marines", None)
        if identity is None:
            return None
        route, chapter = identity
        if chapter:
            chapters.add(chapter)
        if route != "space-marines":
            routes.add(route)
    if roster.detachment_id:
        owners = {r[0] for r in conn.execute(
            "SELECT DISTINCT faction_id FROM enhancements WHERE detachment_id=?",
            (roster.detachment_id,))}
        if "SM" not in owners:
            return None
    detachment = _chapter_slug(conn, roster)
    if detachment and detachment != "space-marines":
        if detachment not in CHAPTER_SLUGS.values():
            return None
        routes.add(detachment)
        chapters.add(detachment.replace("-", " "))
    if len(chapters) > 1:
        return None
    return next(iter(routes)) if len(routes) == 1 else ("space-marines" if not routes else None)


def _chapter_price_rows(conn, slug, name, receipts):
    """Read one exact retained source head in ordinal order, with its receipt."""
    from db_compile.mfm import _chapter_receipt

    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='official_mfm_points'").fetchone():
        return None
    candidates = conn.execute(
        "SELECT tier,models,cost,section FROM official_mfm_points "
        "WHERE faction_slug=? AND kind='unit' AND lower(unit_name)=lower(?) ORDER BY ordinal",
        (slug, name)).fetchall()
    primary = [r for r in candidates if r[3] in ("UNITS", "FORTIFICATIONS")]
    selected = primary or candidates
    rows = list(dict.fromkeys((r[0], r[1], r[2]) for r in selected))
    if not rows or _chapter_receipt(conn, slug, name, rows, None, receipts) is None:
        return None
    return [{"tier": tier, "models": models, "cost": cost} for tier, models, cost in rows]


def _load_points_json(conn, canonical_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT points_json FROM units WHERE id = ?", (canonical_id,)).fetchone()
    return row[0] if row else None


def recompute(db_path, roster: Roster) -> Roster:
    """给每个单位按其模型数填 points（无法定价留 None）。返回新 Roster（不改入参）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        new_units: List[RosterUnit] = []
        counts = Counter()
        columns = {r[1] for r in conn.execute("PRAGMA table_info(units)")}
        has_keywords = "keywords_json" in columns
        ids = sorted({u.canonical_id for u in roster.units})
        identities = {}
        if ids:
            keyword_column = "keywords_json" if has_keywords else "NULL"
            identities = {r[0]: r[1:] for r in conn.execute(
                "SELECT id,name_en,faction_id,points_json," + keyword_column
                + " FROM units WHERE id IN (" + ",".join("?" for _ in ids) + ")", ids)}
        chapter = _roster_price_slug(conn, roster, identities, has_keywords) if roster.faction_id == "SM" else None
        chapter_rows = {}
        receipts = {}
        for u in roster.units:
            name_row = identities.get(u.canonical_id)
            if not name_row or not isinstance(name_row[0], str):
                new_units.append(replace(u, points=None))
                continue
            pj = name_row[2]
            identity = (name_row[0].casefold(), name_row[1])
            counts[identity] += 1
            try:
                data = json.loads(pj or "{}")
                source = data.get("mfm") or {}
            except (ValueError, AttributeError, TypeError):
                new_units.append(replace(u, points=None))
                continue
            rows = source.get("tiers") or []
            if name_row[1] == "SM":
                if roster.faction_id != "SM" or chapter is None:
                    new_units.append(replace(u, points=None))
                    continue
                if chapter != "space-marines":
                    if identity not in chapter_rows:
                        chapter_rows[identity] = _chapter_price_rows(conn, chapter, name_row[0], receipts)
                    rows = chapter_rows[identity]
                    if rows is None:
                        new_units.append(replace(u, points=None))
                        continue
            weapon_names = ()
            if u.loadout and any(r["models"].casefold().startswith("per ") for r in rows):
                if conn.execute("SELECT 1 FROM sqlite_master WHERE name='weapons'").fetchone():
                    weapon_names = tuple(name for (name,) in conn.execute(
                        "SELECT name_en FROM weapons WHERE unit_id=?", (u.canonical_id,))
                        if isinstance(name, str))
            price = None if source.get("current") is False else (
                _official_cost(rows, u.models, counts[identity], u.loadout, weapon_names)
                if rows else unit_cost(pj, u.models))
            new_units.append(replace(u, points=price))
    finally:
        conn.close()
    return replace(roster, units=tuple(new_units))


def total_points(roster: Roster) -> int:
    """已定价单位点数之和（None 计 0——未定价项由 validate 单独 warn）。"""
    return sum(u.points or 0 for u in roster.units)
