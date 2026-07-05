"""wiki_engine/models.py 测试：frontmatter 序列化/反序列化、实体页渲染。"""
from __future__ import annotations

from pathlib import Path

import pytest

from wiki_engine.models import (
    WikiPage,
    WikiPageFrontmatter,
    WikiIndexEntry,
    LogEntry,
    LintIssue,
    LintResult,
    slugify,
    faction_slug,
    entity_page_path,
)


class TestWikiPageFrontmatter:
    def test_basic_serialization(self):
        fm = WikiPageFrontmatter(
            id="tau-empire/units/fire-warriors",
            name_zh="火战士队",
            name_en="Fire Warriors",
            faction="tau-empire",
            type="unit",
            keywords=["Infantry", "Battleline"],
            updated="2026-07-05",
        )
        fm.generate_tags()
        yaml_text = fm.to_yaml_text()
        assert "id: tau-empire/units/fire-warriors" in yaml_text
        assert "name_zh: 火战士队" in yaml_text
        assert "name_en: Fire Warriors" in yaml_text
        assert "faction: tau-empire" in yaml_text
        assert "type: unit" in yaml_text

    def test_tags_generated(self):
        fm = WikiPageFrontmatter(
            id="tau-empire/units/fire-warriors",
            name_zh="火战士队",
            faction="tau-empire",
            type="unit",
            keywords=["Infantry", "Battleline"],
        )
        fm.generate_tags()
        assert "unit/tau-empire" in fm.tags
        assert "tau-empire" in fm.tags
        assert "unit" in fm.tags
        assert "infantry" in fm.tags
        assert "battleline" in fm.tags

    def test_empty_fields_omitted(self):
        fm = WikiPageFrontmatter(id="test/entity")
        yaml_text = fm.to_yaml_text()
        assert "name_zh:" not in yaml_text  # empty fields should be omitted

    def test_list_serialization(self):
        fm = WikiPageFrontmatter(
            id="test/entity",
            aliases=["FW", "火武士"],
            keywords=["Infantry", "Battleline"],
        )
        yaml_text = fm.to_yaml_text()
        assert "FW" in yaml_text
        assert "火武士" in yaml_text

    def test_dict_points_serialization(self):
        fm = WikiPageFrontmatter(
            id="test/entity",
            type="unit",
            points={"5": 50, "10": 80},
        )
        yaml_text = fm.to_yaml_text()
        assert "points:" in yaml_text
        assert "50" in yaml_text


class TestFrontmatterRoundtrip:
    """往返对称：to_markdown → from_markdown 后所有字段逐一相等（CRITICAL #1）。"""

    def _make_full_page(self) -> WikiPage:
        fm = WikiPageFrontmatter(
            id="tau-empire/units/fire-warriors",
            name_zh="火战士队",
            name_en="Fire Warriors",
            aliases=["FW", "火武士", "Strike Team"],
            faction="tau-empire",
            type="unit",
            points={"5": 50, "10": 80},
            keywords=["Infantry", "Battleline", "Fire Warriors"],
            version={"points": "MFM v1.4", "rules": "Codex 10th"},
            sources=[
                {"book": "钛帝国十版CODEX-20251112", "pages": [1, 2, 3]},
                {"book": "Faction Pack Tau Empire", "pages": [10]},
            ],
            raw=[
                "data_refined/钛帝国十版CODEX-20251112/page_001.md",
                "data_refined/钛帝国十版CODEX-20251112/page_002.md",
                "data_refined/Faction Pack Tau Empire/page_010.md",
            ],
            updated="2026-07-05",
        )
        fm.generate_tags()
        return WikiPage(fm=fm, body="## 属性表\n\n| M | T |\n|---|---|\n| 6 | 3 |")

    def test_full_roundtrip_all_fields_equal(self):
        page = self._make_full_page()
        parsed = WikiPage.from_markdown(page.to_markdown())
        assert parsed is not None
        assert parsed.fm.id == page.fm.id
        assert parsed.fm.name_zh == page.fm.name_zh
        assert parsed.fm.name_en == page.fm.name_en
        assert parsed.fm.aliases == page.fm.aliases
        assert parsed.fm.faction == page.fm.faction
        assert parsed.fm.type == page.fm.type
        assert parsed.fm.points == page.fm.points
        assert parsed.fm.keywords == page.fm.keywords
        assert parsed.fm.tags == page.fm.tags
        assert parsed.fm.version == page.fm.version
        assert parsed.fm.sources == page.fm.sources
        assert parsed.fm.raw == page.fm.raw
        assert parsed.fm.updated == page.fm.updated
        assert parsed.body == page.body

    def test_sources_stay_list_of_dicts(self):
        """list-of-dict 不能被拍成两个独立列表项。"""
        page = self._make_full_page()
        parsed = WikiPage.from_markdown(page.to_markdown())
        assert isinstance(parsed.fm.sources, list)
        assert len(parsed.fm.sources) == 2
        assert parsed.fm.sources[0]["book"] == "钛帝国十版CODEX-20251112"
        assert parsed.fm.sources[0]["pages"] == [1, 2, 3]

    def test_raw_is_list_not_string(self):
        """多行 raw 必须解析回 list[str]，否则下游 for raw_rel in raw 变逐字符迭代。"""
        page = self._make_full_page()
        parsed = WikiPage.from_markdown(page.to_markdown())
        assert isinstance(parsed.fm.raw, list)
        assert len(parsed.fm.raw) == 3
        for item in parsed.fm.raw:
            assert item.startswith("data_refined/")

    def test_double_roundtrip_stable(self):
        """二次往返（写→读→写→读）保持稳定。"""
        page = self._make_full_page()
        once = WikiPage.from_markdown(page.to_markdown())
        twice = WikiPage.from_markdown(once.to_markdown())
        assert twice.fm == once.fm
        assert twice.body == once.body

    def test_verify_warn_roundtrip(self):
        fm = WikiPageFrontmatter(id="test/x", type="unit", verify_warn=True)
        page = WikiPage(fm=fm, body="body")
        parsed = WikiPage.from_markdown(page.to_markdown())
        assert parsed.fm.verify_warn is True

    def test_verify_warn_default_false_omitted(self):
        fm = WikiPageFrontmatter(id="test/x", type="unit")
        assert fm.verify_warn is False
        assert "verify_warn" not in fm.to_yaml_text()


