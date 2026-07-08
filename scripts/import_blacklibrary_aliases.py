"""scripts/import_blacklibrary_aliases.py — 从黑图书馆开放 API 拉 40K 单位中英对照，
灌进 aliases 表（source='blackforum'）作为权威中文别名桥。

抓取逻辑复用 db_compile.blacklibrary（update 管线的 stage_aliases_blackforum 同源）。
本脚本供手动单独跑 / --dry-run 看匹配统计。

用法（项目 venv）：
  .\\.venv\\Scripts\\python.exe scripts\\import_blacklibrary_aliases.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent.tools import DB_PATH
from db_compile.aliases import populate_blackforum_aliases
from db_compile.blacklibrary import load_or_fetch_units, units_to_pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只抓取+匹配统计，不写库")
    args = ap.parse_args()

    print("=" * 60)
    print("黑图书馆 → aliases 中文别名桥导入")
    print("=" * 60)

    units, source = load_or_fetch_units()
    print(f"单位：{len(units)}（来源：{source}）")
    pairs = units_to_pairs(units)

    if args.dry_run:
        conn = sqlite3.connect(str(DB_PATH))
        en2id = {(n or "").strip().lower(): c
                 for c, n in conn.execute("SELECT id, name_en FROM units") if n}
        conn.close()
        matched = sum(1 for _zh, en in pairs if en.strip() and en.strip().lower() in en2id)
        print(f"\n[dry-run] 中英对={len(pairs)}  可匹配 units.name_en={matched}  未写库")
        return

    stats = populate_blackforum_aliases(DB_PATH, pairs)
    print("\n===== 写库结果（source='blackforum'）=====")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\n✅ 已写入 {stats['matched']} 条中文别名到 {DB_PATH}")


if __name__ == "__main__":
    main()
