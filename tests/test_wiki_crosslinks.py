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

    def test_no_nested_link_when_name_inside_existing_link_path(self):
        # 名称落在已有 [[...]] 的路径里不得再注入（基因窃取者 是
        # factions/基因窃取者教派/units/lictor.md 路径的子串）——否则嵌套断链
        page = _make_page(name_zh="潜袭者", name_en="Deathleaper",
                          body="武器：[[factions/基因窃取者教派/units/lictor.md|Lictor]] 之爪。")
        targets = {"基因窃取者": "factions/泰伦虫族/units/genestealers.md"}
        result = inject_wikilinks(page, targets, None)
        assert "[[factions/[[" not in result.body        # 无嵌套
        assert result.body.count("[[") == 1              # 仍只有原来那一条链接

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


class TestInjectionGuards:
    """gnhf 审查模块 6 F2：词界/阵营门——1715 单位名全局扫描曾产出 125 处
    词中注入与跨阵营错链（堡主战斧→SM Castellan、兽人页先知→灵族 Farseer）。"""

    def test_cross_faction_unit_target_not_injected(self):
        page = _make_page(name_zh="加兹古尔", name_en="Ghazghkull",
                          body="据说虚空幽龙很强。")
        targets = {"虚空幽龙": "factions/艾达灵族/units/void-dragon.md"}
        out = inject_wikilinks(page, targets,
                               self_path="factions/兽人/units/ghazghkull.md")
        assert "[[" not in out.body

    def test_same_faction_unit_target_injected(self):
        # 负向成对：同阵营单位名照常注入
        page = _make_page(name_zh="加兹古尔", name_en="Ghazghkull",
                          body="常与战争头目同行。")
        targets = {"战争头目": "factions/兽人/units/warboss.md"}
        out = inject_wikilinks(page, targets,
                               self_path="factions/兽人/units/ghazghkull.md")
        assert "[[factions/兽人/units/warboss.md|战争头目]]" in out.body

    def test_non_unit_target_not_gated(self):
        # core-rules 术语页不受阵营门限制
        page = _make_page(name_zh="加兹古尔", name_en="Ghazghkull",
                          body="可以深入打击进场。")
        targets = {"深入打击": "core-rules/deep-strike.md"}
        out = inject_wikilinks(page, targets,
                               self_path="factions/兽人/units/ghazghkull.md")
        assert "[[core-rules/deep-strike.md|深入打击]]" in out.body

    def test_short_pure_cjk_name_not_injected(self):
        # 两字纯中文名（先知/毒刃/堡主类）同形词遍地，即使同阵营也不注入
        page = _make_page(name_zh="加兹古尔", name_en="Ghazghkull",
                          body="伟大WAAAGH!的先知。")
        targets = {"先知": "factions/兽人/units/weirdboy.md"}
        out = inject_wikilinks(page, targets,
                               self_path="factions/兽人/units/ghazghkull.md")
        assert "[[" not in out.body

    def test_ascii_word_boundary(self):
        # "Vyper" 不得命中 "Vypers" 的前缀（成对：独立词照常注入）
        targets = {"Vyper": "factions/艾达灵族/units/vyper.md"}
        inside = _make_page(name_zh="风行者", name_en="Windrider",
                            body="Vypers move fast.")
        out1 = inject_wikilinks(inside, targets,
                                self_path="factions/艾达灵族/units/windrider.md")
        assert "[[" not in out1.body
        alone = _make_page(name_zh="风行者", name_en="Windrider",
                           body="The Vyper moves fast.")
        out2 = inject_wikilinks(alone, targets,
                                self_path="factions/艾达灵族/units/windrider.md")
        assert "[[factions/艾达灵族/units/vyper.md|Vyper]]" in out2.body


class TestKeywordAliasResolution:
    """武器词条 → core-rules 页的解析（2026-07-25 词条索引配套）。

    背景：建索引时逐条实测，46 个基础词条里 39 个从中英某一侧解析不出规则页——
    `anti.md` 存在却没有任何别名指向它，12 个 ANTI-X 全断。更隐蔽的一层是**大小写**：
    结构库的 keywords_json 存小写（"devastating wounds"），而别名表按官方写法登记大写，
    于是兵牌页同一格里 anti-infantry 2+ 成链（走 IGNORECASE 正则）、
    devastating wounds 是纯文本——一半能点一半不能。
    """

    def test_case_folded_lookup(self):
        from wiki_engine.crosslinks import _resolve_known_alias

        for raw in ("devastating wounds", "DEVASTATING WOUNDS", "Devastating Wounds"):
            assert _resolve_known_alias(raw) == "core-rules/devastating-wounds.md"
        assert _resolve_known_alias("psychic") == "core-rules/psychic-attacks.md"
        assert _resolve_known_alias("twin-linked") == "core-rules/twin-linked.md"
        assert _resolve_known_alias("ignores cover") == "core-rules/ignores-cover.md"

    def test_11e_new_keywords(self):
        """11 版新增/改名词条也要能落地。"""
        from wiki_engine.crosslinks import _resolve_known_alias

        assert _resolve_known_alias("CLEAVE") == "core-rules/cleave.md"
        assert _resolve_known_alias("横扫") == "core-rules/cleave.md"
        assert _resolve_known_alias("横扫1") == "core-rules/cleave.md"
        # 24.07：【手枪】等效替换为【近距离】，页仍名 pistol（改名等于改全部入链）
        assert _resolve_known_alias("CLOSE-QUARTERS") == "core-rules/pistol.md"
        assert _resolve_known_alias("近距离") == "core-rules/pistol.md"

    def test_dice_and_param_variants(self):
        from wiki_engine.crosslinks import _resolve_known_alias

        assert _resolve_known_alias("速射D6+3") == "core-rules/rapid-fire.md"
        assert _resolve_known_alias("连击D3") == "core-rules/sustained-hits.md"
        assert _resolve_known_alias("爆炸2") == "core-rules/blast.md"     # 11版带参形态
        assert _resolve_known_alias("ANTI-EPIC HERO 2+") == "core-rules/anti.md"
        assert _resolve_known_alias("ANTI-VEHICLE") == "core-rules/anti.md"
        assert _resolve_known_alias("反载具") == "core-rules/anti.md"

    def test_does_not_swallow_ordinary_words(self):
        """误链比断链更难发现：ANTI 的中文侧按目标关键词枚举，不用 `^反.*$`。"""
        from wiki_engine.crosslinks import _resolve_known_alias

        for word in ("反击", "反应", "反正", "针对", "Anti", "爆炸性", "速射手"):
            assert _resolve_known_alias(word) is None, word
