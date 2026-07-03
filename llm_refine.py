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
import re
import time
from collections import Counter
from pathlib import Path
from typing import List, Tuple

import fitz

from refine_prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt

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


def verify_numbers(source: str, markdown: str) -> List[str]:
    """校验生成 Markdown 的数字多重集合 ⊆ 原文，返回超出的 token。"""
    src_counts = Counter(re.findall(r"\d+", source))
    bad = []
    for tok, cnt in Counter(re.findall(r"\d+", markdown)).items():
        if cnt > src_counts.get(tok, 0):
            bad.append(tok)
    return sorted(bad)


MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"
MAX_RETRIES = 3


def _strip_code_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*\n", "", content)
        content = re.sub(r"\n```\s*$", "", content)
    return content.strip()


def refine_page(client, page_text: str, prev_tail: str) -> str:
    """调用 LLM 重构单页文本，重试 MAX_RETRIES 次，指数退避。"""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(page_text, prev_tail)},
                ],
                temperature=0.0,
                max_tokens=4096,
            )
            content = _strip_code_fence(resp.choices[0].message.content or "")
            if content:
                return content
            raise ValueError("LLM 返回空内容")
        except Exception as e:  # noqa: BLE001 — 网络/限流/空响应统一重试
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError("LLM 处理失败（重试{}次）: {}".format(MAX_RETRIES, last_err))
