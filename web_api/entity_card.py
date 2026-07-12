"""web_api/entity_card.py — get_datasheet 返回 dict → EntityCard（E6，确定性映射）。

数据全部来自 L3 结构库（英文权威真值 + 可选黑图中文层），零 LLM。诚实红线：
- datasheet 不含 book/page → `src` 如实标「L3 结构库 · <阵营>」，绝不编造页码。
- 能力文本黑图中文层常为空 → abilities 留空数组，不编能力描述。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from web_api.contract import Ability, EntityCard, Stat, WeaponRow
from web_api.richtext import to_richtext


def _fmt_range(val: str) -> str:
    """'60' → '60\"'；'Melee' → '近战'；其余原样。"""
    v = (val or "").strip()
    if v.isdigit():
        return v + '"'
    if v.lower() == "melee":
        return "近战"
    return v


def _fmt_skill(bs_ws: str) -> str:
    """'4' → '4+'；已带 + 或非数字则原样（近战武器 WS 同理）。"""
    v = (bs_ws or "").strip()
    if v.isdigit():
        return v + "+"
    return v


def _weapon_kw(keywords: List[str]) -> Optional[str]:
    """武器关键词列表 → '[a，b]'；空则 None。DB 里单元素可能已是逗号串。"""
    flat: List[str] = []
    for k in keywords or []:
        for part in re.split(r"[,，]", str(k)):
            part = part.strip()
            if part:
                flat.append(part)
    if not flat:
        return None
    return "[" + "，".join(flat) + "]"


def _weapon_row(w: Dict[str, Any], hot_weapon: Optional[str]) -> WeaponRow:
    name = str(w.get("name", ""))
    hot = bool(hot_weapon) and hot_weapon.lower() in name.lower()
    return WeaponRow(
        name=name,
        kw=_weapon_kw(w.get("keywords", [])),
        range=_fmt_range(str(w.get("range", ""))),
        a=str(w.get("a", "")),
        skill=_fmt_skill(str(w.get("bs_ws", ""))),
        s=str(w.get("s", "")),
        ap=str(w.get("ap", "")),
        d=str(w.get("d", "")),
        hot=hot,
    )


def _points_str(ds: Dict[str, Any]) -> str:
    """points_options 的 cost 列 → '75 / 150 / 240'；缺则退 points_min。"""
    opts = ds.get("points_options") or []
    costs = [str(o.get("cost")) for o in opts if o.get("cost") is not None]
    if costs:
        return " / ".join(costs)
    pmin = ds.get("points_min")
    return str(pmin) if pmin is not None else "—"


def _composition(ds: Dict[str, Any]):
    """points_options → 每行 RichText（'1 model — 75 分'）。"""
    rows = []
    for o in ds.get("points_options") or []:
        desc = str(o.get("desc", "")).strip()
        cost = o.get("cost")
        line = desc if desc else str(o.get("line", ""))
        if cost is not None:
            line = "{} — {} 分".format(line, cost)
        rows.append(to_richtext(line))
    return rows


def _abilities(zh: Optional[Dict[str, Any]]) -> List[Ability]:
    """黑图中文层 能力 → Ability 列表；空/缺则 []（诚实不编造）。"""
    if not zh:
        return []
    raw = zh.get("能力")
    if not raw:
        return []
    out: List[Ability] = []
    if isinstance(raw, dict):
        raw = [{"name": k, "text": v} for k, v in raw.items()]
    for item in raw:
        if isinstance(item, str):
            out.append(Ability(name=item))
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("标题") or item.get("title") or "")
            text = item.get("text") or item.get("描述") or item.get("desc")
            if name:
                out.append(Ability(name=name, text=str(text) if text else None))
    return out


_STAT_LABELS = [("m", "M"), ("t", "T"), ("sv", "SV"), ("w", "W"), ("ld", "LD"), ("oc", "OC")]


def _wiki_path(faction: Optional[str], unit_id: str, name_en: str) -> str:
    """构造 wiki 路径（best-effort，不保证页存在，前端点击才校验）。"""
    if not faction:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", (name_en or "").lower()).strip("-")
    fac = re.sub(r"[^a-z0-9]+", "-", faction.lower()).strip("-")
    return "factions/{}/units/{}".format(fac, slug) if slug else ""


def build_entity_card(
    tool_result: Dict[str, Any], hot_weapon: Optional[str] = None,
) -> Optional[EntityCard]:
    """get_datasheet 的完整返回 dict → EntityCard；未命中返回 None。"""
    if not tool_result or not tool_result.get("found"):
        return None
    ds = tool_result.get("datasheet") or {}
    if not ds:
        return None
    zh = tool_result.get("datasheet_zh")

    models = ds.get("models") or []
    m0 = models[0] if models else {}
    stats = [Stat(lab=lab, val=str(m0.get(key, "—"))) for key, lab in _STAT_LABELS]
    invuln = str(m0.get("invuln", "-")).strip()
    if invuln and invuln not in ("-", "—", ""):
        stats.append(Stat(lab="INV", val=invuln))

    weapons = ds.get("weapons") or []
    ranged = [_weapon_row(w, hot_weapon) for w in weapons if w.get("kind") == "ranged"]
    melee = [_weapon_row(w, hot_weapon) for w in weapons if w.get("kind") == "melee"]

    faction = ds.get("faction")
    name_zh = ds.get("name_zh") or (zh or {}).get("name_zh") or ds.get("name_en") or ""
    keywords = "，".join(str(k) for k in (ds.get("keywords") or []))

    return EntityCard(
        nameZh=str(name_zh),
        nameEn=str(ds.get("name_en") or ""),
        pts=_points_str(ds),
        stats=stats,
        ranged=ranged,
        melee=melee,
        abilities=_abilities(zh),
        composition=_composition(ds),
        keywords=keywords,
        faction="阵营: " + str(faction) if faction else "阵营: 未知",
        src="L3 结构库 · " + str(faction or "未知阵营"),
        wiki=_wiki_path(faction, str(ds.get("unit_id", "")), str(ds.get("name_en") or "")),
    )
