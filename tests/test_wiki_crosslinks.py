"""wiki_engine/crosslinks.py 测试：wikilink 注入。"""
from __future__ import annotations

from pathlib import Path

import pytest

from wiki_engine.crosslinks import (
    load_link_targets,
    inject_wikilinks,
    inject_all,
)
from wiki_engine.models import WikiPage, WikiPageFrontmatter


def _make_page(name_zh="火战士队", name_en="Fire Warriors",
               body="") -> WikiPage:
    fm = WikiPageFrontmatter(
        id="tau-empire/units/fire-warriors",
        name_zh=name_zh,
        name_en=name_en,
        faction="tau-empire",
        type="unit",
    )
    return WikiPage(fm=fm, body=body)


class TestLoadLinkTargets:
    def test_scans_pages(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        factions = wiki / "factions" / "tau-empire" / "units"
        factions.mkdir(parents=True)
        page = WikiPage(
            fm=WikiPageFrontmatter(
                id="tau/units/fw", name_zh="火战士队",
                name_en="Fire Warriors", faction="tau-empire", type="unit",
            ),
            body="test",
        )
        (factions / "fire-warriors.md").write_text(page.to_markdown(), encoding="utf-8")

        targets = load_link_targets(wiki)
        assert "火战士队" in targets
        assert "Fire Warriors" in targets
        # Path should be relative to wiki root
        assert "factions" in targets["火战士队"]


class TestInjectWikilinks:
    def test_first_occurrence_linked(self):
        page = _make_page(body="火战士队是一支基础步兵单位。火战士队装备脉冲步枪。")
        targets = {"火战士队": "factions/tau-empire/units/fire-warriors.md"}
        # 不链接自己——我们构造的 page 就是火战士队，所以应该 skip self
        result = inject_wikilinks(page, targets)
        # 自身不应被链接
        assert "[[" not in result.body

    def test_other_entity_linked(self):
        page = _make_page(
            name_zh="XV8危机战斗服",
            name_en="XV8 Crisis Battlesuits",
            body="可以与火战士队一起部署。",
        )
        targets = {"火战士队": "factions/tau-empire/units/fire-warriors.md"}
        result = inject_wikilinks(page, targets)
        assert "[[" in result.body
        assert "火战士队" in result.body

    def test_no_self_link(self):
        # A page about 火战士队 should NOT link to itself
        page = _make_page(name_zh="火战士队", body="火战士队是基础单位。")
        targets = {"火战士队": "factions/tau-empire/units/fire-warriors.md"}
        result = inject_wikilinks(page, targets)
        assert "[[" not in result.body

    def test_already_linked(self):
        page = _make_page(
            name_zh="XV8危机战斗服",
            body="[[factions/tau-empire/units/fire-warriors|火战士队]] nearby.",
        )
        targets = {"火战士队": "factions/tau-empire/units/fire-warriors.md"}
        result = inject_wikilinks(page, targets)
        # Should not double-link
        count = result.body.count("[[factions/tau-empire/units/fire-warriors")
        assert count <= 1

    def test_immutable(self):
        page = _make_page(body="original")
        targets = {"not present": "some/path.md"}
        result = inject_wikilinks(page, targets)
        # No changes: result body should be same as original
        assert result.body == "original"
        # Original should also be unchanged (immutable pattern)
        assert page.body == "original"


class TestInjectAllPreservesFrontmatter:
    """CRITICAL #2：inject_all 回写不得破坏嵌套 frontmatter。"""

    def test_full_frontmatter_survives_inject_all(self, tmp_path):
        wiki = tmp_path / "wiki"
        units = wiki / "factions" / "tau-empire" / "units"
        units.mkdir(parents=True)

        # 页面 X：含完整嵌套 frontmatter，正文提及页面 Y 的名称
        fm_x = WikiPageFrontmatter(
            id="tau-empire/units/crisis",
            name_zh="XV8危机战斗服",
            name_en="XV8 Crisis Battlesuits",
            aliases=["危机服", "Crisis Suits"],
            faction="tau-empire",
            type="unit",
            points={"3": 130},
            keywords=["Infantry", "Battlesuit"],
            version={"points": "MFM v1.4"},
            sources=[{"book": "钛帝国十版CODEX-20251112", "pages": [42, 43]}],
            raw=["data_refined/钛帝国十版CODEX-20251112/page_042.md",
                 "data_refined/钛帝国十版CODEX-20251112/page_043.md"],
            updated="2026-07-05",
        )
        fm_x.generate_tags()
        page_x = WikiPage(fm=fm_x, body="可以与火战士队一起部署。")
        (units / "crisis.md").write_text(page_x.to_markdown(), encoding="utf-8")

        # 页面 Y：链接目标
        fm_y = WikiPageFrontmatter(
            id="tau-empire/units/fire-warriors",
            name_zh="火战士队", name_en="Fire Warriors",
            faction="tau-empire", type="unit",
        )
        (units / "fire-warriors.md").write_text(
            WikiPage(fm=fm_y, body="火战士队正文。").to_markdown(), encoding="utf-8")

        modified = inject_all(wiki)
        assert any("crisis" in m for m in modified)

        # 回读页面 X，frontmatter 字段必须无损
        reread = WikiPage.from_markdown(
            (units / "crisis.md").read_text(encoding="utf-8"))
        assert reread is not None
        assert reread.fm.id == fm_x.id
        assert reread.fm.aliases == fm_x.aliases
        assert reread.fm.points == fm_x.points
        assert reread.fm.version == fm_x.version
        assert reread.fm.sources == fm_x.sources
        assert reread.fm.raw == fm_x.raw
        assert reread.fm.updated == fm_x.updated
        # 正文注入了链接
        assert "[[" in reread.body


class TestSelfPathFilter:
    """H14：候选目标路径 == 当前页自身路径时跳过（terms.json 全局别名自链漏洞）。"""

    def test_alias_pointing_to_self_not_injected(self):
        # 全局别名"火武士"→ 本页自己的 en 名，不在 fm 名称集里，
        # 仅靠 self_names 过滤挡不住 → 必须按目标路径过滤
        page = _make_page(name_zh="火战士队", name_en="Fire Warriors",
                          body="社区常称其为火武士。")
        targets = {"Fire Warriors": "factions/tau-empire/units/fire-warriors.md"}
        term_aliases = {"火武士": "Fire Warriors"}
        result = inject_wikilinks(
            page, targets, term_aliases,
            self_path="factions/tau-empire/units/fire-warriors.md")
        assert "[[" not in result.body

    def test_alias_to_other_page_still_injected(self):
        page = _make_page(name_zh="XV8危机战斗服", name_en="XV8 Crisis Battlesuits",
                          body="可与火武士协同作战。")
        targets = {"Fire Warriors": "factions/tau-empire/units/fire-warriors.md"}
        term_aliases = {"火武士": "Fire Warriors"}
        result = inject_wikilinks(
            page, targets, term_aliases,
            self_path="factions/tau-empire/units/crisis.md")
        assert "[[factions/tau-empire/units/fire-warriors.md|火武士]]" in result.body

    def test_inject_all_no_self_link_via_global_alias(self, tmp_path):
        import json
        wiki = tmp_path / "wiki"
        units = wiki / "factions" / "tau-empire" / "units"
        units.mkdir(parents=True)
        fm = WikiPageFrontmatter(
            id="tau/units/fw", name_zh="火战士队", name_en="Fire Warriors",
            faction="tau-empire", type="unit")
        (units / "fire-warriors.md").write_text(
            WikiPage(fm=fm, body="社区常称其为火武士。").to_markdown(),
            encoding="utf-8")
        terms = wiki / "terms.json"
        terms.write_text(json.dumps(
            {"pairs": [{"zh": "火武士", "en": "Fire Warriors"}]},
            ensure_ascii=False), encoding="utf-8")

        modified = inject_all(wiki, terms)
        assert modified == []  # 唯一候选是自链 → 不注入
        body = (units / "fire-warriors.md").read_text(encoding="utf-8")
        assert "[[" not in body.split("---", 2)[2]  # 正文无自链


class TestInjectAllTermsRobustness:
    """M6：inject_all 复用 load_term_aliases，非常规 terms.json 不再崩整个 CLI。"""

    def test_top_level_list_terms_json_survives(self, tmp_path):
        wiki = tmp_path / "wiki"
        units = wiki / "factions" / "tau-empire" / "units"
        units.mkdir(parents=True)
        fm = WikiPageFrontmatter(
            id="tau/units/fw", name_zh="火战士队", name_en="Fire Warriors",
            faction="tau-empire", type="unit")
        (units / "fire-warriors.md").write_text(
            WikiPage(fm=fm, body="正文。").to_markdown(), encoding="utf-8")
        terms = wiki / "terms.json"
        terms.write_text("[1, 2, 3]", encoding="utf-8")  # 顶层非 dict

        # 旧实现 data.get 直接 AttributeError 崩；现在应安全降级为无别名
        modified = inject_all(wiki, terms)
        assert modified == []


class TestLoadLinkTargetsFromFixture:
    def test_parses_aliases(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        fdir = wiki / "factions" / "test" / "units"
        fdir.mkdir(parents=True)
        fm = WikiPageFrontmatter(
            id="test/units/x", name_zh="测试单位",
            name_en="Test Unit", aliases=["TU", "测试"],
            faction="test", type="unit",
        )
        page = WikiPage(fm=fm, body="content")
        (fdir / "test-unit.md").write_text(page.to_markdown(), encoding="utf-8")

        targets = load_link_targets(wiki)
        assert "测试单位" in targets
        assert "Test Unit" in targets
        assert "TU" in targets
        assert "测试" in targets
