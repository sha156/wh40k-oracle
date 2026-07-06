"""wiki_engine/build_outputs.py — 产出 index.md, 阵营索引, log.md（wiki 编译器步骤⑤）。

纯代码实现，扫描 wiki/ 目录，按 frontmatter 字段生成全局索引和阵营索引。
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from wiki_engine.models import (
    LogEntry,
    WikiIndexEntry,
    WikiPage,
    faction_slug,
)


def scan_wiki_pages(wiki_root: Path) -> List[WikiPage]:
    """遍历 wiki/ 下所有 .md 文件，解析 frontmatter + body。

    跳过特殊文件：index.md, log.md, terms.md, lint-report.md。
    """
    skip_names = {"index.md", "log.md", "terms.md", "lint-report.md"}
    pages: List[WikiPage] = []
    for md_file in sorted(wiki_root.rglob("*.md")):
        if md_file.name in skip_names:
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        parsed = WikiPage.from_markdown(text)
        if parsed is None:
            continue
        # 填充路径信息
        rel = str(md_file.relative_to(wiki_root)).replace("\\", "/")
        parsed.fm.id = parsed.fm.id or rel.replace(".md", "")
        pages.append(parsed)
    return pages


def _extract_summary(body: str, max_chars: int = 80) -> str:
    """从 body 首段提取摘要（跳过表格和标题行）。"""
    lines = body.strip().split("\n")
    summary_parts = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith("-"):
            if summary_parts:
                break
            continue
        summary_parts.append(line)
        if len(" ".join(summary_parts)) >= max_chars:
            break
    text = " ".join(summary_parts)[:max_chars]
    return text.strip() + ("..." if len(summary_parts) > 0 and len(" ".join(summary_parts)) > max_chars else "")


def build_global_index(pages: List[WikiPage], wiki_root: Path) -> str:
    """生成 wiki/index.md 全文。

    按 faction → type 分组，生成 Markdown 表格。
    """
    lines = [
        "# WH40K Wiki Index",
        "",
        "_Last updated: {}_".format(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
        "",
        "## 目录",
        "",
    ]

    # 按 faction 分组
    by_faction: Dict[str, List[WikiPage]] = defaultdict(list)
    for page in pages:
        faction = page.fm.faction or "未分类"
        by_faction[faction].append(page)

    for faction_name in sorted(by_faction.keys()):
        fpages = by_faction[faction_name]
        fs = faction_slug(faction_name)
        lines.append("### {}".format(faction_name or "未分类"))
        lines.append("")
        lines.append("| 类型 | 名称 | 摘要 | Updated |")
        lines.append("|------|------|------|---------|")

        for page in sorted(fpages, key=lambda p: (p.fm.type, p.fm.name_zh or p.fm.name_en or "")):
            rel_path = str(entity_page_path_for_display(wiki_root, page))
            name = page.fm.name_zh or page.fm.name_en or page.fm.id
            link = "[{}]({})".format(name, rel_path)
            summary = _extract_summary(page.body)
            updated = page.fm.updated or "-"
            lines.append("| {} | {} | {} | {} |".format(
                page.fm.type or "-", link, summary, updated))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 统计")
    lines.append("")
    lines.append("- **总实体数**: {}".format(len(pages)))
    type_counts = defaultdict(int)
    for page in pages:
        type_counts[page.fm.type] += 1
    for t, c in sorted(type_counts.items()):
        lines.append("- **{}**: {}".format(t or "未知类型", c))
    lines.append("")

    return "\n".join(lines) + "\n"


def entity_page_path_for_display(wiki_root: Path, page: WikiPage) -> str:
    """生成用于 index.md 中的显示路径（相对于 wiki/）。"""
    from wiki_engine.models import entity_page_path as _entity_page_path
    p = _entity_page_path(wiki_root, page.fm)
    return str(p.relative_to(wiki_root)).replace("\\", "/")


def build_faction_index(
    pages: List[WikiPage],
    faction: str,
    wiki_root: Path,
) -> Optional[str]:
    """生成 factions/<slug>/index.md 全文。

    返回 None 如果该阵营没有页面。
    """
    fpages = [p for p in pages if p.fm.faction == faction]
    if not fpages:
        return None

    fs = faction_slug(faction)
    # 从中英文名挑一个显示
    display_name = faction
    for p in fpages:
        if p.fm.name_zh:
            # 阵营名来自 faction 字段本身
            pass

    lines = [
        "# {}".format(display_name),
        "",
        "_Last updated: {}_".format(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
        "",
    ]

    type_order = ["detachment", "unit", "stratagem", "enhancement"]
    by_type: Dict[str, List[WikiPage]] = defaultdict(list)
    for page in fpages:
        by_type[page.fm.type].append(page)

    for etype in type_order:
        if etype not in by_type:
            continue
        epages = by_type[etype]
        type_label = {"unit": "单位", "stratagem": "策略技能",
                      "detachment": "分队", "enhancement": "强化"}.get(etype, etype)
        lines.append("## {}".format(type_label))
        lines.append("")
        for page in sorted(epages, key=lambda p: p.fm.name_zh or p.fm.name_en or ""):
            name = page.fm.name_zh or page.fm.name_en or page.fm.id
            rel_path = entity_page_path_for_display(wiki_root, page)
            link = "[[{}|{}]]".format(rel_path.replace(".md", ""), name)
            summary = _extract_summary(page.body, 60)
            lines.append("- {} — {}".format(link, summary))
        lines.append("")

    return "\n".join(lines) + "\n"


# ── Log 管理 ──────────────────────────────────────────────────────────

_LOG_HEADER = """# Operations Log

