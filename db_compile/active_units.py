"""db_compile/active_units.py — 「现役单位」口径的**唯一真源**（审查 R2-M1）。

在售 ≠ 在 MFM 表里。库里 1715 条来自 Wahapedia 全量，其中数百条是 Legends /
福基世界 / 退环境条目（Karandras、Vampire Raider、Secutarii…），比赛里摆不上桌。
判现役必须 **MFM ∪ 黑图书馆** 两个来源取并集：官方 MFM 页只列 30 个阵营、
**没有 Harlequins 那一组**（实测 aeldari 81 条里无 Troupe / Solitaire / Death Jester），
只按 MFM 判会把在售单位误归档；黑图书馆收录面≈在售面，正好补上这个洞。

这个口径此前有两套。宽的那份在 `web_api/codex.py`（对的，docstring 写明了理由），
窄的那份（只看 MFM）长在 `db_compile/zh_weapons.py` 与 `db_compile/dup_units.py`，
实测比宽口径**少 141 个在售单位**。窄口径的代价不是当天算错——两边当时都是 100%——
而是 `missing_terms()` 这张「还要人工补译多少」的工单**永远看不到那 141 个单位的缺译**，
`coverage_report()` 的百分比也是在窄池上算的：典型的「100% 可能只是比得少」。

全库只准有这一份实现。要改口径就改这里，别在调用处再长一份。
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Set

_log = logging.getLogger(__name__)


def mfm_priced_unit_ids(conn: sqlite3.Connection) -> Set[str]:
    """`points_json` 里带 `mfm` 溯源块的单位 = 出现在官方现行 MFM 点数表里。"""
    ids: Set[str] = set()
    for uid, pj in conn.execute("SELECT id, points_json FROM units"):
        try:
            if pj and (json.loads(pj) or {}).get("mfm"):
                ids.add(uid)
        except (json.JSONDecodeError, TypeError):
            continue
    return ids


def blacklibrary_unit_ids(conn: sqlite3.Connection) -> Set[str]:
    """被黑图书馆中文层收录的单位（收录面≈在售面）。表缺失时抛，见 `active_unit_ids`。"""
    return {uid for (uid,) in conn.execute("SELECT canonical_id FROM unit_zh_detail")
            if uid}


def active_unit_ids(conn: sqlite3.Connection) -> Set[str]:
    """现役单位 id 集合 = MFM 点数表 ∪ 黑图书馆收录。

    `unit_zh_detail` 缺失时**故意让 sqlite3.OperationalError 抛出去**，不退回
    「仅 MFM」：那正是本条 finding 的窄口径，静默退回等于把「库没建全」伪装成
    「这些单位不在售」。调用方该做的是报错或 503，不是接受一个悄悄变窄的池子。
    """
    ids = mfm_priced_unit_ids(conn)
    ids |= blacklibrary_unit_ids(conn)
    return ids
