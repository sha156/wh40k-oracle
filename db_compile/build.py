"""db_sources/wahapedia/*.csv → wh40k.sqlite（L3 核心表导入，蓝图 P2）。"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from wiki_compile.canonical import parse_wahapedia_csv

from db_compile.schema import ALL_DDL

# Wahapedia 官方导出全集（spec 第四节「~20张关系表」的核心子集）。
# db_sources/wahapedia/ 目前只有前两张，其余在 db_sources/wahapedia/README 或
# notes.md 里记为「待下载清单」，不联网补齐（无人值守约束）。
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


@dataclass
class BuildReport:
    row_counts: Dict[str, int] = field(default_factory=dict)
    missing_csv: List[str] = field(default_factory=list)


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


def build_database(csv_dir: Path, db_path: Path,
                    terms_path: Optional[Path] = None) -> BuildReport:
    """建表并导入当前已有的 CSV。缺失的表只建结构，不写入行，计入 missing_csv。"""
    csv_dir = Path(csv_dir)
    report = BuildReport(
        missing_csv=[name for name in EXPECTED_CSV
                     if not (csv_dir / name).exists()])

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        for ddl in ALL_DDL:
            cur.execute(ddl)

        factions_path = csv_dir / "Factions.csv"
        if factions_path.exists():
            rows = [r for r in _read_csv(factions_path) if r.get("id")]
            cur.executemany(
                "INSERT OR REPLACE INTO factions (id, name, link) VALUES (?, ?, ?)",
                [(r["id"], r.get("name", ""), r.get("link")) for r in rows])
            report.row_counts["factions"] = len(rows)

        datasheets_path = csv_dir / "Datasheets.csv"
        if datasheets_path.exists():
            name_zh_by_id = _load_name_zh_by_id(terms_path)
            rows = [r for r in _read_csv(datasheets_path) if r.get("id")]
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
                 for r in rows])
            cur.executemany(
                """INSERT OR REPLACE INTO units
                   (id, faction_id, name_en, name_zh, points_json, keywords_json, version)
                   VALUES (?, ?, ?, ?, NULL, NULL, NULL)""",
                [(r["id"], r.get("faction_id"), r.get("name", ""),
                  name_zh_by_id.get(r["id"]))
                 for r in rows])
            report.row_counts["datasheets"] = len(rows)
            report.row_counts["units"] = len(rows)

        conn.commit()
    finally:
        conn.close()
    return report
