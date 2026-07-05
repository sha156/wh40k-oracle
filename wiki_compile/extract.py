"""extract_entities —— 扫描 data_refined 页级 md，产出实体候选清单（wiki_compile 流水线①）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
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


def _cont_page_continues(lines: List[str]) -> bool:
    """CONT 页是否真的续接前一实体：标记后第一条非空内容若直接是 ## 新标题则不算续页。"""
    for line in lines[1:]:
        if not line.strip():
            continue
        return not line.startswith("## ")
    return True  # 标记后无任何内容/无 ## 标题 → 视为续页


def extract_book(book_dir: Path) -> List[EntityCandidate]:
    """单本书：扫 page_*.md 的 ## 标题；CONT 续页与'详解'页并入实体页码。"""
    out: List[EntityCandidate] = []
    by_key = {}
    current: Optional[EntityCandidate] = None
    for md in sorted(book_dir.glob("page_*.md")):
        page_no = int(md.stem.split("_")[1])
        lines = md.read_text(encoding="utf-8").splitlines()
        if lines and lines[0].strip() == CONT_MARKER and current is not None \
                and page_no not in current.pages and _cont_page_continues(lines):
            current.pages.append(page_no)
        for line in lines:
            if not line.startswith("## "):
                continue
            heading = line[3:].strip()
            base, noise = heading, False
            for suf in NOISE_SUFFIXES:
                if base.endswith(suf):
                    base = base[: -len(suf)].strip()
                    noise = True
                    break
            if not base:
                continue  # 纯解说标题（## 能力详解）
            zh, en = parse_heading(base)
            key = (zh, en)
            if noise:
                cand = by_key.get(key)
                if cand is not None and page_no not in cand.pages:
                    cand.pages.append(page_no)
                continue
            cand = by_key.get(key)
            if cand is None:
                cand = EntityCandidate(book=book_dir.name, raw_heading=heading,
                                       name_zh=zh, name_en=en, pages=[page_no])
                by_key[key] = cand
                out.append(cand)
            elif page_no not in cand.pages:
                cand.pages.append(page_no)
            current = cand
    return out


def extract_entities(data_refined_dir: Path) -> List[EntityCandidate]:
    result: List[EntityCandidate] = []
    for book_dir in sorted(p for p in data_refined_dir.iterdir() if p.is_dir()):
        result.extend(extract_book(book_dir))
    return result
