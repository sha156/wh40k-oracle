"""scripts/fetch_blacklibrary_details.py — 抓黑图书馆全部 40K 单位的中文原生 datasheet。

/app/unit/detail 返回每单位完整中文 datasheet：属性(m/t/sv/w/ld/oc) + 能力 + 射击/近战武器
+ 军表构成。是补 units.name_zh（当前 62/1712）、从源头绕开 PDF 拍扁的权威中文结构数据。

用法：.\\.venv\\Scripts\\python.exe scripts\\fetch_blacklibrary_details.py --out data_blacklibrary\\details.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

LIST_API = "https://blackforum.czmakj.com/app/manager/forum/unit/list"
DETAIL_API = "https://blackforum.czmakj.com/app/unit/detail"
HDR = {"Content-Type": "application/json",
       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def new_session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    return s


def fetch_list(sess) -> list:
    """按页是否满判断结束（空页或不满 pageSize=最后一页），不依赖易失的 total 字段。"""
    units, seen, total, page = [], set(), None, 1
    while page <= 60:
        j = sess.post(LIST_API, json={"pageNum": page, "pageSize": 50,
                      "gameId": 2, "unitName": ""}, headers=HDR, timeout=25).json()
        data = j.get("data") or []
        if total is None and j.get("total"):
            total = j.get("total")
        if not data:
            break
        for u in data:
            if u.get("id") not in seen:
                seen.add(u.get("id"))
                units.append(u)
        if len(data) < 50:  # 最后一页
            break
        page += 1
    print(f"单位列表：{len(units)}/{total}")
    if total and len(units) != total:
        print(f"  ⚠️ 与官方 total 不符，差额 {total - len(units)}")
    return units


def fetch_detail(sess, faction_zh, name_en):
    for attempt in range(3):
        try:
            j = sess.post(DETAIL_API, json={"gameId": 2, "topName": faction_zh,
                          "unitName": name_en}, headers=HDR, timeout=25).json()
            data = j.get("data")
            if isinstance(data, dict) and data.get("unitDetail"):
                return json.loads(data["unitDetail"])
            return None
        except Exception:
            time.sleep(1.0)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data_blacklibrary/details.json")
    args = ap.parse_args()
    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)

    sess = new_session()
    units = fetch_list(sess)
    with_en = [u for u in units if (u.get("unitEnglishName") or "").strip()]
    print(f"有英文名可抓 detail：{len(with_en)}/{len(units)}\n")

    results, ok, empty = [], 0, 0
    for i, u in enumerate(with_en, 1):
        detail = fetch_detail(sess, u.get("topName"), u.get("unitEnglishName"))
        rec = {
            "id": u.get("id"),
            "faction_zh": u.get("topName"),
            "name_zh": u.get("unitName"),
            "name_en": u.get("unitEnglishName"),
            "score": u.get("unitScore"),
            "detail": detail,
        }
        results.append(rec)
        if detail:
            ok += 1
        else:
            empty += 1
        if i % 100 == 0:
            print(f"  {i}/{len(with_en)}  有detail={ok} 空={empty}")
        time.sleep(0.15)

    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== 对账 =====")
    print(f"目标(有英文名): {len(with_en)}")
    print(f"实际抓取: {len(results)}")
    print(f"含 detail: {ok}   空 detail: {empty}")
    # 有属性表的
    with_stats = sum(1 for r in results if r["detail"] and r["detail"].get("属性"))
    print(f"含属性表(m/t/sv/w): {with_stats}")
    print(f"\n已存: {out}")


if __name__ == "__main__":
    main()
