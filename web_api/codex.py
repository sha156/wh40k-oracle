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

from db_compile.calc_points import _min_points as _canonical_min_points
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


def _current_unit_ids(conn: sqlite3.Connection) -> set:
    """现役单位 id 集合 = 出现在官方现行 MFM 点数表 **或** 被黑图书馆收录。

    库里 1715 条来自 Wahapedia 全量，其中 553 条是 Legends / 福基世界 / 退环境条目
    （Karandras、Vampire Raider、Secutarii…），比赛里摆不上桌，默认不该占满图鉴。

    为什么要两个来源取并集而不是只看 MFM：官方 MFM 页只列 30 个阵营，**没有
    Harlequins 那一组**（实测 aeldari 81 条里无 Troupe/Solitaire/Death Jester），
    只按 MFM 判会把 199 个在售单位误归档。黑图书馆收录面≈在售单位，正好补上这个洞。
    """
    cur = set()
    for uid, pj in conn.execute("SELECT id, points_json FROM units"):
        try:
            if pj and (json.loads(pj) or {}).get("mfm"):
                cur.add(uid)
        except (json.JSONDecodeError, TypeError):
            continue
    for (uid,) in conn.execute("SELECT canonical_id FROM unit_zh_detail"):
        cur.add(uid)
    return cur


def list_factions(db_path, include_legacy: bool = False) -> List[Dict[str, Any]]:
    """有单位的阵营列表：{id, name, nameZh, count, legacyCount}，按单位数降序。

    count 默认只数现役单位（与列表口径一致，否则数字对不上会让人以为列表漏了）。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        current = _current_unit_ids(conn)
        rows = conn.execute(
            "SELECT f.id, f.name, u.id FROM factions f "
            "JOIN units u ON u.faction_id = f.id").fetchall()
        tally: Dict[str, List[int]] = {}
        names: Dict[str, str] = {}
        for fid, fname, uid in rows:
            names[fid] = fname
            slot = tally.setdefault(fid, [0, 0])
            if uid in current:
                slot[0] += 1
            else:
                slot[1] += 1
        out = [
            {"id": fid, "name": names[fid], "nameZh": _FACTION_ZH.get(fid),
             "count": (n_cur + n_leg) if include_legacy else n_cur,
             "legacyCount": n_leg}
            for fid, (n_cur, n_leg) in tally.items()
            if (n_cur + n_leg if include_legacy else n_cur) > 0
        ]
        out.sort(key=lambda f: -f["count"])
        return out
    finally:
        conn.close()


def _min_points(points_json: Optional[str]) -> Optional[int]:
    """列表页「N 分起」徽章的点数 = 基准档最小 cost。

    直接复用 db_compile.calc_points 的实现，**不另立第二套点数口径**——
    那边的语义（取 items[].cost 最小值、无 items 才回退顶层 points）是
    agent 的 calc_points 工具与兵牌页共用的权威口径。

    历史缺陷（第 3 轮审查 H1）：这里曾把 points_json 当 list of {"cost": …}
    迭代，而库里存的是 dict（`{"points":…, "items":[…], "mfm":…}`，同文件
    _current_unit_ids 就是按 dict 取 .get("mfm") 的）。迭代 dict 拿到的是 key
    字符串 ⇒ `isinstance(o, dict)` 恒 False ⇒ costs 恒空 ⇒ 全库 1715 个单位的
    pts 恒为 None，图鉴/模拟器/军表三处徽章分支从未走到过（无报错、无空位，
    页面看着完全正常）。所以这里禁止再手写一份解析。
    """
    if not points_json:
        return None
    return _canonical_min_points(points_json)


def list_units(db_path, faction_id: str,
               include_legacy: bool = False) -> List[Dict[str, Any]]:
    """某阵营单位列表：{id, nameEn, nameZh, pts, legacy}，按英文名排序。

    默认只列现役（见 _current_unit_ids）；include_legacy=True 时把传承条目一并返回，
    带 legacy=True 供前端标注——归档不是删除，直链单位页始终可访问。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        current = _current_unit_ids(conn)
        rows = conn.execute(
            "SELECT id, name_en, name_zh, points_json FROM units "
            "WHERE faction_id = ? ORDER BY name_en",
            (faction_id,),
        ).fetchall()
        out = []
        for uid, en, zh, pj in rows:
            legacy = uid not in current
            if legacy and not include_legacy:
                continue
            pmin = _min_points(pj)
            out.append({
                "id": uid, "nameEn": en, "nameZh": zh,
                "pts": ("{} 分起".format(pmin) if pmin is not None else None),
                "legacy": legacy,
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
    """zh 模式：用**落库的** weapons.name_zh 覆盖武器名（原地改 ds_dict['weapons']）。

    2026-07-25 改法：旧实现在渲染时把黑图的中文武器列表按 kind 内**位置**贴到英文行上，
    只用"数量相等"当守卫——挡不住顺序不同的情形，战斗修女小队因此把「爆弹手枪」贴到了
    Ministorum hand flamer（A=D6/BS=N/A）那一行。数值对、名字错，用户无从察觉。
    现在配对在离线侧按数值指纹做（db_compile/zh_weapons.py），配不上就留空 → 显示英文。

    数值永远用英文权威表（黑图数值有漂移，如智能导弹 A=3 vs 官方 4），这里只换 name。
    返回 en→zh 武器名映射（供 loadout 文本翻译复用）。"""
    name_map: Dict[str, str] = {}
    for w in ds_dict.get("weapons") or []:
        zh_name = str(w.get("name_zh") or "").strip()
        en_name = str(w.get("name") or "").strip()
        if zh_name and en_name:
            name_map[en_name] = zh_name
            w["name"] = zh_name
    return name_map


def _localize_weapon_keywords(conn: sqlite3.Connection, ds_dict: Dict[str, Any]) -> None:
    """zh 模式：武器关键词（USR）按对照表逐词翻译，查不到的保英文。

    对照表是离线从**单关键词对单关键词**的行学来的（db_compile.zh_weapons），
    逐词查表没有对齐问题——USR 是封闭小词表，不像武器名那样每单位不同。
    """
    try:
        gloss = {en: zh for en, zh in conn.execute(
            "SELECT term_en, term_zh FROM zh_keyword_glossary")}
    except sqlite3.OperationalError:
        return                      # 老库没这张表：保英文，不报错
    if not gloss:
        return
    for w in ds_dict.get("weapons") or []:
        kws = w.get("keywords") or []
        if not kws:
            continue
        out: List[str] = []
        for k in kws:
            # 库里一格常是「heavy, devastating wounds」这种逗号串，先拆再逐词查
            for part in str(k).split(","):
                token = part.strip()
                if token:
                    out.append(gloss.get(token.upper(), token))
        w["keywords"] = out


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
            _localize_weapon_keywords(conn, ds_dict)
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
