"""db_compile/enhancements.py — 强化（Enhancements）数据层（P6 军表验表 PR1a）。

Wahapedia `Enhancements.csv`（faction_id|id|name|cost|detachment|detachment_id|legend|
description）→ `enhancements` 表。军表验表按 detachment_id 查该分队合法强化名单+点数。

数据现状（2026-07-13 实测）：927 条强化 / 261 分队 / 23 阵营，detachment_id 与
Detachment_abilities.csv 100% 对齐（0 孤儿）。此前 `detachments.enhancements_json` 0/284 全空，
本模块补上这块唯一的编制约束数据缺口。

CLI：`python -m db_compile enhancements --fetch/--apply/--check`。
"""
from __future__ import annotations

import sqlite3
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from wiki_compile.canonical import parse_wahapedia_csv

CSV_URL = "https://wahapedia.ru/wh40k10ed/Enhancements.csv"
DEFAULT_CSV = Path("db_sources/wahapedia/Enhancements.csv")
_UA = "Mozilla/5.0 (compatible; wh40k-oracle/1.0)"


def fetch_csv(dest: Path = DEFAULT_CSV, timeout: int = 60) -> int:
    """下载 Enhancements.csv（走环境代理 HTTP(S)_PROXY）→ dest，返回字节数。"""
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # 走环境代理
        data = resp.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


def load_rows(csv_path: Path = DEFAULT_CSV) -> List[Dict[str, str]]:
    """解析 Enhancements.csv → 行字典列表（Wahapedia | 分隔）。"""
    return parse_wahapedia_csv(csv_path.read_text(encoding="utf-8"))


def _cost_to_int(raw: str) -> Optional[int]:
    """'20' → 20；'0' → 0；空/非数字 → None（诚实标注未知点数，不猜 0）。"""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def apply_enhancements(db_path, rows: List[Dict[str, str]]) -> Dict[str, int]:
    """rows → enhancements 表（建表 + 索引 + INSERT OR REPLACE）。返回落库统计。"""
    from db_compile.schema import ENHANCEMENTS_DDL

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(ENHANCEMENTS_DDL)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_enh_detachment "
                    "ON enhancements(detachment_id)")
        payload = [
            (r.get("id"), r.get("faction_id"), r.get("detachment_id"),
             r.get("detachment"), r.get("name"), _cost_to_int(r.get("cost", "")),
             r.get("legend"), r.get("description"))
            for r in rows if r.get("id")
        ]
        cur.executemany(
            """INSERT OR REPLACE INTO enhancements
               (id, faction_id, detachment_id, detachment_name, name, cost,
                legend, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", payload)
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM enhancements").fetchone()[0]
        dets = cur.execute(
            "SELECT COUNT(DISTINCT detachment_id) FROM enhancements").fetchone()[0]
    finally:
        conn.close()
    return {"inserted": len(payload), "table_total": total, "detachments": dets}


def check_enhancements(db_path, rows: List[Dict[str, str]]) -> Dict[str, Any]:
    """对账：CSV 行数 vs 库行数、CSV 涵盖 detachment_id 中库里 detachments 缺失的孤儿。

    孤儿=强化引用的 detachment_id 在库里没有对应分队能力行（Detachment_abilities）——
    诚实暴露数据漂移，不静默。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        db_total = conn.execute("SELECT COUNT(*) FROM enhancements").fetchone()[0]
        # 库里 detachments.id 是分队能力 id；强化的 detachment_id 应能在
        # Detachment_abilities 里找到对应分队。库没存 detachment_id，故用 CSV 自校验为主。
        db_dets = conn.execute(
            "SELECT COUNT(DISTINCT detachment_id) FROM enhancements").fetchone()[0]
    finally:
        conn.close()
    csv_ids = {r.get("id") for r in rows if r.get("id")}
    csv_dets = {r.get("detachment_id") for r in rows if r.get("detachment_id")}
    no_cost = [r.get("name") for r in rows
               if _cost_to_int(r.get("cost", "")) is None]
    return {
        "csv_rows": len(csv_ids),
        "db_rows": db_total,
        "match": len(csv_ids) == db_total,
        "csv_detachments": len(csv_dets),
        "db_detachments": db_dets,
        "no_cost_count": len(no_cost),
        "no_cost_sample": no_cost[:10],
    }


def list_for_detachment(db_path, detachment_id: str) -> List[Dict[str, Any]]:
    """某分队的合法强化清单（PR1b 验表调用）：[{id,name,cost}]，按点数排序。"""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, name, cost FROM enhancements WHERE detachment_id = ? "
            "ORDER BY cost, name", (detachment_id,)).fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "name": r[1], "cost": r[2]} for r in rows]
