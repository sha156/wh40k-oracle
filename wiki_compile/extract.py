"""extract_entities —— 扫描 data_refined 页级 md，产出实体候选清单（wiki_compile 流水线①）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

CONT_MARKER = "<!--CONT-->"

# 形如 (TX4) / （XV104） 的编号前缀
_PREFIX_RE = re.compile(r"^[\(（][^\)）]{1,10}[\)）]\s*")
# 标题结尾的英文名：大写开头、由大写/数字/常见标点组成、一直到行尾
_EN_TAIL_RE = re.compile(r"[A-Z][A-Z0-9'’\-\.,&/\(\) ]*$")
# 解说性子标题后缀：并入同名实体页码，不单独成实体
NOISE_SUFFIXES = ("能力详解", "武器详解", "技能详解", "详解")


@dataclass
class EntityCandidate:
    book: str
    raw_heading: str
    name_zh: Optional[str]
    name_en: Optional[str]
    pages: List[int] = field(default_factory=list)


def parse_heading(heading: str) -> Tuple[Optional[str], Optional[str]]:
    """'克鲁特狂兽小队 KROOTOX RAMPAGERS' → (中文名, 英文名)；缺失侧为 None。"""
    text = _PREFIX_RE.sub("", heading.strip())
    m = _EN_TAIL_RE.search(text)
    if m and len(m.group(0).strip()) >= 3:
        en = m.group(0).strip()
        zh = text[: m.start()].strip() or None
        return zh, en
    return (text or None), None
