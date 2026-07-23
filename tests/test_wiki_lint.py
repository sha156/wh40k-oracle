"""wiki_engine/lint.py 测试：各 lint 规则、自动修复。"""
from __future__ import annotations

from pathlib import Path

import pytest

from wiki_engine.lint import (
    auto_fix_broken_links,
    check_alias_conflicts,
    check_broken_links,
    check_faction_indexes,
    check_index_consistency,
    check_missing_points,
    check_raw_backlinks,
    run_lint,
)
from wiki_engine.models import LintIssue, WikiPage, WikiPageFrontmatter


def _create_wiki_with_pages(wiki_root: Path) -> None:
    """创建含有效页面和断链的测试 wiki。"""
    # 有效页面 A
    fm_a = WikiPageFrontmatter(
        id="test/units/alpha",
        name_zh="阿尔法",
        name_en="Alpha",
        faction="test-faction",
        type="unit",
        points={"1": 10},
    )
    fm_a.generate_tags()
    page_a = WikiPage(fm=fm_a, body="阿尔法单位。参考 [[factions/test-faction/units/beta|贝塔]]。")
    dir_a = wiki_root / "factions" / "test-faction" / "units"
    dir_a.mkdir(parents=True)
    (dir_a / "alpha.md").write_text(page_a.to_markdown(), encoding="utf-8")

    # 有效页面 B
    fm_b = WikiPageFrontmatter(
        id="test/units/beta",
        name_zh="贝塔",
        name_en="Beta",
        faction="test-faction",
        type="unit",
        points={"1": 20},
    )
    fm_b.generate_tags()
    page_b = WikiPage(fm=fm_b, body="贝塔单位。参考 [[factions/test-faction/units/alpha|阿尔法]]。")
    (dir_a / "beta.md").write_text(page_b.to_markdown(), encoding="utf-8")

    # 含断链的页面 C
    fm_c = WikiPageFrontmatter(
        id="test/units/gamma",
        name_zh="伽马",
        name_en="Gamma",
        faction="test-faction",
        type="unit",
    )
    fm_c.generate_tags()
    page_c = WikiPage(fm=fm_c, body="伽马单位。参考 [[factions/test-faction/units/nonexistent|不存在]]。")
    (dir_a / "gamma.md").write_text(page_c.to_markdown(), encoding="utf-8")


