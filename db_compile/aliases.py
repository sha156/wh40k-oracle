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

    同一 zh 别名映射到不同 canonical_id 时（表主键 alias+lang+source 相同），
    保留首个、跳过后续并计入 collided——旧实现 INSERT OR REPLACE 会静默覆盖
    且 matched 虚计。matched 恒等于实际落库行数。
    幂等：先删本源旧行再写。返回 {harvested, matched, unmatched, collided}。
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
        matched = unmatched = collided = 0
        zh_first: Dict[str, str] = {}  # zh → 首个 canonical_id
        for zh, en in pairs:
            cid = en2id.get(en.strip().lower())
            if not cid:
                unmatched += 1
                continue
            prev = zh_first.get(zh)
            if prev is not None:
                if prev != cid:
                    collided += 1
                    print(f"  ⚠️ 别名碰撞：『{zh}』已映射 {prev}，"
                          f"跳过 {en}→{cid}（保留首个）")
                continue  # 同 cid 重复对：无信息量，跳过不计
            zh_first[zh] = cid
            conn.execute(
                "INSERT INTO aliases (alias, canonical_id, lang, source) "
                "VALUES (?, ?, 'zh', ?)", (zh, cid, SOURCE))
            matched += 1
        conn.commit()
    finally:
        conn.close()
    return {"harvested": len(pairs), "matched": matched,
            "unmatched": unmatched, "collided": collided}


BLACKFORUM_SOURCE = "blackforum"


def populate_blackforum_aliases(db_path, pairs: List[Tuple[str, str]]) -> Dict[str, int]:
    """把黑图书馆小程序的 (中文名, 英文名) 对灌进 aliases 表（source='blackforum'）。

    黑图书馆 /app/manager/forum/unit/list 每单位带 unitName(中文)+unitEnglishName(英文)，
    是权威中英桥。en 精确匹配 units.name_en（大小写不敏感），匹配不到诚实计数、不硬塞。
    同一 zh 映射到不同 canonical_id 时保留首个、跳过后续并计入 collided
    （旧实现 INSERT OR REPLACE 会静默覆盖）。matched 恒等于实际落库行数。
    幂等：先删本源旧行再写。返回 {harvested, matched, unmatched, skipped_no_en, collided}。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        en2id = {
            (name or "").strip().lower(): cid
            for cid, name in conn.execute("SELECT id, name_en FROM units")
            if name
        }
        conn.execute("DELETE FROM aliases WHERE source = ?", (BLACKFORUM_SOURCE,))
        matched = unmatched = skipped_no_en = collided = 0
        zh_first: Dict[str, str] = {}  # zh → 首个 canonical_id
        for zh, en in pairs:
            if not zh or not _CJK.search(zh):
                continue
            if not en or not _LATIN.search(en):
                skipped_no_en += 1
                continue
            cid = en2id.get(en.strip().lower())
            if not cid:
                unmatched += 1
                continue
            prev = zh_first.get(zh)
            if prev is not None:
                if prev != cid:
                    collided += 1
                    print(f"  ⚠️ 别名碰撞：『{zh}』已映射 {prev}，"
                          f"跳过 {en}→{cid}（保留首个）")
                continue  # 同 cid 重复对：跳过不计
            zh_first[zh] = cid
            conn.execute(
                "INSERT INTO aliases (alias, canonical_id, lang, source) "
                "VALUES (?, ?, 'zh', ?)", (zh, cid, BLACKFORUM_SOURCE))
            matched += 1
        conn.commit()
    finally:
        conn.close()
    return {"harvested": len(pairs), "matched": matched,
            "unmatched": unmatched,
            "skipped_no_en": skipped_no_en, "collided": collided}


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


def load_alias_expansions(db_path, min_alias_len: int = 3) -> Dict[str, str]:
    """{中文别名 → "库内规范中文名 英文名"}，供 classic 检索链 expand_query 用。

    这样 classic 与 agent 共用同一份 1633 条别名（此前 classic 只有 app.py 10 条硬编码，
    与 sqlite 别名表两套并行、互不同步）。命中别名时把库内规范名追加进查询串，让 BM25/
    向量召回到正确单位的中文/双语 chunk。

    - 只保留能带来新信息的别名（规范名 != 别名本身；纯自指的跳过）。
    - 跳过长度 < min_alias_len 的别名：2 字别名子串误匹配风险高，且多为库内规范名自指。
    - 多个别名指向同一 id 时 setdefault 保留首个，不覆盖。
    """
    if not Path(db_path).exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    try:
        try:
            rows = conn.execute(
                "SELECT a.alias, u.name_zh, u.name_en "
                "FROM aliases a JOIN units u ON a.canonical_id = u.id "
                "WHERE a.lang = 'zh'"
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
    finally:
        conn.close()
    out: Dict[str, str] = {}
    for alias, name_zh, name_en in rows:
        if not alias or len(alias) < min_alias_len:
            continue
        parts = [p for p in (name_zh, name_en)
                 if p and p.strip() and p != alias]
        if not parts:
            continue
        out.setdefault(alias, " ".join(dict.fromkeys(parts)))
    return out
