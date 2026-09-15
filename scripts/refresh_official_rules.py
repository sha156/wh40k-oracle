"""Apply a reviewed official PDF comparison and reuse unchanged refined pages.

Run from the repository root with --comparison <comparison.json>. Only entries
with an explicit existing path are replaced; Universal Rules Updates is added.
Original PDFs and refined books are preserved in a unique local backup folder.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile


def refresh(comparison):
    import httpx
    from dotenv import load_dotenv
    from openai import OpenAI
    from llm_refine import extract_pages, process_book, page_paths

    load_dotenv()
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required for source-faithful refinement")
    root = Path.cwd().resolve()
    data_root = (root / "data").resolve()
    refined = root / "data_refined"
    backup = Path(tempfile.mkdtemp(prefix="wh40k-before-rules-refresh-"))
    report = {"backup": str(backup), "books": []}
    report_path = comparison.parent / "refresh-report.json"
    with httpx.Client(proxy=os.environ.get("HTTPS_PROXY"), timeout=120) as http:
        client = OpenAI(api_key=key, base_url="https://api.deepseek.com", http_client=http, max_retries=0)
        for item in json.loads(comparison.read_text(encoding="utf-8")):
            existing = item.get("existing")
            if item["title"] == "Universal Rules Updates":
                existing = "data/Universal Rules Updates.pdf"
            elif not existing or not item.get("changed_pages"):
                continue
            target = (root / existing).resolve()
            if not target.is_relative_to(data_root) or target.suffix.lower() != ".pdf":
                raise ValueError("Target must be a PDF within data/")
            raw = (root / item["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("Downloaded PDF hash mismatch")
            book_dir = refined / target.stem
            old_cache = {}
            if target.exists():
                shutil.copy2(target, backup / target.name)
                if book_dir.exists():
                    shutil.copytree(book_dir, backup / target.stem)
                    for page in extract_pages(target):
                        md, meta = page_paths(book_dir, page["page"])
                        if md.exists() and meta.exists():
                            old_cache[page["sha256"]] = (md.read_bytes(), meta.read_bytes())
            target.write_bytes(raw)
            book_dir.mkdir(parents=True, exist_ok=True)
            # Move cached content by source hash, not by old page number.
            for page in extract_pages(target):
                if page["sha256"] in old_cache:
                    md, meta = page_paths(book_dir, page["page"])
                    body, metadata = old_cache[page["sha256"]]
                    md.write_bytes(body)
                    meta.write_bytes(metadata)
            summary = process_book(client, target, refined, workers=4, lang="en", reuse_source_cache=True)
            report["books"].append(dict(summary, source_url=item["url"], sha256=item["sha256"]))
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(summary, ensure_ascii=False), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    args = parser.parse_args()
    refresh(args.comparison)
