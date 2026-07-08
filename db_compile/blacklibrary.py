"""blacklibrary：黑图书馆小程序开放 API 中英对照源。

blackforum.czmakj.com 后端无签名墙，直连枚举 40K 单位（中英名+分数+完整中文 datasheet）。
是补 aliases 中文别名层的权威源（比 LLM 机翻可靠：中英都是官方汉化组译名）。

requests 必须 trust_env=False——抓包时 Fiddler 会开系统代理并劫持导致 SSL 失败。
fetch 结果缓存到 db_sources/blacklibrary/units.json，供 --offline 重建复用。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional, Tuple

import requests

LIST_API = "https://blackforum.czmakj.com/app/manager/forum/unit/list"
GAME_ID_40K = 2
PAGE_SIZE = 50
_HDR = {"Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

DEFAULT_CACHE = Path("db_sources/blacklibrary/units.json")


def fetch_unit_list() -> List[dict]:
    """全量翻页拉 40K 单位。按页是否满判结束（不依赖易失的 total 字段，防早停）。"""
    sess = requests.Session()
    sess.trust_env = False
    units: List[dict] = []
    seen = set()
    total = None
    page = 1
    while page <= 60:
        for attempt in range(3):
            try:
                j = sess.post(LIST_API, json={"pageNum": page, "pageSize": PAGE_SIZE,
                              "gameId": GAME_ID_40K, "unitName": ""},
                              headers=_HDR, timeout=25).json()
                data = j.get("data") or []
                if total is None and j.get("total"):
                    total = j.get("total")
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1.5)
        if not data:
            break
        for u in data:
            if u.get("id") not in seen:
                seen.add(u.get("id"))
                units.append(u)
        if len(data) < PAGE_SIZE:
            break
        page += 1
    return units


def load_or_fetch_units(cache_path: Optional[Path] = None,
                        offline: bool = False) -> Tuple[List[dict], str]:
    """在线抓取并刷新缓存；离线或抓取失败时读缓存。返回 (units, 来源说明)。"""
    cache_path = Path(cache_path) if cache_path else DEFAULT_CACHE
    if offline:
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8")), "缓存(offline)"
        return [], "无缓存(offline)"
    try:
        units = fetch_unit_list()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(units, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        return units, "在线抓取"
    except Exception as exc:
        if cache_path.exists():
            return (json.loads(cache_path.read_text(encoding="utf-8")),
                    f"抓取失败复用缓存({type(exc).__name__})")
        raise


def units_to_pairs(units: List[dict]) -> List[Tuple[str, str]]:
    """(unitName 中文, unitEnglishName 英文) 对。"""
    return [(u.get("unitName") or "", u.get("unitEnglishName") or "") for u in units]
