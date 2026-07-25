"""wiki_engine/html_md.py — 官方结构库里的 HTML 片段 → wiki markdown。

`stratagems.text_zh` / `detachments.rule_text` / `enhancements.description` 三列存的
不是纯文本，是 Wahapedia 的 HTML 片段。实测标签分布（全库扫描，2026-07-25）：

    stratagems   1681/1682 含 HTML：b 10324、br 7031、span 4742、li 94、ul 46、div 42、i 16
    detachments   284/348  含 HTML：span 2602、br 655、li 437、td 404、b 374、tr 248、
                                    p 180、ul 175、div 140、table 130、i 32、a 32、img 12
    enhancements  533/1058 含 HTML：span 2202、li 148、br 65、ul 64、b 48、i 4、ol 2

三处**不能偷懒**的地方，偷了就是改规则：

① `<img src="…/d1.png">` 是**骰面图标**（2 个分队的 D6 结果表用它）。整条 `<[^>]+>` 正则
   剥标签会把「结果为 1-2 时」变成「结果为 时」——一句读着通顺、意思没了的规则。
② `<table>` 是真表格（130 处，如「战斗规模 → 可选单位数」档位表）。压成一行就没法读了。
③ 相邻的 `<span class="kwb">ADEPTUS</span> <span class="kwb">CUSTODES</span>` 是**一个**
   关键词而不是两个，拆开会让关键词识别与后续链接全错位。

关键词只在 `crosslinks._resolve_known_alias` 认得时才输出 `[[裸链]]`（交给
canonicalize_known_terms 落成真链接）；认不得的输出纯文本。**绝不预埋红链**——
本 wiki 里红链是 lint error，不是 TODO（宪法 §5）。
"""
from __future__ import annotations

import html as _html
import re
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

# 认识且有对应 markdown 语义的标签。不在此列的会进 warnings 供人工核对，
# 不静默吞——静默吞标签＝静默改规则文本。
_KNOWN_TAGS = {
    "b", "strong", "i", "em", "br", "p", "div", "span", "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "td", "th", "a", "img", "sup", "sub",
    "font", "u",
}

# 骰面图标：/wh40k10ed/img/d3.png → 3
_DICE_IMG = re.compile(r"/d(\d)\.png\s*$", re.IGNORECASE)


