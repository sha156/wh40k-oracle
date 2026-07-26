"""wiki_engine/core_rules_zh.py — GW 官方简体中文核心规则 → 按官方节号切好的中文正文。

源是 `data/官方中文/chi_01-06_..._core_rules-*.pdf`：GW 官方发布的 11 版核心规则
**简体中文全译本**，88 页，与英文原版同一套 NN.NN 节号体系。

**这与「正文一律官方英文」的裁决不冲突**。那条裁决（2026-07-25）拒的是
`data_refined/战锤40K总规则10版老湿腐版1.11` 这类**十版民间汉化**——版本漂移，
叠上去会得到"读着通顺但与官网不一致"的规则页。本模块用的是 **GW 官方 11 版中文**，
按 wiki 宪法 §6 的权威级别（GW 官方中文 > 汉化组 > 社区）与英文原版同档。

**配对键是官方节号，不是标题文本、也不是顺序**。中英两版的节号一一对应，
`cross_check()` 实测 156 = 156、双向差集为空。这条跨语言对账顺带逮出了英文侧
积压的 19 节缺失（切分正则漏 6 + refine 产物丢节号 13）——
单侧的排版探测器发现不了它们，因为探测器与被测正则共用同一条假设。

CLI：python -m wiki_engine core-rules（中文正文已并入主生成器）
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from wiki_engine.pdf_sections import (PdfSection, SECTION_EN, SECTION_ZH,
                                      raw_page_text, split_sections)

ZH_PDF = Path("data/官方中文/chi_01-06_warhammer40k_new40k_core_rules-"
              "gihrxgzhgo-iickazpeog.pdf")
EN_PDF = Path("data/Core Rules - New 40K Core Rules.pdf")
ZH_BOOK = "核心规则（GW 官方简体中文，11 版）"

# 目录页的章行：`01.核心概念 第 8 页`
_TOC_CHAPTER_ZH = re.compile(r"^(\d{2})[.．]\s*(.+?)\s+第\s*(\d+)\s*页\s*$", re.M)
# 卷的页码范围行：`第 06-25 页`。卷名在它**上一行**（`基础规则`）。
_TOC_PART_RANGE = re.compile(r"^第\s*\d+\s*[-–—]\s*\d+\s*页\s*$")

# 侧栏里的「另请参见」是交叉引用索引，wiki 自己有 crosslinks 体系，重复渲染只会挤占版面；
# `++ … ++` 是页脚氛围引言，不是规则。两者都从侧栏补充说明里剔除。
_ASIDE_DROP = re.compile(r"^\s*(?:另请参见|SEE ALSO|\+\+)")

# 页脚氛围引言（`++ 异形的心灵无法接受帝皇的祝福 ++`）排在正文栏里，
# 位置上与正文无异，只能按这个官方版式约定认出来。它不是规则，混在小节末尾
# 会被读成规则的一部分。
_FLAVOUR_LINE = re.compile(r"^\+\+.*\+\+\s*\d*$")

# 官方中文计谋/规则条目的固定字段名。PDF 里它们各自起一行，但合并排版折行时
# 会被粘成「…方法。时机：对手移动阶段结束时。目标：一个位于…」这样一长条，
# 恰好把最需要一眼看清的触发条件糊掉。在这些词前强制断段。
_FIELD_HEADS = re.compile(
    r"^(?:时机|目标|效果|限制|满足条件|持续时间|花费|所需|额外效果)[:：]")
# 计谋卡片抬头：`1CP` 与 `核心计谋` 各自独立成行。
_CARD_HEADS = re.compile(r"^(?:\d+\s*CP|核心计谋|阵营计谋)$")
# 官方编号步骤：`1.\t选择敌方单位：…`。攻击流程这类逐步规则全靠它分步，
# 合并成一整段就没法读了。要求序号后跟分隔符，才不会吃掉「1CP」和正文里的年份。
_NUMBERED_STEP = re.compile(r"^(\d+)[.、．][ \t]*(?=\S)")


@dataclass(frozen=True)
class ChapterZh:
    num: str        # "01"
    title: str      # "核心概念"
    part: str       # "基础规则"
    page: int


def parse_toc_zh(pdf_path: Path = ZH_PDF) -> List[ChapterZh]:
    """官方中文目录页 → 24 章中文章名与分卷。解析不足 20 章直接抛错，不返回半张表。"""
    if not pdf_path.exists():
        raise FileNotFoundError(
            "找不到官方中文核心规则 {}——中文章名的唯一真源。"
            "缺了只能按记忆译章名，那是编数据".format(pdf_path))
    # 目录页走 PDF 原始 block 顺序：卷归属靠行的先后关系判定，
    # 一旦被正文那套分栏重排打乱，21–23 章会跟到「参考」卷底下去。
    text = raw_page_text(pdf_path, 1)            # page_002 是目录页
    lines = text.splitlines()
    chapters: List[ChapterZh] = []
    part = ""
    for i, line in enumerate(lines):
        if _TOC_PART_RANGE.match(line.strip()):
            # 页码范围行的上一行是卷名；卷名自带页码时（`简介  第 04-05 页`）走不到这里
            prev = lines[i - 1].strip() if i else ""
            if prev and not _TOC_CHAPTER_ZH.match(prev):
                part = prev
            continue
        m = _TOC_CHAPTER_ZH.match(line.strip())
        if m:
            chapters.append(ChapterZh(num=m.group(1), title=m.group(2).strip(),
                                      part=part, page=int(m.group(3))))
    if len(chapters) < 20:
        raise ValueError(
            "中文目录页只解析出 {} 章（预期 24）——官方 PDF 可能换版，先核对再生成"
            .format(len(chapters)))
    return chapters


@lru_cache(maxsize=4)
def _sections_cached(pdf: str, kind: str) -> Tuple[Tuple[str, PdfSection], ...]:
    pattern = SECTION_ZH if kind == "zh" else SECTION_EN
    return tuple(sorted(split_sections(Path(pdf), pattern).items()))


def load_zh_sections(pdf_path: Path = ZH_PDF) -> Dict[str, PdfSection]:
    """{节号: 中文小节}。PDF 解析不便宜（88 页 × 版面分栏），按路径缓存。"""
    return dict(_sections_cached(str(pdf_path), "zh"))


def load_en_pdf_sections(pdf_path: Path = EN_PDF) -> Dict[str, PdfSection]:
    """{节号: 英文小节}（PDF 直提）。只作 refine 产物缺节时的兜底与对账基准。"""
    return dict(_sections_cached(str(pdf_path), "en"))


def useful_asides(section: PdfSection) -> List[str]:
    """侧栏补充说明里真正是规则内容的那些。"""
    return [a for a in section.asides if not _ASIDE_DROP.match(a)]


def format_zh_body(section: PdfSection) -> str:
    """中文小节正文 → markdown。见 `format_zh_text`。"""
    return format_zh_text(section.body)


def format_zh_text(body: str) -> str:
    """官方中文 PDF 文本 → markdown。

    PDF 文本层的换行是**排版换行**（一栏排满就折行），不是段落分隔。
    直接保留会得到每行 20 来字的锯齿正文；直接全删又会把项目符号列表压成一坨。
    所以：项目符号 / 编号步骤 / 计谋字段各自成块，其余连续行按折行判据合并成段。
    """
    blocks: List[List[str]] = []       # [[kind, text], …]
    current: Optional[List[str]] = None

    def start(kind: str, text: str) -> List[str]:
        block = [kind, text]
        blocks.append(block)
        return block

    # 「上一行是不是被排版折断的」用物理判据：PDF 只有把一行**排满**才会折行，
    # 段落的最后一行则通常没排满。所以拿本节最长行当满行基准，
    # 上一行接近满行 = 下一行是它的续行；上一行明显短 = 段落已结束。
    # 不能改用「上一行以句号结尾就分段」——中文段落内部本来就多句相连，
    # 那样会把一整段切成一句一段。
    # 再加一条「上一行没收句」：行宽基准取全节最长行，而列表缩进后行宽本就更窄，
    # 单靠宽度会把「…但是存在」判成段落已结束、续行「以下限制：」甩成孤立一段。
    # 两条是 OR：排满了是折行，没收句也是折行。
    widths = [len(ln.strip()) for ln in body.splitlines() if ln.strip()]
    full_line = (max(widths) * 0.85) if widths else 0.0
    prev_width = 0.0
    prev_open = False

    for raw in body.splitlines():
        line = raw.strip()
        if not line or _FLAVOUR_LINE.match(line):
            current = None                        # 空行/氛围引言 = 段落到此为止
            prev_width, prev_open = 0.0, False
            continue
        wrapped = prev_width >= full_line or prev_open
        prev_width = len(line)
        prev_open = not line.endswith(tuple("。！？"))
        if line[0] in "▪▫►◄•·":
            current = start("bullet", line.lstrip("▪▫►◄•·").strip())
        elif _CARD_HEADS.match(line):
            start("card", line)
            current = None                        # 卡片抬头独立成段，不接续行
        else:
            step = _NUMBERED_STEP.match(line)
            if step:
                current = start(
                    "step", "{}. {}".format(step.group(1), line[step.end():].strip()))
            elif _FIELD_HEADS.match(line) or current is None:
                current = start("para", line)
            elif current[0] in ("bullet", "step"):
                # 列表项自成完整句，**看标点不看行宽**：列表缩进后每行本来就比
                # 正文短，套用全节统一的满行阈值会把「…的次数不能超过」判成
                # 段落已结束，续行「一次。」被甩成孤立一段。
                # 反过来「…单位/模型。」已经收句，后面那段就不该并进这个列表项。
                if current[1].rstrip().endswith(tuple("。！？")):
                    current = start("para", line)
                else:
                    current[1] += line
            elif not wrapped:
                current = start("para", line)
            else:
                # 普通行：这是上一块被版面折断的下半截，接回去而不是另起一段。
                # 中文折行处不留空格；只有折断处两侧都是 ASCII 时才补一个，
                # 免得把 `Waaagh! 抢走` 拼成 `Waaagh!抢走`。
                sep = " " if (current[1][-1:].isascii() and current[1][-1:].strip()
                              and line[:1].isascii()) else ""
                current[1] += sep + line

    out: List[str] = []
    for i, (kind, text) in enumerate(blocks):
        if not text:
            continue
        if kind == "bullet":
            out.append("- " + text)
        elif kind == "card":
            out.append("**{}**".format(text))
        else:
            out.append(text)
    return "\n\n".join(out)


def cross_check_report(zh_pdf: Path = ZH_PDF,
                       en_pdf: Path = EN_PDF) -> Dict[str, object]:
    """中英节号一致性报告。两版是同一套官方编号，任一侧多出或少掉都是解析漏了。"""
    zh, en = load_zh_sections(zh_pdf), load_en_pdf_sections(en_pdf)
    zs, es = set(zh), set(en)
    return {
        "zh_total": len(zh), "en_total": len(en),
        "zh_only": sorted(zs - es), "en_only": sorted(es - zs),
        "matched": len(zs & es),
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="wiki_engine.core_rules_zh")
    ap.add_argument("--zh", default=str(ZH_PDF))
    ap.add_argument("--en", default=str(EN_PDF))
    args = ap.parse_args()
    chapters = parse_toc_zh(Path(args.zh))
    rep = cross_check_report(Path(args.zh), Path(args.en))
    print("中文目录 {} 章；中文 {} 节 / 英文 {} 节，配上 {} 节".format(
        len(chapters), rep["zh_total"], rep["en_total"], rep["matched"]))
    if rep["zh_only"] or rep["en_only"]:
        print("⚠️ 节号不一致——某一侧解析漏了，别当成「这版没这节」：")
        print("   仅中文有：{}".format(rep["zh_only"]))
        print("   仅英文有：{}".format(rep["en_only"]))
    else:
        print("✅ 中英节号完全一致")


if __name__ == "__main__":
    main()
