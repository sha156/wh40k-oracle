"""按对账结果补齐 refine 缺口（T2）：missing 页直接 refine，truncated 页删缓存后强制重跑。

lang（决定 prompt 版本）从该书已缓存页的 meta.prompt_version 推断（v1-en→en / v1→zh），
无缓存则按书名是否含 CJK 猜。stale/fallback 页 process_book 的 is_cached 自会重跑，无需特判。
读环境变量 DEEPSEEK_API_KEY（.env 自动加载），走 Clash 代理。

用法：python scripts/refine_gaps.py <reconcile.json>   # 先跑 refine_reconcile.py 产出该 json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
os.chdir(REPO)

# 加载 .env（llm_refine 只读环境变量，自身不解析 .env）
env = REPO / ".env"
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import httpx  # noqa: E402
from openai import OpenAI  # noqa: E402

import llm_refine as R  # noqa: E402
from llm_refine import _has_cjk, page_paths  # noqa: E402

OUT = REPO / "data_refined"


def book_lang(book_dir: Path) -> str:
    """从已缓存页的 prompt_version 推断 lang；无缓存按书名 CJK 猜。"""
    c = Counter()
    for mp in book_dir.glob("page_*.meta.json"):
        try:
            c[json.loads(mp.read_text(encoding="utf-8")).get("prompt_version")] += 1
        except (json.JSONDecodeError, OSError):
            pass
    if c:
        return "en" if c.most_common(1)[0][0] == R.PROMPT_VERSION_EN else "zh"
    return "zh" if _has_cjk(book_dir.name) else "en"


def main() -> int:
    rec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    gap_books = rec["gap_books"]
    # 只处理有 missing 或 truncated 的书（verify_warn 是质量疑点，另行人工核，不在此重跑）
    targets = [b for b in gap_books
               if b["counts"]["missing"] or b["counts"]["truncated"]]
    if not targets:
        print("无 missing/truncated 缺口，无需补齐。")
        return 0

    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=R.BASE_URL,
                    http_client=httpx.Client(proxy="http://127.0.0.1:7897"))

    grand = {"done": 0, "cached": 0, "failed": 0, "verify_warn": 0}
    for b in targets:
        stem = b["book"]
        pdf = REPO / "data" / (stem + ".pdf")
        book_dir = OUT / stem
        if not pdf.exists():
            print(f"⚠️ 跳过 {stem}：PDF 不存在")
            continue
        lang = book_lang(book_dir)
        trunc = b["pages"].get("truncated", [])
        # 截断页删缓存 → process_book 的 is_cached 会重跑它们
        for no in trunc:
            for p in page_paths(book_dir, no):
                p.unlink(missing_ok=True)
        miss = b["counts"]["missing"]
        print(f"\n▶ {stem}（lang={lang}）：missing {miss} + truncated {len(trunc)} 待补")
        summ = R.process_book(client, pdf, OUT, workers=4, lang=lang)
        for k in grand:
            grand[k] += summ.get(k, 0)
        print(f"  完成 done={summ['done']} cached={summ['cached']} "
              f"failed={summ['failed']} verify_warn={summ['verify_warn']}")

    print(f"\n=== 补齐汇总 ===")
    print(f"done {grand['done']} / cached {grand['cached']} / "
          f"failed {grand['failed']} / verify_warn {grand['verify_warn']}")
    if grand["failed"]:
        print("⚠️ 有失败页（写了 fallback 原文），需复查后重跑")
    return 0


if __name__ == "__main__":
    sys.exit(main())
