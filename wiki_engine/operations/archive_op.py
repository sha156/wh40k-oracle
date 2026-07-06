"""wiki_engine/operations/archive_op.py — Archive 操作。

保存 AI 判断/模拟分析/裁判判定为 wiki 页（标 [Archived]）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from wiki_engine.build_outputs import build_log_entry, write_log
from wiki_engine.models import WikiPage, WikiPageFrontmatter, slugify


def archive_judgment(
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    wiki_root: Optional[Path] = None,
) -> str:
    """保存 AI 判断/分析为 wiki/faq/ 下的归档页。

    返回创建的文件路径。
    """
    if wiki_root is None:
        wiki_root = Path("wiki")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = slugify(title)

    # 构建 frontmatter
    fm = WikiPageFrontmatter(
        id="faq/{}".format(slug),
        name_zh=title,
        type="archived",
        tags=(tags or []) + ["archived"],
        updated=now,
    )
    fm.generate_tags()

    page = WikiPage(
        fm=fm,
        body="# {}\n\n> ⚠️ 此页面由 AI 生成并归档。内容可能不是最终裁判。\n\n{}".format(
            title, content),
    )

    # 写到 wiki/faq/
    faq_dir = wiki_root / "faq"
    faq_dir.mkdir(parents=True, exist_ok=True)
    file_path = faq_dir / "{}.md".format(slug)
    file_path.write_text(page.to_markdown(), encoding="utf-8")

    # 日志
    entry = build_log_entry(
        operation="archive",
        description="归档: {}".format(title),
    )
    write_log(wiki_root / "log.md", entry)

    return str(file_path)
