"""
llm_refine.py — 用 LLM 将 PDF 页文本重构为结构化 Markdown
==========================================================
用法：
  python llm_refine.py --book 钛帝国十版CODEX-20251112   # 按文件名子串匹配单本
  python llm_refine.py --all                              # 全量
需要环境变量 DEEPSEEK_API_KEY。结果缓存于 data_refined/<书名>/page_NNN.md，
按页文本哈希 + prompt 版本增量，可断点续跑。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import fitz
from tqdm import tqdm

from refine_prompt import (
    PROMPT_VERSION, PROMPT_VERSION_EN,
    SYSTEM_PROMPT, SYSTEM_PROMPT_EN,
    build_user_prompt,
)

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


MODEL = "deepseek-v4-pro"
BASE_URL = "https://api.deepseek.com"
MAX_RETRIES = 3


def _strip_code_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*\n", "", content)
        content = re.sub(r"\n```\s*$", "", content)
    return content.strip()


def refine_page(client, page_text: str, prev_tail: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """调用 LLM 重构单页文本，重试 MAX_RETRIES 次，指数退避。"""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
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


PREV_TAIL_CHARS = 500
DATA_DIR = Path("data")
OUT_DIR = Path("data_refined")


def process_book(client, pdf_path: Path, out_root: Path, workers: int = 4, lang: str = "zh") -> dict:
    """整本处理：提取→过滤→并发 LLM→缓存落盘。返回统计 summary。"""
    pages = extract_pages(pdf_path)
    book_dir = out_root / pdf_path.stem
    book_dir.mkdir(parents=True, exist_ok=True)

    pv = PROMPT_VERSION_EN if lang == "en" else PROMPT_VERSION
    sp = SYSTEM_PROMPT_EN if lang == "en" else SYSTEM_PROMPT

    summary = {"book": pdf_path.name, "total": len(pages), "done": 0,
               "cached": 0, "skipped": 0, "failed": 0, "verify_warn": 0}

    raw_by_no = {p["page"]: p["text"] for p in pages}
    jobs, skipped_pages = [], []
    for p in pages:
        if len(p["text"].strip()) < MIN_TEXT_CHARS:
            summary["skipped"] += 1
            skipped_pages.append(p["page"])
        elif is_cached(book_dir, p["page"], p["sha256"], pv):
            summary["cached"] += 1
        else:
            jobs.append(p)

    if skipped_pages:
        (book_dir / "skipped_pages.json").write_text(
            json.dumps(skipped_pages), encoding="utf-8")

    def _work(p):
        prev_tail = raw_by_no.get(p["page"] - 1, "")[-PREV_TAIL_CHARS:]
        # 通过模块属性调用，保证测试可 monkeypatch
        md = globals()["refine_page"](client, p["text"], prev_tail, sp)
        bad = verify_numbers(p["text"], md)
        save_page(book_dir, p["page"], md, {
            "sha256": p["sha256"], "prompt_version": pv,
            "model": MODEL, "verify_ok": not bad, "fallback": False,
        })
        return p["page"], bad

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_work, p): p for p in jobs}
        for fut in tqdm(as_completed(futures), total=len(futures),
                        desc=pdf_path.stem[:24], unit="页"):
            p = futures[fut]
            try:
                page_no, bad = fut.result()
                summary["done"] += 1
                if bad:
                    summary["verify_warn"] += 1
                    tqdm.write("  数字校验警告 第{}页：出现原文没有的数字 {}".format(page_no, bad))
            except Exception as e:  # noqa: BLE001 — 单页失败兜底，不中断整本
                summary["failed"] += 1
                tqdm.write("  第{}页失败，写入原始文本兜底: {}".format(p["page"], e))
                save_page(book_dir, p["page"], p["text"], {
                    "sha256": p["sha256"], "prompt_version": pv,
                    "model": MODEL, "verify_ok": True, "fallback": True,
                })
    return summary


def main():
    parser = argparse.ArgumentParser(description="LLM 重构 PDF 为结构化 Markdown")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--book", type=str, help="按文件名子串匹配单本 PDF")
    group.add_argument("--all", action="store_true", help="处理 data 目录全部 PDF")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--lang", choices=["en", "zh"], default="zh",
                        help="PDF 语言（zh=中文汉化版, en=英文官方版）")
    parser.add_argument("--data-dir", type=str, default=str(DATA_DIR))
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误：未设置环境变量 DEEPSEEK_API_KEY")
        sys.exit(1)

    from openai import OpenAI
    import httpx
    http_client = httpx.Client(proxy="http://127.0.0.1:7897")
    client = OpenAI(api_key=api_key, base_url=BASE_URL, http_client=http_client)

    pdfs = sorted(Path(args.data_dir).glob("*.pdf"))
    if args.book:
        pdfs = [p for p in pdfs if args.book in p.stem]
        if not pdfs:
            print("错误：没有文件名包含「{}」的 PDF".format(args.book))
            sys.exit(1)

    out_root = Path(args.out_dir)
    for pdf in pdfs:
        summary = process_book(client, pdf, out_root, workers=args.workers, lang=args.lang)
        print("完成 {book}: 新处理{done} 缓存{cached} 跳过{skipped} "
              "失败{failed} 数字警告{verify_warn} / 共{total}页".format(**summary))


if __name__ == "__main__":
    main()
