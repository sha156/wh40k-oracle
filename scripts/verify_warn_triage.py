"""verify_warn 逐页分诊助手（只读，不联网、不调 LLM）。

对每个 verify_warn 页，重算 verify_numbers 的「超额数字 token」，并给出：
  - 每个 bad token 的 源计数 vs md 计数
  - 该 token 在 refined markdown 中每次出现的所在行（判断是否结构性/造数）
  - 可选 --source 打印原始 PDF 页文本

用法：
  python scripts/verify_warn_triage.py               # 汇总全部 verify_warn 页的 bad token
  python scripts/verify_warn_triage.py <书stem> <页>  # 单页详情
  python scripts/verify_warn_triage.py <书stem> <页> --source  # 附原文
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import fitz  # noqa: E402
from llm_refine import extract_pages, page_paths, verify_numbers  # noqa: E402

DATA_DIR = REPO / "data"
OUT_DIR = REPO / "data_refined"
RECON = REPO / "scratchpad_reconcile.json"


def _bad_detail(source: str, markdown: str) -> list[dict]:
    src_counts = Counter(re.findall(r"\d+", source))
    md_counts = Counter(re.findall(r"\d+", markdown))
    md_lines = markdown.splitlines()
    out = []
    for tok in verify_numbers(source, markdown):
        lines = [i + 1 for i, ln in enumerate(md_lines)
                 if re.search(r"(?<!\d)" + re.escape(tok) + r"(?!\d)", ln)]
        out.append({"tok": tok, "src": src_counts.get(tok, 0),
                    "md": md_counts.get(tok, 0), "lines": lines})
    return out


def _page_source_md(stem: str, page_no: int):
    pdf = DATA_DIR / (stem + ".pdf")
    pages = {p["page"]: p for p in extract_pages(pdf)}
    src = pages[page_no]["text"]
    md_path, _ = page_paths(OUT_DIR / stem, page_no)
    md = md_path.read_text(encoding="utf-8")
    return src, md


def one(stem: str, page_no: int, show_source: bool) -> None:
    src, md = _page_source_md(stem, page_no)
    detail = _bad_detail(src, md)
    print(f"\n===== {stem}  页{page_no} =====")
    print(f"源文本 {len(src)} 字 / md {len(md)} 字 / bad token {len(detail)} 个\n")
    md_lines = md.splitlines()
    for d in detail:
        print(f"  [{d['tok']}]  源出现 {d['src']} 次 / md 出现 {d['md']} 次  行 {d['lines']}")
        for ln in d["lines"]:
            print(f"      L{ln}: {md_lines[ln-1].strip()[:110]}")
    if show_source:
        print("\n----- 原始 PDF 页文本 -----")
        print(src)


def summary() -> None:
    d = json.loads(RECON.read_text(encoding="utf-8"))
    for b in d["gap_books"]:
        vw = b["pages"].get("verify_warn", [])
        for pg in vw:
            src, md = _page_source_md(b["book"], pg)
            detail = _bad_detail(src, md)
            toks = ", ".join(f"{x['tok']}({x['src']}→{x['md']})" for x in detail)
            print(f"{b['book'][:38]:38} p{pg:<4} bad={len(detail):2} | {toks[:90]}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        summary()
    else:
        one(args[0], int(args[1]), "--source" in sys.argv)
