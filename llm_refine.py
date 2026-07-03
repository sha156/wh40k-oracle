"""
llm_refine.py — 用 LLM 将 PDF 页文本重构为结构化 Markdown
==========================================================
用法：
  python llm_refine.py --book 钛帝国十版CODEX-20251112   # 按文件名子串匹配单本
  python llm_refine.py --all                              # 全量
需要环境变量 DEEPSEEK_API_KEY。结果缓存于 data_refined/<书名>/page_NNN.md，
按页文本哈希 + prompt 版本增量，可断点续跑。
"""
import hashlib
import json
from pathlib import Path
from typing import List, Tuple

import fitz

MIN_TEXT_CHARS = 20


def extract_pages(pdf_path: Path) -> List[dict]:
    """逐页提取文本，附 1-based 页号与 SHA-256。"""
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append({
            "page": i + 1,
            "text": text,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    doc.close()
    return pages


def page_paths(book_dir: Path, page_no: int) -> Tuple[Path, Path]:
    stem = "page_{:03d}".format(page_no)
    return book_dir / (stem + ".md"), book_dir / (stem + ".meta.json")


def save_page(book_dir: Path, page_no: int, markdown: str, meta: dict) -> None:
    book_dir.mkdir(parents=True, exist_ok=True)
    md_path, meta_path = page_paths(book_dir, page_no)
    md_path.write_text(markdown, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding="utf-8")


def is_cached(book_dir: Path, page_no: int, sha256: str, prompt_version: str) -> bool:
    md_path, meta_path = page_paths(book_dir, page_no)
    if not (md_path.exists() and meta_path.exists()):
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return (meta.get("sha256") == sha256
            and meta.get("prompt_version") == prompt_version
            and not meta.get("fallback", False))
