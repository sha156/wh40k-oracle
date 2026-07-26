"""web_api/wiki_blocks.py — wiki markdown → WikiBlock/WikiSection（确定性块级 tokenizer）。

`wiki/` 下的分队/战略/增强页由 `wiki_engine/entity_pages.py` 确定性生成，形态是封闭的
（实测 3063 页只出现：`## 小节`、`### 子标题`、单行段落、`- ` 列表、`1. ` 列表、
markdown 表格、`> ` 引用），所以这里用正则逐行切块就够，不引 markdown 库。
前端拿到的是块数组，零解析——它没有 markdown 渲染器，也不该有。

三条容易踩的规矩：

1. **wikilink 一律降成显示名纯文本。** `[[路径\\|显示名]]` 与 `[[路径]]` 都只保留显示名。
   前端此刻没有 wiki 路由，渲染成 `<a>` 就是一片 404——宁可少个链接，不给死链。
   竖线有两种写法（正文里是裸 `|`，表格行里被 `escape_table_pipes` 转义成 `\\|`），
   两种都要认；只认一种会把另一种的整个路径当显示名喷到页面上。

2. **段落一行一块，不做跨行合并。** 实测 11806/11892 段本就是单行；剩下的多行游程是
   「**Incursion:** Up to 500 pts / **Strike Force:** …」这类伪列表，合并成一段会连成
   一句读不通的话。惟一例外是列表项的惰性续行（见 `_take_list`），那是 CommonMark 语义。

3. **表格单元格是纯字符串**（契约如此），所以要在这里把 `**粗体**` 星号剥掉、把转义竖线
   `\\|` 还原成 `|`——留着的话前端只会原样显示星号和反斜杠。拆列必须按**未转义**的竖线拆，
   先还原再拆会把单元格里的 `\\|` 当成列分隔符，整行断列。

导语（frontmatter 与第一个 `##` 之间那行）**不进块**：它是 cp/phase/detachment/cost
这些 frontmatter 字段拼出来的展示串，契约里那些字段都有，重复给一遍只会两处打架。
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterator, List, Optional, Tuple

import yaml

from web_api.contract import (InlineText, WikiBlock, WikiDetails, WikiHeading,
                              WikiListBlock, WikiParagraph, WikiQuote,
                              WikiSection, WikiTable)
from web_api.richtext import to_richtext

# ── 行首形态 ──────────────────────────────────────────────────────────

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_UL_ITEM = re.compile(r"^[-*]\s+(.*)$")
_OL_ITEM = re.compile(r"^\d+[.)]\s+(.*)$")
# 表格分隔行：|---|---| / |:--|--:| 之类
_TABLE_SEP = re.compile(r"^\|[\s\-:|]+\|$")
_QUOTE = re.compile(r"^\s*>\s?")
# 折叠块（核心规则页的中英对照）。整行匹配、不含行内写法：生成器写的就是独占一行，
# 放宽成"行内出现 <details>"只会把正文里提到这个词的句子误当成折叠开头
_DETAILS_OPEN = re.compile(r"^<details>\s*$")
_DETAILS_CLOSE = re.compile(r"^</details>\s*$")
_SUMMARY = re.compile(r"^<summary>(.*)</summary>\s*$")

_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
# 整行就是一对单星号：`*ARMIES*`。核心规则每节中文标题下面那行英文小节名就长这样
# （实测全库 165 处单星号里 164 处是整行）。**只认整行**、不做通用行内配对：
# 库里另有 `| 屁精监工 | 6" | 5* |` 这种脚注标记，和 PDF 直提残留的落单星号
# （`。*护卫单位`），通用配对会把两个不相干的星号之间的正文整段变成斜体
_WHOLE_LINE_EM = re.compile(r"^\*([^*]+)\*$")


# ── wikilink ─────────────────────────────────────────────────────────

def _lines_with_depth(body: str) -> List[Tuple[str, int]]:
    """逐行标注「此行位于第几层 `<details>` 内」。0 = 折叠之外。

    **凡是按 `## ` 切小节的地方都必须过这一层**，否则折叠里的英文标题会被当成小节分界。
    这不是假想的防御：核心规则页的英文原文自带 `## BATTLEFIELD MORALE` 这类标题
    （refine 产物的章节标题），实测 24 章里有 57 处。不认折叠深度就会
    ① 把折叠从那一行腰斩、后半段英文全部漏成顶层假小节，② 计数还显得挺正常
    （156 个折叠一个不少），是典型的看着对、内容已经错位。

    `<details>` 与 `</details>` 这两行本身算**在折叠内**（深度 ≥1）：它们是折叠的一部分，
    算作外层会让紧贴闭合标签的下一行判断出现一格错位。
    """
    out: List[Tuple[str, int]] = []
    depth = 0
    for line in body.splitlines():
        s = line.strip()
        if _DETAILS_OPEN.match(s):
            depth += 1
        out.append((line, depth))
        if _DETAILS_CLOSE.match(s) and depth > 0:
            depth -= 1
    return out


def _iter_sections(body: str) -> Iterator[Tuple[Optional[str], List[str]]]:
    """正文 → (小节名, 该节原始行) 序列；第一段的小节名为 None（导语）。

    切分只认**折叠之外**的 `## `（见 `_lines_with_depth`）。parse_sections /
    parse_intro / list_link_targets / section_table_rows 全部走它，
    四处各写一遍 `startswith("## ")` 就是四份会各自漂移的规则。
    """
    title: Optional[str] = None
    buf: List[str] = []
    for line, depth in _lines_with_depth(body):
        if depth == 0 and line.startswith("## "):
            yield title, buf
            title = line[3:].strip()
            buf = []
            continue
        buf.append(line)
    yield title, buf


def _link_parts(inner: str) -> Tuple[str, str]:
    """`[[…]]` 内文 → (目标路径, 显示名)。转义竖线与裸竖线都认。"""
    bits = re.split(r"\\\||\|", inner, maxsplit=1)
    target = bits[0].strip()
    if len(bits) > 1:
        return target, bits[1].strip()
    # 无管道的裸链接（本库实测 0 处，纯属防御）：拿末段文件名当显示名，
    # 否则会把 `factions/兽人/units/mek.md` 整条路径喷到正文里。
    tail = target.rsplit("/", 1)[-1]
    return target, tail[:-3] if tail.endswith(".md") else tail


def flatten_wikilinks(text: str) -> str:
    """把 `[[路径\\|显示名]]` / `[[路径]]` 降成显示名纯文本。"""
    return _WIKILINK.sub(lambda m: _link_parts(m.group(1))[1], text)


def list_link_targets(body: str, section_title: str) -> List[Tuple[str, str]]:
    """取某个 `## 小节` 下**列表项**里的 wikilink，返回 [(wiki 相对路径, 显示名)]。

    分队页的「## 增强」「## 战略」两节就是这种链接清单，详情端点靠它找子页。
    在这里按原始 markdown 扫，而不是从已解析的块里回捞——块里链接早被压成纯文本了，
    再想还原路径就只能靠名字猜，而名字跨阵营会撞（Infestation Swarm 有两个）。
    """
    out: List[Tuple[str, str]] = []
    for title, buf in _iter_sections(body):
        if title != section_title:
            continue
        for line in buf:
            stripped = line.strip()
            if not (_UL_ITEM.match(stripped) or _OL_ITEM.match(stripped)):
                continue
            for m in _WIKILINK.finditer(stripped):
                out.append(_link_parts(m.group(1)))
    return out


# ── frontmatter ──────────────────────────────────────────────────────

def split_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """`---` 包围的 YAML frontmatter → (dict, 正文)。没有 frontmatter 返回 ({}, 原文)。

    用 PyYAML 而不是手搓 `key: value`：这些页就是 wiki_engine 用 yaml.safe_dump 写出来的，
    同一套解析规则往返才对称。手搓一套「差不多的」规则，迟早在引号/撇号上和写入侧打架。
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    raw = text[3:end]
    rest = text[end + 4:]
    if rest.startswith("\n"):
        rest = rest[1:]
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}, text
    return (data if isinstance(data, dict) else {}), rest


