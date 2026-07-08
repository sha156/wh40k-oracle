"""scripts/import_blacklibrary_aliases.py — 从黑图书馆小程序开放 API 拉 40K 单位中英对照，
灌进 aliases 表（source='blackforum'）作为权威中文别名桥。

黑图书馆后端无签名墙，直连即可（requests 需 trust_env=False 绕开系统代理，
否则抓包时 Fiddler 开的 System Proxy 会劫持并 SSL 失败）。

用法（项目 venv）：
  .\.venv\Scripts\python.exe scripts\import_blacklibrary_aliases.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Tuple

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent.tools import DB_PATH
from db_compile.aliases import populate_blackforum_aliases

API = "https://blackforum.czmakj.com/app/manager/forum/unit/list"
GAME_ID_40K = 2
PAGE_SIZE = 50
HDR = {"Content-Type": "application/json",
       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_all_units() -> List[dict]:
    """全量翻页拉 40K 单位。对账官方 total，报差额。"""
    sess = requests.Session()
    sess.trust_env = False  # 绕开系统代理（Fiddler System Proxy）
    units: List[dict] = []
    seen_ids = set()
    total = None
    page = 1
    while page <= 60:
        body = {"pageNum": page, "pageSize": PAGE_SIZE,
                "gameId": GAME_ID_40K, "unitName": ""}
        data = None
        for attempt in range(3):
            try:
                j = sess.post(API, json=body, headers=HDR, timeout=25).json()
                data = j.get("data") or []
                if total is None:
                    total = j.get("total") or j.get("totalCount")
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"  ⚠️ page {page} 三次失败: {exc}")
                time.sleep(1.5)
        if not data:
            break
        new = 0
        for u in data:
            uid = u.get("id")
            if uid in seen_ids:
                continue
            seen_ids.add(uid)
            units.append(u)
            new += 1
        print(f"  page {page}: +{new}（累计 {len(units)}/{total}）")
        if len(data) < PAGE_SIZE:  # 最后一页（不依赖易失的 total 字段）
            break
        page += 1

    print(f"\n对账：官方 total={total}  实际抓取={len(units)}  差额={(total or 0) - len(units)}")
    return units


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="只抓取+匹配统计，不写库")
    args = ap.parse_args()

    print("=" * 60)
    print("黑图书馆 → aliases 中文别名桥导入")
    print("=" * 60)

    units = fetch_all_units()
    pairs: List[Tuple[str, str]] = [
        (u.get("unitName") or "", u.get("unitEnglishName") or "") for u in units
    ]

    if args.dry_run:
        # 干跑：只统计匹配数，不写
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        en2id = {(n or "").strip().lower(): c
                 for c, n in conn.execute("SELECT id, name_en FROM units") if n}
        conn.close()
        matched = sum(1 for zh, en in pairs if en.strip() and en.strip().lower() in en2id)
        print(f"\n[dry-run] 中英对={len(pairs)}  可匹配 units.name_en={matched}  未写库")
        return

    stats = populate_blackforum_aliases(DB_PATH, pairs)
    print("\n===== 写库结果（source='blackforum'）=====")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\n✅ 已写入 {stats['matched']} 条中文别名到 {DB_PATH}")


if __name__ == "__main__":
    main()
