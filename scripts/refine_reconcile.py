"""data_refined 缓存全量对账（T2）：每本 PDF 物理页 vs 缓存页，逐页分类，报差额。

分类（一页只落一类，优先级自上而下）：
  ok         —— 缓存存在、sha256 与当前 PDF 一致、非 fallback（无需动作）
  skipped    —— 源文本 < MIN_TEXT_CHARS（空白/图页，合法跳过，非缺口）
  missing    —— 源有实义文本但无 .md 缓存（真·缺口，需 refine）
  fallback   —— meta.fallback=True（LLM 当时失败写了兜底原文，需重跑）
  stale      —— sha256 与当前 PDF 文本不一致（PDF 或提取变了，需重跑）
  truncated  —— 缓存 .md 相对源文本异常短（疑精炼截断，需人工核/重跑）
  verify_warn—— meta.verify_ok=False（数字校验未过，疑造数，需人工核）

缺口 = missing + fallback + stale（应 refine）；suspect = truncated + verify_warn（应人工核）。
纯审计，不联网、不调 LLM。用法：python scripts/refine_reconcile.py [输出json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import fitz  # noqa: E402
from llm_refine import MIN_TEXT_CHARS, extract_pages, page_paths  # noqa: E402

DATA_DIR = REPO / "data"
OUT_DIR = REPO / "data_refined"
# 截断判定：缓存 md 去空白后长度 < 源文本长度 × 此比例，且源文本够长（>阈值）才算疑截断。
# 精炼后的结构化 markdown 通常与源相当或更长；显著更短多为截断/丢内容。
TRUNC_RATIO = 0.30
TRUNC_MIN_SRC = 300


def audit_book(pdf_path: Path) -> dict:
    book_dir = OUT_DIR / pdf_path.stem
    pages = extract_pages(pdf_path)
    buckets = {k: [] for k in
               ("ok", "skipped", "missing", "fallback", "stale",
                "truncated", "verify_warn")}
    for p in pages:
        no, text, sha = p["page"], p["text"], p["sha256"]
        if len(text.strip()) < MIN_TEXT_CHARS:
            buckets["skipped"].append(no)
            continue
        md_path, meta_path = page_paths(book_dir, no)
        if not md_path.exists():
            buckets["missing"].append(no)
            continue
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}
        if meta.get("fallback", False):
            buckets["fallback"].append(no)
            continue
        if meta.get("sha256") and meta.get("sha256") != sha:
            buckets["stale"].append(no)
            continue
        md_len = len(md_path.read_text(encoding="utf-8").strip())
        if len(text.strip()) >= TRUNC_MIN_SRC and md_len < TRUNC_RATIO * len(text.strip()):
            buckets["truncated"].append(no)
            continue
        if meta.get("verify_ok") is False:
            buckets["verify_warn"].append(no)
            continue
        buckets["ok"].append(no)
    return {"book": pdf_path.stem, "pdf_pages": len(pages),
            "counts": {k: len(v) for k, v in buckets.items()},
            "pages": {k: v for k, v in buckets.items()
                      if v and k not in ("ok", "skipped")}}


def main() -> int:
    pdfs = sorted(p for p in DATA_DIR.glob("*.pdf"))
    reports, gap_books = [], []
    tot = {k: 0 for k in ("missing", "fallback", "stale", "truncated", "verify_warn")}
    no_cache = []
    for pdf in pdfs:
        if not (OUT_DIR / pdf.stem).is_dir():
            no_cache.append(pdf.stem)
            continue
        r = audit_book(pdf)
        reports.append(r)
        c = r["counts"]
        gaps = c["missing"] + c["fallback"] + c["stale"]
        suspect = c["truncated"] + c["verify_warn"]
        for k in tot:
            tot[k] += c[k]
        if gaps or suspect:
            gap_books.append(r)
            flag = "🔴" if gaps else "🟡"
            det = "；".join(f"{k} {r['pages'][k]}" for k in
                           ("missing", "fallback", "stale", "truncated", "verify_warn")
                           if k in r["pages"])
            print(f"{flag} {r['book'][:40]:40} 页{r['pdf_pages']:3} | {det}")

    print("\n=== 全库对账汇总 ===")
    print(f"扫描 {len(pdfs)} 本 PDF，{len(reports)} 本有缓存目录，"
          f"{len(no_cache)} 本无缓存目录")
    print(f"缺口(应 refine)：missing {tot['missing']} / fallback {tot['fallback']} / "
          f"stale {tot['stale']}")
    print(f"疑点(应人工核)：truncated {tot['truncated']} / verify_warn {tot['verify_warn']}")
    if no_cache:
        print(f"无缓存目录的 PDF（{len(no_cache)}）："
              + "、".join(s[:24] for s in no_cache[:12])
              + ("…" if len(no_cache) > 12 else ""))

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "refine_reconcile.json"
    out.write_text(json.dumps(
        {"summary": {"pdfs": len(pdfs), "with_cache": len(reports),
                     "no_cache": no_cache, "totals": tot},
         "gap_books": gap_books, "all": reports},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n明细写入 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