class TestWikiPage:
    def test_to_markdown_roundtrip(self):
        fm = WikiPageFrontmatter(
            id="tau-empire/units/fire-warriors",
            name_zh="火战士队",
            faction="tau-empire",
            type="unit",
        )
        body = "## 属性表\n\n| M | T | SV | W | LD | OC |\n|---|---|---|---|---|---|"
        page = WikiPage(fm=fm, body=body)

        md = page.to_markdown()
        assert md.startswith("---\n")
        assert "火战士队" in md
        assert "## 属性表" in md

        # 简易 roundtrip
        parsed = WikiPage.from_markdown(md)
        assert parsed is not None
        assert parsed.fm.name_zh == "火战士队"
        assert "## 属性表" in parsed.body

    def test_from_markdown_no_frontmatter(self):
        result = WikiPage.from_markdown("just body, no frontmatter")
        assert result is None


class TestSlugify:
    def test_chinese(self):
        # slugify uses simple transliteration; Chinese chars are kept
        result = slugify("火战士队")
        assert len(result) > 0

    def test_english(self):
        assert slugify("Fire Warriors") == "fire-warriors"

    def test_mixed(self):
        result = slugify("Shas'o R'alai")
        assert "shas" in result
        assert "ralai" in result

    def test_empty(self):
        assert slugify("") == "unnamed"


class TestEntityPagePath:
    def test_unit_page_path(self):
        fm = WikiPageFrontmatter(
            id="tau-empire/units/fire-warriors",
            name_zh="火战士队",
            name_en="Fire Warriors",
            faction="tau-empire",
            type="unit",
        )
        wiki_root = Path("/fake/wiki")
        p = entity_page_path(wiki_root, fm)
        assert "factions" in str(p)
        assert "units" in str(p)
        assert "fire-warriors" in str(p).lower()

    def test_core_rule_path(self):
        fm = WikiPageFrontmatter(
            id="core-rules/charge-phase",
            name_zh="冲锋阶段",
            type="core-rule",
        )
        wiki_root = Path("/fake/wiki")
        p = entity_page_path(wiki_root, fm)
        assert "core-rules" in str(p)


class TestLogEntry:
    def test_to_markdown_line(self):
        entry = LogEntry(
            timestamp="2026-07-05 12:00 UTC",
            operation="ingest",
            description="测试",
        )
        line = entry.to_markdown_line()
        assert "2026-07-05" in line
        assert "ingest" in line
        assert "测试" in line


class TestLintIssue:
    def test_to_markdown_error(self):
        issue = LintIssue(
            severity="error",
            rule="broken-links",
            page_path="test/page.md",
            message="断链: [[missing]]",
            auto_fixable=True,
            fix_description="建议替换为 [[exists]]",
        )
        md = issue.to_markdown()
        assert "❌" in md
        assert "broken-links" in md
        assert "test/page.md" in md

    def test_to_markdown_info(self):
        issue = LintIssue(
            severity="info",
            rule="missing-points",
            page_path=None,
            message="无点数",
        )
        md = issue.to_markdown()
        assert "ℹ️" in md
        assert "无点数" in md


class TestLintResult:
    def test_report_generation(self):
        result = LintResult(
            issues=[
                LintIssue("error", "broken-links", "a.md", "bad link"),
                LintIssue("warning", "alias-conflicts", None, "conflict"),
            ],
            auto_fixed=1,
            total=2,
        )
        report = result.to_report()
        assert "# Lint Report" in report
        assert "bad link" in report
        assert "conflict" in report
        assert "**Auto-fixed:** 1" in report

    def test_empty_report(self):
        result = LintResult(issues=[], auto_fixed=0, total=0)
        report = result.to_report()
        assert "没有发现问题" in report