class _Converter(HTMLParser):
    """HTML 片段 → markdown。表格单独收集后统一渲染（表格里还会套表格）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: List[str] = []
        self.warnings: List[str] = []
        self._kw_buf: List[str] = []          # 连续 kwb span 的暂存（相邻的是同一个关键词）
        self._kw_depth = 0
        self._list_stack: List[str] = []      # "ul" / "ol"
        self._ol_counter: List[int] = []
        # 表格：栈式，支持嵌套（外层常是只含一个单元格的布局表）
        self._tables: List[List[List[str]]] = []
        self._had_th: List[bool] = []         # 该表是否出现过 <th>（决定首行是不是表头）
        self._row: List[List[str]] = []
        self._cell: Optional[List[str]] = None

    # ── 输出目标：在单元格里就写进单元格，否则写进正文 ──
    def _emit(self, text: str) -> None:
        if self._cell is not None:
            self._cell.append(text)
        else:
            self.out.append(text)

    def _flush_keyword(self) -> None:
        """把攒起来的相邻 kwb span 合成一个关键词再落地。"""
        if not self._kw_buf:
            return
        label = " ".join(w for w in (s.strip() for s in self._kw_buf) if w)
        self._kw_buf = []
        if not label:
            return
        from wiki_engine.crosslinks import _resolve_known_alias
        # 认得的才做裸链（交给 canonicalize 落成 [[path|label]]）；认不得的留纯文本
        self._emit("[[{}]]".format(label) if _resolve_known_alias(label) else label)

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        attrd = {k.lower(): (v or "") for k, v in attrs}
        if tag not in _KNOWN_TAGS:
            self.warnings.append("未知标签 <{}>".format(tag))
            return
        if tag != "span":
            self._flush_keyword()

        if tag in ("b", "strong"):
            self._emit("**")
        elif tag in ("i", "em"):
            self._emit("*")
        elif tag == "br":
            self._emit("\n")
        elif tag in ("p", "div"):
            self._emit("\n")
        elif tag == "span":
            cls = attrd.get("class", "")
            # kwb / kwb2 / kwbu 都是关键词徽章（tt kwbu、kwb kwbu 等组合类也算）
            if "kwb" in cls.split() or any(c.startswith("kwb") for c in cls.split()):
                self._kw_depth += 1
            else:
                self._flush_keyword()
        elif tag in ("ul", "ol"):
            self._list_stack.append(tag)
            self._ol_counter.append(0)
            self._emit("\n")
        elif tag == "li":
            depth = max(0, len(self._list_stack) - 1)
            indent = "  " * depth
            if self._list_stack and self._list_stack[-1] == "ol":
                self._ol_counter[-1] += 1
                self._emit("\n{}{}. ".format(indent, self._ol_counter[-1]))
            else:
                self._emit("\n{}- ".format(indent))
        elif tag == "table":
            self._tables.append([])
            self._had_th.append(False)
        elif tag == "tr":
            if self._tables:
                self._row = []
        elif tag in ("td", "th"):
            if self._tables:
                self._cell = []
                if tag == "th" and self._had_th:
                    self._had_th[-1] = True
        elif tag == "img":
            m = _DICE_IMG.search(attrd.get("src", ""))
            if m:
                self._emit(m.group(1))       # 骰面 → 数字，丢了规则就废了
            else:
                self.warnings.append("非骰面图片 <img src={!r}>".format(attrd.get("src")))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag not in _KNOWN_TAGS:
            return
        if tag == "span":
            if self._kw_depth > 0:
                self._kw_depth -= 1
                if self._kw_depth == 0:
                    pass                      # 交给下一个非 span 边界统一 flush（合并相邻）
            return
        self._flush_keyword()

        if tag in ("b", "strong"):
            self._emit("**")
        elif tag in ("i", "em"):
            self._emit("*")
        elif tag in ("p", "div"):
            self._emit("\n")
        elif tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()
                self._ol_counter.pop()
            self._emit("\n")
        elif tag in ("td", "th"):
            if self._tables and self._cell is not None:
                self._row.append(self._cell)
                self._cell = None
        elif tag == "tr":
            if self._tables and self._row:
                self._tables[-1].append(["".join(c) for c in self._row])
                self._row = []
        elif tag == "table":
            if self._tables:
                rows = self._tables.pop()
                has_head = self._had_th.pop() if self._had_th else False
                self._emit(_render_table(rows, has_head))

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if self._kw_depth > 0:
            self._kw_buf.append(data)
            return
        # kwb span 之间只隔空白时，视为同一个关键词的分词（ADEPTUS␣CUSTODES）
        if self._kw_buf and not data.strip():
            self._kw_buf.append(" ")
            return
        self._flush_keyword()
        self._emit(data)

    def close_all(self) -> str:
        self._flush_keyword()
        self.close()
        return "".join(self.out)


def _render_table(rows: List[List[str]], has_header: bool = False) -> str:
    """单元格矩阵 → markdown 表格。

    Wahapedia 的档位表常套两层：外层只有一个单元格、内容是真表格。这种"布局表"
    直接把内层结果透传，不再包一层（包了会渲染出一个 1×1 的空壳表）。

    has_header=False 时**补一行空表头**，而不是把首行提成表头。实测全库 404 个 td、
    0 个 th——这些表根本没有表头行，把「1 | 增益说明」这种骰面结果行提成表头
    就是凭空造了一个不存在的语义（还会被渲染成加粗居中）。空表头难看但不说谎。
    """
    rows = [[_squash(c) for c in r] for r in rows]
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return ""
    if len(rows) == 1 and len(rows[0]) == 1:
        return "\n{}\n".format(rows[0][0])          # 布局表：透传
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    if has_header:
        head, body = rows[0], rows[1:]
    else:
        head, body = [""] * width, rows
    lines = ["| " + " | ".join(head) + " |",
             "|" + "|".join(["---"] * width) + "|"]
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    return "\n" + "\n".join(lines) + "\n"


def _squash(text: str) -> str:
    """表格单元格：换行/多空白压成单空格，竖线转义（否则会把表格切列）。"""
    t = re.sub(r"\s+", " ", text or "").strip()
    return t.replace("|", "\\|")


def _tidy(md: str) -> str:
    """收尾：合并空白、去行尾空格、压掉 3 行以上空行、修复列表前的多余空行。"""
    md = _html.unescape(md)
    md = md.replace(" ", " ")
    md = re.sub(r"[ \t]+", " ", md)
    md = re.sub(r" *\n *", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"\*\*\s*\*\*", "", md)              # 空粗体（<b></b>）
    return md.strip()


def html_to_markdown(raw: Optional[str]) -> Tuple[str, List[str]]:
    """HTML 片段 → (markdown, 警告清单)。空输入返回 ("", [])。"""
    if not raw or not str(raw).strip():
        return "", []
    conv = _Converter()
    try:
        conv.feed(str(raw))
        text = conv.close_all()
    except Exception as exc:                         # 解析崩了要吼，不能吐半截规则
        return "", ["HTML 解析失败：{}: {}".format(type(exc).__name__, exc)]
    return _tidy(text), sorted(set(conv.warnings))


# ── 战略分段 ───────────────────────────────────────────────────────

# 官方段标签。实测 1682 条里 1673 条是 <b>WHEN:</b> 形态、133 条另有 RESTRICTIONS；
# 少数几条没加 <b>（AoI/TYR 各一条），另有 6 条灵族用 <span class="aeText">TRIGGER:</span>。
# 因此标签匹配不依赖 <b>，只认「行首/换行后的 大写标签 + 冒号」。
_SECTION_KEYS = ["WHEN", "TRIGGER", "TARGET", "EFFECT", "RESTRICTIONS"]
_SECTION_RE = re.compile(
    r"(?:^|\n)\s*\*{0,2}\s*(" + "|".join(_SECTION_KEYS) + r")\s*:\s*\*{0,2}",
    re.IGNORECASE)

# 段名 → wiki 小节名（宪法 §4.4 固定四节；TRIGGER 与 WHEN 是同一段的两种排版）
SECTION_TITLES = {
    "WHEN": "使用时机", "TRIGGER": "使用时机",
    "TARGET": "使用对象", "EFFECT": "效果", "RESTRICTIONS": "限制",
}


def split_stratagem(raw: Optional[str]) -> Tuple[Dict[str, str], List[str], List[str]]:
    """战略正文 → ({段名: markdown}, 段序, 警告)。

    拆不出标准段时返回空 dict —— 调用方应**原样保留整段并显式标注**，不许硬切
    （切错等于改规则，宪法 §4.4）。
    """
    md, warns = html_to_markdown(raw)
    if not md:
        return {}, [], warns
    hits = list(_SECTION_RE.finditer(md))
    if not hits:
        return {}, [], warns + ["未识别到 WHEN/TARGET/EFFECT 段"]
    sections: Dict[str, str] = {}
    order: List[str] = []
    for i, m in enumerate(hits):
        key = m.group(1).upper()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(md)
        body = md[m.end():end].strip()
        title = SECTION_TITLES[key]
        if title in sections:                        # 同名段重复：并进去，不覆盖丢内容
            sections[title] = (sections[title] + "\n\n" + body).strip()
        else:
            sections[title] = body
            order.append(title)
    lead = md[:hits[0].start()].strip()
    if lead:
        warns.append("段前有游离文本（已并入首段）：{}".format(lead[:60]))
        first = order[0]
        sections[first] = (lead + "\n\n" + sections[first]).strip()
    empty = [t for t in order if not sections[t]]
    if empty:
        warns.append("空段：{}".format("、".join(empty)))
    return sections, order, warns
