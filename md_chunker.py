"""
md_chunker.py — 将 LLM 重构后的 Markdown 按条目（## 标题）分块
一个单位/战略技能/升级 = 一个完整 chunk，跨页条目自动合并。
仅依赖 langchain_core，保持可独立测试。
"""
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_core.documents import Document

CONT_MARKER = "<!--CONT-->"


# 武器表子标题：属性表 + 这些段落必须与单位名永远同块，见
# docs/superpowers/specs/2026-07-02-llm-pdf-refine-design.md:77-78
_WEAPON_SEGMENT_PREFIXES = ("### 远程武器", "### 近战武器")


def _hard_split(text: str, max_chunk_chars: int) -> List[str]:
    """无 ### 锚点的超长正文按字符数硬切（H5）。

    在 max_chunk_chars 内优先找最近的段落边界（\\n\\n）断开，退而求其次找
    单个换行，都没有才裸切字符，尽量不撕裂段落。"""
    parts: List[str] = []
    rest = text
    while len(rest) > max_chunk_chars:
        cut = rest.rfind("\n\n", 0, max_chunk_chars)
        if cut <= 0:
            cut = rest.rfind("\n", 0, max_chunk_chars)
        if cut <= 0:
            cut = max_chunk_chars
        parts.append(rest[:cut].rstrip("\n"))
        rest = rest[cut:].lstrip("\n")
    if rest:
        parts.append(rest)
    return parts


def _split_oversize(heading: str, body_lines: List[str],
                    max_chunk_chars: int) -> List[str]:
    """超长条目按 ### 边界二次切分，后续段落标题加（续）。

    硬性不变量：属性表（首个 ### 边界前的内容）与 ### 远程武器/### 近战武器
    段永远与单位名同块（chunk 0），即便因此超出 max_chunk_chars 也不拆分——
    这是覆盖体积预算的强约束。其余段落（如 ### 技能、单位构成等）仍按原有的
    体积装箱逻辑放入后续（续）chunk。若条目中不存在武器子段（非兵牌条目，如
    战略技能/升级），则完全等同于原实现：仅首段受保护，其余段落纯按体积装箱。
    """
    text = "\n".join(body_lines)
    if len(text) <= max_chunk_chars:
        return ["## {}\n{}".format(heading, text) if text else "## " + heading]
    if "\n### " not in "\n" + text:
        # 超长但无 ### 锚点（H5）：按字符数硬切，优先在段落边界 \n\n 附近断开，
        # 每段沿用同一 "## 标题（续）" 保持 unit/page 元数据一致——否则纯文字
        # 长章节会合并成无上限巨型 chunk，嵌入被静默截断。
        out = []
        for i, part in enumerate(_hard_split(text, max_chunk_chars)):
            prefix = "## {}\n" if i == 0 else "## {}（续）\n"
            out.append(prefix.format(heading) + part)
        return out

    segments, current = [], []
    for line in body_lines:
        if line.startswith("### ") and current:
            segments.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        segments.append("\n".join(current))

    weapon_indices = [i for i, seg in enumerate(segments)
                       if i > 0 and seg.startswith(_WEAPON_SEGMENT_PREFIXES)]

    if not weapon_indices:
        # 无武器段：等同于原实现，仅首段（属性表）受保护，其余纯按体积装箱
        parts, buf = [], ""
        for seg in segments:
            if buf and len(buf) + len(seg) > max_chunk_chars:
                parts.append(buf)
                buf = seg
            else:
                buf = buf + "\n" + seg if buf else seg
        if buf:
            parts.append(buf)
    else:
        # 有武器段：属性表 + 全部武器段强制同块，忽略体积预算；
        # 其余段落按体积装箱进入后续（续）chunk
        protected = [segments[0]] + [segments[i] for i in weapon_indices]
        rest = [seg for i, seg in enumerate(segments)
                if i != 0 and i not in weapon_indices]

        parts, buf = ["\n".join(protected)], ""
        for seg in rest:
            if buf and len(buf) + len(seg) > max_chunk_chars:
                parts.append(buf)
                buf = seg
            else:
                buf = buf + "\n" + seg if buf else seg
        if buf:
            parts.append(buf)

    out = []
    for i, part in enumerate(parts):
        prefix = "## {}\n" if i == 0 else "## {}（续）\n"
        out.append(prefix.format(heading) + part)
    return out


def chunk_markdown(pages: List[Tuple[int, str]], base_meta: dict,
                   max_chunk_chars: int = 2000) -> List[Document]:
    """按 ## 标题切分为条目 chunk；返回带 unit/page 元数据的 Document 列表。"""
    entries = []          # (heading, page_no, body_lines)
    heading, heading_page, body = None, None, []

    def _flush():
        if heading is None and not any(l.strip() for l in body):
            return
        entries.append((heading, heading_page, list(body)))

    for page_no, md_text in pages:
        for line in md_text.splitlines():
            if line.strip() == CONT_MARKER:
                continue
            if line.startswith("## "):
                _flush()
                heading, heading_page, body = line[3:].strip(), page_no, []
            else:
                if heading is None and heading_page is None:
                    heading_page = page_no
                body.append(line)
    _flush()

    docs = []
    for h, pg, body_lines in entries:
        if h is None:
            # 前言：取首个 "# " 一级标题作条目名
            h = "前言"
            for line in body_lines:
                if line.startswith("# "):
                    h = line[2:].strip()
                    break
        for text in _split_oversize(h, body_lines, max_chunk_chars):
            meta = dict(base_meta)
            meta["unit"] = h
            meta["page"] = pg
            docs.append(Document(page_content=text.strip(), metadata=meta))
    return docs


def load_refined_book(pdf_path: Path, refined_root: Path,
                      base_meta: dict) -> Optional[List[Document]]:
    """读取 data_refined/<书名>/page_*.md 并分块。

    目录不存在、无页文件、或分块结果为空（页文件全空）都返回 None，
    让 ingest.py 回退到 PDF 抽取（H4）——否则空 refined 目录会被误判
    "已完成"，该书 0 chunk 入库且被 processed_log 永久跳过。"""
    book_dir = refined_root / pdf_path.stem
    md_files = sorted(book_dir.glob("page_*.md"))
    if not md_files:
        return None
    pages = [(int(f.stem.split("_")[1]), f.read_text(encoding="utf-8"))
             for f in md_files]
    chunks = chunk_markdown(pages, base_meta)
    return chunks if chunks else None
