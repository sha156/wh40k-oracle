"""web_api/codex.py — 图鉴（L3 结构库只读浏览，BUILD-PLAN Stage 4）。

阵营列表 → 单位列表 → 单位兵牌（复用 build_entity_card）。全部只读查 sqlite，零 LLM。
中文阵营名从 unit_zh_detail.faction_zh 取众数（英文 factions 表无中文名）。
"""
from __future__ import annotations

import json
import re
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


def _load_abilities(conn: sqlite3.Connection, unit_id: str) -> List[Dict[str, Any]]:
    """abilities 表（英文权威、完整覆盖）→ [{name_en, text}]，按插入序。"""
    try:
        rows = conn.execute(
            "SELECT name_en, name_zh, text_zh FROM abilities WHERE owner_id = ? "
            "ORDER BY rowid", (unit_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [{"name_en": r[0] or r[1] or "", "text": r[2] or ""} for r in rows]


def _load_meta(conn: sqlite3.Connection, unit_id: str) -> Dict[str, Any]:
    """datasheets 表官方元信息：战场角色/装备/背景/受损档/可带首领。"""
    try:
        r = conn.execute(
            "SELECT role, loadout, legend, damaged_w, damaged_description, leader_footer "
            "FROM datasheets WHERE id = ?", (unit_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return {}
    if not r:
        return {}
    return {
        "role": r[0], "loadout": r[1], "legend": r[2],
        "damaged_w": r[3], "damaged_description": r[4], "leader_footer": r[5],
    }


def _load_faction_keywords(conn: sqlite3.Connection, unit_id: str) -> List[str]:
    """units.keywords_json 里的 faction_keywords。"""
    r = conn.execute("SELECT keywords_json FROM units WHERE id = ?", (unit_id,)).fetchone()
    if not r or not r[0]:
        return []
    try:
        data = json.loads(r[0])
    except (json.JSONDecodeError, TypeError):
        return []
    return data.get("faction_keywords") or []


def _localize_weapon_names(
    ds_dict: Dict[str, Any], zh: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """zh 模式：黑图中文层武器名/关键词覆盖到英文武器行（原地改 ds_dict['weapons']）。

    诚实约束：数值永远用英文权威表（黑图数值有漂移，如智能导弹 A=3 vs 官方 4），
    只换 name 与 keywords 显示；按 kind 内位置匹配，且**数量不等则整组不换**——
    错配的中文名比英文名更糟（自信的错误）。

    返回 en→zh 武器名映射（供 loadout 文本翻译复用）。"""
    name_map: Dict[str, str] = {}
    if not zh:
        return name_map
    wj = zh.get("武器") or {}
    if not isinstance(wj, dict):
        return name_map
    kind_map = {"ranged": wj.get("射击武器") or [], "melee": wj.get("近战武器") or []}
    weapons = ds_dict.get("weapons") or []
    for kind, zh_rows in kind_map.items():
        idx = [i for i, w in enumerate(weapons) if w.get("kind") == kind]
        if not zh_rows or len(idx) != len(zh_rows):
            continue  # 数量不等：不换，保英文
        for i, zh_row in zip(idx, zh_rows):
            nm = str((zh_row or {}).get("name") or "").strip()
            if nm:
                en_name = str(weapons[i].get("name") or "").strip()
                if en_name:
                    name_map[en_name] = nm
                weapons[i]["name"] = nm
            kw = (zh_row or {}).get("skill")
            if isinstance(kw, list) and kw:
                weapons[i]["keywords"] = [str(k) for k in kw]
    return name_map


_LOADOUT_PREFIXES = [
    ("Every model is equipped with:", "每个模型装备："),
    ("This model is equipped with:", "本模型装备："),
    ("This unit is equipped with:", "本单位装备："),
]


def _localize_loadout(loadout: str, name_map: Dict[str, str]) -> str:
    """zh 模式：装备文本前缀 + 武器名按映射翻译；映射不到的名字保英文（诚实）。"""
    if not loadout:
        return loadout
    from web_api.entity_card import _strip_html
    out = _strip_html(loadout)  # 原文带 <b> 标签，先剥再翻（否则「：</b> 」清不掉空格）
    for en, zh_txt in _LOADOUT_PREFIXES:
        out = re.sub(re.escape(en), zh_txt, out, flags=re.IGNORECASE)
    # 长名优先替换，避免「gauss cannon」抢先命中「twin gauss cannon」的子串
    for en in sorted(name_map, key=len, reverse=True):
        out = re.sub(re.escape(en), name_map[en], out, flags=re.IGNORECASE)
    out = out.replace("; ", "；").replace(";", "；").replace("： ", "：")
    if out.rstrip().endswith("."):
        out = out.rstrip()[:-1] + "。"
    return out


def _load_zh_composition(conn: sqlite3.Connection, unit_id: str) -> List[str]:
    """intro_json 的「单位构成」区块 → 原生中文构成行（如 '1 艘毁灭炮艇，95分'）。"""
    try:
        r = conn.execute(
            "SELECT intro_json FROM unit_zh_detail WHERE canonical_id = ?", (unit_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return []
    if not r or not r[0]:
        return []
    try:
        blocks = json.loads(r[0])
    except (json.JSONDecodeError, TypeError):
        return []
    lines: List[str] = []
    in_section = False
    for b in blocks if isinstance(blocks, list) else []:
        t = b.get("type") if isinstance(b, dict) else None
        if t == "h3":
            in_section = str(b.get("content", "")).strip() == "单位构成"
            continue
        if in_section and isinstance(b.get("content"), list):
            txt = " ".join(
                str(s.get("text", "")) for s in b["content"] if isinstance(s, dict)
            ).strip()
            if txt:
                lines.append(txt)
    return lines


def _localize_composition(ds_dict: Dict[str, Any]) -> None:
    """zh 模式：points_options 的 'N models' → 'N 个模型'（原地改）。"""
    for o in ds_dict.get("points_options") or []:
        o["desc"] = re.sub(r"\bmodels?\b", "个模型", str(o.get("desc") or ""))


def unit_card(
    db_path, unit_id: str, lang: str = "zh", hot_weapon: Optional[str] = None,
) -> Optional[EntityCard]:
    """单位 id → 完整 EntityCard（属性/武器/能力/装备/受损档/关键词，复用 build_entity_card）。

    lang="zh"（默认）：能力/武器名/构成尽量本地化（黑图中文层，覆盖不到保英文）；
    lang="en"：全英文（能力一律 abilities 表、武器名英文）。
    数值两种模式都用英文权威表。未找到返回 None。"""
    from db_compile.blacklibrary import load_zh_detail
    from db_compile.datasheet import lookup_datasheet

    ds = lookup_datasheet(db_path, unit_id)
    if ds is None:
        return None
    conn = sqlite3.connect(str(db_path))
    try:
        zh = load_zh_detail(db_path, unit_id)
        ds_dict = asdict(ds)
        meta = _load_meta(conn, unit_id)
        zh_composition: List[str] = []
        if lang == "zh":
            name_map = _localize_weapon_names(ds_dict, zh)
            _localize_composition(ds_dict)
            if meta.get("loadout"):
                meta["loadout"] = _localize_loadout(str(meta["loadout"]), name_map)
            # 背景文案无中文源：zh 模式不硬塞英文抒情段（切 EN 一键可看），诚实不机翻
            meta["legend"] = None
            # 原生中文构成（intro_json，含正确量词「1 艘毁灭炮艇，95分」）优先
            zh_composition = _load_zh_composition(conn, unit_id)
        res = {
            "found": True,
            "datasheet": ds_dict,
            # en 模式不给中文层 → _abilities 走英文表、name_zh 仍由 datasheet 提供
            "datasheet_zh": zh if lang == "zh" else None,
            "abilities": _load_abilities(conn, unit_id),
            "meta": meta,
            "faction_keywords": _load_faction_keywords(conn, unit_id),
            "zh_composition": zh_composition,
            "lang": lang,
        }
    finally:
        conn.close()
    return build_entity_card(res, hot_weapon)


def faction_exists(db_path, faction_id: str) -> bool:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(
            "SELECT 1 FROM factions WHERE id = ? LIMIT 1", (faction_id,)
        ).fetchone() is not None
    finally:
        conn.close()