# ── 块级 tokenizer ────────────────────────────────────────────────────

def _inline(text: str) -> List[Any]:
    return to_richtext(flatten_wikilinks(text).strip())


def _strip_bold(text: str) -> str:
    return _BOLD.sub(r"\1", text).strip()


def _emphasis_line(line: str) -> Optional[List[Any]]:
    """整行 `*斜体*` → 一个 em span；不是这种形态返回 None（交回常规 tokenizer）。

    不留星号是必须的：前端行内渲染器只认 `**粗体**`，单星号会原样显示成
    `*ARMIES*`——核心规则 156 节每节都在中文标题正下方露一次。

    这里不再往里切数值/关键词（Inline 是**平的**，没有嵌套）。代价只落在库里
    另外 3 处整行斜体的长句上：它们会少掉句内的关键词配色，但文字一字不少。
    """
    m = _WHOLE_LINE_EM.match(flatten_wikilinks(line).strip())
    if m is None:
        return None
    inner = m.group(1).strip()
    return [InlineText(t="em", s=inner)] if inner else None


def _row_cells(line: str) -> List[str]:
    """表格一行 → 单元格列表（wikilink 已压平、转义竖线已还原，**粗体星号尚在**）。

    粗体留到最后再剥：空表头提升（见 `_take_table`）要靠「整格是不是粗体」判断。
    """
    return [flatten_wikilinks(c).replace("\\|", "|").strip()
            for c in _UNESCAPED_PIPE.split(_strip_row_edges(line))]


