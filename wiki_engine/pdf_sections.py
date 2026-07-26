"""wiki_engine/pdf_sections.py — 官方核心规则 PDF → 按官方节号切出的小节清单。

**为什么直接读 PDF、而不是复用 `data_refined/` 的 refine 产物**：refine 是 LLM 逐页
清洗出的 markdown，排版质量比 PDF 文本层好得多，但它在改写小节标题时会**丢掉官方
节号**——实测 13 节受害（`1. SELECT WEAPONS 04.01` 被写成 `**1. SELECT WEAPONS**:`，
`TERRAIN CATEGORIES 13.02` 整条标题消失）。节号是中英两版唯一可靠的配对键，丢了就配不上。
所以：**正文优先用 refine 产物（排版好），节号缺失时用本模块从 PDF 兜底**。

**为什么要列感知排序**：核心规则是双栏排版，计谋页更是双栏卡片。PyMuPDF 的
`get_text(sort=True)` 按视觉行序读，会把左右两栏**横向交错**成
`15.10RAPID INGRESS  15.07    1CP  SMOKESCREEN` 这种废话。按 (列, y) 排序才能拿到
「读完左栏再读右栏」的正确顺序。

**分栏必须按 x0 聚类，不能按页宽等分**。等分是本模块第一版的写法，在窄侧边栏页上
静默出错：第 16 页侧边栏在 x0≈107、正文在 x0≈187，页宽 454 等分成两半的分界是 227，
于是**两者都落进左半列**，再按 y 排序就把侧边栏逐行插进了正文——
「一个没有任何远程武器的模型…」和「为攻击单位中的每一个模型选择武器…」交替出现，
读起来像正文，实际是两段被拼碎的文字。栏间距（≥40pt）远大于栏内 x0 抖动（≤10pt），
按间隔切分能稳定分出真实的栏。

**这个模块存在的真正价值是对账**：中英两版 PDF 是同一套官方节号体系，
两边直提出来的节号集合**必须完全相同**。不同就是某一侧解析漏了——这条交叉验证
逮住了英文侧积压已久的 19 节缺失（正则漏切 6 + refine 丢号 13），
而仓库原有的 `unextracted_hints()` 探测器对它们**全部无感**：
它与被测正则共用「节号在行尾」的假设，只能发现自己已经想到的形态。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# 除换行与制表符外的控制字符 + 零宽字符。PDF 文本层残留（实测 0x08 退格符挂在
# `## [CLOSE-QUARTERS] 24.07` 行尾）肉眼不可见，却让「行尾匹配」整条失效——
# 章节切不出来，页面看着完整却少几节。解析前必须先清。
CONTROL_CHARS = re.compile(
    "[" + "".join(chr(c) for c in list(range(0, 9)) + [11, 12] + list(range(14, 32)) + [127])
    + "​‌‍⁠﻿­]")

# 官方节号：NN.NN，章号 01–24。`.00` 是**章级**引用（目录式清单里的「- Actions 16.00」），
# 官方节号从 .01 起，没有 .00 这一节。
_CHAPTER_MIN, _CHAPTER_MAX = "01", "24"

# 中文版小节标题：`军队 01.01`、`迅速入场 15.07`。
# 排除项目符号开头的行——`▪战斗震慑掷骰 01.07` 是「参见」清单项而不是标题，
# 认它会把一节正文从中间劈开。
SECTION_ZH = re.compile(
    r"^(?![ \t]*[▪▫►◄•·\-–—])[ \t]*(?P<title>[^\n]{0,40}?)[ \t]*"
    r"(?P<ch>\d{2})\.(?P<sec>\d{2})[ \t]*$", re.M)

# 英文版小节标题：`RAPID INGRESS 15.07`、`1. SELECT WEAPONS 04.01`、`TERRAIN CATEGORIES 13.02`，
# 以及第 24 章的词条形态 `[BLAST] 24.05`——方括号开头，漏掉它就少 22 节（整章的大半）。
# 首字符限定为大写字母/数字/左方括号，天然排除了 `▪Aura Abilities 22.01` 这类清单项。
SECTION_EN = re.compile(
    r"^[ \t]*(?P<title>[A-Z0-9\[][^\n]{0,60}?)[ \t]*"
    r"(?P<ch>\d{2})\.(?P<sec>\d{2})[ \t]*$", re.M)

# 标题跨行续接判据：**前一行带序号、本行不带序号**时，前一行是本标题的上半。
# 唯一实测样本是 `6. UNIT COMPOSITION` + `AND OTHER RULES 02.06`（官方标题
# 「6. UNIT COMPOSITION AND OTHER RULES」被版式拆成两行）。
# 反过来不能只看「前一行短且全大写」——第 16 页的步骤清单
# `3.\tRESOLVE ATTACKS` 正好排在 `1. SELECT WEAPONS 04.01` 上面，那样会误拼。
_NUMBERED_HEAD = re.compile(r"^[ \t]*\d+[.、\t ]")


@dataclass(frozen=True)
class PdfSection:
    """PDF 直提出的一节。`page` 是 1 起的 PDF 物理页码。

    `asides` 是版面上的侧边栏补充说明框，已从 `body` 剥离——
    它是官方正文的一部分（不能丢），但混在正文里会被读成规则本身（不能留）。
    """
    num: str            # "15.07"
    title: str          # "RAPID INGRESS" / "迅速入场"
    body: str
    page: int
    asides: Tuple[str, ...] = ()


# 栏间距下限。实测栏内 x0 抖动 ≤10pt（正文 187.1 与其缩进行 195.6），
# 相邻栏间距 ≥32pt（侧边栏 107.7 → 正文 187.1 是 79pt）。40 落在两者之间，
# 且离两侧都远，不是卡在边缘的魔数。
COLUMN_GAP = 40.0

# 同一侧边栏内相邻行的垂直间距。中文版侧边栏是逐行 block（行高 11pt），
# 两个不同侧边栏之间隔 36pt。20 落在中间，能把第 16 页的三个侧边栏
# （无远程/近战武器的模型 / 选择目标 / 副武器）分成三块而不是粘成一坨。
ASIDE_LINE_GAP = 20.0

# 侧边栏判据：栏宽不足**页宽**的这个比例。
#
# 两条都是踩出来的。① 不能用「非最宽栏即侧栏」——计谋页是双栏卡片，两栏都是正文，
# 那样会把右栏整栏（15.10–15.12 三条计谋）打成"侧边栏"，ASIDE 标记跨节残留、
# 烟幕的正文漏进迅速入场。② 基准也不能取「最宽栏」——第 57 页的页脚横幅
# `++ 信仰是最坚固的铠甲 ++` 横跨整页 323pt，把基准抬到让 176pt 的计谋正文栏
# 只剩 0.55，29 个小节的正文因此整段跑进侧边栏、页面上只剩标题。
# 页宽是稳定基准：实测侧边栏 65pt（14%）、计谋栏 176pt（39%）、正文栏 224pt（49%），
# 0.25 落在 14% 与 39% 之间，两侧都有充裕余量。
_ASIDE_WIDTH_RATIO = 0.25

# 侧边栏包裹标记。侧边栏是版面上的补充说明框，混进正文会读成规则本身；
# 但它也是官方正文的一部分，丢掉就是漏规则。所以按视觉位置插回正文流、
# 用标记圈起来，切分后能整块剥离单独渲染。
ASIDE_OPEN, ASIDE_CLOSE = "<!--ASIDE-->", "<!--/ASIDE-->"
_ASIDE_BLOCK = re.compile(
    re.escape(ASIDE_OPEN) + r"\n?(.*?)\n?" + re.escape(ASIDE_CLOSE), re.S)

# 版面装饰（页码「16」、章号「04」、重复的章标题「进行攻击」）要滤掉，
# 否则近半数节都挂着一个内容为「16」的"侧边栏"，把人训练成忽略侧边栏。
#
# 判据只能用**长度**，不能用页边位置：实测计谋卡片页的第一张卡片标题
# 「迅速入场 15.07」在 y=29.8，页码在 y=28.3——两者相差 1.5pt，
# 几何上根本分不开。按 6% 页高划页眉带会连着切掉 9 个真小节的标题
# （15.05/15.07 与第 24 章七个词条），而节数从 156 掉到 147 这件事
# **不会报错**，只会让页面安静地少几节。
_ASIDE_MIN_CHARS = 25


def _column_bounds(x0s: Sequence[float], gap: float = COLUMN_GAP) -> List[float]:
    """一维聚类：把 block 的 x0 按「间隔超过 gap 就换栏」切成若干栏的左边界。"""
    bounds: List[float] = []
    prev: Optional[float] = None
    for x in sorted(x0s):
        if prev is None or x - prev > gap:
            bounds.append(x)
        prev = x
    return bounds


def _merge_aside_runs(blocks: Sequence[tuple],
                      line_gap: float = ASIDE_LINE_GAP) -> List[Tuple[float, str]]:
    """同一侧栏里垂直相邻的行合并成一个整块，返回 [(顶部y, 文本)]。

    不合并的话，中文版逐行 block 会插回正文流时被拆成几十个独立标记，
    正文被切得七零八落。
    """
    runs: List[Tuple[float, List[str]]] = []
    last_bottom: Optional[float] = None
    for b in sorted(blocks, key=lambda b: (round(b[1], 1), b[0])):
        text = b[4].strip()
        if not text:
            continue
        if last_bottom is not None and b[1] - last_bottom <= line_gap and runs:
            runs[-1][1].append(text)
        else:
            runs.append((b[1], [text]))
        last_bottom = b[3]
    return [(y, "\n".join(parts)) for y, parts in runs]


def page_texts(pdf_path: Path, gap: float = COLUMN_GAP) -> List[str]:
    """逐页提取文本：正文栏为主流，侧边栏按视觉位置插回并用 ASIDE 标记圈起。

    栏数由每页的 block 分布自动测出，不写死——核心规则同一本里既有单栏跨页说明、
    双栏正文，也有「窄侧边栏 + 宽正文」和双栏计谋卡片，写死栏数必错一批。

    **正文栏 = 字符最多的那一栏**。以它为主流、侧边栏按 y 插回，
    是为了让侧边栏落在它视觉上所属的那一节里。若简单地「按栏号顺序拼接」，
    排在正文栏左边的侧边栏会整块挂到**上一页最后一节**的末尾——跨章挂错。
    """
    import fitz  # PyMuPDF；延迟导入，避免没装时整个 wiki_engine 不可用

    out: List[str] = []
    with fitz.open(str(pdf_path)) as doc:
        for page in doc:
            # b = (x0, y0, x1, y1, text, block_no, block_type)；type 0 才是文字
            blocks = [b for b in page.get_text("blocks")
                      if b[6] == 0 and b[4].strip()]
            if not blocks:
                out.append("")
                continue
            bounds = _column_bounds([b[0] for b in blocks], gap)

            def column_of(x0: float) -> int:
                idx = 0
                for i, left in enumerate(bounds):
                    if x0 >= left - 0.01:
                        idx = i
                return idx

            by_column: Dict[int, List[tuple]] = {}
            for b in blocks:
                by_column.setdefault(column_of(b[0]), []).append(b)

            def col_width(col: int) -> float:
                bs = by_column[col]
                return max(b[2] for b in bs) - min(b[0] for b in bs)

            page_width = page.rect.width or 1.0
            text_cols = sorted(c for c in by_column
                               if col_width(c) >= page_width * _ASIDE_WIDTH_RATIO)
            if not text_cols:                       # 理论上不会发生；退化成全是正文
                text_cols = sorted(by_column)

            # 正文栏按「先读完左栏再读右栏」拼接；侧栏合并成块后带标记按 y 插入。
            # 正文栏的排序键要保证栏间不交错，所以用 (栏序, y) 而不是纯 y。
            items: List[Tuple[Tuple[int, float], str]] = []
            for order, col in enumerate(text_cols):
                for b in sorted(by_column[col], key=lambda b: (round(b[1], 1), b[0])):
                    items.append(((order, round(b[1], 1)), b[4].strip()))
            for col, col_blocks in by_column.items():
                if col in text_cols:
                    continue
                order = sum(1 for c in text_cols if c < col) - 1
                for y, text in _merge_aside_runs(col_blocks):
                    if len(text.strip()) < _ASIDE_MIN_CHARS:
                        continue
                    items.append(((max(order, 0), round(y, 1)),
                                  "{}\n{}\n{}".format(ASIDE_OPEN, text, ASIDE_CLOSE)))
            items.sort(key=lambda it: it[0])
            out.append(CONTROL_CHARS.sub("", "\n".join(t for _, t in items)))
    return out


def _mask_asides(doc: str) -> str:
    """把 ASIDE 块内容换成等长空格，**保留换行与字符偏移**。

    偏移必须原样保持：调用方拿遮蔽版找标题位置，再回原文取正文。
    换行必须保留：标题正则是逐行匹配的，把换行也吃掉会让相邻行粘连、
    连正文里的真标题都匹配不上。
    """
    return _ASIDE_BLOCK.sub(
        lambda m: "".join(c if c == "\n" else " " for c in m.group(0)), doc)


def strip_asides(body: str) -> Tuple[str, List[str]]:
    """把正文里的 ASIDE 块剥出来，返回（纯正文, 侧边栏文本列表）。

    用状态机而不是「匹配成对标记」：一个侧边栏常常跨越小节边界，
    切分后某一节手里只剩**半个**标记。成对正则对半个标记视而不见，
    于是 `<!--/ASIDE--><!--ASIDE-->` 原样留在正文里给读者看。
    开头就遇到 CLOSE，说明这一节是从上一个侧边栏的中间开始的。
    """
    parts = re.split(r"({}|{})".format(re.escape(ASIDE_OPEN),
                                       re.escape(ASIDE_CLOSE)), body)
    first_mark = next((p for p in parts if p in (ASIDE_OPEN, ASIDE_CLOSE)), None)
    in_aside = first_mark == ASIDE_CLOSE
    clean_parts: List[str] = []
    asides: List[str] = []
    current: List[str] = []
    for part in parts:
        if part == ASIDE_OPEN:
            in_aside = True
            continue
        if part == ASIDE_CLOSE:
            if "".join(current).strip():
                asides.append("".join(current).strip())
            current = []
            in_aside = False
            continue
        (current if in_aside else clean_parts).append(part)
    if "".join(current).strip():
        asides.append("".join(current).strip())
    clean = re.sub(r"\n{3,}", "\n\n", "".join(clean_parts)).strip()
    return clean, asides


def raw_page_text(pdf_path: Path, index: int) -> str:
    """按 PDF 自身的 block 顺序取某页文本（0 起），不做分栏重排。

    目录页要用这个：它是一张跨两栏排下来的清单，PDF 的原始 block 顺序
    已经是「01…24」的正确阅读序。套用正文那套分栏 + 侧栏归位，
    第二栏的 21–23 章会被挪到 24 之后，卷归属跟着错位。
    """
    import fitz

    with fitz.open(str(pdf_path)) as doc:
        blocks = [b for b in doc[index].get_text("blocks")
                  if b[6] == 0 and b[4].strip()]
    return CONTROL_CHARS.sub("", "\n".join(b[4].strip() for b in blocks))


def build_document(texts: Sequence[str]) -> Tuple[str, List[Tuple[int, int]]]:
    """按页序拼成整份文档，并记录每个字符偏移属于第几页。

    **先拼再切**：小节会跨页续行，按页切会把一条规则拦腰截断。
    """
    chunks: List[str] = []
    offsets: List[Tuple[int, int]] = []
    pos = 0
    for i, t in enumerate(texts):
        offsets.append((pos, i + 1))
        chunks.append(t)
        pos += len(t) + 1
    return "\n".join(chunks), offsets


def _page_at(offsets: Sequence[Tuple[int, int]], pos: int) -> int:
    page = offsets[0][1] if offsets else 0
    for start, num in offsets:
        if start > pos:
            break
        page = num
    return page


def _continued_title(doc: str, match_start: int, title: str) -> Tuple[str, int]:
    """标题被版式拆成两行时，把上半行接回来。返回（完整标题, 上半行起点偏移）。

    起点偏移要一并返回：上半行必须从**上一节的正文**里切掉，
    否则「活跃玩家和」会留在 01.02 末尾，读起来像一句没写完的规则。
    """
    if _NUMBERED_HEAD.match(title):
        return title, match_start         # 本行自带序号，说明标题从本行起头
    line_start = doc.rfind("\n", 0, match_start) + 1
    prev_end = line_start - 1
    if prev_end <= 0:
        return title, match_start
    prev_start = doc.rfind("\n", 0, prev_end) + 1
    prev = doc[prev_start:prev_end].strip()
    if not prev:
        return title, match_start
    # ① 英文：上半行带序号（`6. UNIT COMPOSITION` + `AND OTHER RULES 02.06`）
    if _NUMBERED_HEAD.match(prev) and len(prev) <= 60:
        return "{} {}".format(prev, title).strip(), prev_start
    # ② 中文：上半行是个不带标点的短行（`活跃玩家和` + `对立玩家 01.03`）。
    #    再要求**它自己的上一行**已经收句，确认它是独立短行而不是某段的末行——
    #    只看「短且无标点」会把正文里的表格碎片当成标题上半截吞掉。
    if len(prev) <= _ZH_TITLE_HEAD_MAX and len(title) <= _ZH_TITLE_HEAD_MAX \
            and not prev.endswith(tuple("。！？，、；：)）】.,;:")):
        before_end = prev_start - 1
        if before_end <= 0:
            return "{}{}".format(prev, title).strip(), prev_start
        before = doc[doc.rfind("\n", 0, before_end) + 1:before_end].strip()
        if not before or before.endswith(tuple("。！？.")):
            return "{}{}".format(prev, title).strip(), prev_start
    return title, match_start


# 中文跨行标题上下半截各自的长度上限。官方中文小节名都很短
# （`活跃玩家和` + `对立玩家`），放宽会开始吞正文。
_ZH_TITLE_HEAD_MAX = 12


def split_sections(pdf_path: Path, pattern: re.Pattern,
                   gap: float = COLUMN_GAP) -> Dict[str, PdfSection]:
    """PDF → {节号: PdfSection}。同一节号重复出现时，正文更长的那份胜出。

    节号在目录页与「参见」清单里也会出现，那些命中的正文极短，
    靠「长者胜」自然被真正的正文顶掉。
    """
    doc, offsets = build_document(page_texts(pdf_path, gap=gap))
    # 找小节标题时先把侧边栏内容遮住。侧边栏里的「另请参见」索引整列都是
    # `▪[额外攻击] 24.11` 这样的节号引用，其中被版式折行的那些
    # （`▪射击处于交战状态的` / `凶兽与载具 17.03`）第二行不带项目符号，
    # 长得和真标题一模一样。不遮的话「3.结算攻击 04.03」的正文范围会被
    # 截断在它自己的侧边栏里，**整节正文变成空字符串**——而且中英两版
    # 一起空，对账也发现不了。
    hits = list(pattern.finditer(_mask_asides(doc)))
    # 先把每个标题的完整形态与真实起点算出来，再切正文：一节的正文必须止于
    # **下一节标题的起点**，而跨行标题的起点在它的上半行，不在节号那一行。
    titles = [_continued_title(doc, m.start(), m.group("title").strip())
              for m in hits]
    found: Dict[str, PdfSection] = {}
    for i, m in enumerate(hits):
        chapter, sec = m.group("ch"), m.group("sec")
        if not (_CHAPTER_MIN <= chapter <= _CHAPTER_MAX) or sec == "00":
            continue
        num = "{}.{}".format(chapter, sec)
        end = titles[i + 1][1] if i + 1 < len(hits) else len(doc)
        body, asides = strip_asides(doc[m.end():end].strip())
        title = titles[i][0]
        prev = found.get(num)
        if prev is not None and len(prev.body) >= len(body):
            continue
        found[num] = PdfSection(num=num, title=title, body=body,
                                page=_page_at(offsets, m.start()),
                                asides=tuple(asides))
    return found


def section_numbers(sections: Dict[str, PdfSection]) -> List[str]:
    return sorted(sections)


def cross_check(zh: Dict[str, PdfSection],
                en: Dict[str, PdfSection]) -> Dict[str, List[str]]:
    """中英两版节号必须**完全相同**——它们是同一套官方编号体系的两个语言版本。

    任何一侧多出或少掉都不是「这个版本没这节」，而是那一侧解析漏了。
    这条交叉验证是本模块存在的主要理由：单侧的正则探测器只能发现
    自己已经想到的排版形态，跨语言对账不受这个盲区限制。
    """
    zh_nums, en_nums = set(zh), set(en)
    return {
        "zh_only": sorted(zh_nums - en_nums),
        "en_only": sorted(en_nums - zh_nums),
        "common": sorted(zh_nums & en_nums),
    }
