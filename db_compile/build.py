"""db_sources/wahapedia/*.csv → wh40k.sqlite（L3 核心表导入，蓝图 P2）。

支持全部 11 张 Wahapedia 导出 CSV（除 Wargear.csv 永 404 外，其余均可从官网获取）：
  Factions.csv + Datasheets.csv        → factions / datasheets / units (基本骨架)
  Datasheets_models.csv                → models (M/T/Sv/W/LD/OC 属性)
  Datasheets_models_cost.csv           → units.points_json (点数)
  Datasheets_wargear.csv              → weapons (武器数据，含 name+stats inline)
  Datasheets_abilities.csv             → abilities (单位→技能关联)
  Abilities.csv                        → abilities (通用技能主表)
  Stratagems.csv                       → stratagems
  Detachment_abilities.csv             → detachments
  Datasheets_keywords.csv              → units.keywords_json (关键词)
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from wiki_compile.canonical import parse_wahapedia_csv

from db_compile.schema import ALL_DDL

# Wahapedia 官方导出全集（spec 第四节「~20张关系表」的核心子集）。
# Wargear.csv 永 404——但 Datasheets_wargear.csv 已内联 name+stats，不影响武器导入。
EXPECTED_CSV = (
    "Factions.csv",
    "Datasheets.csv",
    "Datasheets_models.csv",
    "Datasheets_models_cost.csv",
    "Datasheets_wargear.csv",
    "Wargear.csv",
    "Datasheets_abilities.csv",
    "Abilities.csv",
    "Stratagems.csv",
    "Detachment_abilities.csv",
    "Datasheets_keywords.csv",
)

# Wargear.csv 已知永久 404，从警告列表排除
KNOWN_MISSING = {"Wargear.csv"}


@dataclass
class BuildReport:
    row_counts: Dict[str, int] = field(default_factory=dict)
    missing_csv: List[str] = field(default_factory=list)
    # 因缺 id 被跳过的行数（按表披露），如 {"factions": 2}——不静默丢
    skipped: Dict[str, int] = field(default_factory=dict)


def _read_csv(path: Path) -> List[dict]:
    return parse_wahapedia_csv(path.read_text(encoding="utf-8"))


def _load_name_zh_by_id(terms_path: Optional[Path]) -> Dict[str, str]:
    """wiki/terms.json: canonical_id → name_zh（wiki_compile 已配对的中文名）。"""
    if terms_path is None or not terms_path.exists():
        return {}
    try:
        data = json.loads(terms_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {p["canonical_id"]: p["zh"] for p in data.get("pairs", [])
            if isinstance(p, dict) and p.get("zh") and p.get("canonical_id")}


def _insert_factions(cur, rows: List[dict]) -> Tuple[int, int]:
    """→ (写入行数, 缺 id 跳过行数)。缺 id 列/空 id 不崩、计数披露（防御风格同 _insert_abilities）。"""
    valid = [r for r in rows if r.get("id")]
    cur.executemany(
        "INSERT OR REPLACE INTO factions (id, name, link) VALUES (?, ?, ?)",
        [(r["id"], r.get("name", ""), r.get("link")) for r in valid])
    return len(valid), len(rows) - len(valid)


def _insert_datasheets(cur, rows: List[dict],
                       name_zh_by_id: Dict[str, str]) -> Tuple[int, int]:
    """→ (写入行数, 缺 id 跳过行数)。"""
    valid = [r for r in rows if r.get("id")]
    cur.executemany(
        """INSERT OR REPLACE INTO datasheets
           (id, name, faction_id, source_id, legend, role, loadout,
            transport, virtual, leader_head, leader_footer,
            damaged_w, damaged_description, link)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(r["id"], r.get("name", ""), r.get("faction_id"),
          r.get("source_id"), r.get("legend"), r.get("role"),
          r.get("loadout"), r.get("transport"), r.get("virtual"),
          r.get("leader_head"), r.get("leader_footer"),
          r.get("damaged_w"), r.get("damaged_description"),
          r.get("link"))
         for r in valid])
    # units 表同步
    cur.executemany(
        """INSERT OR REPLACE INTO units
           (id, faction_id, name_en, name_zh, points_json, keywords_json, version)
           VALUES (?, ?, ?, ?, NULL, NULL, NULL)""",
        [(r["id"], r.get("faction_id"), r.get("name", ""),
          name_zh_by_id.get(r["id"]))
         for r in valid])
    return len(valid), len(rows) - len(valid)


