"""aliases：中文别名层——从 data_refined 双语标题提取「中文名→canonical_id」灌进 aliases 表。

架构：英文是权威真值，中文是叠在上面的多版本别名层。中文来自汉化 PDF 的 llm_refine
产物 data_refined，标题格式 `## 中文名 ENGLISH NAME`（如 `## 刀虫 HORMAGAUNTS`）。
中文 → 英文（从标题）→ canonical_id（精确匹配 units.name_en）→ 写入 aliases 表。

aliases 表 schema 天生支持多→一（主键 alias+lang+source），可容纳多个汉化组的不同译名。
本模块只灌 source='data_refined'，幂等（重跑先清同源旧行）。en 匹配不到的诚实计数、不硬塞。
"""
from __future__ import annotations

import glob
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

from wiki_compile.extract import parse_heading

_CJK = re.compile(r"[一-鿿]")
_LATIN = re.compile(r"[A-Za-z]")
SOURCE = "data_refined"


def harvest_bilingual_pairs(data_refined_dir) -> List[Tuple[str, str]]:
    """扫 data_refined 全部 md 的 `## 中文 ENGLISH` 标题，提取带中文的 (zh, en) 去重对。"""
    pairs: List[Tuple[str, str]] = []
    pattern = os.path.join(str(data_refined_dir), "**", "*.md")
    for f in glob.glob(pattern, recursive=True):
        try:
            text = Path(f).read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if not line.startswith("## "):
                continue
            zh, en = parse_heading(line[3:].strip())
            if zh and en and _CJK.search(zh) and _LATIN.search(en):
                pairs.append((zh.strip(), en.strip()))
    return list(dict.fromkeys(pairs))


def populate_aliases(db_path, data_refined_dir) -> Dict[str, int]:
    """把 (中文→canonical_id) 灌进 aliases 表。en 精确匹配 units.name_en（大小写不敏感）。

    幂等：先删本源旧行再写。返回 {harvested, matched, unmatched}。
    """
    pairs = harvest_bilingual_pairs(data_refined_dir)
    conn = sqlite3.connect(str(db_path))
    try:
        en2id = {
            (name or "").strip().lower(): cid
            for cid, name in conn.execute("SELECT id, name_en FROM units")
            if name
        }
        conn.execute("DELETE FROM aliases WHERE source = ?", (SOURCE,))
        matched = 0
        for zh, en in pairs:
            cid = en2id.get(en.strip().lower())
            if not cid:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO aliases (alias, canonical_id, lang, source) "
                "VALUES (?, ?, 'zh', ?)", (zh, cid, SOURCE))
            matched += 1
        conn.commit()
    finally:
        conn.close()
    return {"harvested": len(pairs), "matched": matched,
            "unmatched": len(pairs) - matched}


def load_zh_aliases(db_path) -> Dict[str, str]:
    """从 aliases 表读所有中文别名 → canonical_id（供 entity_resolver 装载）。"""
    if not Path(db_path).exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    try:
        try:
            rows = conn.execute(
                "SELECT alias, canonical_id FROM aliases WHERE lang = 'zh'").fetchall()
        except sqlite3.OperationalError:
            return {}
        return {alias: cid for alias, cid in rows}
    finally:
        conn.close()
