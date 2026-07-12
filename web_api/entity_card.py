"""web_api/entity_card.py — get_datasheet 返回 dict → EntityCard（E6，确定性映射）。

数据全部来自 L3 结构库（英文权威真值 + 可选黑图中文层），零 LLM。诚实红线：
- datasheet 不含 book/page → `src` 如实标「L3 结构库 · <阵营>」，绝不编造页码。
- 能力文本黑图中文层常为空 → abilities 留空数组，不编能力描述。
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional

from web_api.contract import Ability, DamagedProfile, EntityCard, Stat, WeaponRow
from web_api.richtext import to_richtext


def _strip_html(s: Optional[str]) -> str:
    """去 HTML 标签 + 反转义实体，压缩空白。官方字段（loadout/能力文本）常带 <b>/<span>。"""
    if not s:
        return ""
    text = re.sub(r"<[^>]+>", "", str(s))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fmt_range(val: str, lang: str = "zh") -> str:
    """'60' → '60\"'；'Melee' → zh 模式译「近战」、en 模式原样；其余原样。"""
    v = (val or "").strip()
    if v.isdigit():
        return v + '"'
    if v.lower() == "melee":
        return "近战" if lang == "zh" else "Melee"
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


def _weapon_row(w: Dict[str, Any], hot_weapon: Optional[str], lang: str = "zh") -> WeaponRow:
    name = str(w.get("name", ""))
    hot = bool(hot_weapon) and hot_weapon.lower() in name.lower()
    return WeaponRow(
        name=name,
        kw=_weapon_kw(w.get("keywords", [])),
        range=_fmt_range(str(w.get("range", "")), lang),
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


def _composition(ds: Dict[str, Any], lang: str = "zh"):
    """points_options → 每行 RichText（'1 个模型 — 75 分' / '1 model — 75 pts'）。"""
    unit = "分" if lang == "zh" else "pts"
    rows = []
    for o in ds.get("points_options") or []:
        desc = str(o.get("desc", "")).strip()
        cost = o.get("cost")
        line = desc if desc else str(o.get("line", ""))
        if cost is not None:
            line = "{} — {} {}".format(line, cost, unit)
        rows.append(to_richtext(line))
    return rows


def _split_tag(name: str):
    """『【阵营技能】：破敌重誓』→ (tag='阵营技能', name='破敌重誓')；无标签则 (None, name)。"""
    m = re.match(r"^【(?P<tag>[^】]+)】[:：]?\s*(?P<rest>.*)$", name.strip())
    if m:
        return m.group("tag"), (m.group("rest").strip() or m.group("tag"))
    return None, name.strip()


def _zh_abilities(zh: Optional[Dict[str, Any]]) -> List[Ability]:
    """黑图中文层 abilities_json → Ability 列表（本地化，含阵营技能）。"""
    if not zh:
        return []
    raw = zh.get("能力") or zh.get("abilities")
    if not isinstance(raw, list):
        return []
    out: List[Ability] = []
    for item in raw:
        if isinstance(item, str):
            tag, nm = _split_tag(item)
            out.append(Ability(tag=tag, name=nm))
        elif isinstance(item, dict):
            nm = str(item.get("name") or item.get("标题") or item.get("title") or "")
            if not nm:
                continue
            tag, nm2 = _split_tag(nm)
            text = _strip_html(item.get("contentHtml")) or _flatten_content(item.get("content"))
            out.append(Ability(tag=tag, name=nm2, text=text or None))
    return out


def _flatten_content(content: Any) -> str:
    """黑图 content 嵌套结构 → 纯文本（兜底，contentHtml 缺时用）。"""
    if not isinstance(content, list):
        return ""
    parts: List[str] = []
    for block in content:
        if isinstance(block, dict):
            inner = block.get("content")
            if isinstance(inner, list):
                for span in inner:
                    if isinstance(span, dict) and span.get("text"):
                        parts.append(str(span["text"]))
    return " ".join(parts).strip()


def _eng_abilities(raw: Any) -> List[Ability]:
    """abilities 表条目 [{name_en/name, text/text_zh}] → Ability 列表（英文，完整覆盖）。"""
    if not isinstance(raw, list):
        return []
    out: List[Ability] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        nm = str(item.get("name_en") or item.get("name") or "").strip()
        if not nm:
            continue
        text = _strip_html(item.get("text") or item.get("text_zh"))
        out.append(Ability(name=nm, text=text or None))
    return out


def _abilities(zh: Optional[Dict[str, Any]], eng: Any) -> List[Ability]:
    """能力列表：中文层若不比英文表少则用中文（本地化优先），否则用英文表（完整）。

    英文 abilities 表覆盖 1709/1715 单位，是完整权威源；黑图中文层稀疏但已本地化。
    以「谁更全」二选一，避免跨语言无法可靠去重造成的重复。"""
    zh_abils = _zh_abilities(zh)
    eng_abils = _eng_abilities(eng)
    if zh_abils and len(zh_abils) >= len(eng_abils):
        return zh_abils
    return eng_abils


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
        invuln_val = invuln + "+" if invuln.isdigit() else invuln
    else:
        invuln_val = None

    lang = str(tool_result.get("lang") or "zh")
    weapons = ds.get("weapons") or []
    ranged = [_weapon_row(w, hot_weapon, lang) for w in weapons if w.get("kind") == "ranged"]
    melee = [_weapon_row(w, hot_weapon, lang) for w in weapons if w.get("kind") == "melee"]

    faction = ds.get("faction")
    name_zh = ds.get("name_zh") or (zh or {}).get("name_zh") or ds.get("name_en") or ""
    keywords = "，".join(str(k) for k in (ds.get("keywords") or []))

    # 官方元信息（codex 装配时提供；chat 的 get_datasheet 无则留空，向后兼容）
    meta = tool_result.get("meta") or {}
    _role_raw = _strip_html(meta.get("role"))
    role = _role_raw if _role_raw and _role_raw.lower() != "other" else None
    loadout = _strip_html(meta.get("loadout")) or None
    legend = _strip_html(meta.get("legend")) or None
    leads = _strip_html(meta.get("leader_footer")) or None
    dmg_w = str(meta.get("damaged_w") or "").strip()
    dmg_text = _strip_html(meta.get("damaged_description"))
    damaged = DamagedProfile(w=dmg_w, text=dmg_text) if (dmg_w and dmg_text) else None
    fkw = tool_result.get("faction_keywords") or []
    faction_keywords = "，".join(str(k) for k in fkw) or None

    return EntityCard(
        nameZh=str(name_zh),
        nameEn=str(ds.get("name_en") or ""),
        pts=_points_str(ds),
        role=role,
        stats=stats,
        invuln=invuln_val,
        ranged=ranged,
        melee=melee,
        abilities=_abilities(zh, tool_result.get("abilities")),
        loadout=loadout,
        damaged=damaged,
        leads=leads,
        composition=(
            [to_richtext(line) for line in tool_result["zh_composition"]]
            if tool_result.get("zh_composition")
            else _composition(ds, lang)
        ),
        keywords=keywords,
        factionKeywords=faction_keywords,
        legend=legend,
        faction="阵营: " + str(faction) if faction else "阵营: 未知",
        src="L3 结构库 · " + str(faction or "未知阵营"),
        wiki=_wiki_path(faction, str(ds.get("unit_id", "")), str(ds.get("name_en") or "")),
    )
