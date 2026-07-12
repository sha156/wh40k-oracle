"""web_api/richtext.py — 轻标记纯文本 → RichText inline 数组（确定性 tokenizer）。

结构化 LLM 只写自然中文 + 三种轻标记，本模块用正则确定性切 span，不依赖 LLM 精确吐结构：
  【关键词】或 [非数字…]  → kw   （方括号内是纯数字则视为引用）
  [n]（纯数字）           → cite
  **结论**                → strong
  未被标记包裹的数值 token → num  （2.3 / 67% / 3+ / D6+1 / S12 / AP-4 / 5++ …）
  其余                     → text

歧义消解：`[` 后纯数字 → cite；含非数字 → kw（`[2]` 是引用、`[重型]` 是关键词）。
数值识别只作用于 text 段，绝不切进 kw/cite/strong 内部。
"""
from __future__ import annotations

import re
from typing import List

from web_api.contract import Inline, InlineCite, InlineText

# 显式标记：**strong** / 【kw】 / [inner]
_MARKER = re.compile(
    r"\*\*(?P<strong>[^*]+)\*\*"
    r"|【(?P<kw>[^】]+)】"
    r"|\[(?P<inner>[^\]]+)\]"
)

# 数值 token：可选 × 前缀 / 属性字母前缀（AP/S/T/W/M/OC/Ld/D），
# 数字主体带 . / + - 组合，尾随 + 或 %。
_NUM = re.compile(
    r"×?(?:AP|Ap|ap|S|T|W|M|OC|Oc|Ld|LD|ld|D)?-?\d+(?:[./+]\d+)*\+*%?"
)


def _split_numbers(text: str) -> List[Inline]:
    out: List[Inline] = []
    pos = 0
    for m in _NUM.finditer(text):
        if m.start() > pos:
            out.append(InlineText(t="text", s=text[pos:m.start()]))
        out.append(InlineText(t="num", s=m.group(0)))
        pos = m.end()
    if pos < len(text):
        out.append(InlineText(t="text", s=text[pos:]))
    return out


def to_richtext(s: str) -> List[Inline]:
    """轻标记纯文本 → RichText。空串返回空列表。"""
    if not s:
        return []
    out: List[Inline] = []
    pos = 0
    for m in _MARKER.finditer(s):
        if m.start() > pos:
            out.extend(_split_numbers(s[pos:m.start()]))
        if m.group("strong") is not None:
            out.append(InlineText(t="strong", s=m.group("strong")))
        elif m.group("kw") is not None:
            out.append(InlineText(t="kw", s="[" + m.group("kw") + "]"))
        else:
            inner = m.group("inner")
            if inner.isdigit():
                out.append(InlineCite(n=int(inner)))
            else:
                out.append(InlineText(t="kw", s="[" + inner + "]"))
        pos = m.end()
    if pos < len(s):
        out.extend(_split_numbers(s[pos:]))
    # 去掉空 text span（相邻标记间可能产生）
    return [x for x in out if not (isinstance(x, InlineText) and x.s == "")]