def _insert_models(cur, rows: List[dict]) -> int:
    cur.executemany(
        """INSERT OR REPLACE INTO models
           (unit_id, name, m, t, sv, invuln, w, ld, oc)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(r.get("datasheet_id"), r.get("name", ""),
          r.get("M"), r.get("T"), r.get("Sv"),
          r.get("inv_sv"), r.get("W"), r.get("Ld"), r.get("OC"))
         for r in rows])
    return len(rows)


def _insert_points(cur, rows: List[dict]) -> int:
    """按 datasheet_id 分组累加点数，回写 units.points_json。

    用一个 datasheet 内所有模型/选项的 cost 之和作为总点数，
    同时保存明细用于验证。
    """
    groups: Dict[str, list] = defaultdict(list)
    for r in rows:
        ds_id = r.get("datasheet_id")
        if ds_id:
            groups[ds_id].append({
                "line": r.get("line"),
                "desc": r.get("description", ""),
                "cost": int(r.get("cost", 0)) if r.get("cost") else 0,
            })
    updated = 0
    for ds_id, items in groups.items():
        total = sum(item["cost"] for item in items)
        payload = json.dumps({"points": total, "items": items}, ensure_ascii=False)
        cur.execute(
            "UPDATE units SET points_json = ? WHERE id = ?",
            (payload, ds_id))
        if cur.rowcount > 0:
            updated += 1
    return updated


def _insert_weapons(cur, rows: List[dict]) -> int:
    """从 Datasheets_wargear.csv 导入武器数据。

    无单独 Wargear.csv 主表，武器名+属性已内联在此 CSV 中。
    武器 ID 用 {datasheet_id}_w{单位内序号}——不能用 CSV 的 line 列：大量行（如
    Chaos Lord 等 300 个 datasheet）line 为空，旧代码据此错误跳过 2007 行武器；
    且同一单位多把武器 line_in_wargear 常全为 1，单用任一列都会 id 冲突被折叠。
    """
    count = 0
    seq: dict = {}
    for r in rows:
        ds_id = r.get("datasheet_id")
        # 将 description 列（武器技能如 "anti-infantry 4+, devastating wounds"）
        # 序列化到 keywords_json
        kw = r.get("description", "").strip()
        name = r.get("name", "").strip()
        if not ds_id or not name:
            continue
        seq[ds_id] = seq.get(ds_id, 0) + 1
        weapon_id = f"{ds_id}_w{seq[ds_id]}"
        cur.execute(
            """INSERT OR REPLACE INTO weapons
               (id, unit_id, name_en, range, a, bs_ws, s, ap, d, keywords_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (weapon_id, ds_id, name,
             r.get("range", ""), r.get("A", ""),
             r.get("BS_WS", ""), r.get("S", ""),
             r.get("AP", ""), r.get("D", ""),
             json.dumps([kw], ensure_ascii=False) if kw else None,
             ))
        count += 1
    return count


def _insert_abilities(cur, master_rows: List[dict],
                      link_rows: List[dict]) -> int:
    """导入技能：主表 Abilities.csv（全局技能）+ Datasheets_abilities.csv（单位链接）。

    Abilities.csv 中每条有一个唯一 id。Datasheets_abilities.csv 引用这个 id 并补充
    单位级上下文（scope/name/description）。两者合并到 abilities 表。
    """
    count = 0
    # 先把主表写入（owner_id=NULL）
    for r in master_rows:
        aid = r.get("id")
        if not aid:
            continue
        cur.execute(
            """INSERT OR REPLACE INTO abilities
               (id, name_en, text_zh, dsl_status)
               VALUES (?, ?, ?, 'not_modeled')""",
            (aid, r.get("name", ""), r.get("description", "")))
        count += 1

    # 再写单位链接（owner_id=datasheet_id，补充 scope、可能重载 name/description）。
    # 关键：链接行的主键必须每(单位,技能)对唯一，否则以 ability_id 为主键会被
    # INSERT OR REPLACE 折叠——一个技能被多个单位共享时只剩最后一个单位（7158 行→48 行，
    # 丢失约 3500 条单位→技能关联）。改用「单位内递增序号」做主键（同 weapons 的修法），
    # 并以 name 为准（不再要求 ability_id 非空，保住 3600+ 条无全局 id 的单位专属技能）。
    ab_seq: dict = {}
    for r in link_rows:
        ds_id = r.get("datasheet_id")
        name = (r.get("name") or "").strip()
        if not ds_id or not name:
            continue
        ab_seq[ds_id] = ab_seq.get(ds_id, 0) + 1
        row_id = f"{ds_id}_a{ab_seq[ds_id]}"
        scope = r.get("model", "")  # Core / Faction / Leader
        cur.execute(
            """INSERT OR REPLACE INTO abilities
               (id, owner_id, scope, name_en, text_zh, dsl_status)
               VALUES (?, ?, ?, ?, ?, 'not_modeled')""",
            (row_id, ds_id, scope, name, r.get("description", "")))
        count += 1
    return count


def _insert_stratagems(cur, rows: List[dict]) -> int:
    cur.executemany(
        """INSERT OR REPLACE INTO stratagems
           (id, faction, detachment, name_en, cp_cost, phase, text_zh, dsl_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'not_modeled')""",
        [(r.get("id"), r.get("faction_id"), r.get("detachment"),
          r.get("name"), r.get("cp_cost"), r.get("phase"),
          r.get("description"))
         for r in rows if r.get("id")])
    return len(rows)


def _insert_detachments(cur, rows: List[dict]) -> int:
    cur.executemany(
        """INSERT OR REPLACE INTO detachments
           (id, faction, name_en, rule_text)
           VALUES (?, ?, ?, ?)""",
        [(r.get("id"), r.get("faction_id"),
          r.get("name"), r.get("description"))
         for r in rows if r.get("id")])
    return len(rows)


def _insert_keywords(cur, rows: List[dict]) -> int:
    """按 datasheet_id 分组，分别聚合 faction/non-faction keywords 到 JSON。

    Datasheets_keywords.csv 约 15877 行，对应约 1712 个 datasheet。
    """
    groups: Dict[str, Dict[str, list]] = defaultdict(
        lambda: {"keywords": [], "faction_keywords": []})
    for r in rows:
        ds_id = r.get("datasheet_id")
        kw = r.get("keyword", "").strip()
        if not ds_id or not kw:
            continue
        if r.get("is_faction_keyword", "").strip().lower() == "true":
            groups[ds_id]["faction_keywords"].append(kw)
        else:
            groups[ds_id]["keywords"].append(kw)

    updated = 0
    for ds_id, data in groups.items():
        payload = json.dumps(data, ensure_ascii=False)
        cur.execute(
            "UPDATE units SET keywords_json = ? WHERE id = ?",
            (payload, ds_id))
        if cur.rowcount > 0:
            updated += 1
    return updated


def build_database(csv_dir: Path, db_path: Path,
                    terms_path: Optional[Path] = None) -> BuildReport:
    """建表并导入当前已有的 CSV。

    缺失的 CSV（Wargear.csv 除外）计入 missing_csv；已有数据的表如实导入行数；
    缺 id 被跳过的行计入 skipped 披露。

    原子替换：先写 `<db>.tmp.sqlite`，全部导入成功 commit 后 os.replace 到 db_path；
    中途任何失败删临时文件、旧库保持原样（旧实现先 unlink 旧库，崩溃留残缺 db）。
    """
    csv_dir = Path(csv_dir)
    report = BuildReport(
        missing_csv=[name for name in EXPECTED_CSV
                     if name not in KNOWN_MISSING
                     and not (csv_dir / name).exists()])

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_suffix(".tmp.sqlite")
    if tmp_path.exists():
        tmp_path.unlink()

    try:
        conn = sqlite3.connect(str(tmp_path))
        try:
            cur = conn.cursor()
            for ddl in ALL_DDL:
                cur.execute(ddl)

            name_zh_by_id = _load_name_zh_by_id(terms_path)

            # 1. Factions
            path = csv_dir / "Factions.csv"
            if path.exists():
                n, skipped = _insert_factions(cur, _read_csv(path))
                report.row_counts["factions"] = n
                if skipped:
                    report.skipped["factions"] = skipped

            # 2. Datasheets + Units
            path = csv_dir / "Datasheets.csv"
            if path.exists():
                n, skipped = _insert_datasheets(
                    cur, _read_csv(path), name_zh_by_id)
                report.row_counts["datasheets"] = n
                report.row_counts["units"] = n
                if skipped:
                    report.skipped["datasheets"] = skipped

            # 3. Models
            path = csv_dir / "Datasheets_models.csv"
            if path.exists():
                report.row_counts["models"] = _insert_models(
                    cur, _read_csv(path))

            # 4. Points (回写 units.points_json)
            path = csv_dir / "Datasheets_models_cost.csv"
            if path.exists():
                report.row_counts["points_updated"] = _insert_points(
                    cur, _read_csv(path))

            # 5. Weapons
            path = csv_dir / "Datasheets_wargear.csv"
            if path.exists():
                report.row_counts["weapons"] = _insert_weapons(
                    cur, _read_csv(path))

            # 6. Abilities (主表 + 单位链接)
            path_m = csv_dir / "Abilities.csv"
            path_l = csv_dir / "Datasheets_abilities.csv"
            if path_m.exists() or path_l.exists():
                master_rows = _read_csv(path_m) if path_m.exists() else []
                link_rows = _read_csv(path_l) if path_l.exists() else []
                n_total = _insert_abilities(cur, master_rows, link_rows)
                report.row_counts["abilities"] = n_total

            # 7. Stratagems
            path = csv_dir / "Stratagems.csv"
            if path.exists():
                report.row_counts["stratagems"] = _insert_stratagems(
                    cur, _read_csv(path))

            # 8. Detachments
            path = csv_dir / "Detachment_abilities.csv"
            if path.exists():
                report.row_counts["detachments"] = _insert_detachments(
                    cur, _read_csv(path))

            # 9. Keywords (回写 units.keywords_json)
            path = csv_dir / "Datasheets_keywords.csv"
            if path.exists():
                report.row_counts["keywords_updated"] = _insert_keywords(
                    cur, _read_csv(path))

            conn.commit()
        finally:
            conn.close()
        # 全部成功才替换正式库（Windows 上 os.replace 同卷原子）
        os.replace(str(tmp_path), str(db_path))
    except BaseException:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass  # 临时文件清理失败不掩盖原始异常
        raise
    return report