def _take_table(lines: List[str], i: int) -> Tuple[WikiTable, int]:
    head = _row_cells(lines[i])
    i += 2                                     # 表头行 + 分隔行
    rows: List[List[str]] = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        if _TABLE_SEP.match(lines[i].strip()):
            i += 1
            continue
        rows.append(_row_cells(lines[i]))
        i += 1

    # 空表头提升：html_md 转出来的表一律不带 <th>，写成 `| | |` + 分隔行，真表头
    # 掉进了第一个数据行。不提升的话前端画出来就是一条空白表头 + 一行看着像数据的
    # "D6 / BUTTON EFFECT"。判据见 `_looks_like_header` 与 `_has_header_row`。
    if rows and all(not c for c in head) and _has_header_row(rows):
        head = rows[0]
        rows = rows[1:]

    head = [_strip_bold(c) for c in head]
    rows = [[_strip_bold(c) for c in r] for r in rows]
    # 列数对齐：短行补空格，长行反过来把表头撑宽。宁可多一列空表头，也不截断
    # ——截断是静默丢内容，而表格里丢掉的往往正是那条规则的数值。
    width = max([len(head)] + [len(r) for r in rows]) if (head or rows) else 0
    head = head + [""] * (width - len(head))
    rows = [r + [""] * (width - len(r)) for r in rows]
    return WikiTable(head=head, rows=rows), i


def _has_header_row(rows: List[List[str]]) -> bool:
    """首行是不是掉进表体的表头？

    光看首行不够：**表头之所以认得出来，是因为它和表体长得不一样**。机械修会
    Haloscreed Battle Clade 那张表整张都是全大写档位对（`INCURSION: | 1 UNIT` /
    `STRIKE FORCE | 2 UNITS` / `ONSLAUGHT | 3 UNITS`），只看首行会把「Incursion 档」
    这一条数据提成表头——那一档就此从表体消失，页面变成"这张表只有 Strike Force 和
    Onslaught"，是条毫不心虚的错误答案。所以再加一条：表体里至少要有一行**不**像表头。

    只有一行的表因此一律不提升（`rows[1:]` 为空）：提上去就剩一张空表，
    留在表体里最多是少一行表头，宁可少画表头也不吞内容。
    """
    if not _looks_like_header(rows[0]):
        return False
    return not all(_looks_like_header(r) for r in rows[1:])


