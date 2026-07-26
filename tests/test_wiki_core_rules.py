"""tests/test_wiki_core_rules.py — 11 版核心规则全文切章。

这一层的失败模式不是崩溃，而是**页面看着完整、内容少了几节**：小节标题在 refine
产物里有五六种排版，正则漏认一种就整章少内容，而生成器照样报"成功"。
所以用例全都围绕「漏切必须被发现」写。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from wiki_engine.core_rules import (REFINED_DIR, _SECTION, collect_sections,
                                    generate_all, looks_like_table,
                                    merge_bilingual, parse_toc,
                                    unextracted_hints)
from wiki_engine.core_rules_zh import ZH_PDF

REPO = Path(__file__).resolve().parent.parent
REFINED = REPO / REFINED_DIR
needs_refined = pytest.mark.skipif(
    not (REFINED / "page_002.md").exists(), reason="需要核心规则 refine 产物")
needs_zh_pdf = pytest.mark.skipif(
    not (REPO / ZH_PDF).exists(), reason="需要 GW 官方中文核心规则 PDF")


# ── 小节标题的排版变体（每一条都是实测踩出来的）────────────────────

@pytest.mark.parametrize("line,title,chapter,sec", [
    ("### [BLAST] 24.05", "[BLAST]", "24", "05"),
    ("## MEASURING DISTANCES 01.04", "MEASURING DISTANCES", "01", "04"),
    ("### TERRAIN OBJECTIVES (14.01)", "TERRAIN OBJECTIVES", "14", "01"),
    ("1. START OF COMMAND PHASE 08.01", "START OF COMMAND PHASE", "08", "01"),
    ("1.  **START OF CHARGE PHASE 11.01**", "START OF CHARGE PHASE", "11", "01"),
    ("**1. START OF SHOOTING PHASE 10.01**", "START OF SHOOTING PHASE", "10", "01"),
    ("## 21 SURGE MOVES 21.01", "SURGE MOVES", "21", "01"),
    # 第 15 章 11 条核心计谋全是这个形态：节号后面还挂着 CP 花费。
    # 漏掉它整章只剩 1 节，而 unextracted_hints() 也看不见——探测器
    # 与本正则共用「节号在行尾」的假设，一起瞎。
    ("## COMMAND RE-ROLL 15.02 (1CP)", "COMMAND RE-ROLL", "15", "02"),
    ("## HEROIC INTERVENTION 15.11 (2CP)", "HEROIC INTERVENTION", "15", "11"),
])
def test_section_heading_variants(line, title, chapter, sec):
    m = _SECTION.match(line)
    assert m, "认不出这种排版：{!r}".format(line)
    assert (m.group(1), m.group(2), m.group(3)) == (title, chapter, sec)


def test_section_regex_ignores_prose():
    """正文里提到节号不算标题，否则会把规则正文切碎。"""
    for line in ("Resolve a charge with your unit (11.02). While doing so,",
                 "see the Fight phase 12.03 for details",
                 "pg 6-25"):
        assert _SECTION.match(line) is None, line


# ── 目录（章名与分卷的真源）────────────────────────────────────────

@needs_refined
def test_toc_gives_all_24_chapters_with_parts():
    chapters = parse_toc(REFINED)
    assert len(chapters) == 24
    nums = [c.num for c in chapters]
    assert nums == ["{:02d}".format(i) for i in range(1, 25)]
    first, last = chapters[0], chapters[-1]
    assert (first.title, first.part) == ("CORE CONCEPTS", "BASIC RULES")
    assert (last.title, last.part) == ("CORE ABILITIES", "REFERENCE")
    assert all(c.part for c in chapters), "有章没归到卷"


def test_toc_missing_file_raises(tmp_path):
    """目录页缺失必须抛错——缺了就只能靠记忆补章名，那是编数据。"""
    with pytest.raises(FileNotFoundError):
        parse_toc(tmp_path)


def test_toc_too_few_chapters_raises(tmp_path):
    (tmp_path / "page_002.md").write_text(
        "## BASIC RULES\n01. CORE CONCEPTS - pg 8\n", encoding="utf-8")
    with pytest.raises(ValueError, match="只解析出"):
        parse_toc(tmp_path)


# ── 切章 ──────────────────────────────────────────────────────────

@needs_refined
def test_every_chapter_has_sections():
    """一章都切不出来 = 排版变体没认出来，不是"这章没内容"。"""
    sections = collect_sections(REFINED)
    chapters = parse_toc(REFINED)
    empty = [c.num for c in chapters if not sections.get(c.num)]
    assert not empty, "这些章一节都没切出来：{}".format(empty)


@needs_refined
def test_no_unextracted_section_numbers():
    """对账：行尾带节号却没被切出来的，一条都不许有。

    第 10/11/21 章与 24.07 都是这条对账逮出来的——漏切时页面看着完整，
    只有拿"疑似标题"去比才发现少了内容。
    """
    assert unextracted_hints(REFINED) == []


@needs_refined
def test_known_chapter_shapes():
    """几个被漏切过的章，钉死节数，防回归。"""
    sections = collect_sections(REFINED)
    assert len(sections["11"]) == 4      # 曾只切出 1 节（粗体包裹标题）
    assert len(sections["10"]) == 7      # 曾只切出 4 节（粗体在序号外面）
    assert len(sections["24"]) == 38     # 曾只切出 28 节（行尾控制字符）
    nums = [s.num for s in sections["24"]]
    assert "24.07" in nums, "[CLOSE-QUARTERS] 又丢了（行尾 0x08 退格符）"
    # 第 15 章曾只切出 15.01——11 条核心计谋的标题带 (1CP) 后缀，正则不认。
    # refine 产物本身还丢了 15.07–15.10/15.12 的节号，那 5 节走 PDF 兜底，
    # 所以这里断言的是 refine 侧能切出的 7 条。
    assert {s.num for s in sections["15"]} == {
        "15.01", "15.02", "15.03", "15.04", "15.05", "15.06", "15.11"}


@needs_refined
def test_control_characters_do_not_break_matching():
    """PDF 提取残留的控制字符肉眼不可见，但会让行尾匹配整条失效。"""
    raw = (REFINED / "page_080.md").read_text(encoding="utf-8", errors="ignore")
    assert any(ord(c) < 9 or ord(c) in (11, 12) or 14 <= ord(c) < 32 for c in raw), \
        "样本页不再含控制字符，本用例失去意义，请换一页或删除"
    assert "24.07" in {s.num for s in collect_sections(REFINED)["24"]}


@needs_refined
def test_sections_carry_source_pages():
    """无源不落笔：每节都要能回溯到 refine 的哪一页。"""
    sections = collect_sections(REFINED)
    for chapter, lst in sections.items():
        for s in lst:
            assert s.source_pages, "{} 没有来源页".format(s.num)
            assert all(p.startswith("page_") for p in s.source_pages)


@needs_refined
@needs_zh_pdf
def test_generate_writes_24_pages(tmp_path):
    rep = generate_all(REFINED, tmp_path)
    assert rep["chapters"] == 24 and rep["written"] == 24
    assert not rep["empty_chapters"] and not rep["orphan_chapters"]
    # 每一节都要配到英文原文：只有中文的节意味着某一侧解析漏了，
    # 而页面上只会表现为「这一节没有英文可展开」，不会报错
    assert rep["sections_without_en"] == []
    page = (tmp_path / "core-rules" / "sections" / "11-charge-phase.md").read_text(
        encoding="utf-8")
    assert "id: core-rules-11" in page
    # 中文标题在前、英文原名在下，正文中文、英文进折叠块
    assert "## 1. 冲锋阶段开始 11.01" in page
    assert "*START OF CHARGE PHASE*" in page
    assert "<summary>官方英文原文" in page
    # 语言口径要写在页面上，读者才知道判定以哪一份为准
    assert "GW 官方简体中文版" in page and "判定规则以英文原文为准" in page


@needs_refined
@needs_zh_pdf
def test_chapter_15_regains_all_twelve_stratagems(tmp_path):
    """第 15 章曾经只剩 1 节：11 条核心计谋因标题带 (1CP) 后缀被整体漏切。"""
    generate_all(REFINED, tmp_path)
    page = (tmp_path / "core-rules" / "sections" / "15-stratagems.md").read_text(
        encoding="utf-8")
    for num in ["15.0{}".format(i) for i in range(1, 10)] + ["15.10", "15.11", "15.12"]:
        assert " {}\n".format(num) in page, "第 15 章又丢了 {}".format(num)
    assert "迅速入场 15.07" in page and "*RAPID INGRESS*" in page
