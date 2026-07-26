"""tests/test_wiki_core_rules_zh.py — 官方中文核心规则的提取、分栏与中英配对。

这一层的失败模式**全都不报错**：分栏错了正文会被侧边栏逐行插花，
阈值取错整节正文会跑进侧边栏、页面上只剩标题，节号被侧栏里的索引行截断
会让一节正文变成空字符串。所以用例围绕「静默失真必须被逮住」写，
而不是围绕「函数能跑通」写。

最强的一条是 `test_zh_en_section_numbers_match`：中英两版是同一套官方编号，
两侧节号集合必须完全相等。它不依赖任何一侧的排版假设，
正是它逮出了英文侧积压的 19 节缺失。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from wiki_engine.core_rules_zh import (EN_PDF, ZH_PDF, cross_check_report,
                                       format_zh_body, load_en_pdf_sections,
                                       load_zh_sections, parse_toc_zh,
                                       useful_asides)
from wiki_engine.pdf_sections import (ASIDE_CLOSE, ASIDE_OPEN, PdfSection,
                                      _column_bounds, _mask_asides,
                                      strip_asides)

REPO = Path(__file__).resolve().parent.parent
needs_zh = pytest.mark.skipif(not (REPO / ZH_PDF).exists(),
                              reason="需要 GW 官方中文核心规则 PDF")
needs_en = pytest.mark.skipif(not (REPO / EN_PDF).exists(),
                              reason="需要官方英文核心规则 PDF")


def _section(body: str) -> PdfSection:
    return PdfSection(num="01.01", title="测试", body=body, page=1)


# ── 分栏（一维聚类）────────────────────────────────────────────────

def test_column_bounds_splits_on_gap():
    """栏内 x0 抖动小、栏间距大，按间隔切才分得出真实的栏。"""
    assert _column_bounds([107.7, 110.0, 187.1, 195.6]) == [107.7, 187.1]


def test_column_bounds_single_column():
    assert _column_bounds([187.1, 190.0, 195.6]) == [187.1]


# ── 侧边栏剥离 ────────────────────────────────────────────────────

def test_strip_asides_extracts_and_cleans():
    body = "正文一\n{}\n边栏内容\n{}\n正文二".format(ASIDE_OPEN, ASIDE_CLOSE)
    clean, asides = strip_asides(body)
    assert asides == ["边栏内容"]
    assert "ASIDE" not in clean and "边栏内容" not in clean
    assert "正文一" in clean and "正文二" in clean


def test_strip_asides_handles_marker_split_across_sections():
    """侧边栏常跨小节边界，切分后一节手里只剩**半个**标记。

    成对匹配的正则对半个标记视而不见，`<!--/ASIDE--><!--ASIDE-->`
    就会原样留在正文里给读者看。
    """
    body = "尾巴内容\n{}\n正文\n{}\n开头内容".format(ASIDE_CLOSE, ASIDE_OPEN)
    clean, asides = strip_asides(body)
    assert "ASIDE" not in clean
    assert clean.strip() == "正文"
    assert set(asides) == {"尾巴内容", "开头内容"}


def test_mask_asides_preserves_offsets_and_newlines():
    """遮蔽必须等长且保留换行：调用方拿遮蔽版找标题、回原文取正文。"""
    body = "标题 01.01\n{}\n干扰 17.03\n{}\n正文".format(ASIDE_OPEN, ASIDE_CLOSE)
    masked = _mask_asides(body)
    assert len(masked) == len(body)
    assert masked.count("\n") == body.count("\n")
    assert "17.03" not in masked and "01.01" in masked


# ── 中文正文格式化 ────────────────────────────────────────────────

def test_format_joins_wrapped_lines_into_one_paragraph():
    """PDF 的换行是排版折行，不是段落分隔——不合并就是每行 20 字的锯齿正文。"""
    out = format_zh_body(_section("在游戏中的每一名玩家都将指挥一支军队，每\n"
                                  "一支军队都由单位构成。"))
    assert out == "在游戏中的每一名玩家都将指挥一支军队，每一支军队都由单位构成。"


def test_format_keeps_bullet_continuation_in_the_same_item():
    """列表项缩进后行本来就短，套用全节满行阈值会把续行甩成孤立一段。"""
    out = format_zh_body(_section(
        "▪每一名玩家在同一个阶段中使用相同计谋的次数不能超过\n一次。\n"
        "▪除非有其他明确规定，不能超过一次。"))
    assert "- 每一名玩家在同一个阶段中使用相同计谋的次数不能超过一次。" in out
    assert "\n\n一次。" not in out


def test_format_does_not_swallow_next_paragraph_after_a_closed_bullet():
    """列表项已经收句，后面那段就不该并进来——哪怕它正好排满一行。"""
    out = format_zh_body(_section(
        "▪敌方单位和模型指的是您对手的军队中的单位/模型。\n"
        "如一个规则没有明确规定是对己方还是敌方单位生效，那么它将对任何单位生效。"))
    assert out.startswith("- 敌方单位和模型指的是您对手的军队中的单位/模型。")
    assert "\n\n如一个规则没有明确规定" in out


def test_format_breaks_before_stratagem_field_heads():
    """时机/目标/效果/限制 是计谋最该一眼看清的部分，粘成一条就没法读。"""
    out = format_zh_body(_section(
        "1CP\n核心计谋\n风味文字。\n时机：对手移动阶段结束时。\n"
        "目标：一个己方单位。\n效果：进行一次入场移动。\n限制：第一轮不能用。"))
    assert "**1CP**" in out and "**核心计谋**" in out
    for field in ("时机：", "目标：", "效果：", "限制："):
        assert "\n\n{}".format(field) in out


def test_format_numbers_official_steps():
    out = format_zh_body(_section("按照以下流程结算攻击：\n"
                                  "1.\t选择敌方单位：选择一个敌方单位。\n"
                                  "2.\t拾取攻击骰：拾取骰子。"))
    assert "1. 选择敌方单位：选择一个敌方单位。" in out
    assert "2. 拾取攻击骰：拾取骰子。" in out


def test_format_drops_footer_flavour_text():
    """`++ … ++` 是页脚氛围引言，排在正文栏里，混进小节末尾会被读成规则。"""
    out = format_zh_body(_section("这是规则正文。\n++ 异形的心灵无法接受帝皇的祝福 ++"))
    assert "++" not in out
    assert out.strip() == "这是规则正文。"


def test_useful_asides_drops_cross_reference_index():
    """侧栏里的「另请参见」是交叉引用索引，wiki 自己有 crosslinks 体系。"""
    sec = PdfSection(num="04.03", title="结算攻击", body="", page=17,
                     asides=("另请参见\n选择武器\n▪[近距离] 24.07", "这是真的补充说明框。"))
    assert useful_asides(sec) == ["这是真的补充说明框。"]


# ── 中文目录 ──────────────────────────────────────────────────────

@needs_zh
def test_zh_toc_gives_24_chapters_with_parts():
    chapters = parse_toc_zh()
    assert [c.num for c in chapters] == ["{:02d}".format(i) for i in range(1, 25)]
    assert chapters[0].title == "核心概念" and chapters[0].part == "基础规则"
    assert chapters[-1].title == "核心技能" and chapters[-1].part == "参考"
    assert all(c.part for c in chapters), "有章没归到卷"


def test_zh_toc_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_toc_zh(tmp_path / "不存在.pdf")


# ── 中英交叉对账（本文件最重要的一条）──────────────────────────────

@needs_zh
@needs_en
def test_zh_en_section_numbers_match():
    """中英两版是同一套官方编号，节号集合必须完全相等。

    任一侧多出或少掉都不是「这个版本没这节」，而是那一侧解析漏了。
    这条不依赖任何排版假设，因此能发现单侧探测器发现不了的缺失——
    英文侧的 19 节缺口（正则漏 6 + refine 丢节号 13）就是它逮到的。
    """
    rep = cross_check_report()
    assert rep["zh_only"] == [], "中文有、英文没有——英文侧解析漏了"
    assert rep["en_only"] == [], "英文有、中文没有——中文侧解析漏了"
    assert rep["matched"] == 156


@needs_zh
def test_section_bodies_are_not_empty():
    """整节正文变成空字符串是本模块最阴的失真：

    04.03「结算攻击」的侧栏里全是 `▪[额外攻击] 24.11` 这样的节号引用，
    被版式折行的那些第二行不带项目符号、长得和真标题一样，
    于是这一节的正文范围被截断在它自己的侧边栏里。
    """
    zh = load_zh_sections()
    empty = [n for n, s in zh.items() if not format_zh_body(s).strip()]
    assert empty == [], "这些节的中文正文是空的：{}".format(empty)
    assert len(format_zh_body(zh["04.03"])) > 200


@needs_zh
def test_stratagem_cards_stay_in_their_own_section():
    """计谋页是双栏卡片、两栏都是正文。

    把右栏整栏当成侧边栏的话，烟幕（15.10）的正文会漏进迅速入场（15.07）。
    """
    zh = load_zh_sections()
    body = format_zh_body(zh["15.07"])
    assert "迅速" in zh["15.07"].title
    assert "入场移动" in body
    assert "烟幕" not in body and "神枪手" not in body


@needs_zh
def test_wrapped_chinese_titles_are_rejoined():
    """`活跃玩家和` + `对立玩家 01.03` 被版式拆成两行。

    不接回来的话，上半行会留在 01.02 的正文末尾，读起来像一句没写完的规则。
    """
    zh = load_zh_sections()
    assert zh["01.03"].title == "活跃玩家和对立玩家"
    assert not format_zh_body(zh["01.02"]).rstrip().endswith("活跃玩家和")


@needs_zh
@needs_en
def test_page_footer_decorations_are_not_treated_as_asides():
    """页码「16」、章名这类版面装饰不该变成「侧边栏」。

    但判据只能用长度不能用页边位置：计谋卡片标题在 y=29.8、页码在 y=28.3，
    按页高划页眉带会连着切掉 9 个真小节。
    """
    zh = load_zh_sections()
    for num, sec in zh.items():
        for aside in sec.asides:
            assert len(aside) >= 25, "{} 挂了一条装饰性侧栏：{!r}".format(num, aside)