def _looks_like_header(cells: List[str]) -> bool:
    """这一行是不是掉进表体的表头？判据：每格非空、**没有一个小写字母**、至少一格有字母。

    Wahapedia 的表头一律全大写（BATTLE SIZE / NUMBER OF UNITS / D6 / BUTTON EFFECT），
    正文行必然带小写，这条线切得比"每格都加粗"干净——实测 16 张表里 the-angelic-host
    的表头只加粗了一格（`| **BATTLE SIZE** | UNITS |`），按加粗判会漏掉它。
    反过来 creations-of-bile 的首行是 `| 1 | **Cholinergic Accelerants:** Add 1 to… |`，
    带小写，正确地不被当表头（那张表本来就没有表头）。
    """
    if not cells or any(not c for c in cells):
        return False
    plain = [_strip_bold(c) for c in cells]
    if any(re.search(r"[a-z]", c) for c in plain):
        return False
    return any(re.search(r"[A-Z一-鿿]", c) for c in plain)


def _item_kind(line: str) -> Optional[str]:
    s = line.strip()
    if _UL_ITEM.match(s):
        return "ul"
    if _OL_ITEM.match(s):
        return "ol"
    return None


def _item_text(line: str) -> str:
    s = line.strip()
    m = _UL_ITEM.match(s) or _OL_ITEM.match(s)
    return m.group(1).strip() if m else s


def _take_list(lines: List[str], i: int) -> Tuple[WikiListBlock, int]:
    """连续列表项 → 一个 ul/ol 块，带 CommonMark 惰性续行。

    惰性续行是必须的：黑暗灵族「战斗药剂」写成 `1. Adrenalight` + 下一行效果描述，
    不续行的话效果会掉成独立段落、并且把列表切断——6 条药剂会渲染成六个各自从 1
    开始编号的单项列表。空行也不能直接收尾（同一份列表的条目之间就隔着空行），
    要往后探一眼：下一个非空行还是同类列表项就继续。
    """
    kind = _item_kind(lines[i]) or "ul"
    items: List[str] = []
    n = len(lines)
    while i < n:
        s = lines[i].rstrip()
        if not s.strip():
            j = i
            while j < n and not lines[j].strip():
                j += 1
            if j < n and _item_kind(lines[j]) == kind:
                i = j
                continue
            break
        this_kind = _item_kind(s)
        if this_kind == kind:
            items.append(_item_text(s))
            i += 1
            continue
        if this_kind is not None or _HEADING.match(s) or s.lstrip()[:1] in ("|", ">"):
            break
        if not items:
            break
        items[-1] = (items[-1] + " " + s.strip()).strip()
        i += 1
    return WikiListBlock(t=kind, items=[_inline(x) for x in items]), i


def _take_details(lines: List[str], i: int) -> Tuple[WikiDetails, int]:
    """`<details>` … `</details>` → 一个折叠块（内部照常递归切块）。

    两处刻意的选择：

    · **按 `<details>` 计数配对**，不认第一个 `</details>` 就收尾。库里此刻没有嵌套折叠，
      但真出现嵌套时提前收尾会把外层剩下的正文全部当成兄弟块甩出去，且完全不报错。
    · **没有闭合标签就吃到结尾**。这种页是被截断了；把剩下的正文都收进折叠里，
      内容一条不丢（只是多包了层折叠），比在这里 `break` 丢掉后半页安全。
    """
    i += 1                                      # 吃掉 <details>
    n = len(lines)
    summary = ""
    if i < n:
        m = _SUMMARY.match(lines[i].strip())
        if m:
            summary = flatten_wikilinks(m.group(1)).strip()
            i += 1
    depth = 1
    body: List[str] = []
    while i < n:
        s = lines[i].strip()
        if _DETAILS_OPEN.match(s):
            depth += 1
        elif _DETAILS_CLOSE.match(s):
            depth -= 1
            if depth == 0:
                i += 1
                break
        body.append(lines[i])
        i += 1
    return WikiDetails(summary=summary, blocks=parse_blocks(body)), i