> 追加式操作日志。每次 Ingest/Lint/Archive/Rebuild 操作追加一行。
> 格式自动生成，勿手动编辑。

"""


def build_log_entry(
    operation: str,
    description: str,
    affected_pages: Optional[List[str]] = None,
    cascade_updates: Optional[List[str]] = None,
) -> LogEntry:
    """创建一条日志条目。"""
    return LogEntry(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        operation=operation,
        description=description,
        affected_pages=affected_pages or [],
        cascade_updates=cascade_updates or [],
    )


def write_log(log_path: Path, entry: LogEntry) -> None:
    """追加式写入 log.md。不存在则创建含表头的文件。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(_LOG_HEADER + LogEntry.log_table_header() + "\n",
                            encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry.to_markdown_line() + "\n")


def build_all_outputs(
    wiki_root: Path,
    log_entries: Optional[List[LogEntry]] = None,
) -> Dict[str, Any]:
    """全量构建输出：index.md + 各阵营 index.md + log.md 追加。

    返回 {index: str, faction_indexes: int, log_entries: int}。
    """
    pages = scan_wiki_pages(wiki_root)
    if not pages:
        print("wiki/ 下没有找到实体页，跳过构建。")
        return {"index": "", "faction_indexes": 0, "log_entries": 0}

    # 全局索引
    index_md = build_global_index(pages, wiki_root)
    index_path = wiki_root / "index.md"
    index_path.write_text(index_md, encoding="utf-8")
    print("index.md: {} 个实体".format(len(pages)))

    # 阵营索引
    factions_seen: set = set()
    for page in pages:
        if page.fm.faction:
            factions_seen.add(page.fm.faction)

    faction_count = 0
    for faction in sorted(factions_seen):
        faction_index = build_faction_index(pages, faction, wiki_root)
        if faction_index:
            fs = faction_slug(faction)
            fi_path = wiki_root / "factions" / fs / "index.md"
            fi_path.parent.mkdir(parents=True, exist_ok=True)
            fi_path.write_text(faction_index, encoding="utf-8")
            faction_count += 1
            print("  factions/{}/index.md: {} 个实体".format(fs,
                  len([p for p in pages if p.fm.faction == faction])))

    # log
    log_count = 0
    if log_entries:
        log_path = wiki_root / "log.md"
        for entry in log_entries:
            write_log(log_path, entry)
            log_count += 1
        print("log.md: {} 条新记录".format(log_count))

    return {"index": str(index_path), "faction_indexes": faction_count,
            "log_entries": log_count}
