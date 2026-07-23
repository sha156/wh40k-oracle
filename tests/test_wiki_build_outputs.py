"""wiki_engine/build_outputs.py 测试：index 生成、阵营索引、日志。"""
from __future__ import annotations

from pathlib import Path

import pytest

from wiki_engine.build_outputs import (
    build_all_outputs,
    build_faction_index,
    build_global_index,
    build_log_entry,
    scan_wiki_pages,
    write_log,
)
from wiki_engine.models import WikiPage, WikiPageFrontmatter


def _create_test_pages(wiki_root: Path) -> None:
    """创建测试用的 wiki 页面结构。"""
    # Unit page
    fm1 = WikiPageFrontmatter(
        id="tau-empire/units/fire-warriors",
        name_zh="火战士队",
        name_en="Fire Warriors",
        faction="tau-empire",
        type="unit",
        keywords=["Infantry", "Battleline"],
        updated="2026-07-05",
    )
    fm1.generate_tags()
    page1 = WikiPage(fm=fm1, body="火战士队是钛帝国的基础步兵单位。\n\n## 属性表\n\n测试内容。")
    dir1 = wiki_root / "factions" / "tau-empire" / "units"
    dir1.mkdir(parents=True)
    (dir1 / "fire-warriors.md").write_text(page1.to_markdown(), encoding="utf-8")

    # Detachment page
    fm2 = WikiPageFrontmatter(
        id="tau-empire/detachments/kaoyu",
        name_zh="空育猎核",
        name_en="Kauyon Hunter Cadre",
        faction="tau-empire",
        type="detachment",
        updated="2026-07-05",
    )
    fm2.generate_tags()
    page2 = WikiPage(fm=fm2, body="空育猎核是钛帝国的分队规则。\n\n## 分队规则\n\n测试。")
    dir2 = wiki_root / "factions" / "tau-empire" / "detachments"
    dir2.mkdir(parents=True)
    (dir2 / "kauyon.md").write_text(page2.to_markdown(), encoding="utf-8")


class TestScanWikiPages:
    def test_finds_pages(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_test_pages(wiki)
        pages = scan_wiki_pages(wiki)
        assert len(pages) >= 2
        names = [p.fm.name_zh for p in pages]
        assert "火战士队" in names
        assert "空育猎核" in names

    def test_skips_special_files(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "index.md").write_text("# Index", encoding="utf-8")
        (wiki / "log.md").write_text("# Log", encoding="utf-8")
        _create_test_pages(wiki)
        pages = scan_wiki_pages(wiki)
        # index.md and log.md should be skipped
        paths = [p.fm.id for p in pages]
        assert "index" not in paths


class TestBuildGlobalIndex:
    def test_generates_table(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_test_pages(wiki)
        pages = scan_wiki_pages(wiki)
        index_md = build_global_index(pages, wiki)
        assert "# WH40K Wiki Index" in index_md
        assert "火战士队" in index_md
        assert "tau-empire" in index_md

    def test_includes_statistics(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_test_pages(wiki)
        pages = scan_wiki_pages(wiki)
        index_md = build_global_index(pages, wiki)
        assert "统计" in index_md
        assert "总实体数" in index_md


class TestBuildFactionIndex:
    def test_generates_faction_page(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_test_pages(wiki)
        pages = scan_wiki_pages(wiki)
        index_md = build_faction_index(pages, "tau-empire", wiki)
        assert index_md is not None
        assert "火战士队" in index_md
        assert "空育猎核" in index_md

    def test_unknown_faction_returns_none(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_test_pages(wiki)
        pages = scan_wiki_pages(wiki)
        result = build_faction_index(pages, "nonexistent", wiki)
        assert result is None


class TestLog:
    def test_build_and_write(self, tmp_path):
        log_path = tmp_path / "log.md"
        entry = build_log_entry(
            operation="test",
            description="测试日志",
            affected_pages=["page1.md"],
        )
        write_log(log_path, entry)
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "test" in content
        assert "测试日志" in content
        assert "page1.md" in content

    def test_appends_to_existing(self, tmp_path):
        log_path = tmp_path / "log.md"
        e1 = build_log_entry("test1", "first")
        e2 = build_log_entry("test2", "second")
        write_log(log_path, e1)
        write_log(log_path, e2)
        content = log_path.read_text(encoding="utf-8")
        assert "first" in content
        assert "second" in content


class TestBuildAllOutputs:
    def test_creates_index_and_log(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_test_pages(wiki)
        entry = build_log_entry("rebuild", "build_all_outputs test")
        result = build_all_outputs(wiki, log_entries=[entry])
        assert result["faction_indexes"] >= 1
        assert (wiki / "index.md").exists()
        assert (wiki / "log.md").exists()
        assert (wiki / "factions" / "tau-empire" / "index.md").exists()


class TestDataCorrectnessFixes:
    """gnhf 审查模块 6 F4/F7：去重页链接目标 + 摘要剥 wikilink。"""

    def test_dedup_page_linked_by_real_path_no_orphan(self, tmp_path):
        # F4：同名单位第二页 slug 去重成 -2，索引必须链到真实 -2 文件而非从 name 反推
        wiki = tmp_path / "wiki"
        d = wiki / "factions" / "space-marines" / "units"
        d.mkdir(parents=True)
        for slug, uid in (("repulsor", "000000001"), ("repulsor-2", "000000002")):
            fm = WikiPageFrontmatter(id=uid, name_zh="反击者", name_en="Repulsor",
                                     faction="space-marines", type="unit",
                                     updated="2026-07-23")
            (d / (slug + ".md")).write_text(
                WikiPage(fm=fm, body="body").to_markdown(), encoding="utf-8")
        pages = scan_wiki_pages(wiki)
        idx = build_global_index(pages, wiki)
        # 两个真实文件都被链到，无孤儿（此前从 name 反推两个都指向 repulsor.md）
        assert "space-marines/units/repulsor.md" in idx
        assert "space-marines/units/repulsor-2.md" in idx

    def test_summary_strips_wikilinks_no_broken_table(self, tmp_path):
        # F7：正文首段含 [[path|显示]] → 摘要剥成纯文本，竖线不进 index 表格断列
        wiki = tmp_path / "wiki"
        d = wiki / "factions" / "orks" / "units"
        d.mkdir(parents=True)
        fm = WikiPageFrontmatter(id="x", name_zh="小子", name_en="Boyz",
                                 faction="orks", type="unit", updated="2026-07-23")
        body = "会被[[core-rules/precision.md|精准]]武器点名的近战单位。\n\n## 属性表\n"
        (d / "boyz.md").write_text(WikiPage(fm=fm, body=body).to_markdown(),
                                   encoding="utf-8")
        pages = scan_wiki_pages(wiki)
        idx = build_global_index(pages, wiki)
        boyz_row = [ln for ln in idx.split("\n")
                    if "boyz.md" in ln and ln.startswith("|")][0]
        assert "[[" not in boyz_row and "精准" in boyz_row
        # 表格行列数正确（表头 4 列 → 前后各一竖线共 5 个分隔）
        assert boyz_row.count("|") == 5
