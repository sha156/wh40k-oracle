"""tests/test_wiki_changelog.py — 官方「规则更新」章节 → 规则变更清单。

这一层最容易出的错是**安静地少抽几条**：起点定位偏一页、分栏没认出来、
字号档位飘一点，页面照样生成、看着也完整，只是某个分遣队的改动整块没了。
所以用例围绕「少抽必须被发现」写：三态区分（无章节 / 有章节但空 / 有条目）、
孤儿行对账、以及 v1.1 增量的红色标记不能丢。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from wiki_engine.changelog import (RED, UNIVERSAL_PDF, ZH_DIR, ChangeEntry,
                                   FactionChanges, collect_all,
                                   extract_faction_updates,
                                   extract_universal_updates, generate_all,
                                   render_faction_page, render_index)

REPO = Path(__file__).resolve().parent.parent
SORORITAS = REPO / ZH_DIR / ("chi_22-07_warhammer_40,000_faction_pack_"
                             "adepta_sororitas-mfa81okiaa-ljhyvd7hha.pdf")
DAEMONS = REPO / ZH_DIR / ("chi_22-07_warhammer_40,000_faction_pack_"
                           "chaos_daemons-snmzlfr9db-l7slhzjniq.pdf")
DEATHWATCH = REPO / ZH_DIR / ("chi_08-06_warhammer40000_faction_pack_"
                              "deathwatch-osd2qkkmkd-ipyq0msvac.pdf")

needs_sororitas = pytest.mark.skipif(not SORORITAS.exists(),
                                     reason="需要官方中文修女会阵营包")
needs_universal = pytest.mark.skipif(not (REPO / UNIVERSAL_PDF).exists(),
                                     reason="需要官方中文《通用规则更新》")
needs_zh_dir = pytest.mark.skipif(not (REPO / ZH_DIR).exists(),
                                  reason="需要 GW 官方中文 PDF 目录")


# ── 提取 ──────────────────────────────────────────────────────────

@needs_sororitas
def test_extracts_entries_with_groups_and_bodies():
    fc = extract_faction_updates(SORORITAS)
    assert fc.chapter_found and fc.version == "1.1"
    assert fc.faction_zh == "修女会", "阵营中文名要从章节页的巨号标题读"
    assert len(fc.entries) >= 15
    titles = {e.title for e in fc.entries}
    assert "帝皇圣光计谋，CP 花费" in titles
    groups = {e.group for e in fc.entries}
    assert "军队规则" in groups and "数据表" in groups
    assert all(e.body for e in fc.entries), "有条目抽到了标题却没抽到正文"


@needs_sororitas
def test_red_highlight_marks_the_v11_increment():
    """官方用红色标出「初版发布之后所作的修订」——这是 v1.1 增量的唯一一手证据。

    手上只有 v1.1 一版 PDF，没有 v1.0 可以 diff；红色丢了就再也算不出增量。
    """
    fc = extract_faction_updates(SORORITAS)
    new = {e.title for e in fc.entries if e.new_in_latest}
    assert "神圣干预计谋，效果部分" in new
    assert "神圣忏悔对答强化" in new
    # 不能全标红，否则等于没标
    assert 0 < len(new) < len(fc.entries)


@needs_sororitas
def test_entry_bodies_are_reflowed_not_raw_pdf_lines():
    """PDF 的换行是排版折行。原样保留会得到每行 20 来字的锯齿正文。"""
    fc = extract_faction_updates(SORORITAS)
    body = next(e.body for e in fc.entries if e.title == "神圣忏悔对答强化")
    assert "仅限大修女，宫廷官或教廷牧师模型。" in body


@needs_sororitas
def test_footer_effective_date_is_not_glued_to_last_entry():
    """页脚的生效日期行排在正文栏里、字号也和正文一样，混进去会被读成改动的一部分。"""
    fc = extract_faction_updates(SORORITAS)
    assert not any("起适用于对战模式" in e.body for e in fc.entries)


@needs_sororitas
def test_no_orphan_lines():
    """章节里的每一行都要归进某个条目——落单的行说明有排版变体没认出来。"""
    fc = extract_faction_updates(SORORITAS)
    assert fc.orphan_lines == [], "有行没归进任何条目：{}".format(fc.orphan_lines)


# ── 三态：0 条不等于抽取失败 ──────────────────────────────────────

@pytest.mark.skipif(not DAEMONS.exists(), reason="需要官方中文混沌恶魔阵营包")
def test_chapter_present_but_officially_empty():
    """混沌恶魔有「规则更新」章，但导言之后直接是常见问题解答。

    这是**官方本次没有改动**，不是抽取失败——两者必须能分开，
    否则真出问题时会被当成"又一个空章节"放过去。
    """
    fc = extract_faction_updates(DAEMONS)
    assert fc.chapter_found is True
    assert fc.entries == []


@pytest.mark.skipif(not DEATHWATCH.exists(), reason="需要官方中文死亡守望阵营包")
def test_first_edition_pack_has_no_update_chapter():
    fc = extract_faction_updates(DEATHWATCH)
    assert fc.chapter_found is False
    assert fc.version == "1.0"


# ── 通用规则更新 ──────────────────────────────────────────────────

@needs_universal
def test_universal_updates_merge_wrapped_title():
    """`可以在每个阶段/回合中` + `使用超过一次的计谋` 是被版式拆成两行的一个标题。"""
    uc = extract_universal_updates(REPO / UNIVERSAL_PDF)
    assert uc.version == "1.0"
    titles = [e.title for e in uc.entries]
    assert "可以在每个阶段/回合中使用超过一次的计谋" in titles
    assert len(uc.entries) == 4
    assert all(e.body for e in uc.entries)


# ── 渲染 ──────────────────────────────────────────────────────────

def _fake_changes() -> FactionChanges:
    return FactionChanges(
        faction="adepta sororitas", faction_zh="修女会", pdf="x.pdf",
        version="1.1", chapter_found=True, pages=[13],
        entries=[
            ChangeEntry("adepta sororitas", "军队规则", "甲计谋，CP 花费",
                        "修改为“2CP”。", False, 13),
            ChangeEntry("adepta sororitas", "军队规则", "乙强化",
                        "修改为：“持有者获得忏悔者关键词。”", True, 13),
        ])


def test_faction_page_marks_new_entries_and_uses_chinese_name():
    page, slug = render_faction_page(_fake_changes())
    assert slug == "adepta-sororitas"
    text = page.to_markdown()
    assert "《修女会》阵营包 v1.1" in text
    assert "### 乙强化 🆕" in text
    assert "### 甲计谋，CP 花费\n" in text and "甲计谋，CP 花费 🆕" not in text
    # 口径要写在页面上：读者得知道 🆕 是官方红色高亮，不是我们推断的
    assert "红色高亮" in text


def test_faction_page_says_which_kind_of_zero():
    empty = FactionChanges(faction="chaos daemons", faction_zh="混沌恶魔",
                           pdf="x.pdf", version="1.1", chapter_found=True)
    assert "官方本次没有列出任何改动" in render_faction_page(empty)[0].to_markdown()
    first = FactionChanges(faction="deathwatch", faction_zh="", pdf="x.pdf",
                           version="1.0", chapter_found=False)
    assert "尚无改动可列" in render_faction_page(first)[0].to_markdown()


def test_index_counts_and_links():
    index = render_index([_fake_changes()]).to_markdown()
    assert "**2 条阵营改动**" in index
    assert "| 修女会 | v1.1 | 2 | 1 |" in index
    assert "changelog/factions/adepta-sororitas.md" in index
    # 两条线口径不同，页面上要说清楚，别让人把数值漂移当成 v1.1 改动
    assert "fp_errata_patches.json" in index


# ── 端到端 ────────────────────────────────────────────────────────

@needs_zh_dir
def test_generate_all_writes_pages_and_reports_nothing_orphaned(tmp_path):
    rep = generate_all(REPO / ZH_DIR, tmp_path)
    assert rep["packs"] >= 27
    assert rep["entries"] > 500 and rep["new_in_latest"] > 50
    assert rep["universal"] == 4
    assert rep["written"] == rep["packs"] + 1        # 每包一页 + 总览
    assert rep["orphan_lines"] == {}, "有行没归进条目：{}".format(rep["orphan_lines"])
    assert (tmp_path / "changelog" / "index.md").exists()
    assert (tmp_path / "changelog" / "factions" / "space-marines.md").exists()


@needs_zh_dir
def test_collect_all_puts_universal_first():
    all_changes = collect_all(REPO / ZH_DIR)
    assert all_changes[0].faction == "Universal"
