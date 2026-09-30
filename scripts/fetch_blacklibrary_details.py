"""scripts/fetch_blacklibrary_details.py — 抓黑图书馆全部 40K 单位的中文原生 datasheet。

/app/unit/detail 返回每单位完整中文 datasheet：属性(m/t/sv/w/ld/oc) + 能力 + 射击/近战武器
+ 军表构成。是补 units.name_zh（当前 62/1712）、从源头绕开 PDF 拍扁的权威中文结构数据。

用法：.\\.venv\\Scripts\\python.exe scripts\\fetch_blacklibrary_details.py --out data_blacklibrary\\details.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
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


def _source_id(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).strip():
        raise ValueError("detail identity has no stable source id")
    return str(value).strip()


def _normalized_name(value):
    return re.sub(r"[^a-z0-9]", "", value.lower()) if isinstance(value, str) else ""


def fetch_detail(sess, faction_zh, name_en, *, expected_id):
    """抓单个单位 detail。返回 (detail, failed)：

    failed=True 表示三次尝试全部异常（网络/解析/身份不符），区别于服务端正常响应但
    无 unitDetail 的 (None, False)——main 的熔断只统计前者。
    异常不再静默吞：打印类型与消息（requests 网络异常 / JSONDecodeError 响应
    非 JSON / KeyError-TypeError 结构不符，类型名足以区分）。
    """
    for attempt in range(3):
        try:
            response = sess.post(DETAIL_API, json={"gameId": 2, "topName": faction_zh,
                                 "unitName": name_en}, headers=HDR, timeout=25)
            response.raise_for_status()
            j = response.json()
            if not isinstance(j, dict) or str(j.get("code")) != "200" or "data" not in j:
                raise ValueError("detail response is not a successful source envelope")
            data = j["data"]
            if data is None:
                return None, False
            # Same-name responses can silently come from another faction. Validate
            # the envelope identity before parsing even an empty unitDetail body.
            if (not isinstance(data, dict)
                    or _source_id(data.get("id")) != _source_id(expected_id)
                    or data.get("gameId") != 2 or data.get("topName") != faction_zh
                    or not _normalized_name(name_en)
                    or _normalized_name(data.get("unitEnglishName")) != _normalized_name(name_en)):
                raise ValueError("detail response identity differs from the listed unit")
            if "unitDetail" not in data:
                raise ValueError("detail response lacks unitDetail")
            body = data["unitDetail"]
            if body is None or body == "":
                return None, False
            detail = json.loads(body) if isinstance(body, str) else body
            if not isinstance(detail, dict):
                raise ValueError("unitDetail must be an object")
            return detail, False
        except (requests.RequestException, json.JSONDecodeError,
                KeyError, TypeError, ValueError) as exc:
            print(f"  [detail失败 {attempt + 1}/3] {name_en}: "
                  f"{type(exc).__name__}: {exc}")
            time.sleep(1.0)
    return None, True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="db_sources/blacklibrary/details.json")
    args = ap.parse_args()
    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    prior = {}
    if out.exists():
        old_records = json.loads(out.read_text(encoding="utf-8"))
        if not isinstance(old_records, list):
            raise ValueError("Existing detail cache must be a list")
        for old in old_records:
            sid = _source_id(old.get("id"))
            if sid in prior:
                raise ValueError("Existing detail cache has duplicate source id: " + sid)
            prior[sid] = old

    sess = new_session()
    units = fetch_list(sess)
    with_en = [u for u in units if (u.get("unitEnglishName") or "").strip()]
    print(f"有英文名可抓 detail：{len(with_en)}/{len(units)}\n")

    # 熔断（评审 H 项）：连续 N 个单位全部三连失败 → 网络/接口大概率整体故障，
    # 提前中止并显眼报错，不再吞到底跑完全程假装正常。
    FAIL_BREAKER = 10
    results, ok, empty, failed_count, retained, consecutive_failed = [], 0, 0, 0, 0, 0
    seen = set()
    for i, u in enumerate(with_en, 1):
        sid = _source_id(u.get("id"))
        if sid in seen:
            raise ValueError("Fetched inventory has duplicate source id: " + sid)
        seen.add(sid)
        detail, failed = fetch_detail(sess, u.get("topName"), u.get("unitEnglishName"),
                                      expected_id=u.get("id"))
        status = "failed" if failed else ("captured" if detail else "source_empty")
        rec = {
            "id": u.get("id"),
            "faction_zh": u.get("topName"),
            "name_zh": u.get("unitName"),
            "name_en": u.get("unitEnglishName"),
            "score": u.get("unitScore"),
            "detail": detail,
            "detail_status": status,
            "authority": "third_party_community_source",
        }
        if detail and not failed:
            rec["provenance"] = {
                "status": "verified_capture", "endpoint": DETAIL_API,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "authority": "third_party_community_source",
            }
        elif sid in prior:
            previous = prior[sid]
            rec = dict(previous, detail_status=status, provenance={
                "status": "retained_previous_cache", "reason": status,
                "authority": "third_party_community_source",
                "previous": previous.get("provenance"),
            })
            retained += 1
        results.append(rec)
        if detail and not failed:
            ok += 1
        elif failed:
            failed_count += 1
        else:
            empty += 1
        consecutive_failed = consecutive_failed + 1 if failed else 0
        if consecutive_failed >= FAIL_BREAKER:
            partial = out.with_suffix(".partial.json")
            partial.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                               encoding="utf-8")
            raise SystemExit(
                "\n" + "!" * 60 +
                f"\n熔断中止：连续 {FAIL_BREAKER} 个单位三连失败（进度 {i}/{len(with_en)}），"
                f"\n网络/接口大概率整体故障，请检查连通性后重跑。"
                f"\n已抓到的部分结果暂存: {partial}（非完整数据，勿当正式产物用）\n" +
                "!" * 60
            )
        if i % 100 == 0:
            print(f"  {i}/{len(with_en)}  有detail={ok} 空={empty}")
        time.sleep(0.15)

    # A partial inventory or source-side deletion must not erase older evidence.
    for sid, old in prior.items():
        if sid not in seen:
            results.append(dict(old, provenance={
                "status": "retained_previous_cache", "reason": "absent_from_inventory",
                "authority": "third_party_community_source", "previous": old.get("provenance"),
            }))
            retained += 1
    temporary = out.with_suffix(out.suffix + ".tmp")
    temporary.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(out)

    print("\n===== 对账 =====")
    print(f"目标(有英文名): {len(with_en)}")
    print(f"实际抓取: {len(with_en)}   缓存记录: {len(results)}")
    print(f"验证 detail: {ok}   源空 detail: {empty}   失败: {failed_count}   保留旧缓存: {retained}")
    # 有属性表的
    with_stats = sum(1 for r in results if r["detail"] and r["detail"].get("属性"))
    print(f"含属性表(m/t/sv/w): {with_stats}")
    print(f"\n已存: {out}")


if __name__ == "__main__":
    main()
