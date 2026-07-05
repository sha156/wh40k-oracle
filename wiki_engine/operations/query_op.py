"""wiki_engine/operations/query_op.py — Query 操作。

读 index.md 定位 → 读实体页 → 返回带引用的知识。
供 L5 Agent 工具调用。纯代码实现（grep），不调 LLM。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from wiki_engine.models import WikiIndexEntry, WikiPage


def load_index(wiki_root: Path) -> List[WikiIndexEntry]:
    """解析 wiki/index.md 为结构化索引列表。"""
    index_path = wiki_root / "index.md"
    if not index_path.exists():
        return []

    entries: List[WikiIndexEntry] = []
    text = index_path.read_text(encoding="utf-8")
    # 解析 Markdown 表格行
    in_table = False
    current_faction = ""
    current_type = ""

    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("### "):
            current_faction = line[4:].strip()
            continue
        if line.startswith("| ") and "名称" not in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 4:
                # | 类型 | 名称 | 摘要 | Updated |
                # name 可能包含 Markdown 链接 [name](path)
                name_link = parts[1]
                m = re.match(r"\[(.+?)\]\((.+?)\)", name_link)
                if m:
                    display_name = m.group(1)
                    path = m.group(2)
                    entries.append(WikiIndexEntry(
                        path=path,
                        title_zh=display_name,
                        title_en=None,
                        faction=current_faction,
                        type=parts[0],
                        summary=parts[2],
                        updated=parts[3] if parts[3] != "-" else "",
                    ))
    return entries


def find_entity(
    name: str,
    index: List[WikiIndexEntry],
    wiki_root: Path,
) -> Optional[WikiPage]:
    """按中文名/英文名/别名查找实体页。先精确匹配，再模糊。

    返回 WikiPage 或 None。
    """
    # 精确匹配
    name_lower = name.strip().lower()
    for entry in index:
        if (entry.title_zh and entry.title_zh.lower() == name_lower) or \
           (entry.title_en and entry.title_en.lower() == name_lower):
            page_path = wiki_root / entry.path
            if page_path.exists():
                text = page_path.read_text(encoding="utf-8")
                return WikiPage.from_markdown(text)
            # 尝试加 .md 后缀
            page_path = wiki_root / (entry.path + ".md")
            if page_path.exists():
                text = page_path.read_text(encoding="utf-8")
                return WikiPage.from_markdown(text)

    # 模糊匹配：在 title_zh, title_en 中搜索子串
    for entry in index:
        titles = [t for t in (entry.title_zh, entry.title_en) if t]
        if any(name_lower in t.lower() for t in titles):
            page_path = wiki_root / entry.path
            if page_path.exists():
                text = page_path.read_text(encoding="utf-8")
                return WikiPage.from_markdown(text)

    return None


def search_entities(
    query: str,
    index: List[WikiIndexEntry],
) -> List[WikiIndexEntry]:
    """全文检索 index.md + entity page 标题。纯代码 grep。"""
    query_lower = query.strip().lower()
    if not query_lower:
        return index

    results: List[WikiIndexEntry] = []
    for entry in index:
        score = 0
        if entry.title_zh and query_lower in entry.title_zh.lower():
            score += 10
        if entry.title_en and query_lower in entry.title_en.lower():
            score += 10
        if entry.summary and query_lower in entry.summary.lower():
            score += 3
        if entry.faction and query_lower in entry.faction.lower():
            score += 2
        if entry.type and query_lower in entry.type.lower():
            score += 1
        if score > 0:
            results.append((score, entry))

    results.sort(key=lambda x: -x[0])
    return [e for _, e in results]


def query(
    query_text: str,
    wiki_root: Path,
) -> Dict:
    """主入口：搜索→读页→返回带引用的知识。

    返回 {found: bool, page: Optional[WikiPage], results: List[WikiIndexEntry]}。
    """
    index = load_index(wiki_root)
    if not index:
        return {"found": False, "page": None, "results": []}

    # 先尝试精确查找
    page = find_entity(query_text, index, wiki_root)
    if page is not None:
        return {"found": True, "page": page, "results": []}

    # 否则全文检索
    results = search_entities(query_text, index)
    return {"found": len(results) > 0, "page": None, "results": results[:10]}
