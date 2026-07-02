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
from pathlib import Path
from typing import List

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
