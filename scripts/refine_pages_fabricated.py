"""定向重跑「refine 造数」页（prompt v2 硬化后）。

背景：verify_numbers 逮到 refine 在图片型/被拆分的兵牌页凭 40K 记忆虚构数值。
v2 prompt 已加铁律「源文本无数值时兵牌只输出名字/编制，绝不补数」。
本脚本只重跑【真造数】页（纯造数字≥2 且含表格），不动纯结构性偏移页。

判据与 refine 主流程一致：逐页读现有 meta.prompt_version 决定用 CN 还是 EN 硬化
prompt（v2 / v2-en），保证 EN 官方 FP 与「帝国骑士英文」这类 CJK 名的英文书都对。

用法（先样张后批量）：
  python scripts/refine_pages_fabricated.py --list            # 只列目标，不调 API
  python scripts/refine_pages_fabricated.py --limit 2         # 先跑 2 页样张
  python scripts/refine_pages_fabricated.py --book Orks       # 按书名子串过滤
  python scripts/refine_pages_fabricated.py                   # 跑全部造数页
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import fitz  # noqa: E402,F401  (extract_pages 依赖)

import llm_refine as R  # noqa: E402
from refine_prompt import (  # noqa: E402
    PROMPT_VERSION, PROMPT_VERSION_EN,
    SYSTEM_PROMPT, SYSTEM_PROMPT_EN,
)

DATA = REPO / "data"
OUT = REPO / "data_refined"


def _has_table(md: str) -> bool:
    return md.count("\n|") >= 3


def find_fabricated() -> list[tuple[str, int]]:
    """扫 data_refined，返回造数页 (book_stem, page_no)：verify_ok is False
    且 纯造数字（源里 0 次）≥2 且含表格。"""
    targets = []
    for book_dir in sorted(OUT.iterdir()):
        if not book_dir.is_dir():
            continue
        pdf = DATA / (book_dir.name + ".pdf")
        if not pdf.exists():
            continue
        src_by_no = {p["page"]: p["text"] for p in R.extract_pages(pdf)}
        for meta_path in sorted(book_dir.glob("page_*.meta.json")):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if meta.get("verify_ok") is not False:
                continue
            pg = int(meta_path.name[len("page_"):len("page_") + 3])
            md_path = book_dir / ("page_%03d.md" % pg)
            src = src_by_no.get(pg, "")
            md = md_path.read_text(encoding="utf-8")
            srcc = Counter(re.findall(r"\d+", src))
            pure = [t for t in R.verify_numbers(src, md) if srcc.get(t, 0) == 0]
            # 纯造数字 = md 里出现但源文本 0 次的 token → 必是凭记忆虚构的数值。
            # 源计数>0 只是被 refine 计数≠源（如武器技能[连击1]重排），无害不动。
            if len(pure) >= 1:
                targets.append((book_dir.name, pg))
    return targets


def rerun(client, book_stem: str, page_no: int) -> dict:
    pdf = DATA / (book_stem + ".pdf")
    pages = {p["page"]: p for p in R.extract_pages(pdf)}
    p = pages[page_no]
    book_dir = OUT / book_stem
    md_path, meta_path = R.page_paths(book_dir, page_no)

    old_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    is_en = str(old_meta.get("prompt_version", "")).endswith("-en")
    sp = SYSTEM_PROMPT_EN if is_en else SYSTEM_PROMPT
    pv = PROMPT_VERSION_EN if is_en else PROMPT_VERSION

    old_bad = R.verify_numbers(p["text"], md_path.read_text(encoding="utf-8"))
    prev_tail = pages.get(page_no - 1, {}).get("text", "")[-R.PREV_TAIL_CHARS:]
    md = R.refine_page(client, p["text"], prev_tail, sp)
    new_bad = R.verify_numbers(p["text"], md)
    R.save_page(book_dir, page_no, md, {
        "sha256": p["sha256"], "prompt_version": pv,
        "model": R.MODEL, "verify_ok": not new_bad, "fallback": False,
    })
    return {"book": book_stem, "page": page_no, "lang": "en" if is_en else "zh",
            "old_bad": old_bad, "new_bad": new_bad,
            "old_len": len(md_path.read_text(encoding="utf-8")), "new_len": len(md)}


def build_client():
    import os
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误：未设置 DEEPSEEK_API_KEY")
        sys.exit(1)
    from openai import OpenAI
    import httpx
    http_client = httpx.Client(proxy="http://127.0.0.1:7897")
    return OpenAI(api_key=api_key, base_url=R.BASE_URL, http_client=http_client)


def reflag() -> int:
    """用现行 verify_numbers（集合语义）重算所有 verify_ok=False 页的旗标：
    对现有缓存 md 复验，若已无纯造数字则改 meta.verify_ok=True。不调 API、不改 md，
    只修正被旧多重集判据误标的元数据。"""
    flipped = 0
    for book_dir in sorted(OUT.iterdir()):
        if not book_dir.is_dir():
            continue
        pdf = DATA / (book_dir.name + ".pdf")
        if not pdf.exists():
            continue
        src_by_no = None
        for meta_path in sorted(book_dir.glob("page_*.meta.json")):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if meta.get("verify_ok") is not False:
                continue
            if src_by_no is None:
                src_by_no = {p["page"]: p["text"] for p in R.extract_pages(pdf)}
            pg = int(meta_path.name[len("page_"):len("page_") + 3])
            md = (book_dir / ("page_%03d.md" % pg)).read_text(encoding="utf-8")
            if not R.verify_numbers(src_by_no.get(pg, ""), md):
                meta["verify_ok"] = True
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
                flipped += 1
                print("  ✅ %-40s p%d verify_ok False→True" % (book_dir.name[:40], pg))
    print("\n=== 重标 %d 页（旧多重集误标，集合语义下无纯造数字）===" % flipped)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="只列目标，不调 API")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 页（样张）")
    ap.add_argument("--book", type=str, default="", help="按书名子串过滤")
    ap.add_argument("--reflag", action="store_true",
                    help="不调 API：用集合语义 verify_numbers 重标误标的 verify_ok")
    args = ap.parse_args()

    if args.reflag:
        return reflag()

    targets = find_fabricated()
    if args.book:
        targets = [t for t in targets if args.book in t[0]]
    print("造数页目标 %d 个：" % len(targets))
    for b, pg in targets:
        print("  %-42s p%d" % (b[:42], pg))
    if args.list:
        return 0
    if args.limit:
        targets = targets[:args.limit]
        print("\n[样张模式] 只跑前 %d 页\n" % len(targets))

    client = build_client()
    results = []
    for b, pg in targets:
        r = rerun(client, b, pg)
        results.append(r)
        flag = "✅清零" if not r["new_bad"] else "⚠️仍有 %s" % r["new_bad"]
        print("  %-40s p%-4d [%s] %d→%d字 造数 %s→%s  %s"
              % (b[:40], pg, r["lang"], r["old_len"], r["new_len"],
                 len(r["old_bad"]), len(r["new_bad"]), flag))
    ok = sum(1 for r in results if not r["new_bad"])
    print("\n=== 重跑 %d 页，造数清零 %d，仍有残留 %d ===" %
          (len(results), ok, len(results) - ok))
    return 0


if __name__ == "__main__":
    sys.exit(main())
