"""
md_chunker.py — 将 LLM 重构后的 Markdown 按条目（## 标题）分块
一个单位/战略技能/升级 = 一个完整 chunk，跨页条目自动合并。
仅依赖 langchain_core，保持可独立测试。
"""
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_core.documents import Document

CONT_MARKER = "<!--CONT-->"


def _split_oversize(heading: str, body_lines: List[str],
                    max_chunk_chars: int) -> List[str]:
    """超长条目按 ### 边界二次切分，后续段落标题加（续）。"""
    text = "\n".join(body_lines)
    if len(text) <= max_chunk_chars or "\n### " not in "\n" + text:
        return ["## {}\n{}".format(heading, text) if text else "## " + heading]

    segments, current = [], []
    for line in body_lines:
        if line.startswith("### ") and current:
            segments.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        segments.append("\n".join(current))

    parts, buf = [], ""
    for seg in segments:
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
    """读取 data_refined/<书名>/page_*.md 并分块；目录不存在或为空返回 None。"""
    book_dir = refined_root / pdf_path.stem
    md_files = sorted(book_dir.glob("page_*.md"))
    if not md_files:
        return None
    pages = [(int(f.stem.split("_")[1]), f.read_text(encoding="utf-8"))
             for f in md_files]
    return chunk_markdown(pages, base_meta)