class TestBrokenLinks:
    def test_detects_broken_link(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_wiki_with_pages(wiki)
        issues = check_broken_links(wiki)
        broken = [i for i in issues if i.rule == "broken-links"]
        assert len(broken) == 1
        assert "nonexistent" in broken[0].message

    def test_no_broken_links_in_clean_wiki(self, tmp_path):
        wiki = tmp_path / "wiki"
        dir_a = wiki / "factions" / "test-faction" / "units"
        dir_a.mkdir(parents=True)
        fm = WikiPageFrontmatter(id="test/units/x", name_zh="X",
                                 faction="test-faction", type="unit")
        page = WikiPage(fm=fm, body="Clean page.")
        (dir_a / "x.md").write_text(page.to_markdown(), encoding="utf-8")
        issues = check_broken_links(wiki)
        broken = [i for i in issues if i.rule == "broken-links"]
        assert len(broken) == 0

    def test_escaped_pipe_table_wikilink_not_broken(self, tmp_path):
        # 表格内 [[path\|别名]] 的转义竖线不得被误判为断链（否则 --fix 会反向去转义
        # 破坏 Obsidian 表格渲染）——target 应剥掉尾随反斜杠后判存在性
        wiki = tmp_path / "wiki"
        cr = wiki / "core-rules"
        cr.mkdir(parents=True)
        (cr / "rapid-fire.md").write_text(
            WikiPage(fm=WikiPageFrontmatter(id="rapid-fire", name_zh="速射",
                                            type="core-rule"),
                     body="速射规则。").to_markdown(), encoding="utf-8")
        units = wiki / "factions" / "orks" / "units"
        units.mkdir(parents=True)
        (units / "warboss.md").write_text(
            WikiPage(fm=WikiPageFrontmatter(id="orks/units/warboss", name_zh="战争头目",
                                            faction="orks", type="unit"),
                     body="| 武器 | 技能 |\n|---|---|\n"
                          "| 枪 | [[core-rules/rapid-fire.md\\|速射2]] |").to_markdown(),
            encoding="utf-8")
        broken = [i for i in check_broken_links(wiki) if i.rule == "broken-links"]
        assert broken == []


class TestMissingPoints:
    def test_detects_missing_points(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_wiki_with_pages(wiki)
        issues = check_missing_points(wiki)
        # gamma has no points
        missing = [i for i in issues if "伽马" in str(i.page_path) or "gamma" in str(i.page_path).lower()]
        # At least gamma should be flagged
        assert len(issues) >= 1


class TestAliasConflicts:
    def test_no_conflicts_in_clean_wiki(self, tmp_path):
        wiki = tmp_path / "wiki"
        dir_a = wiki / "factions" / "test" / "units"
        dir_a.mkdir(parents=True)
        fm1 = WikiPageFrontmatter(id="a", name_zh="单位A", faction="test", type="unit")
        fm2 = WikiPageFrontmatter(id="b", name_zh="单位B", faction="test", type="unit")
        (dir_a / "a.md").write_text(WikiPage(fm=fm1, body="A").to_markdown(), encoding="utf-8")
        (dir_a / "b.md").write_text(WikiPage(fm=fm2, body="B").to_markdown(), encoding="utf-8")
        issues = check_alias_conflicts(wiki)
        assert len(issues) == 0

    def test_detects_alias_conflict(self, tmp_path):
        wiki = tmp_path / "wiki"
        dir_a = wiki / "factions" / "test" / "units"
        dir_a.mkdir(parents=True)
        fm1 = WikiPageFrontmatter(id="a", name_zh="单位A", aliases=["冲突名"],
                                  faction="test", type="unit")
        fm2 = WikiPageFrontmatter(id="b", name_zh="单位B", aliases=["冲突名"],
                                  faction="test", type="unit")
        (dir_a / "a.md").write_text(WikiPage(fm=fm1, body="A").to_markdown(), encoding="utf-8")
        (dir_a / "b.md").write_text(WikiPage(fm=fm2, body="B").to_markdown(), encoding="utf-8")
        issues = check_alias_conflicts(wiki)
        assert len(issues) >= 1
        assert "冲突名" in issues[0].message


class TestFactionIndexes:
    def test_detects_missing_index(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_wiki_with_pages(wiki)
        # Don't create faction index
        issues = check_faction_indexes(wiki)
        # test-faction should be flagged as missing index
        faction_issues = [i for i in issues if i.rule == "faction-indexes"]
        assert len(faction_issues) >= 1

    def test_no_issue_when_index_exists(self, tmp_path):
        wiki = tmp_path / "wiki"
        dir_a = wiki / "factions" / "test-faction" / "units"
        dir_a.mkdir(parents=True)
        fm = WikiPageFrontmatter(id="x", name_zh="X", faction="test-faction", type="unit")
        (dir_a / "x.md").write_text(WikiPage(fm=fm, body="X").to_markdown(), encoding="utf-8")
        # Create the faction index
        idx_dir = wiki / "factions" / "test-faction"
        idx_dir.mkdir(parents=True, exist_ok=True)
        (idx_dir / "index.md").write_text("# Test Faction", encoding="utf-8")
        issues = check_faction_indexes(wiki)
        faction_issues = [i for i in issues if i.rule == "faction-indexes"]
        assert len(faction_issues) == 0


class TestFactionSlugConsistency:
    """MEDIUM #8：check_faction_indexes 必须用 models.faction_slug，而非手写 slug 化。"""

    def test_underscore_faction_matches_built_index(self, tmp_path):
        # build_outputs 用 faction_slug("test_faction") → "test-faction"
        # 手写 slug 化会去找 factions/test_faction/ → 误报
        wiki = tmp_path / "wiki"
        from wiki_engine.models import faction_slug
        fs = faction_slug("test_faction")
        assert fs == "test-faction"

        dir_a = wiki / "factions" / fs / "units"
        dir_a.mkdir(parents=True)
        fm = WikiPageFrontmatter(id="x", name_zh="X",
                                 faction="test_faction", type="unit")
        (dir_a / "x.md").write_text(WikiPage(fm=fm, body="X").to_markdown(),
                                    encoding="utf-8")
        (wiki / "factions" / fs / "index.md").write_text("# Test", encoding="utf-8")

        issues = check_faction_indexes(wiki)
        faction_issues = [i for i in issues if i.rule == "faction-indexes"]
        assert len(faction_issues) == 0


class TestVerifyWarn:
    """MEDIUM #11：verify_warn=True 的页面应被 lint 报 warning。"""

    def test_flagged_page_reported(self, tmp_path):
        from wiki_engine.lint import check_verify_warnings
        wiki = tmp_path / "wiki"
        dir_a = wiki / "factions" / "test" / "units"
        dir_a.mkdir(parents=True)
        fm = WikiPageFrontmatter(id="test/units/x", name_zh="X",
                                 faction="test", type="unit", verify_warn=True)
        (dir_a / "x.md").write_text(WikiPage(fm=fm, body="X").to_markdown(),
                                    encoding="utf-8")
        issues = check_verify_warnings(wiki)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].rule == "verify-warn"

    def test_clean_page_not_reported(self, tmp_path):
        from wiki_engine.lint import check_verify_warnings
        wiki = tmp_path / "wiki"
        dir_a = wiki / "factions" / "test" / "units"
        dir_a.mkdir(parents=True)
        fm = WikiPageFrontmatter(id="test/units/x", name_zh="X",
                                 faction="test", type="unit")
        (dir_a / "x.md").write_text(WikiPage(fm=fm, body="X").to_markdown(),
                                    encoding="utf-8")
        issues = check_verify_warnings(wiki)
        assert issues == []


class TestGeneratedFilesNotScanned:
    """H15：lint 不得扫描自己生成的报告/索引文件的出链，
    否则 lint-report.md 里的 [[断链示例]] 会被当成新断链，假阳性自我复现。"""

    def _clean_wiki(self, tmp_path):
        wiki = tmp_path / "wiki"
        dir_a = wiki / "factions" / "test" / "units"
        dir_a.mkdir(parents=True)
        fm = WikiPageFrontmatter(id="test/units/x", name_zh="X",
                                 faction="test", type="unit")
        (dir_a / "x.md").write_text(WikiPage(fm=fm, body="干净页面。").to_markdown(),
                                    encoding="utf-8")
        return wiki

    def test_broken_link_text_in_lint_report_not_flagged(self, tmp_path):
        wiki = self._clean_wiki(tmp_path)
        (wiki / "lint-report.md").write_text(
            "# Lint Report\n- ❌ 断链: [[不存在的目标]]\n", encoding="utf-8")
        issues = check_broken_links(wiki)
        assert [i for i in issues if i.rule == "broken-links"] == []

    def test_terms_and_log_md_not_scanned(self, tmp_path):
        wiki = self._clean_wiki(tmp_path)
        (wiki / "terms.md").write_text("[[另一个不存在目标]]", encoding="utf-8")
        (wiki / "log.md").write_text("| x | [[第三个不存在目标]] |", encoding="utf-8")
        issues = check_broken_links(wiki)
        assert [i for i in issues if i.rule == "broken-links"] == []

    def test_real_page_broken_link_still_flagged(self, tmp_path):
        # 排除生成产物不能顺带把真实页面的断链也放过
        wiki = self._clean_wiki(tmp_path)
        (wiki / "lint-report.md").write_text("[[报告示例]]", encoding="utf-8")
        dir_a = wiki / "factions" / "test" / "units"
        fm = WikiPageFrontmatter(id="test/units/y", name_zh="Y",
                                 faction="test", type="unit")
        (dir_a / "y.md").write_text(
            WikiPage(fm=fm, body="引用 [[真的断了]]。").to_markdown(),
            encoding="utf-8")
        issues = check_broken_links(wiki)
        broken = [i for i in issues if i.rule == "broken-links"]
        assert len(broken) == 1
        assert "真的断了" in broken[0].message


class TestFrontmatterParseCheck:
    """M7：frontmatter 解析失败的页面不再静默消失，报 error 级 issue。"""

    def test_broken_frontmatter_reported_as_error(self, tmp_path):
        from wiki_engine.lint import check_frontmatter_parse
        wiki = tmp_path / "wiki"
        dir_a = wiki / "factions" / "test" / "units"
        dir_a.mkdir(parents=True)
        fm = WikiPageFrontmatter(id="test/units/good", name_zh="好页",
                                 faction="test", type="unit")
        (dir_a / "good.md").write_text(WikiPage(fm=fm, body="OK").to_markdown(),
                                       encoding="utf-8")
        (dir_a / "bad.md").write_text("没有 frontmatter 的裸正文", encoding="utf-8")

        issues = check_frontmatter_parse(wiki)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].rule == "frontmatter-parse"
        assert "bad.md" in issues[0].page_path
        assert "脱离索引" in issues[0].message

    def test_generated_and_review_files_skipped(self, tmp_path):
        from wiki_engine.lint import check_frontmatter_parse
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        # 生成产物与 review_needed 系列本就没有 frontmatter，不应误报
        (wiki / "index.md").write_text("# 索引", encoding="utf-8")
        (wiki / "lint-report.md").write_text("# 报告", encoding="utf-8")
        (wiki / "review_needed.md").write_text("# 待人工校对", encoding="utf-8")
        (wiki / "review_needed.backup-20260710-120000.md").write_text(
            "# 旧版", encoding="utf-8")
        assert check_frontmatter_parse(wiki) == []

    def test_registered_in_lint_rules(self):
        from wiki_engine.lint import LINT_RULES, check_frontmatter_parse
        assert check_frontmatter_parse in LINT_RULES


class TestIndexConsistency:
    def test_index_missing(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        issues = check_index_consistency(wiki)
        assert len(issues) == 1
        assert "不存在" in issues[0].message

    def test_index_with_valid_links(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_wiki_with_pages(wiki)
        # Build index first
        from wiki_engine.build_outputs import build_global_index, scan_wiki_pages
        pages = scan_wiki_pages(wiki)
        index_md = build_global_index(pages, wiki)
        (wiki / "index.md").write_text(index_md, encoding="utf-8")
        issues = check_index_consistency(wiki)
        assert len(issues) == 0


class TestAutoFixBrokenLinks:
    def test_fixes_with_suggestion(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_wiki_with_pages(wiki)

        # Create a fixable issue manually
        issue = LintIssue(
            severity="error",
            rule="broken-links",
            page_path="factions/test-faction/units/gamma.md",
            message="断链: [[factions/test-faction/units/nonexistent]]",
            auto_fixable=True,
            fix_description="建议替换为 [[factions/test-faction/units/beta]]",
        )
        fixed = auto_fix_broken_links([issue], wiki)
        assert fixed >= 1
        # Verify the file was fixed
        gamma_path = wiki / "factions" / "test-faction" / "units" / "gamma.md"
        content = gamma_path.read_text(encoding="utf-8")
        assert "nonexistent" not in content
        assert "factions/test-faction/units/beta" in content


class TestRunLint:
    def test_full_run(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_wiki_with_pages(wiki)
        result = run_lint(wiki, auto_fix=True)
        assert result.total >= 1  # At minimum, missing faction index
        # Check that auto-fix ran
        assert isinstance(result.auto_fixed, int)

    def test_no_auto_fix(self, tmp_path):
        wiki = tmp_path / "wiki"
        _create_wiki_with_pages(wiki)
        result = run_lint(wiki, auto_fix=False)
        assert result.auto_fixed == 0


class TestRawBacklinks:
    def test_invalid_backlink(self, tmp_path):
        wiki = tmp_path / "wiki"
        refined = tmp_path / "data_refined"
        dir_a = wiki / "factions" / "test" / "units"
        dir_a.mkdir(parents=True)
        fm = WikiPageFrontmatter(
            id="test/units/x",
            name_zh="X",
            faction="test",
            type="unit",
            raw=["data_refined/nonexistent/page_001.md"],
        )
        (dir_a / "x.md").write_text(WikiPage(fm=fm, body="X").to_markdown(), encoding="utf-8")
        issues = check_raw_backlinks(wiki, refined)
        assert len(issues) >= 1
        assert "nonexistent" in issues[0].message