def parse_blocks(lines: List[str]) -> List[WikiBlock]:
    """一段 markdown 行 → WikiBlock 数组。"""
    out: List[WikiBlock] = []
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].rstrip()
        if not s.strip():
            i += 1
            continue
        if _DETAILS_OPEN.match(s.strip()):
            det, i = _take_details(lines, i)
            out.append(det)
            continue
        # 落单的 </details>（上一块已收尾/页面被改坏）：丢掉标签本身，不当正文喷出去
        if _DETAILS_CLOSE.match(s.strip()):
            i += 1
            continue
        m = _HEADING.match(s)
        if m:
            out.append(WikiHeading(level=len(m.group(1)),
                                   text=flatten_wikilinks(m.group(2)).strip()))
            i += 1
            continue
        if _QUOTE.match(s):
            buf: List[str] = []
            while i < n and _QUOTE.match(lines[i].rstrip()) and lines[i].strip():
                buf.append(_QUOTE.sub("", lines[i].rstrip()))
                i += 1
            out.append(WikiQuote(inline=_inline(" ".join(x for x in buf if x))))
            continue
        if (s.lstrip().startswith("|") and i + 1 < n
                and _TABLE_SEP.match(lines[i + 1].strip())):
            table, i = _take_table(lines, i)
            out.append(table)
            continue
        if _item_kind(s):
            lst, i = _take_list(lines, i)
            out.append(lst)
            continue
        out.append(WikiParagraph(inline=_emphasis_line(s) or _inline(s)))
        i += 1
    return out


def parse_intro(body: str) -> List[WikiBlock]:
    """第一个 `##` **之前**那几块（导语）。

    与 `parse_sections` 刻意分开、按需调用：分队页的导语是 frontmatter 字段拼出来的
    展示串，重复给一遍只会两处打架（见本模块顶注）；核心规则页与变更清单页的导语里
    装的却是「判定规则以英文原文为准」「🆕 判据来自官方红色高亮」这类**诚实披露**，
    丢了页面就变成一份看着毫不心虚的定稿。所以按页型决定要不要它，不做成默认行为。
    """
    for title, buf in _iter_sections(body):
        if title is None:
            return parse_blocks(buf)
    return []


def find_wikilinks(text: str) -> List[Tuple[str, str]]:
    """一段文本里的全部 wikilink → [(目标路径, 显示名)]。

    表格单元格里的链接靠它取：`list_link_targets` 只扫列表项（分队页的清单是列表），
    而变更清单的一览表把明细链接放在表格最后一列。转义竖线两种写法都认（`_link_parts`）。
    """
    return [_link_parts(m.group(1)) for m in _WIKILINK.finditer(text)]


def section_table_rows(body: str, section_title: str) -> List[List[str]]:
    """某个 `## 小节` 下表格的**数据行**，单元格保留原始 markdown（含 wikilink）。

    表头行与分隔行都剔掉：表头的判据是「下一行是分隔行」，比按内容猜表头稳
    （`_looks_like_header` 那套是给没有表头的表用的，这里的表明确有表头）。

    为什么不从已解析的块里回捞：块里的 wikilink 早被压成显示名（全是「查看」），
    路径没了就只能靠阵营名去猜文件名——而 slug 与显示名并不一一对应
    （orkss.md ↔ 欧克蛮人、imperia-knights.md ↔ 帝国骑士）。
    """
    rows: List[List[str]] = []
    for title, buf in _iter_sections(body):
        if title != section_title:
            continue
        for idx, line in enumerate(buf):
            s = line.strip()
            if not s.startswith("|") or _TABLE_SEP.match(s):
                continue
            nxt = buf[idx + 1].strip() if idx + 1 < len(buf) else ""
            if _TABLE_SEP.match(nxt):           # 这是表头行
                continue
            rows.append([c.strip()
                         for c in _UNESCAPED_PIPE.split(_strip_row_edges(s))])
    return rows


def _strip_row_edges(line: str) -> str:
    """剥掉表格行首尾的竖线。行尾若是转义竖线 `\\|` 则不剥——那是单元格内容。"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return s


def parse_sections(body: str) -> List[WikiSection]:
    """正文（不含 frontmatter）→ `## 小节` 数组。第一个 `##` 之前的导语按设计丢弃
    （核心规则页那种导语里有诚实披露的，另调 `parse_intro` 取）。"""
    return [WikiSection(title=title, blocks=parse_blocks(buf))
            for title, buf in _iter_sections(body) if title is not None]


def pick_sections(sections: List[WikiSection],
                  titles: Tuple[str, ...]) -> List[WikiSection]:
    """按小节名筛选并保持给定顺序（页面缺某节时就少一节，不塞空壳）。"""
    by_title = {s.title: s for s in sections}
    return [by_title[t] for t in titles if t in by_title]
