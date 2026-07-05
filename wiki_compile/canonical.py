# wiki_compile/canonical.py
"""Wahapedia CSV 下载与解析 —— 中英配对的 canonical 英文名锚点（spec 决策4）。"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

WAHAPEDIA_BASE = "https://wahapedia.ru/wh40k10ed"
TABLES = ("Factions.csv", "Datasheets.csv")


@dataclass(frozen=True)
class CanonicalEntry:
    id: str
    name: str
    faction_id: str


def parse_wahapedia_csv(text: str) -> List[Dict[str, str]]:
    """Wahapedia 导出：| 分隔、行尾多一个 |、首行表头、可能带 BOM。"""
    lines = [ln for ln in text.replace("﻿", "").splitlines() if ln.strip()]
    header = [h.strip() for h in lines[0].split("|")]
    rows: List[Dict[str, str]] = []
    for ln in lines[1:]:
        fields = ln.split("|")
        rows.append({h: (fields[i].strip() if i < len(fields) else "")
                     for i, h in enumerate(header) if h})
    return rows


def fetch_tables(dest: Path) -> None:
    """下载 canonical 表。需环境代理（HTTPS_PROXY），urllib 自动读取。"""
    dest.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        url = "{}/{}".format(WAHAPEDIA_BASE, table)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            (dest / table).write_bytes(resp.read())
        print("已下载", table)


def load_canonical(csv_dir: Path) -> List[CanonicalEntry]:
    rows = parse_wahapedia_csv(
        (csv_dir / "Datasheets.csv").read_text(encoding="utf-8"))
    return [CanonicalEntry(id=r.get("id", ""), name=r.get("name", ""),
                           faction_id=r.get("faction_id", ""))
            for r in rows if r.get("name")]
